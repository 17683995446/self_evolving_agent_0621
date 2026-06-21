"""终身学习与灾难性遗忘防护模块"""
from typing import Any, Dict, Final, List, Optional

import numpy as np

from root.left.app.left.src.utils_main.exceptions import ValidationError
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class ExperienceReplay:
    """经验回放（存储和抽样历史经验）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ExperienceReplay.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.capacity: int = int(config.get("capacity", 1000))
        self.batch_size: int = int(config.get("batch_size", 32))
        self.buffer: List[Dict[str, Any]] = []
        self.position: int = 0
        logger.info(f"ExperienceReplay initialized capacity={self.capacity}", "lifelong")

    def store(self, experience: Dict[str, Any]) -> None:
        logger.debug("[ExperienceReplay.store] start")
        Validator.require_type(experience, dict, "experience")
        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
        else:
            self.buffer[self.position] = experience
        self.position = (self.position + 1) % max(self.capacity, 1)
        logger.debug(f"[ExperienceReplay.store] size={len(self.buffer)}")

    def sample(self) -> List[Dict[str, Any]]:
        logger.debug("[ExperienceReplay.sample] start")
        if not self.buffer:
            return []
        n = min(self.batch_size, len(self.buffer))
        indices = np.random.choice(len(self.buffer), size=n, replace=False)
        result = [self.buffer[i] for i in indices]
        logger.debug(f"[ExperienceReplay.sample] sampled={len(result)}")
        return result

    def get_state(self) -> Dict[str, Any]:
        return {
            "size": len(self.buffer),
            "capacity": self.capacity,
            "batch_size": self.batch_size,
        }


class ElasticWeightConsolidation:
    """弹性权重巩固（Fisher信息保护重要参数）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ElasticWeightConsolidation.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.lambda_ewc: float = float(config.get("lambda_ewc", 100.0))
        self.fisher: Dict[str, np.ndarray] = {}
        self.optimal_params: Dict[str, np.ndarray] = {}
        logger.info(f"ElasticWeightConsolidation initialized lambda={self.lambda_ewc}", "lifelong")

    def compute_fisher(self, params: Dict[str, np.ndarray], gradients: Dict[str, np.ndarray]) -> None:
        logger.debug("[ElasticWeightConsolidation.compute_fisher] start")
        for name, grad in gradients.items():
            if grad is None:
                continue
            fisher_val = np.square(grad)
            if name in self.fisher:
                self.fisher[name] = 0.9 * self.fisher[name] + 0.1 * fisher_val
            else:
                self.fisher[name] = fisher_val.copy()
            logger.debug(f"[ElasticWeightConsolidation.compute_fisher] {name} fisher_norm={np.linalg.norm(self.fisher[name]):.4f}")
        self.optimal_params = {k: v.copy() for k, v in params.items()}

    def penalty(self, params: Dict[str, np.ndarray]) -> float:
        logger.debug("[ElasticWeightConsolidation.penalty] start")
        if not self.fisher or not self.optimal_params:
            return 0.0
        total = 0.0
        for name in self.fisher:
            if name not in params or name not in self.optimal_params:
                continue
            diff = params[name] - self.optimal_params[name]
            total += float(np.sum(self.fisher[name] * np.square(diff)))
        penalty_val = 0.5 * self.lambda_ewc * total
        logger.debug(f"[ElasticWeightConsolidation.penalty] penalty={penalty_val:.4f}")
        return penalty_val

    def get_state(self) -> Dict[str, Any]:
        return {
            "lambda_ewc": self.lambda_ewc,
            "protected_params": list(self.fisher.keys()),
        }


