"""自动技能进化模块测试"""
import os
import tempfile
from typing import Any, Dict

from root.left.app.left.src.core_mod.auto_skill_evolver import AutoSkillEvolver, SKILL_TEMPLATES


class TestAutoSkillEvolver:
    """测试 Agent 自我生成并加载技能的能力"""

    def test_list_available_templates(self) -> None:
        evolver = AutoSkillEvolver({"skill_dir": tempfile.mkdtemp()})
        templates = evolver.list_available_templates()
        assert "test_coverage_low" in templates
        assert "log_accumulation" in templates
        assert "pycache_bloat" in templates

    def test_dry_run_does_not_write_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            evolver = AutoSkillEvolver({"skill_dir": tmpdir, "dry_run": True})
            gaps: list[Dict[str, Any]] = [{"type": "test_coverage_low"}]
            result = evolver.evolve(gaps)
            assert result["total"] == 1
            assert len(result["evolved"]) == 1
            assert result["evolved"][0]["dry_run"] is True
            assert not os.path.exists(result["evolved"][0]["file_path"])

    def test_evolve_generates_and_loads_skill(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            evolver = AutoSkillEvolver({"skill_dir": tmpdir, "dry_run": False, "skill_config": {}})
            gaps: list[Dict[str, Any]] = [{"type": "test_coverage_low"}]
            result = evolver.evolve(gaps)
            assert result["total"] == 1
            assert len(result["evolved"]) == 1
            evolved = result["evolved"][0]
            assert evolved["dry_run"] is False
            assert evolved["loaded"] is True
            assert evolved["healthy"] is True
            assert os.path.exists(evolved["file_path"])
            assert evolver.is_skill_loaded(evolved["module_name"]) is True

    def test_unknown_gap_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            evolver = AutoSkillEvolver({"skill_dir": tmpdir, "dry_run": False})
            gaps: list[Dict[str, Any]] = [{"type": "unknown_gap"}]
            result = evolver.evolve(gaps)
            assert result["total"] == 1
            assert len(result["evolved"]) == 0

    def test_multiple_gaps_evolve_multiple_skills(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            evolver = AutoSkillEvolver({"skill_dir": tmpdir, "dry_run": False, "skill_config": {}})
            gaps: list[Dict[str, Any]] = [
                {"type": "log_accumulation"},
                {"type": "pycache_bloat"},
            ]
            result = evolver.evolve(gaps)
            assert result["total"] == 2
            assert len(result["evolved"]) == 2
            for evolved in result["evolved"]:
                assert evolved["loaded"] is True
                assert evolved["healthy"] is True

    def test_skill_template_source_has_required_class(self) -> None:
        for template in SKILL_TEMPLATES.values():
            assert template.class_name in template.source_code
            assert "BaseModule" in template.source_code
