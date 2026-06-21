"""元学习模块单元测试"""
import numpy as np
import pytest

from root.left.app.left.src.core_mod.meta import (
    TaskEmbedding, MetaParameterOptimizer,
    TransferLearning, FastAdaptation, MetaLearner,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestTaskEmbedding:
    """测试任务嵌入"""

    def test_normal_embed(self) -> None:
        te = TaskEmbedding({"dim": 4})
        emb = te.embed("task1", [1.0, 2.0, 3.0])
        assert len(emb) == 4
        assert abs(np.linalg.norm(emb) - 1.0) < 0.01

    def test_cache(self) -> None:
        te = TaskEmbedding({"dim": 4})
        emb1 = te.embed("task1", [1.0, 2.0])
        emb2 = te.embed("task1", [3.0, 4.0])
        assert np.allclose(emb1, emb2)

    def test_similarity_same(self) -> None:
        te = TaskEmbedding({"dim": 4})
        te.embed("a", [1.0, 0.0, 0.0, 0.0])
        te.embed("b", [1.0, 0.0, 0.0, 0.0])
        sim = te.similarity("a", "b")
        assert sim > 0.99

    def test_similarity_orthogonal(self) -> None:
        te = TaskEmbedding({"dim": 4})
        te.embed("a", [1.0, 0.0, 0.0, 0.0])
        te.embed("b", [0.0, 1.0, 0.0, 0.0])
        sim = te.similarity("a", "b")
        assert abs(sim) < 0.01

    def test_similarity_missing(self) -> None:
        te = TaskEmbedding({})
        assert te.similarity("a", "b") == 0.0


class TestMetaParameterOptimizer:
    """测试元参数优化器"""

    def test_normal_update(self) -> None:
        opt = MetaParameterOptimizer({})
        val = opt.update("learning_rate", 0.1)
        assert val > 0.01

    def test_bounds(self) -> None:
        opt = MetaParameterOptimizer({"meta_lr": 1.0})
        for _ in range(100):
            opt.update("learning_rate", 1.0)
        assert opt.get_params()["learning_rate"] <= 1.0

    def test_unknown_param(self) -> None:
        opt = MetaParameterOptimizer({})
        assert opt.update("unknown", 0.1) == 0.0

    def test_negative_delta(self) -> None:
        opt = MetaParameterOptimizer({})
        val = opt.update("learning_rate", -0.5)
        assert val < 0.01


class TestTransferLearning:
    """测试迁移学习"""

    def test_store_and_find(self) -> None:
        tl = TransferLearning({"similarity_threshold": 0.5})
        te = TaskEmbedding({"dim": 4})
        te.embed("task1", [1.0, 0.0, 0.0, 0.0])
        te.embed("task2", [0.9, 0.1, 0.0, 0.0])
        tl.store_knowledge("task1", {"lr": 0.01})
        similar = tl.find_similar_tasks(te, "task2")
        assert "task1" in similar

    def test_transfer_merge(self) -> None:
        tl = TransferLearning({"similarity_threshold": 0.5})
        te = TaskEmbedding({"dim": 4})
        te.embed("task1", [1.0, 0.0, 0.0, 0.0])
        te.embed("task2", [0.9, 0.1, 0.0, 0.0])
        tl.store_knowledge("task1", {"lr": 0.01})
        merged = tl.transfer(te, "task2")
        assert merged is not None
        assert "lr" in merged

    def test_no_similar(self) -> None:
        tl = TransferLearning({"similarity_threshold": 0.99})
        te = TaskEmbedding({"dim": 4})
        te.embed("task1", [1.0, 0.0, 0.0, 0.0])
        te.embed("task2", [0.0, 1.0, 0.0, 0.0])
        tl.store_knowledge("task1", {"lr": 0.01})
        merged = tl.transfer(te, "task2")
        assert merged is None


class TestFastAdaptation:
    """测试快速适应"""

    def test_normal_adapt(self) -> None:
        fa = FastAdaptation({"adaptation_steps": 50, "learning_rate": 0.05})
        weights = np.array([0.0, 0.0], dtype=np.float64)
        data = [([1.0, 2.0], 5.0), ([2.0, 1.0], 4.0)]
        adapted = fa.adapt(weights, data)
        pred = np.dot(adapted, np.array([1.0, 2.0]))
        assert abs(pred - 5.0) < 1.5

    def test_empty_data(self) -> None:
        fa = FastAdaptation({})
        weights = np.array([1.0, 2.0])
        adapted = fa.adapt(weights, [])
        assert np.allclose(adapted, weights)


class TestMetaLearner:
    """测试元学习器主控"""

    def test_normal_init(self) -> None:
        mod = MetaLearner({})
        assert mod.embedding is not None

    def test_register_task(self) -> None:
        mod = MetaLearner({"embedding": {"dim": 4}})
        emb = mod.register_task("t1", [1.0, 2.0])
        assert len(emb) == 4

    def test_optimize_param(self) -> None:
        mod = MetaLearner({})
        val = mod.optimize_param("learning_rate", 0.1)
        assert val > 0.0

    def test_store_and_transfer(self) -> None:
        mod = MetaLearner({"transfer": {"similarity_threshold": 0.5}, "embedding": {"dim": 4}})
        mod.register_task("task1", [1.0, 0.0, 0.0, 0.0])
        mod.register_task("task2", [0.9, 0.1, 0.0, 0.0])
        mod.store_and_transfer("task1", {"lr": 0.01})
        merged = mod.store_and_transfer("task2", {"lr": 0.02})
        assert merged is not None

    def test_fast_adapt(self) -> None:
        mod = MetaLearner({"adaptation": {"adaptation_steps": 10, "learning_rate": 0.01}})
        weights = [0.0, 0.0]
        data = [([1.0, 2.0], 5.0)]
        adapted = mod.fast_adapt(weights, data)
        assert len(adapted) == 2

    def test_meta_state(self) -> None:
        mod = MetaLearner({})
        state = mod.get_meta_state()
        assert "params" in state
        assert "tasks" in state

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValidationError):
            MetaLearner(None)
