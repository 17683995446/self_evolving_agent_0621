"""自愈动作 Playbook

把抽象的推荐（如“缓存太多”）翻译成具体可执行的动作步骤，
并通过 ActionExecutor + ApprovalGate + EffectVerifier 组成完整闭环。
"""
from string import Template
from typing import Any, Dict, List, Optional

from root.left.app.left.src.core_mod.action_executor import ActionExecutor
from root.left.app.left.src.core_mod.effect_verifier import EffectVerifier
from root.left.app.left.src.utils_main.logger import logger


class ActionPlaybook:
    """一个 Playbook 对应一类自愈场景"""

    def __init__(
        self,
        playbook_id: str,
        name: str,
        triggers: List[str],
        steps: List[Dict[str, Any]],
        effect_metric: Optional[str] = None,
        effect_better: str = "lower",
    ) -> None:
        self.playbook_id = playbook_id
        self.name = name
        self.triggers = triggers
        self.steps = steps
        self.effect_metric = effect_metric
        self.effect_better = effect_better

    def matches(self, recommendation: Dict[str, Any]) -> bool:
        text = f"{recommendation.get('title', '')} {recommendation.get('reason', '')} {recommendation.get('action', '')}"
        return any(trigger.lower() in text.lower() for trigger in self.triggers)


class PlaybookRegistry:
    """Playbook 注册表"""

    def __init__(self) -> None:
        self._playbooks: Dict[str, ActionPlaybook] = {}

    def register(self, playbook: ActionPlaybook) -> None:
        self._playbooks[playbook.playbook_id] = playbook

    def find_match(self, recommendation: Dict[str, Any]) -> Optional[ActionPlaybook]:
        for playbook in self._playbooks.values():
            if playbook.matches(recommendation):
                return playbook
        return None

    def list(self) -> List[str]:
        return list(self._playbooks.keys())


def build_default_playbooks() -> PlaybookRegistry:
    """预置常见自愈 Playbook"""
    registry = PlaybookRegistry()
    registry.register(ActionPlaybook(
        playbook_id="pycache_cleanup",
        name="清理 Python 缓存",
        triggers=["缓存", "pycache", "__pycache__"],
        steps=[
            {
                "action_type": "shell",
                "command": "find $target_root -type d -name __pycache__ -exec rm -rf {} +",
            },
        ],
        effect_metric="pycache_files",
        effect_better="lower",
    ))
    registry.register(ActionPlaybook(
        playbook_id="log_cleanup",
        name="清理过期日志",
        triggers=["日志", "log"],
        steps=[
            {
                "action_type": "shell",
                "command": "find $log_dir -type f -name '*.log' -mtime +$retention_days -delete",
            },
        ],
        effect_metric="log_files",
        effect_better="lower",
    ))
    registry.register(ActionPlaybook(
        playbook_id="service_restart",
        name="重启服务",
        triggers=["服务", "restart", "重启"],
        steps=[
            {
                "action_type": "shell",
                "command": "echo systemctl restart $service",
            },
        ],
        effect_metric="error_count",
        effect_better="lower",
    ))
    registry.register(ActionPlaybook(
        playbook_id="test_coverage_boost",
        name="补测试",
        triggers=["测试", "覆盖率"],
        steps=[
            {
                "action_type": "shell",
                "command": "echo 'pytest --cov=src tests/'",
            },
        ],
        effect_metric="test_ratio",
        effect_better="higher",
    ))
    return registry


class PlaybookRunner:
    """Playbook 执行器

    根据推荐匹配 Playbook，执行动作，并验证效果。
    """

    def __init__(
        self,
        registry: PlaybookRegistry,
        executor: ActionExecutor,
        verifier: Optional[EffectVerifier] = None,
    ) -> None:
        self.registry = registry
        self.executor = executor
        self.verifier = verifier or EffectVerifier({})

    def run(
        self,
        recommendations: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        context = context or {}
        results: List[Dict[str, Any]] = []
        for rec in recommendations:
            playbook = self.registry.find_match(rec)
            if playbook is None:
                continue
            logger.info(f"[PlaybookRunner.run] matched playbook={playbook.playbook_id} rec={rec.get('title')}", "playbook")
            result = self._run_playbook(playbook, rec, context)
            results.append(result)
        return results

    def _run_playbook(
        self,
        playbook: ActionPlaybook,
        recommendation: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        before_value = self._get_metric_value(context, playbook.effect_metric)
        if before_value is not None:
            self.verifier.capture_before(playbook.effect_metric, before_value)

        step_results: List[Dict[str, Any]] = []
        all_success = True
        for step in playbook.steps:
            rendered = self._render_step(step, recommendation, context)
            action_result = self.executor.execute(rendered)
            step_results.append(action_result.to_dict())
            if not action_result.success:
                all_success = False
                break

        after_value = self._get_metric_value(context, playbook.effect_metric)
        effect = None
        if before_value is not None and after_value is not None:
            effect = self.verifier.capture_after(playbook.effect_metric, after_value)

        return {
            "playbook_id": playbook.playbook_id,
            "playbook_name": playbook.name,
            "recommendation_title": recommendation.get("title", ""),
            "success": all_success,
            "steps": step_results,
            "effect": effect,
        }

    def _render_step(
        self,
        step: Dict[str, Any],
        recommendation: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        rendered: Dict[str, Any] = {}
        params = {
            "target_root": context.get("target_root", "/workspace/self_evolving_agent"),
            "log_dir": context.get("log_dir", "/workspace/self_evolving_agent"),
            "retention_days": context.get("retention_days", 7),
            "service": context.get("service", "app"),
        }
        for key, value in step.items():
            if isinstance(value, str):
                rendered[key] = Template(value).safe_substitute(params)
            else:
                rendered[key] = value
        return rendered

    def _get_metric_value(self, context: Dict[str, Any], metric_name: Optional[str]) -> Optional[float]:
        if not metric_name:
            return None
        return context.get("metrics", {}).get(metric_name)

    def get_state(self) -> Dict[str, Any]:
        """获取 Playbook 执行器状态"""
        return {
            "registered_playbooks": self.registry.list(),
            "dry_run": self.executor.dry_run,
        }

    def reset(self) -> None:
        """重置 Playbook 执行器"""
        logger.debug("[PlaybookRunner.reset] called", "playbook")

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[PlaybookRunner.health_check] called", "playbook")
        return len(self.registry.list()) > 0