class KnowledgeConsolidation:
    """知识巩固（蒸馏旧知识到新模型）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[KnowledgeConsolidation.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.temperature: float = float(config.get("temperature", 2.0))
        self.alpha: float = float(config.get("alpha", 0.5))
        self.old_outputs: Dict[str, np.ndarray] = {}
        logger.info(f"KnowledgeConsolidation initialized temp={self.temperature}", "lifelong")

    def register_old_outputs(self, task_id: str, outputs: np.ndarray) -> None:
        logger.debug(f"[KnowledgeConsolidation.register_old_outputs] task={task_id}")
        self.old_outputs[task_id] = outputs.copy()

    def distill_loss(self, task_id: str, new_outputs: np.ndarray) -> float:
        logger.debug(f"[KnowledgeConsolidation.distill_loss] task={task_id}")
        old = self.old_outputs.get(task_id)
        if old is None:
            return 0.0
        if len(new_outputs) != len(old):
            target = len(old)
            if len(new_outputs) < target:
                new_outputs = np.pad(new_outputs, (0, target - len(new_outputs)))
            else:
                new_outputs = new_outputs[:target]
        old_soft = self._softmax(old / self.temperature)
        new_soft = self._softmax(new_outputs / self.temperature)
        loss = float(-np.sum(old_soft * np.log(new_soft + 1e-8)))
        logger.debug(f"[KnowledgeConsolidation.distill_loss] loss={loss:.4f}")
        return loss

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x))
        return exp_x / np.sum(exp_x)

    def get_state(self) -> Dict[str, Any]:
        return {
            "temperature": self.temperature,
            "alpha": self.alpha,
            "old_tasks": list(self.old_outputs.keys()),
        }


class ProgressiveNeuralNetwork:
    """渐进神经网络（横向扩展新任务列）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[ProgressiveNeuralNetwork.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.input_dim: int = int(config.get("input_dim", 10))
        self.hidden_dim: int = int(config.get("hidden_dim", 16))
        self.columns: Dict[str, Dict[str, np.ndarray]] = {}
        self.adapters: Dict[str, List[np.ndarray]] = {}
        logger.info(f"ProgressiveNeuralNetwork initialized hidden={self.hidden_dim}", "lifelong")

    def add_column(self, task_id: str) -> None:
        logger.debug(f"[ProgressiveNeuralNetwork.add_column] task={task_id}")
        if task_id in self.columns:
            return
        self.columns[task_id] = {
            "W1": np.random.randn(self.input_dim, self.hidden_dim) * 0.01,
            "b1": np.zeros(self.hidden_dim),
            "W2": np.random.randn(self.hidden_dim, 1) * 0.01,
            "b2": np.zeros(1),
        }
        self.adapters[task_id] = []
        for prev_task in self.columns:
            if prev_task != task_id:
                adapter = np.random.randn(self.hidden_dim, self.hidden_dim) * 0.01
                self.adapters[task_id].append(adapter)
        logger.debug(f"[ProgressiveNeuralNetwork.add_column] columns={len(self.columns)}")

    def forward(self, task_id: str, x: List[float]) -> float:
        logger.debug(f"[ProgressiveNeuralNetwork.forward] task={task_id}")
        col = self.columns.get(task_id)
        if col is None:
            return 0.0
        x_arr = np.array(x, dtype=np.float64)
        if len(x_arr) < self.input_dim:
            x_arr = np.pad(x_arr, (0, self.input_dim - len(x_arr)))
        else:
            x_arr = x_arr[:self.input_dim]
        h = np.maximum(0, np.dot(x_arr, col["W1"]) + col["b1"])
        for adapter in self.adapters.get(task_id, []):
            h = h + np.maximum(0, np.dot(h, adapter))
        out = float((np.dot(h, col["W2"]) + col["b2"]).item())
        logger.debug(f"[ProgressiveNeuralNetwork.forward] out={out:.4f}")
        return out

    def get_state(self) -> Dict[str, Any]:
        return {
            "column_count": len(self.columns),
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
            "tasks": list(self.columns.keys()),
        }


class LifelongLearningModule:
    """终身学习主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[LifelongLearningModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.replay = ExperienceReplay(config.get("replay", {}))
        logger.debug("[LifelongLearningModule.__init__] replay created")
        self.ewc = ElasticWeightConsolidation(config.get("ewc", {}))
        logger.debug("[LifelongLearningModule.__init__] ewc created")
        self.consolidation = KnowledgeConsolidation(config.get("consolidation", {}))
        logger.debug("[LifelongLearningModule.__init__] consolidation created")
        self.pnn = ProgressiveNeuralNetwork(config.get("pnn", {}))
        logger.debug("[LifelongLearningModule.__init__] pnn created")
        self.current_task: Optional[str] = None
        logger.info("LifelongLearningModule initialized", "lifelong")

    def start_task(self, task_id: str, features: List[float]) -> None:
        logger.debug(f"[LifelongLearningModule.start_task] task={task_id}")
        self.current_task = task_id
        self.pnn.add_column(task_id)
        self.replay.store({"task_id": task_id, "features": features, "type": "task_start"})
        logger.info("[LifelongLearningModule.start_task] task column added", "lifelong")

    def learn(self, features: List[float], target: float) -> Dict[str, Any]:
        logger.debug(f"[LifelongLearningModule.learn] task={self.current_task}")
        if self.current_task is None:
            raise ValidationError("No active task. Call start_task first.")
        pred = self.pnn.forward(self.current_task, features)
        error = pred - target
        self.replay.store({
            "task_id": self.current_task,
            "features": features,
            "target": target,
            "pred": pred,
        })
        samples = self.replay.sample()
        ewc_penalty = 0.0
        col = self.pnn.columns.get(self.current_task)
        if col is not None:
            params = {k: v.copy() for k, v in col.items()}
            grad = {"W2": error * col["W2"]}
            self.ewc.compute_fisher(params, grad)
            ewc_penalty = self.ewc.penalty(params)
        result = {
            "pred": pred,
            "error": error,
            "replay_samples": len(samples),
            "ewc_penalty": ewc_penalty,
        }
        logger.debug(f"[LifelongLearningModule.learn] error={error:.4f} replay={len(samples)}")
        return result

    def consolidate(self, task_id: str, new_outputs: np.ndarray) -> float:
        logger.debug(f"[LifelongLearningModule.consolidate] task={task_id}")
        return self.consolidation.distill_loss(task_id, new_outputs)

    def get_state(self) -> Dict[str, Any]:
        return {
            "replay": self.replay.get_state(),
            "ewc": self.ewc.get_state(),
            "consolidation": self.consolidation.get_state(),
            "pnn": self.pnn.get_state(),
            "current_task": self.current_task,
        }
