"""常量与枚举单元测试"""
import pytest
from root.left.app.left.src.utils_main.constants import (
    MetricType, DriveType, TaskType, TaskStatus,
    PredictionLevel, ScenarioType, AdjustmentType, ErrorCode,
)


class TestMetricType:
    """测试MetricType"""

    def test_normal_value(self) -> None:
        assert MetricType.SYSTEM.value == "system"

    def test_empty_not_member(self) -> None:
        with pytest.raises(ValueError):
            MetricType("")

    def test_boundary_case_sensitive(self) -> None:
        with pytest.raises(ValueError):
            MetricType("SYSTEM")

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValueError):
            MetricType(None)


class TestDriveType:
    """测试DriveType"""

    def test_normal_value(self) -> None:
        assert DriveType.SAFE.value == "safe"

    def test_empty_not_member(self) -> None:
        with pytest.raises(ValueError):
            DriveType("")

    def test_boundary_all_members(self) -> None:
        assert len(list(DriveType)) == 3

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValueError):
            DriveType(None)


class TestTaskType:
    """测试TaskType"""

    def test_normal_value(self) -> None:
        assert TaskType.GAIN.value == "gain"

    def test_empty_not_member(self) -> None:
        with pytest.raises(ValueError):
            TaskType("")

    def test_boundary_all_members(self) -> None:
        assert len(list(TaskType)) == 3

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValueError):
            TaskType(None)


class TestTaskStatus:
    """测试TaskStatus"""

    def test_normal_value(self) -> None:
        assert TaskStatus.PENDING.value == "pending"

    def test_empty_not_member(self) -> None:
        with pytest.raises(ValueError):
            TaskStatus("")

    def test_boundary_all_members(self) -> None:
        assert len(list(TaskStatus)) == 5

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValueError):
            TaskStatus(None)


class TestPredictionLevel:
    """测试PredictionLevel"""

    def test_normal_value(self) -> None:
        assert PredictionLevel.LOW.value == "low"

    def test_empty_not_member(self) -> None:
        with pytest.raises(ValueError):
            PredictionLevel("")

    def test_boundary_all_members(self) -> None:
        assert len(list(PredictionLevel)) == 3

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValueError):
            PredictionLevel(None)


class TestScenarioType:
    """测试ScenarioType"""

    def test_normal_value(self) -> None:
        assert ScenarioType.EMERGENCY.value == "emergency"

    def test_empty_not_member(self) -> None:
        with pytest.raises(ValueError):
            ScenarioType("")

    def test_boundary_all_members(self) -> None:
        assert len(list(ScenarioType)) == 4

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValueError):
            ScenarioType(None)


class TestAdjustmentType:
    """测试AdjustmentType"""

    def test_normal_value(self) -> None:
        assert AdjustmentType.WEIGHT.value == "weight"

    def test_empty_not_member(self) -> None:
        with pytest.raises(ValueError):
            AdjustmentType("")

    def test_boundary_all_members(self) -> None:
        assert len(list(AdjustmentType)) == 4

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValueError):
            AdjustmentType(None)


class TestErrorCode:
    """测试ErrorCode"""

    def test_normal_value(self) -> None:
        assert ErrorCode.SUCCESS.value == 0

    def test_empty_not_member(self) -> None:
        with pytest.raises(ValueError):
            ErrorCode("")

    def test_boundary_all_members(self) -> None:
        assert len(list(ErrorCode)) == 19

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ValueError):
            ErrorCode(None)
