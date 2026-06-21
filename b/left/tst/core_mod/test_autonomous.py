"""自主目标生成与动机涌现模块测试"""

from root.left.app.left.src.core_mod.autonomous import (
    AutonomousGoalModule,
    CuriosityDrive,
    GoalGenerator,
    IntrinsicReward,
    MotivationEmergence,
)


class TestIntrinsicReward:
    """IntrinsicReward 单元测试"""

    def test_init_normal(self) -> None:
        ir = IntrinsicReward({"novelty_weight": 0.5, "progress_weight": 0.3})
        assert ir.novelty_weight == 0.5
        assert ir.progress_weight == 0.3

    def test_compute_first_state(self) -> None:
        ir = IntrinsicReward({})
        reward = ir.compute([0.5, 0.5], 0.6, True)
        assert reward > 0.0
        assert ir.prev_performance == 0.6

    def test_compute_progress(self) -> None:
        ir = IntrinsicReward({})
        ir.compute([0.5], 0.5, True)
        reward = ir.compute([0.5], 0.8, True)
        assert reward > 0.0

    def test_compute_no_progress(self) -> None:
        ir = IntrinsicReward({})
        ir.compute([0.5], 0.8, True)
        reward = ir.compute([0.5], 0.7, True)
        assert reward >= 0.0

    def test_novelty_decreases(self) -> None:
        ir = IntrinsicReward({})
        r1 = ir.compute([0.5, 0.5], 0.5, True)
        r2 = ir.compute([0.5, 0.5], 0.5, True)
        assert r2 <= r1

    def test_seen_trim(self) -> None:
        ir = IntrinsicReward({"max_seen": 3})
        for i in range(5):
            ir.compute([float(i)], 0.5, True)
        assert len(ir.seen_states) == 3

    def test_get_state(self) -> None:
        ir = IntrinsicReward({})
        s = ir.get_state()
        assert "seen_count" in s
        assert "weights" in s


class TestCuriosityDrive:
    """CuriosityDrive 单元测试"""

    def test_init_normal(self) -> None:
        cd = CuriosityDrive({"threshold": 0.2})
        assert cd.threshold == 0.2

    def test_update(self) -> None:
        cd = CuriosityDrive({})
        curiosity = cd.update(1.0, 0.0)
        assert curiosity > 0.0

    def test_is_curious_true(self) -> None:
        cd = CuriosityDrive({"threshold": 0.1})
        for _ in range(15):
            cd.update(1.0, 0.0)
        assert cd.is_curious() is True

    def test_is_curious_false(self) -> None:
        cd = CuriosityDrive({"threshold": 0.5})
        for _ in range(15):
            cd.update(1.0, 0.99)
        assert cd.is_curious() is False

    def test_is_curious_empty(self) -> None:
        cd = CuriosityDrive({})
        assert cd.is_curious() is False

    def test_history_trim(self) -> None:
        cd = CuriosityDrive({"max_history": 3})
        for i in range(5):
            cd.update(float(i), 0.0)
        assert len(cd.error_history) == 3

    def test_get_state(self) -> None:
        cd = CuriosityDrive({})
        cd.update(1.0, 0.5)
        s = cd.get_state()
        assert s["history_size"] == 1


