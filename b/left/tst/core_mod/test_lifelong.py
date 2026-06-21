"""终身学习与灾难性遗忘防护模块测试"""
import numpy as np
import pytest

from root.left.app.left.src.core_mod.lifelong import (
    ElasticWeightConsolidation,
    ExperienceReplay,
    KnowledgeConsolidation,
    LifelongLearningModule,
    ProgressiveNeuralNetwork,
)
from root.left.app.left.src.utils_main.exceptions import ValidationError


class TestExperienceReplay:
    """ExperienceReplay 单元测试"""

    def test_init_normal(self) -> None:
        er = ExperienceReplay({"capacity": 100, "batch_size": 16})
        assert er.capacity == 100
        assert er.batch_size == 16

    def test_store_and_sample(self) -> None:
        er = ExperienceReplay({"capacity": 10, "batch_size": 2})
        for i in range(5):
            er.store({"id": i})
        samples = er.sample()
        assert len(samples) == 2

    def test_sample_empty(self) -> None:
        er = ExperienceReplay({})
        assert er.sample() == []

    def test_capacity_overflow(self) -> None:
        er = ExperienceReplay({"capacity": 3})
        for i in range(5):
            er.store({"id": i})
        assert len(er.buffer) == 3

    def test_get_state(self) -> None:
        er = ExperienceReplay({})
        er.store({"id": 1})
        s = er.get_state()
        assert s["size"] == 1


class TestElasticWeightConsolidation:
    """ElasticWeightConsolidation 单元测试"""

    def test_init_normal(self) -> None:
        ewc = ElasticWeightConsolidation({"lambda_ewc": 50.0})
        assert ewc.lambda_ewc == 50.0

    def test_penalty_before_fisher(self) -> None:
        ewc = ElasticWeightConsolidation({})
        params = {"W": np.array([1.0, 2.0])}
        assert ewc.penalty(params) == 0.0

    def test_compute_fisher_and_penalty(self) -> None:
        ewc = ElasticWeightConsolidation({"lambda_ewc": 10.0})
        params = {"W": np.array([1.0, 2.0])}
        grads = {"W": np.array([0.5, 0.5])}
        ewc.compute_fisher(params, grads)
        penalty = ewc.penalty(params)
        assert penalty == 0.0
        shifted = {"W": np.array([2.0, 3.0])}
        penalty2 = ewc.penalty(shifted)
        assert penalty2 > 0.0

    def test_fisher_moving_average(self) -> None:
        ewc = ElasticWeightConsolidation({})
        params = {"W": np.ones(3)}
        ewc.compute_fisher(params, {"W": np.ones(3)})
        first = ewc.fisher["W"].copy()
        ewc.compute_fisher(params, {"W": np.zeros(3)})
        second = ewc.fisher["W"]
        assert not np.array_equal(first, second)

    def test_get_state(self) -> None:
        ewc = ElasticWeightConsolidation({})
        s = ewc.get_state()
        assert s["lambda_ewc"] == 100.0


class TestKnowledgeConsolidation:
    """KnowledgeConsolidation 单元测试"""

    def test_init_normal(self) -> None:
        kc = KnowledgeConsolidation({"temperature": 1.0, "alpha": 0.3})
        assert kc.temperature == 1.0
        assert kc.alpha == 0.3

    def test_distill_no_old(self) -> None:
        kc = KnowledgeConsolidation({})
        loss = kc.distill_loss("t1", np.array([1.0, 2.0]))
        assert loss == 0.0

    def test_distill_with_old(self) -> None:
        kc = KnowledgeConsolidation({"temperature": 2.0})
        kc.register_old_outputs("t1", np.array([1.0, 0.0]))
        loss = kc.distill_loss("t1", np.array([0.0, 1.0]))
        assert loss > 0.0

    def test_distill_different_length(self) -> None:
        kc = KnowledgeConsolidation({})
        kc.register_old_outputs("t1", np.array([1.0, 0.0, 0.5]))
        loss = kc.distill_loss("t1", np.array([0.0, 1.0]))
        assert loss > 0.0

    def test_get_state(self) -> None:
        kc = KnowledgeConsolidation({})
        s = kc.get_state()
        assert "temperature" in s


