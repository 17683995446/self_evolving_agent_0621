"""配置差异对比与变更审计测试"""
from __future__ import annotations

import json
import os
import tempfile

import pytest
import yaml

from root.left.app.left.src.cli import main
from root.left.app.left.src.utils_main.config_diff import (
    ConfigDiff,
    diff_against_defaults,
    diff_configs,
    diff_files,
    generate_audit_report,
    render_diff,
    save_audit_report,
)
from root.left.app.left.src.utils_main.config_loader import DEFAULT_CONFIG


# ---------------------------------------------------------------------------
# 测试数据
# ---------------------------------------------------------------------------

CONFIG_A = {
    "loop_interval": 1.0,
    "max_loops": 1000,
    "log_level": "INFO",
    "phase1": {
        "sensory": {
            "collectors": {"system": {"enabled": True, "interval": 1.0}},
        },
    },
}

CONFIG_B = {
    "loop_interval": 2.0,  # 修改
    "max_loops": 1000,
    "log_level": "DEBUG",  # 修改
    "new_key": "new_value",  # 新增
    "phase1": {
        "sensory": {
            "collectors": {"system": {"enabled": False, "interval": 1.0}},  # 修改
        },
    },
}

CONFIG_C = {
    "loop_interval": 1.0,
    "max_loops": 1000,
    "log_level": "INFO",
    # phase1 被删除
}


# ---------------------------------------------------------------------------
# ConfigDiff 数据类测试
# ---------------------------------------------------------------------------

class TestConfigDiff:
    """测试 ConfigDiff 数据类"""

    def test_to_dict(self):
        d = ConfigDiff("a.b", 1, 2, "modified")
        result = d.to_dict()
        assert result["path"] == "a.b"
        assert result["old_value"] == 1
        assert result["new_value"] == 2
        assert result["change_type"] == "modified"

    def test_description_known_path(self):
        d = ConfigDiff("loop_interval", 1.0, 2.0, "modified")
        assert "主循环间隔" in d.description

    def test_description_unknown_path(self):
        d = ConfigDiff("unknown.path", 1, 2, "modified")
        assert d.description == ""


# ---------------------------------------------------------------------------
# diff_configs 测试
# ---------------------------------------------------------------------------

class TestDiffConfigs:
    """测试配置对比"""

    def test_identical_configs_no_diff(self):
        diffs = diff_configs(CONFIG_A, CONFIG_A)
        assert diffs == []

    def test_modified_value(self):
        diffs = diff_configs(CONFIG_A, CONFIG_B)
        paths = [d.path for d in diffs]
        assert "loop_interval" in paths
        assert "log_level" in paths

    def test_added_key(self):
        diffs = diff_configs(CONFIG_A, CONFIG_B)
        added = [d for d in diffs if d.change_type == "added"]
        paths = [d.path for d in added]
        assert "new_key" in paths

    def test_removed_key(self):
        diffs = diff_configs(CONFIG_A, CONFIG_C)
        removed = [d for d in diffs if d.change_type == "removed"]
        paths = [d.path for d in removed]
        assert "phase1" in paths

    def test_nested_modified(self):
        diffs = diff_configs(CONFIG_A, CONFIG_B)
        phase1_diffs = [d for d in diffs if d.path.startswith("phase1")]
        assert len(phase1_diffs) > 0
        # system.enabled 从 True 改为 False
        enabled_diff = [d for d in phase1_diffs if d.path == "phase1.sensory.collectors.system.enabled"]
        assert len(enabled_diff) == 1
        assert enabled_diff[0].old_value is True
        assert enabled_diff[0].new_value is False

    def test_change_type_modified(self):
        diffs = diff_configs(CONFIG_A, CONFIG_B)
        modified = [d for d in diffs if d.change_type == "modified"]
        assert len(modified) > 0

    def test_diffs_sorted_by_path(self):
        diffs = diff_configs(CONFIG_A, CONFIG_B)
        paths = [d.path for d in diffs]
        assert paths == sorted(paths)

    def test_empty_configs(self):
        diffs = diff_configs({}, {})
        assert diffs == []

    def test_added_to_empty(self):
        diffs = diff_configs({}, {"a": 1})
        assert len(diffs) == 1
        assert diffs[0].change_type == "added"
        assert diffs[0].new_value == 1

    def test_removed_to_empty(self):
        diffs = diff_configs({"a": 1}, {})
        assert len(diffs) == 1
        assert diffs[0].change_type == "removed"
        assert diffs[0].old_value == 1

    def test_prefix(self):
        diffs = diff_configs({"a": 1}, {"a": 2}, prefix="root")
        assert diffs[0].path == "root.a"


