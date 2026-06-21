"""Agent 共享行为混入

把 SelfEvolvingAgent 与 ProductionAgent 都需要的能力（获取核心模块、
统一关闭、析构时释放资源、运行时控制）抽到这里，避免两边重复实现。
"""
import sys
import threading
from typing import Any, Dict

from root.left.app.left.src.utils_main.logger import logger


class ClosableAgentMixin:
    """可关闭 Agent 的共享行为"""

    def __init__(self) -> None:
        # 运行时控制状态
        self._paused: bool = False
        self._control_lock: threading.Lock = threading.Lock()

    def get_core_modules(self) -> Dict[str, Any]:
        """获取所有核心模块实例，用于合规检查与统一关闭"""
        modules: Dict[str, Any] = {
            "action_executor": self.action_executor,
            "effect_verifier": self.effect_verifier,
            "recommendation_engine": self.recommendation_engine,
            "dashboard": self.dashboard,
            "phase_one": self.phase_one,
            "phase_two": self.phase_two,
            "phase_three": self.phase_three,
        }
        if hasattr(self.phase_one, "data_collector"):
            modules["data_collector"] = self.phase_one.data_collector
        return modules

    # ------------------------------------------------------------------
    # 运行时控制
    # ------------------------------------------------------------------

    def pause(self) -> None:
        """暂停 Agent 主循环（不停止，可恢复）。"""
        with self._control_lock:
            self._paused = True
        logger.info("Agent paused", "control")

    def resume(self) -> None:
        """恢复已暂停的 Agent 主循环。"""
        with self._control_lock:
            self._paused = False
        logger.info("Agent resumed", "control")

    def is_paused(self) -> bool:
        """返回 Agent 是否处于暂停状态。"""
        with self._control_lock:
            return self._paused

    def get_control_status(self) -> Dict[str, Any]:
        """返回运行时控制状态摘要。"""
        with self._control_lock:
            return {
                "running": getattr(self, "running", False),
                "paused": self._paused,
                "loop_count": getattr(self, "loop_count", 0),
            }

    def reload_config(self, env: str = "dev") -> Dict[str, Any]:
        """重新加载配置并重新初始化各阶段模块（热更新）。

        Args:
            env: 要加载的环境名称

        Returns:
            操作结果字典，包含 success 和 message

        注意: 调用此方法前应确保 Agent 处于暂停或停止状态，
        否则并发修改可能导致不可预期行为。
        """
        from root.left.app.left.src.utils_main.config_loader import ConfigLoader
        from root.left.app.left.src.utils_main.validators import ConfigValidator

        try:
            new_config = ConfigLoader.load_config(env)
            ConfigValidator.validate_config(new_config)
            # 先关闭旧模块，再初始化新模块
            if hasattr(self, "_init_phases"):
                self._init_phases(new_config)
            self.config = new_config
            logger.info(f"Config reloaded from env={env}", "control")
            return {"success": True, "message": f"配置已从 {env} 环境重新加载", "env": env}
        except Exception as e:
            logger.error(f"Config reload failed: {e}", "control")
            return {"success": False, "message": f"配置重载失败: {e}", "env": env}

    def _wait_if_paused(self, check_interval: float = 0.5) -> None:
        """如果处于暂停状态，则阻塞等待直到恢复或停止。

        应在主循环每次迭代前调用。
        """
        import time
        while self.is_paused() and getattr(self, "running", False):
            time.sleep(check_interval)

    # ------------------------------------------------------------------
    # 关闭与析构
    # ------------------------------------------------------------------

    def close(self) -> None:
        """关闭 Agent，释放所有模块占用的资源"""
        self.stop()
        if getattr(self, "phase_one", None) is not None:
            for module in self.get_core_modules().values():
                if hasattr(module, "close") and callable(getattr(module, "close")):
                    module.close()

    def __del__(self) -> None:
        if sys.is_finalizing():
            return
        try:
            self.close()
        except Exception:
            pass