class TestGoalGenerator:
    """GoalGenerator 单元测试"""

    def test_init_normal(self) -> None:
        gg = GoalGenerator({"max_goals": 10, "state_dim": 3})
        assert gg.max_goals == 10
        assert gg.state_dim == 3

    def test_generate(self) -> None:
        gg = GoalGenerator({})
        goal = gg.generate([0.5, 0.5])
        assert "id" in goal
        assert "target" in goal
        assert len(goal["target"]) == 5

    def test_generate_pad(self) -> None:
        gg = GoalGenerator({"state_dim": 8})
        goal = gg.generate([0.5])
        assert len(goal["target"]) == 8

    def test_generate_truncate(self) -> None:
        gg = GoalGenerator({"state_dim": 2})
        goal = gg.generate([0.1, 0.2, 0.3, 0.4, 0.5])
        assert len(goal["target"]) == 2

    def test_select_best(self) -> None:
        gg = GoalGenerator({})
        gg.generate([0.5])
        gg.generate([0.6])
        best = gg.select_best()
        assert best is not None
        assert "priority" in best

    def test_select_best_empty(self) -> None:
        gg = GoalGenerator({})
        assert gg.select_best() is None

    def test_goal_trim(self) -> None:
        gg = GoalGenerator({"max_goals": 2})
        for i in range(5):
            gg.generate([float(i)])
        assert len(gg.goal_pool) == 2

    def test_get_state(self) -> None:
        gg = GoalGenerator({})
        s = gg.get_state()
        assert s["goal_count"] == 0


class TestMotivationEmergence:
    """MotivationEmergence 单元测试"""

    def test_init_normal(self) -> None:
        me = MotivationEmergence({"drives": {"a": 0.8}, "adaptation_rate": 0.2})
        assert me.drives["a"] == 0.8
        assert me.adaptation_rate == 0.2

    def test_update_increase(self) -> None:
        me = MotivationEmergence({})
        me.update({"survival": 1.0})
        assert me.drives["survival"] > 0.5

    def test_update_decrease(self) -> None:
        me = MotivationEmergence({})
        me.update({"survival": 0.0})
        assert me.drives["survival"] < 0.5

    def test_update_clip(self) -> None:
        me = MotivationEmergence({})
        for _ in range(200):
            me.update({"survival": 1.0})
        assert me.drives["survival"] > 0.99

    def test_get_dominant(self) -> None:
        me = MotivationEmergence({})
        assert me.get_dominant() == "survival"
        for _ in range(50):
            me.update({"exploration": 1.0})
        assert me.get_dominant() == "exploration"

    def test_get_state(self) -> None:
        me = MotivationEmergence({})
        s = me.get_state()
        assert "drives" in s
        assert "dominant" in s


class TestAutonomousGoalModule:
    """AutonomousGoalModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = AutonomousGoalModule({})
        assert mod.intrinsic is not None
        assert mod.curiosity is not None
        assert mod.generator is not None
        assert mod.motivation is not None

    def test_generate_goal(self) -> None:
        mod = AutonomousGoalModule({})
        goal = mod.generate_goal([0.5, 0.5], 0.6)
        assert "id" in goal
        assert "intrinsic_reward" in goal
        assert "target" in goal

    def test_evaluate_action(self) -> None:
        mod = AutonomousGoalModule({})
        result = mod.evaluate_action(1.0, 0.5, 0.6, [0.5, 0.5], True)
        assert "curiosity" in result
        assert "intrinsic_reward" in result
        assert "is_curious" in result

    def test_update_motivation(self) -> None:
        mod = AutonomousGoalModule({})
        mod.update_motivation({"survival": 1.0})
        assert mod.motivation.drives["survival"] > 0.5

    def test_get_dominant_motivation(self) -> None:
        mod = AutonomousGoalModule({})
        assert mod.get_dominant_motivation() == "survival"

    def test_get_state(self) -> None:
        mod = AutonomousGoalModule({})
        s = mod.get_state()
        assert "intrinsic" in s
        assert "curiosity" in s
        assert "generator" in s
        assert "motivation" in s

    def test_boundary_empty_state(self) -> None:
        mod = AutonomousGoalModule({})
        goal = mod.generate_goal([], 0.5)
        assert len(goal["target"]) == 5

    def test_boundary_large_state(self) -> None:
        mod = AutonomousGoalModule({"generator": {"state_dim": 2}})
        goal = mod.generate_goal([0.1, 0.2, 0.3, 0.4, 0.5], 0.5)
        assert len(goal["target"]) == 2
