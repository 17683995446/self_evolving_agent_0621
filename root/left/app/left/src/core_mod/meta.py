"""元学习与快速适应模块"""
import copy
from typing import Any, Dict, Final, List, Optional, Tuple

import numpy as np

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class TaskEmbedding:
    """任务嵌入"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[TaskEmbedding.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.dim: int = int(config.get("dim", 8))
        self.embeddings: Dict[str, np.ndarray] = {}
        logger.info(f"TaskEmbedding initialized dim={self.dim}", "meta")

    def embed(self, task_id: str, features: List[float]) -> np.ndarray:
        logger.debug(f"[TaskEmbedding.embed] task_id={task_id}")
        if task_id in self.embeddings:
            logger.debug("[TaskEmbedding.embed] cached")
            return self.embeddings[task_id]
        arr = np.array(features, dtype=np.float64)
        if len(arr) < self.dim:
            arr = np.pad(arr, (0, self.dim - len(arr)))
        elif len(arr) > self.dim:
            arr = arr[:self.dim]
        arr = arr / (np.linalg.norm(arr) + 1e-8)
        self.embeddings[task_id] = arr
        logger.debug(f"[TaskEmbedding.embed] created dim={self.dim}")
        return arr

    def similarity(self, task_a: str, task_b: str) -> float:
        emb_a = self.embeddings.get(task_a)
        emb_b = self.embeddings.get(task_b)
        if emb_a is None or emb_b is None:
            return 0.0
        sim = float(np.dot(emb_a, emb_b))
        logger.debug(f"[TaskEmbedding.similarity] {task_a} vs {task_b} sim={sim:.4f}")
        return sim


class MetaParameterOptimizer:
    """元参数优化器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[MetaParameterOptimizer.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.meta_lr: float = float(config.get("meta_lr", 0.01))
        self.params: Dict[str, float] = {
            "learning_rate": 0.01,
            "exploration_ratio": 0.3,
            "ema_alpha": 0.3,
            "regularization": 0.001,
        }
        self.gradients: Dict[str, List[float]] = {k: [] for k in self.params}
        self.max_grad_history: int = int(config.get("max_grad_history", 50))
        logger.info("MetaParameterOptimizer initialized", "meta")

    def update(self, param_name: str, performance_delta: float) -> float:
        logger.debug(f"[MetaParameterOptimizer.update] param={param_name} delta={performance_delta:.4f}")
        if param_name not in self.params:
            logger.warning(f"[MetaParameterOptimizer.update] unknown param={param_name}")
            return 0.0
        grad = performance_delta * self.meta_lr
        self.gradients[param_name].append(grad)
        if len(self.gradients[param_name]) > self.max_grad_history:
            self.gradients[param_name].pop(0)
        avg_grad = float(np.mean(self.gradients[param_name]))
        self.params[param_name] += avg_grad
        self.params[param_name] = max(0.0001, min(1.0, self.params[param_name]))
        logger.debug(f"[MetaParameterOptimizer.update] new_value={self.params[param_name]:.4f}")
        return self.params[param_name]

    def get_params(self) -> Dict[str, float]:
        return copy.deepcopy(self.params)


class TransferLearning:
    """迁移学习机制"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[TransferLearning.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.similarity_threshold: float = float(config.get("similarity_threshold", 0.7))
        self.knowledge_base: Dict[str, Dict[str, Any]] = {}
        logger.info(f"TransferLearning initialized threshold={self.similarity_threshold}", "meta")

    def store_knowledge(self, task_id: str, knowledge: Dict[str, Any]) -> None:
        logger.debug(f"[TransferLearning.store_knowledge] task_id={task_id}")
        self.knowledge_base[task_id] = copy.deepcopy(knowledge)

    def find_similar_tasks(
        self, task_embedding: TaskEmbedding, target_task: str
    ) -> List[str]:
        logger.debug(f"[TransferLearning.find_similar_tasks] target={target_task}")
        similar = []
        for task_id in self.knowledge_base:
            if task_id == target_task:
                continue
            sim = task_embedding.similarity(target_task, task_id)
            if sim >= self.similarity_threshold:
                similar.append(task_id)
                logger.debug(f"[TransferLearning.find_similar_tasks] similar={task_id} sim={sim:.4f}")
        logger.debug(f"[TransferLearning.find_similar_tasks] found={len(similar)}")
        return similar

    def transfer(
        self, task_embedding: TaskEmbedding, target_task: str
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"[TransferLearning.transfer] target={target_task}")
        similar = self.find_similar_tasks(task_embedding, target_task)
        if not similar:
            logger.debug("[TransferLearning.transfer] no similar tasks")
            return None
        merged = {}
        total_weight = 0.0
        for task_id in similar:
            weight = task_embedding.similarity(target_task, task_id)
            knowledge = self.knowledge_base.get(task_id, {})
            for key, value in knowledge.items():
                if isinstance(value, (int, float)):
                    merged[key] = merged.get(key, 0.0) + value * weight
            total_weight += weight
        if total_weight > 0:
            for key in merged:
                merged[key] /= total_weight
        logger.info(f"[TransferLearning.transfer] merged from {len(similar)} tasks", "meta")
        return merged


class FastAdaptation:
    """快速适应引擎"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[FastAdaptation.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.adaptation_steps: int = int(config.get("adaptation_steps", 5))
        self.learning_rate: float = float(config.get("learning_rate", 0.1))
        logger.info(f"FastAdaptation initialized steps={self.adaptation_steps}", "meta")

    def adapt(
        self,
        base_weights: np.ndarray,
        few_shot_data: List[Tuple[List[float], float]]
    ) -> np.ndarray:
        logger.debug(f"[FastAdaptation.adapt] data_size={len(few_shot_data)}")
        weights = base_weights.copy()
        for step in range(self.adaptation_steps):
            total_grad = np.zeros_like(weights)
            for x, y in few_shot_data:
                x_arr = np.array(x, dtype=np.float64)
                pred = float(np.dot(weights, x_arr))
                error = pred - y
                total_grad += error * x_arr
            avg_grad = total_grad / max(len(few_shot_data), 1)
            weights -= self.learning_rate * avg_grad
            logger.debug(f"[FastAdaptation.adapt] step={step} grad_norm={np.linalg.norm(avg_grad):.4f}")
        return weights


class MetaLearner:
    """元学习器主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[MetaLearner.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.embedding = TaskEmbedding(config.get("embedding", {}))
        logger.debug("[MetaLearner.__init__] embedding created")
        self.optimizer = MetaParameterOptimizer(config.get("optimizer", {}))
        logger.debug("[MetaLearner.__init__] optimizer created")
        self.transfer = TransferLearning(config.get("transfer", {}))
        logger.debug("[MetaLearner.__init__] transfer created")
        self.adaptation = FastAdaptation(config.get("adaptation", {}))
        logger.debug("[MetaLearner.__init__] adaptation created")
        logger.info("MetaLearner initialized", "meta")

    def register_task(self, task_id: str, features: List[float]) -> np.ndarray:
        logger.debug(f"[MetaLearner.register_task] task_id={task_id}")
        return self.embedding.embed(task_id, features)

    def optimize_param(self, param_name: str, performance_delta: float) -> float:
        logger.debug(f"[MetaLearner.optimize_param] param={param_name}")
        return self.optimizer.update(param_name, performance_delta)

    def store_and_transfer(
        self, task_id: str, knowledge: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        logger.debug(f"[MetaLearner.store_and_transfer] task_id={task_id}")
        self.transfer.store_knowledge(task_id, knowledge)
        return self.transfer.transfer(self.embedding, task_id)

    def fast_adapt(
        self,
        base_weights: List[float],
        few_shot_data: List[Tuple[List[float], float]]
    ) -> List[float]:
        logger.debug(f"[MetaLearner.fast_adapt] data_size={len(few_shot_data)}")
        weights_arr = np.array(base_weights, dtype=np.float64)
        adapted = self.adaptation.adapt(weights_arr, few_shot_data)
        return adapted.tolist()

    def get_meta_state(self) -> Dict[str, Any]:
        return {
            "params": self.optimizer.get_params(),
            "tasks": list(self.embedding.embeddings.keys()),
            "knowledge_base_size": len(self.transfer.knowledge_base),
        }
