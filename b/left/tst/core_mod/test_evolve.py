"""进化模块单元测试"""
import pytest
from root.left.app.left.src.core_mod.evolve import (
    Snapshot, SnapshotManager, RefactorEngine,
    FeatureEngine, ReviewEngine, EvolutionModule,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestSnapshot:
    """测试Snapshot"""

    def test_normal_init(self) -> None:
        snap = Snapshot("s1", {"key": "val"}, 0.5)
        assert snap.snapshot_id == "s1"

    def test_empty_config(self) -> None:
        snap = Snapshot("s1", {}, 0.0)
        assert snap.config == {}

    def test_boundary_zero_perf(self) -> None:
        snap = Snapshot("s1", {}, 0.0)
        assert snap.performance == 0.0

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            Snapshot(None, {}, 0.0)

    def test_to_dict(self) -> None:
        snap = Snapshot("s1", {}, 0.5)
        d = snap.to_dict()
        assert "snapshot_id" in d


class TestSnapshotManager:
    """测试SnapshotManager"""

    def test_normal_save(self) -> None:
        mgr = SnapshotManager({"max_snapshots": 5})
        mgr.save({"k": 1}, 0.5)
        assert mgr.get_snapshot_count() == 1

    def test_empty_snapshots(self) -> None:
        mgr = SnapshotManager({})
        assert mgr.should_rollback(0.5) is False

    def test_boundary_rollback(self) -> None:
        mgr = SnapshotManager({"rollback_threshold": 0.1})
        mgr.save({"k": 1}, 0.5)
        assert mgr.should_rollback(0.3) is True

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            SnapshotManager(None)

    def test_get_best(self) -> None:
        mgr = SnapshotManager({})
        mgr.save({"k": 1}, 0.3)
        mgr.save({"k": 2}, 0.8)
        best = mgr.get_best_snapshot()
        assert best.performance == 0.8

    def test_max_snapshots(self) -> None:
        mgr = SnapshotManager({"max_snapshots": 2})
        mgr.save({"k": 1}, 0.1)
        mgr.save({"k": 2}, 0.2)
        mgr.save({"k": 3}, 0.3)
        assert mgr.get_snapshot_count() == 2


class TestRefactorEngine:
    """测试RefactorEngine"""

    def test_normal_analyze(self) -> None:
        eng = RefactorEngine({"error_threshold": 0.5})
        result = eng.analyze([0.1, 0.2], 0.1)
        assert result["needs_refactor"] is False

    def test_empty_history(self) -> None:
        eng = RefactorEngine({})
        result = eng.analyze([], 0.0)
        assert result["needs_refactor"] is False

    def test_boundary_high_error(self) -> None:
        eng = RefactorEngine({"error_threshold": 0.3})
        result = eng.analyze([], 0.5)
        assert result["needs_refactor"] is True

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            RefactorEngine(None)

    def test_generate_adjustments(self) -> None:
        eng = RefactorEngine({})
        config = {"exploration": {"base_exploration_ratio": 0.2}}
        new_config = eng.generate_adjustments(config)
        assert new_config["exploration"]["base_exploration_ratio"] > 0.2


class TestFeatureEngine:
    """测试FeatureEngine"""

    def test_normal_detect_gap(self) -> None:
        eng = FeatureEngine({})
        preds = {"low": [{"target_metric": "cpu", "predicted_value": 50.0}]}
        actual = {"system_metrics": {"cpu": 55.0}}
        gap = eng.detect_gap(preds, actual)
        assert gap == 5.0

    def test_empty_predictions(self) -> None:
        eng = FeatureEngine({})
        gap = eng.detect_gap({}, {})
        assert gap == 0.0

    def test_boundary_propose(self) -> None:
        eng = FeatureEngine({})
        feature = eng.propose_feature(0.2, 0.1)
        assert feature == "enhance_prediction_model"

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            FeatureEngine(None)

    def test_no_propose(self) -> None:
        eng = FeatureEngine({})
        feature = eng.propose_feature(0.05, 0.1)
        assert feature is None


class TestReviewEngine:
    """测试ReviewEngine"""

    def test_normal_approve(self) -> None:
        eng = ReviewEngine({})
        assert eng.review_adjustments({}, 0.5, 0.5) is True

    def test_empty_config(self) -> None:
        eng = ReviewEngine({})
        assert eng.review_adjustments({}, 1.0, 1.0) is True

    def test_boundary_reject(self) -> None:
        eng = ReviewEngine({})
        assert eng.review_adjustments({}, 0.8, 1.0) is False

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            ReviewEngine(None)


class TestEvolutionModule:
    """测试EvolutionModule"""

    def test_normal_evolve(self) -> None:
        mod = EvolutionModule({})
        result = mod.evolve({}, [0.5], {}, {}, 0.1)
        assert "snapshot_count" in result

    def test_empty_performance(self) -> None:
        mod = EvolutionModule({})
        result = mod.evolve({}, [], {}, {}, 0.0)
        assert result["should_adjust"] is False

    def test_boundary_should_rollback(self) -> None:
        mod = EvolutionModule({})
        mod.evolve({}, [0.5], {}, {}, 0.1)
        assert mod.should_rollback(0.3) is True

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            EvolutionModule(None)

    def test_get_best_snapshot(self) -> None:
        mod = EvolutionModule({})
        mod.evolve({}, [0.5], {}, {}, 0.1)
        snap = mod.get_best_snapshot()
        assert snap is not None

    def test_adjustment_stats(self) -> None:
        mod = EvolutionModule({})
        mod.evolve({}, [0.5], {}, {}, 0.1)
        stats = mod.get_adjustment_stats()
        assert stats["total"] >= 1
