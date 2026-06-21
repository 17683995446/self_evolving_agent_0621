"""配置模板与快速初始化测试"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
import yaml

from root.left.app.left.src.cli import build_parser, main
from root.left.app.left.src.utils_main.config_templates import (
    build_custom_config,
    get_template,
    get_template_raw,
    list_templates,
    render_template,
    save_template,
)


# ---------------------------------------------------------------------------
# 模板查询测试
# ---------------------------------------------------------------------------

class TestListTemplates:
    """测试模板列表"""

    def test_list_templates_returns_list(self) -> None:
        templates = list_templates()
        assert isinstance(templates, list)
        assert len(templates) == 4

    def test_list_templates_has_required_fields(self) -> None:
        templates = list_templates()
        for t in templates:
            assert "name" in t
            assert "description" in t

    def test_list_templates_contains_known_names(self) -> None:
        templates = list_templates()
        names = [t["name"] for t in templates]
        assert "minimal" in names
        assert "standard" in names
        assert "production" in names
        assert "high-frequency" in names


class TestGetTemplate:
    """测试获取模板"""

    def test_get_template_returns_merged_config(self) -> None:
        config = get_template("standard")
        assert config is not None
        # 应包含默认配置的键
        assert "phase1" in config
        assert "phase2" in config
        assert "phase3" in config
        assert "loop_interval" in config

    def test_get_template_applies_overrides(self) -> None:
        config = get_template("minimal")
        assert config is not None
        # minimal 模板应覆盖 loop_interval
        assert config["loop_interval"] == 0.5
        assert config["max_loops"] == 10

    def test_get_template_production_has_health_check(self) -> None:
        config = get_template("production")
        assert config is not None
        assert config["health_check"]["enabled"] is True
        assert config["max_loops"] == 0  # 无限循环

    def test_get_template_unknown_returns_none(self) -> None:
        assert get_template("nonexistent") is None

    def test_get_template_does_not_mutate_default(self) -> None:
        """获取模板不应修改 DEFAULT_CONFIG"""
        from root.left.app.left.src.utils_main.config_loader import DEFAULT_CONFIG
        original_interval = DEFAULT_CONFIG["loop_interval"]
        get_template("minimal")
        assert DEFAULT_CONFIG["loop_interval"] == original_interval


class TestGetTemplateRaw:
    """测试获取原始模板覆盖配置"""

    def test_get_template_raw_returns_overrides_only(self) -> None:
        raw = get_template_raw("minimal")
        assert raw is not None
        # 原始配置只包含覆盖项，不应包含所有默认键
        assert "loop_interval" in raw
        assert raw["loop_interval"] == 0.5

    def test_get_template_raw_unknown_returns_none(self) -> None:
        assert get_template_raw("nonexistent") is None


# ---------------------------------------------------------------------------
# 模板渲染测试
# ---------------------------------------------------------------------------

class TestRenderTemplate:
    """测试模板渲染为 YAML"""

    def test_render_template_returns_yaml(self) -> None:
        text = render_template("standard")
        assert isinstance(text, str)
        # 应能被 yaml 解析
        data = yaml.safe_load(text)
        assert isinstance(data, dict)

    def test_render_template_contains_keys(self) -> None:
        text = render_template("standard")
        assert "phase1" in text
        assert "loop_interval" in text

    def test_render_template_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="未知模板"):
            render_template("nonexistent")


# ---------------------------------------------------------------------------
# 模板保存测试
# ---------------------------------------------------------------------------

class TestSaveTemplate:
    """测试模板保存为文件"""

    def test_save_template_creates_file(self, tmp_path) -> None:
        config_path = str(tmp_path / "test_env.yaml")
        with patch(
            "root.left.app.left.src.utils_main.config_templates._get_config_file_path",
            return_value=config_path,
        ):
            result_path = save_template("standard", "test_env")
            assert result_path == config_path
            assert os.path.exists(config_path)

            # 验证文件内容
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert "phase1" in data
            assert "loop_interval" in data

    def test_save_template_existing_without_force_raises(self, tmp_path) -> None:
        config_path = str(tmp_path / "existing.yaml")
        # 先创建文件
        with open(config_path, "w") as f:
            f.write("existing: content")

        with patch(
            "root.left.app.left.src.utils_main.config_templates._get_config_file_path",
            return_value=config_path,
        ):
            with pytest.raises(FileExistsError):
                save_template("standard", "existing")

    def test_save_template_with_force_overwrites(self, tmp_path) -> None:
        config_path = str(tmp_path / "force_test.yaml")
        # 先创建文件
        with open(config_path, "w") as f:
            f.write("old: content")

        with patch(
            "root.left.app.left.src.utils_main.config_templates._get_config_file_path",
            return_value=config_path,
        ):
            result_path = save_template("standard", "force_test", force=True)
            assert result_path == config_path

            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert "phase1" in data
            assert "old" not in data

    def test_save_template_unknown_raises(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="未知模板"):
            save_template("nonexistent", "env")


# ---------------------------------------------------------------------------
# 自定义配置构建测试
# ---------------------------------------------------------------------------

class TestBuildCustomConfig:
    """测试自定义配置构建"""

    def test_build_custom_config_defaults(self) -> None:
        config = build_custom_config()
        assert config["max_loops"] == 100
        assert config["loop_interval"] == 1.0
        assert config["action_executor"]["dry_run"] is True
        assert config["health_check"]["enabled"] is False

    def test_build_custom_config_custom_values(self) -> None:
        config = build_custom_config(
            max_loops=500,
            loop_interval=0.5,
            dry_run=False,
            health_check=True,
            health_port=9090,
            log_level="DEBUG",
        )
        assert config["max_loops"] == 500
        assert config["loop_interval"] == 0.5
        assert config["action_executor"]["dry_run"] is False
        assert config["health_check"]["enabled"] is True
        assert config["health_check"]["port"] == 9090
        assert config["log_level"] == "DEBUG"

    def test_build_custom_config_includes_all_sections(self) -> None:
        config = build_custom_config()
        assert "phase1" in config
        assert "phase2" in config
        assert "phase3" in config


# ---------------------------------------------------------------------------
# CLI init 子命令测试
# ---------------------------------------------------------------------------

class TestCLIInitList:
    """测试 init --list"""

    def test_init_list_shows_templates(self, capsys) -> None:
        exit_code = main(["init", "--list"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "可用配置模板" in captured.out
        assert "minimal" in captured.out
        assert "standard" in captured.out
        assert "production" in captured.out

    def test_init_list_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["init", "--list"])
        assert args.command == "init"
        assert args.list is True


class TestCLIInitShow:
    """测试 init --show"""

    def test_init_show_standard(self, capsys) -> None:
        exit_code = main(["init", "--show", "standard"])
        captured = capsys.readouterr()
        assert exit_code == 0
        # 应输出 YAML 格式
        assert "phase1" in captured.out
        assert "loop_interval" in captured.out

    def test_init_show_unknown_returns_2(self, capsys) -> None:
        exit_code = main(["init", "--show", "nonexistent"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "错误" in captured.err

    def test_init_show_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["init", "--show", "minimal"])
        assert args.show == "minimal"


class TestCLIInitTemplate:
    """测试 init --template"""

    def test_init_template_creates_file(self, capsys, tmp_path) -> None:
        config_path = str(tmp_path / "new_env.yaml")
        with patch(
            "root.left.app.left.src.utils_main.config_templates._get_config_file_path",
            return_value=config_path,
        ):
            exit_code = main(["init", "--template", "standard", "--env", "new_env"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "配置文件已创建" in captured.out
        assert os.path.exists(config_path)

    def test_init_template_existing_without_force_fails(self, capsys, tmp_path) -> None:
        config_path = str(tmp_path / "exists.yaml")
        with open(config_path, "w") as f:
            f.write("old: data")
        with patch(
            "root.left.app.left.src.utils_main.config_templates._get_config_file_path",
            return_value=config_path,
        ):
            exit_code = main(["init", "--template", "standard", "--env", "exists"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "已存在" in captured.err
        assert "--force" in captured.err

    def test_init_template_with_force_overwrites(self, capsys, tmp_path) -> None:
        config_path = str(tmp_path / "overwrite.yaml")
        with open(config_path, "w") as f:
            f.write("old: data")
        with patch(
            "root.left.app.left.src.utils_main.config_templates._get_config_file_path",
            return_value=config_path,
        ):
            exit_code = main(["init", "--template", "standard", "--env", "overwrite", "--force"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "配置文件已创建" in captured.out

    def test_init_template_unknown_fails(self, capsys) -> None:
        exit_code = main(["init", "--template", "nonexistent", "--env", "test"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "错误" in captured.err

    def test_init_template_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["init", "--template", "standard", "--env", "dev"])
        assert args.template == "standard"
        assert args.env == "dev"
        assert args.force is False


class TestCLIInitNoArgs:
    """测试 init 无参数"""

    def test_init_no_args_shows_usage(self, capsys) -> None:
        exit_code = main(["init"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "用法" in captured.out
        assert "--list" in captured.out
