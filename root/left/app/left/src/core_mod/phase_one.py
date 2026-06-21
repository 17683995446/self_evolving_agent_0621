"""Phase 1 核心"""
from typing import Any, Dict, Final

from root.left.app.left.src.core_mod.data_collector import DataCollectorModule
from root.left.app.left.src.core_mod.sensory import SensoryModule
from root.left.app.left.src.core_mod.drive import DriveEngine
from root.left.app.left.src.core_mod.predict import PredictionModule
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class PhaseOneCore:
    """Phase 1 整合核心"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[PhaseOneCore.__init__] start")
        Validator.require_type(config, dict, "config")
        logger.debug("[PhaseOneCore.__init__] config validated")
        self.config: Final[Dict[str, Any]] = config
        logger.debug("[PhaseOneCore.__init__] config assigned")
        self.sensory = SensoryModule(config.get("sensory", {}))
        logger.debug("[PhaseOneCore.__init__] sensory created")
        self.drive_engine = DriveEngine(config.get("drive", {}))
        logger.debug("[PhaseOneCore.__init__] drive_engine created")
        self.prediction = PredictionModule(config.get("prediction", {}))
        logger.debug("[PhaseOneCore.__init__] prediction created")
        self.data_collector = DataCollectorModule(config.get("data_collector", {}))
        logger.debug("[PhaseOneCore.__init__] data_collector created")

    def step(self) -> Dict[str, Any]:
        logger.debug("[PhaseOneCore.step] start")
        state = self.sensory.perceive()
        state["collected_data"] = self.data_collector.collect_all()
        logger.debug(f"[PhaseOneCore.step] state={state}")
        predictions = self.prediction.predict(state)
        logger.debug(f"[PhaseOneCore.step] predictions keys={list(predictions.keys())}")
        avg_error = self.prediction.get_average_error()
        logger.debug(f"[PhaseOneCore.step] avg_error={avg_error}")
        drive_state = self.drive_engine.compute(state, avg_error, {}, 0.0, 0.0)
        logger.debug(f"[PhaseOneCore.step] drive_state keys={list(drive_state.keys())}")
        performance = self._calc_performance(drive_state, avg_error)
        logger.debug(f"[PhaseOneCore.step] performance={performance}")
        result = self._build_result(state, predictions, drive_state, performance)
        logger.debug("[PhaseOneCore.step] done")
        return result

    def _build_result(
        self, state: Dict[str, Any], predictions: Dict[str, Any],
        drive_state: Dict[str, Any], performance: float
    ) -> Dict[str, Any]:
        logger.debug("[PhaseOneCore._build_result] start")
        result = {
            "state": state,
            "predictions": predictions,
            "drive_state": drive_state,
            "performance": performance,
        }
        logger.debug(f"[PhaseOneCore._build_result] result keys={list(result.keys())}")
        return result

    def _calc_performance(
        self, drive_state: Dict[str, Any], error_rate: float
    ) -> float:
        logger.debug("[PhaseOneCore._calc_performance] start")
        total_reward = drive_state.get("total_reward", 0.0)
        logger.debug(f"[PhaseOneCore._calc_performance] total_reward={total_reward}")
        accuracy = max(0.0, 1.0 - error_rate)
        logger.debug(f"[PhaseOneCore._calc_performance] accuracy={accuracy}")
        result = float(total_reward * 0.7 + accuracy * 0.3)
        logger.debug(f"[PhaseOneCore._calc_performance] result={result}")
        return result

    def get_state(self) -> Dict[str, Any]:
        """获取 Phase 1 状态"""
        return {
            "has_sensory": hasattr(self.sensory, "perceive"),
            "has_drive": hasattr(self.drive_engine, "compute"),
            "has_prediction": hasattr(self.prediction, "predict"),
            "has_data_collector": hasattr(self.data_collector, "collect_all"),
        }

    def reset(self) -> None:
        """重置 Phase 1"""
        logger.debug("[PhaseOneCore.reset] called", "phase1")
        for module in [self.sensory, self.drive_engine, self.prediction, self.data_collector]:
            if hasattr(module, "reset") and callable(getattr(module, "reset")):
                module.reset()

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[PhaseOneCore.health_check] called", "phase1")
        return all(
            module.health_check()
            for module in [self.sensory, self.drive_engine, self.prediction, self.data_collector]
        )