class TestProgressiveNeuralNetwork:
    """ProgressiveNeuralNetwork 单元测试"""

    def test_init_normal(self) -> None:
        pnn = ProgressiveNeuralNetwork({"input_dim": 5, "hidden_dim": 8})
        assert pnn.input_dim == 5
        assert pnn.hidden_dim == 8

    def test_add_column(self) -> None:
        pnn = ProgressiveNeuralNetwork({})
        pnn.add_column("task1")
        assert "task1" in pnn.columns

    def test_add_column_duplicate(self) -> None:
        pnn = ProgressiveNeuralNetwork({})
        pnn.add_column("task1")
        pnn.add_column("task1")
        assert len(pnn.columns) == 1

    def test_forward(self) -> None:
        pnn = ProgressiveNeuralNetwork({"input_dim": 3})
        pnn.add_column("task1")
        out = pnn.forward("task1", [1.0, 2.0, 3.0])
        assert isinstance(out, float)

    def test_forward_missing_task(self) -> None:
        pnn = ProgressiveNeuralNetwork({})
        assert pnn.forward("missing", [1.0]) == 0.0

    def test_forward_pad(self) -> None:
        pnn = ProgressiveNeuralNetwork({"input_dim": 5})
        pnn.add_column("task1")
        out = pnn.forward("task1", [1.0])
        assert isinstance(out, float)

    def test_multi_column_adapters(self) -> None:
        pnn = ProgressiveNeuralNetwork({})
        pnn.add_column("task1")
        pnn.add_column("task2")
        assert len(pnn.adapters.get("task2", [])) >= 0

    def test_get_state(self) -> None:
        pnn = ProgressiveNeuralNetwork({})
        pnn.add_column("task1")
        s = pnn.get_state()
        assert s["column_count"] == 1


class TestLifelongLearningModule:
    """LifelongLearningModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = LifelongLearningModule({})
        assert mod.replay is not None
        assert mod.ewc is not None
        assert mod.pnn is not None

    def test_start_task(self) -> None:
        mod = LifelongLearningModule({})
        mod.start_task("task1", [1.0, 2.0])
        assert mod.current_task == "task1"
        assert "task1" in mod.pnn.columns

    def test_learn_no_task(self) -> None:
        mod = LifelongLearningModule({})
        with pytest.raises(ValidationError):
            mod.learn([1.0], 0.5)

    def test_learn_with_task(self) -> None:
        mod = LifelongLearningModule({})
        mod.start_task("task1", [1.0, 2.0])
        result = mod.learn([1.0, 2.0], 0.5)
        assert "pred" in result
        assert "error" in result
        assert "replay_samples" in result

    def test_learn_replay_populated(self) -> None:
        mod = LifelongLearningModule({"replay": {"capacity": 10, "batch_size": 2}})
        mod.start_task("task1", [1.0])
        for i in range(5):
            mod.learn([float(i)], float(i) * 0.1)
        assert mod.replay.get_state()["size"] >= 5

    def test_consolidate(self) -> None:
        mod = LifelongLearningModule({})
        mod.consolidation.register_old_outputs("t1", np.array([1.0, 0.0]))
        loss = mod.consolidate("t1", np.array([0.0, 1.0]))
        assert loss > 0.0

    def test_multi_task(self) -> None:
        mod = LifelongLearningModule({})
        mod.start_task("task1", [1.0, 2.0])
        mod.learn([1.0, 2.0], 0.5)
        mod.start_task("task2", [3.0, 4.0])
        mod.learn([3.0, 4.0], 0.8)
        assert len(mod.pnn.columns) == 2
        assert mod.current_task == "task2"

    def test_get_state(self) -> None:
        mod = LifelongLearningModule({})
        s = mod.get_state()
        assert "replay" in s
        assert "ewc" in s
        assert "pnn" in s

    def test_boundary_empty_features(self) -> None:
        mod = LifelongLearningModule({})
        mod.start_task("task1", [])
        result = mod.learn([], 0.0)
        assert "pred" in result

    def test_boundary_large_features(self) -> None:
        mod = LifelongLearningModule({"pnn": {"input_dim": 3}})
        mod.start_task("task1", [1.0, 2.0, 3.0, 4.0, 5.0])
        result = mod.learn([1.0, 2.0, 3.0, 4.0, 5.0], 0.5)
        assert "pred" in result
