"""对抗鲁棒性模块单元测试"""
import pytest

from root.left.app.left.src.core_mod.adversarial import (
    AdversarialPerturbation, AdversarialDefense,
    NashEquilibrium, DeceptionDetector, AdversarialTraining, AdversarialModule,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestAdversarialPerturbation:
    """测试对抗扰动"""

    def test_fgsm_changes_input(self) -> None:
        p = AdversarialPerturbation({"epsilon": 0.1})
        x = [0.5, 0.5, 0.5]
        grad = [1.0, -1.0, 0.0]
        adv = p.fgsm(x, grad)
        assert adv != x
        assert adv[0] > x[0]
        assert adv[1] < x[1]

    def test_fgsm_zero_gradient(self) -> None:
        p = AdversarialPerturbation({})
        x = [0.5, 0.5]
        adv = p.fgsm(x, [0.0, 0.0])
        assert adv == x

    def test_random_perturbation(self) -> None:
        p = AdversarialPerturbation({"epsilon": 0.1})
        x = [0.5, 0.5]
        noisy = p.random_perturbation(x)
        assert len(noisy) == len(x)
        assert noisy != x

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            AdversarialPerturbation(None)


class TestAdversarialDefense:
    """测试对抗防御"""

    def test_smooth_reduces_variance(self) -> None:
        d = AdversarialDefense({"smoothing_factor": 0.5})
        x = [0.0, 1.0]
        smoothed = d.smooth(x)
        assert abs(smoothed[1] - smoothed[0]) < abs(x[1] - x[0])

    def test_clip(self) -> None:
        d = AdversarialDefense({"clip_min": 0.0, "clip_max": 1.0})
        x = [-1.0, 2.0]
        clipped = d.smooth(x)
        assert all(0.0 <= v <= 1.0 for v in clipped)

    def test_ensemble_predict(self) -> None:
        d = AdversarialDefense({})
        result = d.ensemble_predict(lambda x: sum(x), [1.0, 2.0], n_perturbations=3)
        assert isinstance(result, float)


class TestNashEquilibrium:
    """测试纳什均衡"""

    def test_normal_solve(self) -> None:
        ne = NashEquilibrium({})
        result = ne.solve_2x2([[3.0, -1.0], [-2.0, 1.0]])
        assert "p1" in result
        assert "p2" in result
        assert "value" in result
        assert abs(sum(result["p1"]) - 1.0) < 0.01
        assert abs(sum(result["p2"]) - 1.0) < 0.01

    def test_singular_matrix(self) -> None:
        ne = NashEquilibrium({})
        result = ne.solve_2x2([[1.0, 1.0], [1.0, 1.0]])
        assert result["p1"] == [0.5, 0.5]

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            NashEquilibrium(None)


class TestDeceptionDetector:
    """测试欺骗检测"""

    def test_normal_consistent(self) -> None:
        dd = DeceptionDetector({"consistency_threshold": 0.5})
        for _ in range(5):
            dd.record("a1", {"cpu": 0.5}, {"cpu": 0.51})
        assert dd.is_deceptive("a1") is False

    def test_deceptive_detected(self) -> None:
        dd = DeceptionDetector({"consistency_threshold": 0.1})
        for _ in range(5):
            dd.record("a1", {"cpu": 0.1}, {"cpu": 0.9})
        assert dd.is_deceptive("a1") is True

    def test_not_enough_data(self) -> None:
        dd = DeceptionDetector({})
        dd.record("a1", {"cpu": 0.1}, {"cpu": 0.9})
        assert dd.is_deceptive("a1") is False

    def test_no_common_keys(self) -> None:
        dd = DeceptionDetector({})
        dd.record("a1", {"a": 0.1}, {"b": 0.9})
        assert dd.is_deceptive("a1") is False


class TestAdversarialTraining:
    """测试对抗训练"""

    def test_generate_batch(self) -> None:
        at = AdversarialTraining({"adv_ratio": 0.5})
        data = [([1.0, 2.0], 3.0), ([2.0, 1.0], 3.0)]
        mixed = at.generate_adversarial_batch(data, lambda x, y: [1.0, 1.0])
        assert len(mixed) == 3

    def test_robust_predict(self) -> None:
        at = AdversarialTraining({})
        result = at.robust_predict(lambda x: sum(x), [1.0, 2.0])
        assert isinstance(result, float)


class TestAdversarialModule:
    """测试对抗模块主控"""

    def test_normal_init(self) -> None:
        mod = AdversarialModule({})
        assert mod.perturber is not None

    def test_generate_fgsm(self) -> None:
        mod = AdversarialModule({"perturbation": {"epsilon": 0.1}})
        adv = mod.generate_fgsm([0.5, 0.5], [1.0, -1.0])
        assert adv != [0.5, 0.5]

    def test_smooth_input(self) -> None:
        mod = AdversarialModule({})
        smoothed = mod.smooth_input([0.0, 1.0])
        assert len(smoothed) == 2

    def test_solve_game(self) -> None:
        mod = AdversarialModule({})
        result = mod.solve_game([[1.0, 0.0], [0.0, 1.0]])
        assert "value" in result

    def test_check_deception(self) -> None:
        mod = AdversarialModule({"deception": {"consistency_threshold": 0.1}})
        for _ in range(5):
            mod.check_deception("a1", {"cpu": 0.1}, {"cpu": 0.9})
        assert mod.check_deception("a1", {"cpu": 0.1}, {"cpu": 0.9}) is True

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            AdversarialModule(None)
