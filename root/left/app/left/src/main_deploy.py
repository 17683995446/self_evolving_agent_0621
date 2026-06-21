"""生产部署入口"""
import os
import signal
import sys
import time
from typing import Any, Dict, Optional

from root.left.app.left.src.core_mod.action_executor import ActionExecutor
from root.left.app.left.src.core_mod.dashboard import Dashboard
from root.left.app.left.src.core_mod.effect_verifier import EffectVerifier
from root.left.app.left.src.core_mod.recommendation_engine import RecommendationEngine
from root.left.app.left.src.core_mod.phase_one import PhaseOneCore
from root.left.app.left.src.core_mod.phase_two import PhaseTwoCore
from root.left.app.left.src.core_mod.phase_three import PhaseThreeCore
from root.left.app.left.src.deploy_server import DeployServer
from root.left.app.left.src.utils_main.agent_mixin import ClosableAgentMixin
from root.left.app.left.src.utils_main.config_loader import ConfigLoader
from root.left.app.left.src.utils_main.exceptions import AgentException
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import ConfigValidator


class ProductionAgent(ClosableAgentMixin):
    """生产级自驱进化Agent"""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        logger.debug("[ProductionAgent.__init__] start")
        super().__init__()
        if config is None:
            env = os.environ.get("AGENT_ENV", "dev")
            config = ConfigLoader.load_config(env)
        ConfigValidator.validate_config(config)
        self.config = config
        self._init_phases(config)
        self.loop_count = 0
        self.running = False
        self.server: Optional[DeployServer] = None
        self._setup_signal_handlers()
        logger.info("ProductionAgent initialized", "main")

    def _init_phases(self, config: Dict[str, Any]) -> None:
        self.phase_one = PhaseOneCore(config.get("phase1", {}))
        self.phase_two = PhaseTwoCore(config.get("phase2", {}))
        self.phase_three = PhaseThreeCore(config.get("phase3", {}))
        self.action_executor = ActionExecutor(config.get("action_executor", {"dry_run": True}))
        self.effect_verifier = EffectVerifier(config.get("effect_verifier", {}))
        self.recommendation_engine = RecommendationEngine(config.get("recommendation", {}))
        self.dashboard = Dashboard(config.get("dashboard", {}))

    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
        logger.debug("[ProductionAgent._setup_signal_handlers] done")

    def _handle_signal(self, signum: int, frame: Any) -> None:
        logger.info(f"[ProductionAgent._handle_signal] received signal={signum}")
        self.stop()

    def start_server(self) -> None:
        hc = self.config.get("health_check", {})
        if hc.get("enabled", False):
            port = int(hc.get("port", 8080))
            self.server = DeployServer(port)
            self.server.start(self)
            logger.info(f"Health server started on port {port}", "main")

    def run(self, max_loops: Optional[int] = None) -> None:
        self.running = True
        self.start_server()
        logger.info(f"Agent run started max_loops={max_loops}", "main")
        while self.running:
            self._wait_if_paused()
            if not self.running:
                break
            self._run_single_loop()
            if self._should_stop(max_loops):
                self.running = False
                break
            self._sleep()
        logger.info("Agent run completed", "main")

    def _should_stop(self, max_loops: Optional[int]) -> bool:
        if max_loops is None:
            return False
        return self.loop_count >= max_loops

    def _sleep(self) -> None:
        interval = self.config.get("loop_interval", 5.0)
        time.sleep(interval)

    def _run_single_loop(self) -> None:
        self.loop_count += 1
        logger.info(f"=== Loop {self.loop_count} started ===", "main")
        phase1_result = self.phase_one.step()
        performance = phase1_result.get("performance", 0.0)
        logger.info(f"Phase1 completed performance={performance:.4f}", "main")
        self.effect_verifier.capture_before("performance", performance)
        if self.phase_two.should_pause(phase1_result):
            logger.warning("Pause triggered by safety gap", "main")
            return
        phase2_result = self._run_phase_two(phase1_result)
        logger.info(f"Phase2 completed tasks={phase2_result.get('task_pool_snapshot', {}).get('total', 0)}", "main")
        self._execute_selected_task(phase2_result)
        self.effect_verifier.capture_after("performance", performance)
        phase3_result = self._run_phase_three(phase1_result, phase2_result)
        logger.info(f"Phase3 completed should_rollback={phase3_result.get('should_rollback', False)}", "main")
        self._handle_rollback(phase3_result)
        logger.info(f"=== Loop {self.loop_count} completed ===", "main")

    def _execute_selected_task(self, phase2_result: Dict[str, Any]) -> None:
        decision = phase2_result.get("decision", {})
        selected = decision.get("selected_task")
        if selected and isinstance(selected, dict):
            task_id = selected.get("task_id")
            if task_id:
                from root.left.app.left.src.utils_main.constants import TaskStatus
                payload = selected.get("payload", {})
                action_result = self.action_executor.execute(payload)
                status = TaskStatus.COMPLETED if action_result.success else TaskStatus.FAILED
                updated = self.phase_two.task_pool.update_task_status(task_id, status)
                logger.info(
                    f"Task executed: {task_id} updated={updated} success={action_result.success} type={action_result.action_type}",
                    "main",
                )

    def _run_phase_two(self, phase1_result: Dict[str, Any]) -> Dict[str, Any]:
        return self.phase_two.step(phase1_result, self.loop_count, 0.0, 0.0)

    def _run_phase_three(self, phase1_result: Dict[str, Any], phase2_result: Dict[str, Any]) -> Dict[str, Any]:
        return self.phase_three.step(self.config, phase1_result, phase2_result)

    def _handle_rollback(self, phase3_result: Dict[str, Any]) -> None:
        if phase3_result.get("should_rollback"):
            logger.warning("Rollback triggered", "main")
            snapshot = phase3_result.get("best_snapshot")
            if snapshot:
                new_config = snapshot.get("config", self.config)
                self.config = new_config
                self._init_phases(new_config)
                logger.info("Config rolled back and phases reinitialized", "main")

    def generate_dashboard_report(
        self,
        phase1_result: Dict[str, Any],
        phase2_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        state = phase1_result.get("state", {})
        drive_state = phase1_result.get("drive_state", {})
        effect_summary = self.effect_verifier.get_summary()
        recs = self.recommendation_engine.generate(state, drive_state, effect_summary)
        report = self.dashboard.build_report(
            state,
            drive_state,
            self.recommendation_engine.to_dict_list(recs),
            effect_summary,
            phase2_result.get("task_pool_snapshot", {}),
            self.loop_count,
        )
        return report

    def stop(self) -> None:
        logger.info("Agent stopping...", "main")
        self.running = False
        if self.server is not None:
            self.server.stop()
            self.server = None
        logger.info("Agent stopped", "main")

    def close(self) -> None:
        """关闭 Agent 并释放所有资源"""
        logger.info("ProductionAgent closing", "main")
        super().close()
        logger.info("ProductionAgent closed", "main")

    def get_state(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "loop_count": self.loop_count,
            "config": self.config,
        }


def main() -> None:
    agent = ProductionAgent()
    try:
        max_loops = agent.config.get("max_loops")
        if max_loops == 0:
            max_loops = None
        agent.run(max_loops=max_loops)
    except AgentException as error:
        logger.error(f"Agent error: {error}", "main", exc_info=True)
        agent.stop()
        sys.exit(1)
    except Exception as error:
        logger.error(f"Unexpected error: {error}", "main", exc_info=True)
        agent.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
