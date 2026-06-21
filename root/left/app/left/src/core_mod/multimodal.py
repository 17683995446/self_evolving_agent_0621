"""跨模态感知融合模块"""
from typing import Any, Dict, Final, List

import numpy as np

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class CrossModalEncoder:
    """跨模态编码器（将不同模态编码到统一空间）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[CrossModalEncoder.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.output_dim: int = int(config.get("output_dim", 16))
        self.encoders: Dict[str, Dict[str, np.ndarray]] = {}
        logger.info(f"CrossModalEncoder initialized output_dim={self.output_dim}", "multimodal")

    def _build_encoder(self, input_dim: int) -> Dict[str, np.ndarray]:
        return {
            "W": np.random.randn(input_dim, self.output_dim) * 0.01,
            "b": np.zeros(self.output_dim),
        }

    def encode(self, modality: str, data: List[float]) -> List[float]:
        logger.debug(f"[CrossModalEncoder.encode] modality={modality}")
        Validator.require_type(modality, str, "modality")
        x = np.array(data, dtype=np.float64)
        if modality not in self.encoders:
            self.encoders[modality] = self._build_encoder(len(x))
        enc = self.encoders[modality]
        if len(x) != enc["W"].shape[0]:
            if len(x) < enc["W"].shape[0]:
                x = np.pad(x, (0, enc["W"].shape[0] - len(x)))
            else:
                x = x[:enc["W"].shape[0]]
        h = np.dot(x, enc["W"]) + enc["b"]
        h = np.maximum(0, h)
        result = [float(v) for v in h]
        logger.debug(f"[CrossModalEncoder.encode] norm={np.linalg.norm(h):.4f}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "output_dim": self.output_dim,
            "modalities": list(self.encoders.keys()),
        }


class ModalityAlignment:
    """模态对齐器（时间对齐、语义对齐）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ModalityAlignment.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.time_window: float = float(config.get("time_window", 1.0))
        self.streams: Dict[str, List[Dict[str, Any]]] = {}
        logger.info(f"ModalityAlignment initialized window={self.time_window}", "multimodal")

    def ingest(self, modality: str, timestamp: float, data: Any) -> None:
        logger.debug(f"[ModalityAlignment.ingest] modality={modality} ts={timestamp}")
        if modality not in self.streams:
            self.streams[modality] = []
        self.streams[modality].append({"timestamp": timestamp, "data": data})
        self._trim_stream(modality)

    def _trim_stream(self, modality: str) -> None:
        stream = self.streams.get(modality, [])
        if len(stream) > 100:
            self.streams[modality] = stream[-100:]
        logger.debug(f"[ModalityAlignment._trim_stream] {modality} size={len(self.streams[modality])}")

    def align(self, reference_ts: float) -> Dict[str, Any]:
        logger.debug(f"[ModalityAlignment.align] ref_ts={reference_ts}")
        result: Dict[str, Any] = {}
        for modality, stream in self.streams.items():
            best = None
            best_diff = float("inf")
            for item in stream:
                diff = abs(item["timestamp"] - reference_ts)
                if diff < best_diff and diff <= self.time_window:
                    best_diff = diff
                    best = item
            if best is not None:
                result[modality] = best["data"]
        logger.debug(f"[ModalityAlignment.align] aligned={list(result.keys())}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "time_window": self.time_window,
            "stream_count": len(self.streams),
            "stream_sizes": {k: len(v) for k, v in self.streams.items()},
        }


class MultiModalFusion:
    """多模态融合器（加权融合、注意力融合）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[MultiModalFusion.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.fusion_dim: int = int(config.get("fusion_dim", 16))
        self.weights: Dict[str, float] = dict(config.get("weights", {}))
        self.attention_temperature: float = float(config.get("attention_temperature", 1.0))
        logger.info(f"MultiModalFusion initialized fusion_dim={self.fusion_dim}", "multimodal")

    def fuse(self, embeddings: Dict[str, List[float]]) -> List[float]:
        logger.debug("[MultiModalFusion.fuse] start")
        Validator.require_type(embeddings, dict, "embeddings")
        if not embeddings:
            return [0.0] * self.fusion_dim
        vecs: Dict[str, np.ndarray] = {}
        for mod, emb in embeddings.items():
            v = np.array(emb, dtype=np.float64)
            if len(v) < self.fusion_dim:
                v = np.pad(v, (0, self.fusion_dim - len(v)))
            else:
                v = v[:self.fusion_dim]
            vecs[mod] = v
        if not vecs:
            return [0.0] * self.fusion_dim
        weights = self._compute_weights(vecs)
        fused = np.zeros(self.fusion_dim)
        for mod, v in vecs.items():
            w = weights.get(mod, 1.0 / len(vecs))
            fused = fused + v * w
        result = [float(v) for v in fused]
        logger.debug(f"[MultiModalFusion.fuse] fused_norm={np.linalg.norm(fused):.4f}")
        return result

    def _compute_weights(self, vecs: Dict[str, np.ndarray]) -> Dict[str, float]:
        if self.weights:
            total = sum(self.weights.get(m, 1.0) for m in vecs)
            return {m: self.weights.get(m, 1.0) / total for m in vecs}
        norms = {m: np.linalg.norm(v) + 1e-8 for m, v in vecs.items()}
        total = sum(norms.values())
        return {m: n / total for m, n in norms.items()}

    def update_weight(self, modality: str, weight: float) -> None:
        logger.debug(f"[MultiModalFusion.update_weight] {modality}={weight}")
        self.weights[modality] = float(np.clip(weight, 0.0, 1.0))

    def get_state(self) -> Dict[str, Any]:
        return {
            "fusion_dim": self.fusion_dim,
            "weights": self.weights.copy(),
        }


class SensorFusionModule:
    """跨模态感知融合主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[SensorFusionModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.encoder = CrossModalEncoder(config.get("encoder", {}))
        logger.debug("[SensorFusionModule.__init__] encoder created")
        self.alignment = ModalityAlignment(config.get("alignment", {}))
        logger.debug("[SensorFusionModule.__init__] alignment created")
        self.fusion = MultiModalFusion(config.get("fusion", {}))
        logger.debug("[SensorFusionModule.__init__] fusion created")
        logger.info("SensorFusionModule initialized", "multimodal")

    def ingest(self, modality: str, timestamp: float, data: List[float]) -> None:
        logger.debug(f"[SensorFusionModule.ingest] modality={modality}")
        self.alignment.ingest(modality, timestamp, data)

    def fuse_at(self, timestamp: float) -> Dict[str, Any]:
        logger.debug(f"[SensorFusionModule.fuse_at] ts={timestamp}")
        aligned = self.alignment.align(timestamp)
        embeddings: Dict[str, List[float]] = {}
        for modality, data in aligned.items():
            if isinstance(data, list):
                embeddings[modality] = self.encoder.encode(modality, data)
        fused = self.fusion.fuse(embeddings)
        return {
            "timestamp": timestamp,
            "aligned_modalities": list(aligned.keys()),
            "embeddings": embeddings,
            "fused": fused,
        }

    def encode(self, modality: str, data: List[float]) -> List[float]:
        logger.debug(f"[SensorFusionModule.encode] modality={modality}")
        return self.encoder.encode(modality, data)

    def get_state(self) -> Dict[str, Any]:
        return {
            "encoder": self.encoder.get_state(),
            "alignment": self.alignment.get_state(),
            "fusion": self.fusion.get_state(),
        }