# ---------------------------------------------------------------------------
# diff_against_defaults 测试
# ---------------------------------------------------------------------------

class TestDiffAgainstDefaults:
    """测试与默认配置对比"""

    def test_identical_to_defaults(self):
        diffs = diff_against_defaults(DEFAULT_CONFIG)
        assert diffs == []

    def test_modified_value(self):
        config = dict(DEFAULT_CONFIG)
        config["loop_interval"] = 5.0
        diffs = diff_against_defaults(config)
        modified = [d for d in diffs if d.change_type == "modified"]
        assert len(modified) == 1
        assert modified[0].path == "loop_interval"
        assert modified[0].old_value == 1.0
        assert modified[0].new_value == 5.0

    def test_added_key(self):
        config = dict(DEFAULT_CONFIG)
        config["custom_key"] = "custom"
        diffs = diff_against_defaults(config)
        added = [d for d in diffs if d.change_type == "added"]
        assert len(added) == 1
        assert added[0].path == "custom_key"


# ---------------------------------------------------------------------------
# diff_files 测试
# ---------------------------------------------------------------------------

class TestDiffFiles:
    """测试文件对比"""

    def test_identical_files(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f1, \
             tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f2:
            yaml.dump(CONFIG_A, f1)
            yaml.dump(CONFIG_A, f2)
            f1_path, f2_path = f1.name, f2.name
        try:
            diffs = diff_files(f1_path, f2_path)
            assert diffs == []
        finally:
            os.unlink(f1_path)
            os.unlink(f2_path)

    def test_different_files(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f1, \
             tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f2:
            yaml.dump(CONFIG_A, f1)
            yaml.dump(CONFIG_B, f2)
            f1_path, f2_path = f1.name, f2.name
        try:
            diffs = diff_files(f1_path, f2_path)
            assert len(diffs) > 0
            paths = [d.path for d in diffs]
            assert "loop_interval" in paths
        finally:
            os.unlink(f1_path)
            os.unlink(f2_path)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            diff_files("/nonexistent/a.yaml", "/nonexistent/b.yaml")


# ---------------------------------------------------------------------------
# render_diff 测试
# ---------------------------------------------------------------------------

class TestRenderDiff:
    """测试差异渲染"""

    def test_no_diffs(self):
        result = render_diff([])
        assert "无差异" in result

    def test_with_diffs(self):
        diffs = diff_configs(CONFIG_A, CONFIG_B)
        result = render_diff(diffs)
        assert "配置差异" in result
        assert "loop_interval" in result

    def test_with_description(self):
        diffs = [ConfigDiff("loop_interval", 1.0, 2.0, "modified")]
        result = render_diff(diffs, show_description=True)
        assert "主循环间隔" in result

    def test_contains_counts(self):
        diffs = diff_configs(CONFIG_A, CONFIG_B)
        result = render_diff(diffs)
        assert "新增" in result
        assert "修改" in result


# ---------------------------------------------------------------------------
# AuditReport 测试
# ---------------------------------------------------------------------------

class TestAuditReport:
    """测试审计报告"""

    def test_generate_report(self):
        config = dict(DEFAULT_CONFIG)
        config["loop_interval"] = 5.0
        report = generate_audit_report(config, env="dev")
        assert report.env == "dev"
        assert report.total_changes == 1
        assert report.modified_count == 1
        assert report.added_count == 0
        assert report.removed_count == 0

    def test_report_to_text(self):
        config = dict(DEFAULT_CONFIG)
        config["loop_interval"] = 5.0
        report = generate_audit_report(config, env="dev")
        text = report.to_text()
        assert "配置审计报告" in text
        assert "loop_interval" in text

    def test_report_to_json(self):
        config = dict(DEFAULT_CONFIG)
        config["loop_interval"] = 5.0
        report = generate_audit_report(config, env="dev")
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["env"] == "dev"
        assert data["total_changes"] == 1

    def test_report_to_dict(self):
        config = dict(DEFAULT_CONFIG)
        config["custom"] = "value"
        report = generate_audit_report(config, env="dev")
        d = report.to_dict()
        assert d["env"] == "dev"
        assert d["total_changes"] == 1
        assert d["added_count"] == 1

    def test_report_with_custom_baseline(self):
        baseline = {"a": 1, "b": 2}
        config = {"a": 1, "b": 3, "c": 4}
        report = generate_audit_report(config, env="test", baseline=baseline)
        assert report.modified_count == 1
        assert report.added_count == 1

    def test_report_no_changes(self):
        report = generate_audit_report(DEFAULT_CONFIG, env="dev")
        assert report.total_changes == 0
        text = report.to_text()
        assert "无变更" in text

    def test_report_config_source(self):
        report = generate_audit_report(DEFAULT_CONFIG, env="dev", config_source="env")
        assert report.config_source == "env"


# ---------------------------------------------------------------------------
# save_audit_report 测试
# ---------------------------------------------------------------------------

class TestSaveAuditReport:
    """测试保存审计报告"""

    def test_save_text(self):
        report = generate_audit_report(DEFAULT_CONFIG, env="dev")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            path = f.name
        try:
            save_audit_report(report, path, fmt="text")
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "配置审计报告" in content
        finally:
            os.unlink(path)

    def test_save_json(self):
        report = generate_audit_report(DEFAULT_CONFIG, env="dev")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            path = f.name
        try:
            save_audit_report(report, path, fmt="json")
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert data["env"] == "dev"
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLIDiff:
    """测试 diff 子命令"""

    def test_diff_no_args_shows_help(self, capsys):
        rc = main(["diff"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "用法" in captured.out

    def test_diff_file_not_found(self, capsys):
        rc = main(["diff", "--file", "/nonexistent/a.yaml", "--file2", "/nonexistent/b.yaml"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "错误" in captured.err

    def test_diff_files(self, capsys, tmp_path):
        file_a = tmp_path / "a.yaml"
        file_b = tmp_path / "b.yaml"
        file_a.write_text(yaml.dump(CONFIG_A), encoding="utf-8")
        file_b.write_text(yaml.dump(CONFIG_B), encoding="utf-8")
        rc = main(["diff", "--file", str(file_a), "--file2", str(file_b)])
        captured = capsys.readouterr()
        assert rc == 0
        assert "配置差异" in captured.out

    def test_diff_files_json(self, capsys, tmp_path):
        file_a = tmp_path / "a.yaml"
        file_b = tmp_path / "b.yaml"
        file_a.write_text(yaml.dump(CONFIG_A), encoding="utf-8")
        file_b.write_text(yaml.dump(CONFIG_B), encoding="utf-8")
        rc = main(["diff", "--file", str(file_a), "--file2", str(file_b), "--json"])
        captured = capsys.readouterr()
        assert rc == 0
        data = json.loads(captured.out)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_diff_files_describe(self, capsys, tmp_path):
        file_a = tmp_path / "a.yaml"
        file_b = tmp_path / "b.yaml"
        file_a.write_text(yaml.dump(CONFIG_A), encoding="utf-8")
        file_b.write_text(yaml.dump(CONFIG_B), encoding="utf-8")
        rc = main(["diff", "--file", str(file_a), "--file2", str(file_b), "--describe"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "说明" in captured.out

    def test_diff_identical_files(self, capsys, tmp_path):
        file_a = tmp_path / "a.yaml"
        file_b = tmp_path / "b.yaml"
        file_a.write_text(yaml.dump(CONFIG_A), encoding="utf-8")
        file_b.write_text(yaml.dump(CONFIG_A), encoding="utf-8")
        rc = main(["diff", "--file", str(file_a), "--file2", str(file_b)])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无差异" in captured.out


# ---------------------------------------------------------------------------
# 帮助系统集成
# ---------------------------------------------------------------------------

class TestHelpIntegration:
    """测试帮助系统是否包含 diff 命令"""

    def test_help_all_contains_diff(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "diff" in captured.out

    def test_help_diff(self, capsys):
        rc = main(["help", "diff"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "diff" in captured.out
        assert "对比" in captured.out or "差异" in captured.out
