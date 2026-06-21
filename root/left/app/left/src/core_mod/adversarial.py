"""对抗鲁棒性与博弈均衡模块"""
from typing import Any, Dict, Final, List, Tuple

import numpy as np

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class AdversarialPerturbation:
    """对抗扰动生成器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[AdversarialPerturbation.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.epsilon: float = float(config.get("epsilon", 0.1))
        self.norm: str = str(config.get("norm", "inf"))
        logger.info(f"AdversarialPerturbation initialized epsilon={self.epsilon}", "adversarial")

    def fgsm(
        self, x: List[float], gradient: List[float]
    ) -> List[float]:
        logger.debug("[AdversarialPerturbation.fgsm] start")
        x_arr = np.array(x, dtype=np.float64)
        grad_arr = np.array(gradient, dtype=np.float64)
        grad_norm = np.linalg.norm(grad_arr)
        if grad_norm < 1e-8:
            return x
        if self.norm == "inf":
            perturbation = self.epsilon * np.sign(grad_arr)
        else:
            perturbation = self.epsilon * grad_arr / grad_norm
        adv = x_arr + perturbation
        result = adv.tolist()
        logger.debug("[AdversarialPerturbation.fgsm] done")
        return result

    def random_perturbation(self, x: List[float]) -> List[float]:
        logger.debug("[AdversarialPerturbation.random_perturbation] start")
        x_arr = np.array(x, dtype=np.float64)
        noise = np.random.uniform(-self.epsilon, self.epsilon, size=x_arr.shape)
        result = (x_arr + noise).tolist()
        logger.debug("[AdversarialPerturbation.random_perturbation] done")
        return result


class AdversarialDefense:
    """对抗防御器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[AdversarialDefense.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.smoothing_factor: float = float(config.get("smoothing_factor", 0.1))
        self.clip_min: float = float(config.get("clip_min", -1.0))
        self.clip_max: float = float(config.get("clip_max", 1.0))
        logger.info("AdversarialDefense initialized", "adversarial")

    def smooth(self, x: List[float]) -> List[float]:
        logger.debug("[AdversarialDefense.smooth] start")
        x_arr = np.array(x, dtype=np.float64)
        smoothed = x_arr * (1.0 - self.smoothing_factor) + self.smoothing_factor * np.mean(x_arr)
        result = np.clip(smoothed, self.clip_min, self.clip_max).tolist()
        logger.debug("[AdversarialDefense.smooth] done")
        return result

    def ensemble_predict(
        self,
        predict_fn: Any,
        x: List[float],
        n_perturbations: int = 5
    ) -> float:
        logger.debug(f"[AdversarialDefense.ensemble_predict] n={n_perturbations}")
        perturber = AdversarialPerturbation({"epsilon": 0.05})
        preds = []
        for _ in range(n_perturbations):
            noisy = perturber.random_perturbation(x)
            preds.append(predict_fn(noisy))
        result = float(np.median(preds))
        logger.debug(f"[AdversarialDefense.ensemble_predict] result={result:.4f}")
        return result


class NashEquilibrium:
    """纳什均衡计算器（2x2零和博弈）"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[NashEquilibrium.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        logger.info("NashEquilibrium initialized", "adversarial")

    def solve_2x2(
        self, payoff_matrix: List[List[float]]
    ) -> Dict[str, Any]:
        logger.debug("[NashEquilibrium.solve_2x2] start")
        Validator.require_type(payoff_matrix, list, "payoff_matrix")
        a, b = payoff_matrix[0][0], payoff_matrix[0][1]
        c, d = payoff_matrix[1][0], payoff_matrix[1][1]
        det = (a + d) - (b + c)
        if abs(det) < 1e-8:
            logger.warning("[NashEquilibrium.solve_2x2] singular matrix", "adversarial")
            return {"p1": [0.5, 0.5], "p2": [0.5, 0.5], "value": (a + b + c + d) / 4.0}
        p = (d - c) / det
        q = (d - b) / det
        p = max(0.0, min(1.0, p))
        q = max(0.0, min(1.0, q))
        game_value = a * p * q + b * p * (1 - q) + c * (1 - p) * q + d * (1 - p) * (1 - q)
        result = {
            "p1": [p, 1.0 - p],
            "p2": [q, 1.0 - q],
            "value": float(game_value),
        }
        logger.info(f"[NashEquilibrium.solve_2x2] value={game_value:.4f}", "adversarial")
        return result


class DeceptionDetector:
    """欺骗检测器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[DeceptionDetector.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.consistency_threshold: float = float(config.get("consistency_threshold", 0.3))
        self.history: List[Dict[str, Any]] = []
        self.max_history: int = int(config.get("max_history", 100))
        logger.info("DeceptionDetector initialized", "adversarial")

    def record(self, agent_id: str, claimed_state: Dict[str, float], observed_state: Dict[str, float]) -> None:
        logger.debug(f"[DeceptionDetector.record] agent={agent_id}")
        inconsistency = self._calc_inconsistency(claimed_state, observed_state)
        self.history.append({
            "agent_id": agent_id,
            "inconsistency": inconsistency,
            "timestamp": __import__("time").time(),
        })
        if len(self.history) > self.max_history:
            self.history.pop(0)
        logger.debug(f"[DeceptionDetector.record] inconsistency={inconsistency:.4f}")

    def is_deceptive(self, agent_id: str) -> bool:
        logger.debug(f"[DeceptionDetector.is_deceptive] agent={agent_id}")
        records = [h for h in self.history if h["agent_id"] == agent_id]
        if len(records) < 3:
            return False
        avg_inconsistency = float(np.mean([r["inconsistency"] for r in records[-10:]]))
        result = avg_inconsistency > self.consistency_threshold
        logger.info(f"[DeceptionDetector.is_deceptive] agent={agent_id} result={result} avg={avg_inconsistency:.4f}", "adversarial")
        return result

    def _calc_inconsistency(
        self, claimed: Dict[str, float], observed: Dict[str, float]
    ) -> float:
        keys = set(claimed.keys()) & set(observed.keys())
        if not keys:
            return 1.0
        diffs = [abs(claimed[k] - observed[k]) for k in keys]
        return float(np.mean(diffs))


class AdversarialTraining:
    """对抗训练循环"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[AdversarialTraining.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.adv_ratio: float = float(config.get("adv_ratio", 0.2))
        self.perturber = AdversarialPerturbation(config.get("perturbation", {}))
        self.defense = AdversarialDefense(config.get("defense", {}))
        logger.info(f"AdversarialTraining initialized adv_ratio={self.adv_ratio}", "adversarial")

    def generate_adversarial_batch(
        self,
        clean_data: List[Tuple[List[float], float]],
        gradient_fn: Any
    ) -> List[Tuple[List[float], float]]:
        logger.debug(f"[AdversarialTraining.generate_adversarial_batch] clean_size={len(clean_data)}")
        adv_batch = []
        n_adv = int(len(clean_data) * self.adv_ratio)
        for i in range(n_adv):
            x, y = clean_data[i]
            grad = gradient_fn(x, y)
            adv_x = self.perturber.fgsm(x, grad)
            adv_batch.append((adv_x, y))
        mixed = clean_data + adv_batch
        logger.debug(f"[AdversarialTraining.generate_adversarial_batch] mixed_size={len(mixed)}")
        return mixed

    def robust_predict(self, predict_fn: Any, x: List[float]) -> float:
        logger.debug("[AdversarialTraining.robust_predict] start")
        smoothed = self.defense.smooth(x)
        return self.defense.ensemble_predict(predict_fn, smoothed)


class AdversarialModule:
    """对抗模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[AdversarialModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.perturber = AdversarialPerturbation(config.get("perturbation", {}))
        logger.debug("[AdversarialModule.__init__] perturber created")
        self.defense = AdversarialDefense(config.get("defense", {}))
        logger.debug("[AdversarialModule.__init__] defense created")
        self.nash = NashEquilibrium(config.get("nash", {}))
        logger.debug("[AdversarialModule.__init__] nash created")
        self.deception = DeceptionDetector(config.get("deception", {}))
        logger.debug("[AdversarialModule.__init__] deception created")
        self.training = AdversarialTraining(config.get("training", {}))
        logger.debug("[AdversarialModule.__init__] training created")
        logger.info("AdversarialModule initialized", "adversarial")

    def generate_fgsm(self, x: List[float], gradient: List[float]) -> List[float]:
        return self.perturber.fgsm(x, gradient)

    def smooth_input(self, x: List[float]) -> List[float]:
        return self.defense.smooth(x)

    def solve_game(self, payoff_matrix: List[List[float]]) -> Dict[str, Any]:
        return self.nash.solve_2x2(payoff_matrix)

    def check_deception(
        self, agent_id: str, claimed: Dict[str, float], observed: Dict[str, float]
    ) -> bool:
        self.deception.record(agent_id, claimed, observed)
        return self.deception.is_deceptive(agent_id)

    def robust_predict(self, predict_fn: Any, x: List[float]) -> float:
        return self.training.robust_predict(predict_fn, x)
