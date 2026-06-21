"""仪表盘测试"""

from root.left.app.left.src.core_mod.dashboard import Dashboard


class TestDashboard:
    """仪表盘测试"""

    def test_build_report(self) -> None:
        dashboard = Dashboard({})
        report = dashboard.build_report(
            state={"cpu_percent": 10.0},
            drive_state={"gaps": {}},
            recommendations=[{"title": "test", "priority": 0.9}],
            effect_summary={"latest": {}},
            task_pool_snapshot={"total": 1},
            loop_count=5,
        )
        assert report["loop_count"] == 5
        assert report["recommendations"][0]["title"] == "test"
        assert "generated_at" in report

    def test_to_json(self) -> None:
        dashboard = Dashboard({})
        report = dashboard.build_report({}, {}, [], {}, {}, 1)
        json_str = dashboard.to_json(report)
        assert "loop_count" in json_str

    def test_to_markdown(self) -> None:
        dashboard = Dashboard({})
        report = dashboard.build_report(
            state={"cpu_percent": 10.0},
            drive_state={"gaps": {}},
            recommendations=[{"title": "CPU", "reason": "high", "action": "cleanup", "priority": 0.9}],
            effect_summary={"latest": {}},
            task_pool_snapshot={"total": 1},
            loop_count=2,
        )
        md = dashboard.to_markdown(report)
        assert "Agent 运行仪表盘" in md
        assert "CPU" in md
        assert "cleanup" in md

    def test_build_summary_with_data(self) -> None:
        dashboard = Dashboard({})
        report = dashboard.build_report(
            state={"cpu_percent": 55.0, "memory_percent": 70.0},
            drive_state={"gaps": {}},
            recommendations=[{"title": "清理磁盘", "priority": 0.9}],
            effect_summary={},
            task_pool_snapshot={"total": 5, "pending": 2},
            loop_count=10,
        )
        summary = dashboard.build_summary(report)
        assert summary["loop_count"] == 10
        assert summary["cpu_percent"] == 55.0
        assert summary["memory_percent"] == 70.0
        assert summary["recommendation_count"] == 1
        assert summary["top_recommendation"] == "清理磁盘"
        assert summary["task_pool_total"] == 5
        assert summary["task_pool_pending"] == 2

    def test_build_summary_empty(self) -> None:
        dashboard = Dashboard({})
        report = dashboard.build_report({}, {}, [], {}, {}, 0)
        summary = dashboard.build_summary(report)
        assert summary["loop_count"] == 0
        assert summary["cpu_percent"] == "N/A"
        assert summary["top_recommendation"] is None
        assert summary["task_pool_total"] == 0

    def test_to_summary_text_with_data(self) -> None:
        dashboard = Dashboard({})
        report = dashboard.build_report(
            state={"cpu_percent": 55.0, "memory_percent": 70.0},
            drive_state={},
            recommendations=[{"title": "清理磁盘", "priority": 0.9}],
            effect_summary={},
            task_pool_snapshot={"total": 5},
            loop_count=10,
        )
        text = dashboard.to_summary_text(report)
        assert "循环=10" in text
        assert "CPU=55.0%" in text
        assert "清理磁盘" in text

    def test_to_summary_text_empty(self) -> None:
        dashboard = Dashboard({})
        report = dashboard.build_report({}, {}, [], {}, {}, 0)
        text = dashboard.to_summary_text(report)
        assert "循环=0" in text
        assert "N/A" in text
        assert "无" in text
