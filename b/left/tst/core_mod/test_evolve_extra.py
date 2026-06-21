"""进化模块补充测试"""
from root.left.app.left.src.core_mod.evolve import (
    SnapshotManager, RefactorEngine, EvolutionModule,
)


class TestSnapshotManagerExtra:
    """测试SnapshotManager额外路径"""

    def test_get_best_snapshot_empty(self) -> None:
        mgr = SnapshotManager({})
        assert mgr.get_best_snapshot() is None

    def test_should_rollback_empty(self) -> None:
        mgr = SnapshotManager({})
        assert mgr.should_rollback(0.5) is False


class TestRefactorEngineExtra:
    """测试RefactorEngine额外路径"""

    def test_generate_adjustments(self) -> None:
        eng = RefactorEngine({})
        config = {"exploration": {"base_exploration_ratio": 0.2}}
        result = eng.generate_adjustments(config)
        assert result["exploration"]["base_exploration_ratio"] > 0.2

    def test_check_stagnation_short(self) -> None:
        eng = RefactorEngine({})
        assert eng._check_stagnation([]) is False


class TestEvolutionModuleExtra:
    """测试EvolutionModule额外路径"""

    def test_get_best_snapshot_empty(self) -> None:
        mod = EvolutionModule({})
        assert mod.get_best_snapshot() is None

    def test_adjustment_stats_empty(self) -> None:
        mod = EvolutionModule({})
        stats = mod.get_adjustment_stats()
        assert stats["total"] == 0
