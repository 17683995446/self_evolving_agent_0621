"""情感计算与社交智能模块"""
import copy
from typing import Any, Dict, Final, List, Tuple

import numpy as np

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class EmotionRecognizer:
    """情感识别器（从valence/arousal维度识别情感）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[EmotionRecognizer.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.threshold: float = float(config.get("threshold", 0.3))
        self.history: List[Dict[str, Any]] = []
        self.max_history: int = int(config.get("max_history", 100))
        logger.info(f"EmotionRecognizer initialized threshold={self.threshold}", "social")

    def recognize(self, features: Dict[str, float]) -> Dict[str, Any]:
        logger.debug("[EmotionRecognizer.recognize] start")
        valence = float(features.get("valence", 0.0))
        arousal = float(features.get("arousal", 0.5))
        emotion = self._classify(valence, arousal)
        confidence = float(np.tanh(abs(valence) + arousal))
        result = {"emotion": emotion, "confidence": confidence, "valence": valence, "arousal": arousal}
        self._add_history(result)
        logger.debug(f"[EmotionRecognizer.recognize] emotion={emotion} conf={confidence:.4f}")
        return result

    def _classify(self, valence: float, arousal: float) -> str:
        if abs(valence) < self.threshold and arousal < self.threshold:
            return "neutral"
        if abs(valence) < self.threshold:
            return "neutral"
        if valence > 0:
            return "joy" if arousal > 0.5 else "contentment"
        return "anger" if arousal > 0.5 else "sadness"

    def _add_history(self, record: Dict[str, Any]) -> None:
        self.history.append(record)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        logger.debug(f"[EmotionRecognizer._add_history] size={len(self.history)}")

    def get_state(self) -> Dict[str, Any]:
        return {"history_size": len(self.history), "threshold": self.threshold}


class SocialContextAnalyzer:
    """社交情境分析器（分析多方交互情境）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SocialContextAnalyzer.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.context_window: int = int(config.get("context_window", 10))
        self.interactions: List[Dict[str, Any]] = []
        self.max_interactions: int = int(config.get("max_interactions", 100))
        logger.info(f"SocialContextAnalyzer initialized window={self.context_window}", "social")

    def observe(self, interaction: Dict[str, Any]) -> None:
        logger.debug("[SocialContextAnalyzer.observe] start")
        self.interactions.append(copy.deepcopy(interaction))
        if len(self.interactions) > self.max_interactions:
            self.interactions.pop(0)
        logger.debug(f"[SocialContextAnalyzer.observe] size={len(self.interactions)}")

    def analyze(self) -> Dict[str, Any]:
        logger.debug("[SocialContextAnalyzer.analyze] start")
        window = self.interactions[-self.context_window:]
        if not window:
            return {"avg_valence": 0.0, "participant_count": 0, "interaction_count": 0}
        valences = [float(i.get("valence", 0.0)) for i in window]
        participants = set()
        for i in window:
            speaker = i.get("speaker")
            if speaker:
                participants.add(speaker)
        result = {
            "avg_valence": float(np.mean(valences)),
            "participant_count": len(participants),
            "interaction_count": len(window),
        }
        logger.debug(f"[SocialContextAnalyzer.analyze] participants={len(participants)}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {"interaction_count": len(self.interactions), "context_window": self.context_window}


class EmpathyModel:
    """共情模型（根据他人情感生成适当响应）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[EmpathyModel.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.empathy_factor: float = float(config.get("empathy_factor", 0.5))
        self.response_map: Dict[str, str] = dict(config.get("response_map", {
            "joy": "celebration",
            "anger": "calm",
            "sadness": "comfort",
            "fear": "reassurance",
            "neutral": "neutral",
        }))
        logger.info(f"EmpathyModel initialized factor={self.empathy_factor}", "social")

    def respond(self, emotion_state: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[EmpathyModel.respond] start")
        emotion = str(emotion_state.get("emotion", "neutral"))
        intensity = float(emotion_state.get("intensity", 0.5))
        response_emotion = self.response_map.get(emotion, "neutral")
        response_intensity = float(np.clip(intensity * self.empathy_factor, 0.0, 1.0))
        result = {
            "response_emotion": response_emotion,
            "response_intensity": response_intensity,
            "target_emotion": emotion,
        }
        logger.debug(f"[EmpathyModel.respond] {emotion} -> {response_emotion}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {"empathy_factor": self.empathy_factor, "mapped_emotions": list(self.response_map.keys())}


class RelationshipTracker:
    """关系追踪器（记录和维护Agent间关系强度）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[RelationshipTracker.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.decay_rate: float = float(config.get("decay_rate", 0.01))
        self.relationships: Dict[Tuple[str, str], float] = {}
        logger.info(f"RelationshipTracker initialized decay={self.decay_rate}", "social")

    def interact(self, agent_a: str, agent_b: str, value: float) -> None:
        logger.debug(f"[RelationshipTracker.interact] {agent_a}-{agent_b} val={value:.4f}")
        key = (agent_a, agent_b)
        current = self.relationships.get(key, 0.0)
        self.relationships[key] = float(np.clip(current + value, 0.0, 1.0))
        logger.debug(f"[RelationshipTracker.interact] new={self.relationships[key]:.4f}")

    def get_relationship(self, agent_a: str, agent_b: str) -> float:
        return self.relationships.get((agent_a, agent_b), 0.0)

    def decay(self) -> None:
        logger.debug("[RelationshipTracker.decay] start")
        for key in list(self.relationships.keys()):
            self.relationships[key] = float(np.clip(self.relationships[key] - self.decay_rate, 0.0, 1.0))
            if self.relationships[key] <= 0.0:
                del self.relationships[key]
        logger.debug(f"[RelationshipTracker.decay] count={len(self.relationships)}")

    def get_state(self) -> Dict[str, Any]:
        return {"relationship_count": len(self.relationships), "decay_rate": self.decay_rate}


class SocialIntelligenceModule:
    """情感计算与社交智能主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SocialIntelligenceModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.emotion = EmotionRecognizer(config.get("emotion", {}))
        logger.debug("[SocialIntelligenceModule.__init__] emotion created")
        self.context = SocialContextAnalyzer(config.get("context", {}))
        logger.debug("[SocialIntelligenceModule.__init__] context created")
        self.empathy = EmpathyModel(config.get("empathy", {}))
        logger.debug("[SocialIntelligenceModule.__init__] empathy created")
        self.relationships = RelationshipTracker(config.get("relationships", {}))
        logger.debug("[SocialIntelligenceModule.__init__] relationships created")
        logger.info("SocialIntelligenceModule initialized", "social")

    def perceive_and_respond(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[SocialIntelligenceModule.perceive_and_respond] start")
        valence = float(input_data.get("valence", 0.0))
        arousal = float(input_data.get("arousal", 0.5))
        emotion_result = self.emotion.recognize({"valence": valence, "arousal": arousal})
        self.context.observe(copy.deepcopy(input_data))
        context_result = self.context.analyze()
        empathy_result = self.empathy.respond({
            "emotion": emotion_result["emotion"],
            "intensity": emotion_result["confidence"],
        })
        result = {
            "emotion": emotion_result,
            "context": context_result,
            "response": empathy_result,
        }
        logger.info(f"[SocialIntelligenceModule.perceive_and_respond] emotion={emotion_result['emotion']}", "social")
        return result

    def track_relationship(self, agent_a: str, agent_b: str, value: float) -> None:
        logger.debug(f"[SocialIntelligenceModule.track_relationship] {agent_a}-{agent_b}")
        self.relationships.interact(agent_a, agent_b, value)

    def get_state(self) -> Dict[str, Any]:
        return {
            "emotion": self.emotion.get_state(),
            "context": self.context.get_state(),
            "empathy": self.empathy.get_state(),
            "relationships": self.relationships.get_state(),
        }
