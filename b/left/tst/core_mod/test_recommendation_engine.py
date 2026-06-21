"""推荐引擎测试"""
from typing import Any, Dict

from root.left.app.left.src.core_mod.recommendation_engine import RecommendationEngine


class TestRecommendationEngine:
    """推荐引擎测试"""

    def test_cpu_recommendation(self) -> None:
        engine = RecommendationEngine({})
        state = {"cpu_percent": 85.0}
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "CPU" in recs[0].title

    def test_memory_recommendation(self) -> None:
        engine = RecommendationEngine({})
        state = {"memory_percent": 85.0}
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "内存" in recs[0].title

    def test_disk_recommendation(self) -> None:
        engine = RecommendationEngine({})
        state = {"disk_usage": {"percent": 95.0}}
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "磁盘" in recs[0].title

    def test_gap_recommendations(self) -> None:
        engine = RecommendationEngine({})
        drive_state = {"gaps": {"safe": 0.7, "gain": 0.8, "eff": 0.9}}
        recs = engine.generate({}, drive_state, {})
        assert len(recs) == 3

    def test_effect_recommendation(self) -> None:
        engine = RecommendationEngine({})
        effect_summary = {"latest": {"performance": 0.1}}
        recs = engine.generate({}, {}, effect_summary)
        assert len(recs) == 1
        assert "表现分" in recs[0].title

    def test_to_dict_list(self) -> None:
        engine = RecommendationEngine({})
        recs = engine.generate({"cpu_percent": 85.0}, {}, {})
        dlist = engine.to_dict_list(recs)
        assert isinstance(dlist, list)
        assert "title" in dlist[0]

    def test_collected_data_error_recommendation(self) -> None:
        engine = RecommendationEngine({})
        state: Dict[str, Any] = {
            "collected_data": {
                "app_log": {
                    "name": "app_log",
                    "success": True,
                    "data": {
                        "lines": ["ERROR timeout"] * 5 + ["WARN slow"] * 2,
                        "counts": {"error": 5, "warn": 2},
                    },
                }
            }
        }
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "错误日志" in recs[0].title

    def test_collected_data_warn_only_recommendation(self) -> None:
        engine = RecommendationEngine({})
        state: Dict[str, Any] = {
            "collected_data": {
                "app_log": {
                    "name": "app_log",
                    "success": True,
                    "data": {
                        "lines": ["WARN slow"] * 3,
                        "counts": {"error": 0, "warn": 3},
                    },
                }
            }
        }
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "警告日志" in recs[0].title

    def test_collected_data_empty(self) -> None:
        engine = RecommendationEngine({})
        state: Dict[str, Any] = {"collected_data": {"app_log": {"name": "app_log", "success": True, "data": {}}}}
        recs = engine.generate(state, {}, {})
        assert len(recs) == 0

    def test_fs_pycache_recommendation(self) -> None:
        engine = RecommendationEngine({"fs_pycache_high": 5})
        state: Dict[str, Any] = {
            "collected_data": {
                "filesystem_scan": {
                    "name": "filesystem_scan",
                    "success": True,
                    "data": {"project_root": "/tmp", "py_files": 10, "test_files": 5, "pycache_files": 10},
                }
            }
        }
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "缓存" in recs[0].title

    def test_fs_log_recommendation(self) -> None:
        engine = RecommendationEngine({"fs_log_high": 1})
        state: Dict[str, Any] = {
            "collected_data": {
                "filesystem_scan": {
                    "name": "filesystem_scan",
                    "success": True,
                    "data": {"project_root": "/tmp", "py_files": 10, "test_files": 5, "log_files": 3},
                }
            }
        }
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "日志" in recs[0].title

    def test_fs_test_ratio_recommendation(self) -> None:
        engine = RecommendationEngine({"fs_test_ratio_low": 0.5})
        state: Dict[str, Any] = {
            "collected_data": {
                "filesystem_scan": {
                    "name": "filesystem_scan",
                    "success": True,
                    "data": {"project_root": "/tmp", "py_files": 10, "test_files": 2},
                }
            }
        }
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "测试" in recs[0].title

    def test_fs_docs_incomplete_recommendation(self) -> None:
        engine = RecommendationEngine({})
        state: Dict[str, Any] = {
            "collected_data": {
                "filesystem_scan": {
                    "name": "filesystem_scan",
                    "success": True,
                    "data": {"project_root": "/tmp", "py_files": 10, "test_files": 10, "docs_complete": False},
                }
            }
        }
        recs = engine.generate(state, {}, {})
        assert len(recs) == 1
        assert "文档" in recs[0].title

    def test_fs_clean(self) -> None:
        engine = RecommendationEngine({"fs_pycache_high": 100, "fs_log_high": 100, "fs_test_ratio_low": 0.1})
        state: Dict[str, Any] = {
            "collected_data": {
                "filesystem_scan": {
                    "name": "filesystem_scan",
                    "success": True,
                    "data": {"project_root": "/tmp", "py_files": 10, "test_files": 10, "pycache_files": 5, "log_files": 2, "docs_complete": True},
                }
            }
        }
        recs = engine.generate(state, {}, {})
        assert len(recs) == 0
