"""效果验证器测试"""

from root.left.app.left.src.core_mod.effect_verifier import EffectVerifier


class TestEffectVerifier:
    """效果验证器测试"""

    def test_capture_before_after(self) -> None:
        v = EffectVerifier({})
        v.capture_before("cpu", 80.0)
        result = v.capture_after("cpu", 60.0)
        assert result["before"] == 80.0
        assert result["after"] == 60.0
        assert result["improved"] is True

    def test_no_before(self) -> None:
        v = EffectVerifier({})
        result = v.capture_after("memory", 50.0)
        assert result["before"] is None
        assert result["improved"] is True

    def test_higher_better(self) -> None:
        v = EffectVerifier({})
        v.capture_before("accuracy", 0.7)
        result = v.capture_after("accuracy", 0.8)
        assert result["improved"] is True

    def test_summary(self) -> None:
        v = EffectVerifier({})
        v.capture_before("cpu", 50.0)
        summary = v.get_summary()
        assert "cpu" in summary["metrics"]
        assert summary["latest"]["cpu"] == 50.0

    def test_max_points(self) -> None:
        v = EffectVerifier({"max_points": 2})
        v.capture_before("x", 1.0)
        v.capture_before("x", 2.0)
        v.capture_before("x", 3.0)
        result = v.capture_after("x", 4.0)
        assert result["before"] == 2.0
