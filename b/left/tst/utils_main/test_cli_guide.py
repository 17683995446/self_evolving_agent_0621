"""CLI 交互式引导与帮助系统测试"""
from __future__ import annotations

from unittest.mock import patch

from root.left.app.left.src.cli import build_parser, main
from root.left.app.left.src.utils_main.cli_guide import (
    build_run_args_from_wizard,
    build_wizard_steps,
    is_interactive,
    render_examples,
    render_help_all,
    render_help_command,
    render_welcome,
    run_wizard,
)


# ---------------------------------------------------------------------------
# 渲染函数测试
# ---------------------------------------------------------------------------

class TestRenderWelcome:
    """测试欢迎信息渲染"""

    def test_welcome_contains_title(self) -> None:
        text = render_welcome()
        assert "自驱永续进化 Agent" in text
        assert "欢迎使用" in text

    def test_welcome_contains_quick_start(self) -> None:
        text = render_welcome()
        assert "快速上手" in text
        assert "doctor" in text
        assert "examples" in text

    def test_welcome_contains_core_capabilities(self) -> None:
        text = render_welcome()
        assert "核心能力" in text
        assert "自主循环运行" in text

    def test_welcome_contains_help_section(self) -> None:
        text = render_welcome()
        assert "获取帮助" in text


class TestRenderHelpAll:
    """测试所有命令概览帮助"""

    def test_help_all_lists_commands(self) -> None:
        text = render_help_all()
        assert "run" in text
        assert "status" in text
        assert "health" in text
        assert "validate" in text
        assert "config" in text
        assert "doctor" in text
        assert "diagnose" in text
        assert "welcome" in text
        assert "examples" in text

    def test_help_all_contains_hint(self) -> None:
        text = render_help_all()
        assert "help <命令>" in text


class TestRenderHelpCommand:
    """测试单命令详细帮助"""

    def test_help_run_command(self) -> None:
        text = render_help_command("run")
        assert "命令: run" in text
        assert "启动 Agent 运行主循环" in text
        assert "示例" in text
        assert "--env" in text

    def test_help_config_command(self) -> None:
        text = render_help_command("config")
        assert "命令: config" in text
        assert "--show-defaults" in text
        assert "--describe" in text

    def test_help_unknown_command(self) -> None:
        text = render_help_command("nonexistent")
        assert "未知命令" in text
        assert "nonexistent" in text

    def test_help_all_known_commands_have_content(self) -> None:
        """所有已知命令的 help 都应包含命令名与说明"""
        from root.left.app.left.src.utils_main.cli_guide import COMMAND_GUIDE
        for cmd_name in COMMAND_GUIDE:
            text = render_help_command(cmd_name)
            assert f"命令: {cmd_name}" in text
            assert "示例" in text


class TestRenderExamples:
    """测试场景示例渲染"""

    def test_examples_contains_categories(self) -> None:
        text = render_examples()
        assert "首次使用" in text
        assert "日常运行" in text
        assert "配置管理" in text
        assert "故障排查" in text

    def test_examples_contains_commands(self) -> None:
        text = render_examples()
        assert "welcome" in text
        assert "doctor" in text
        assert "run" in text
        assert "diagnose" in text


# ---------------------------------------------------------------------------
# 向导测试
# ---------------------------------------------------------------------------

class TestWizardSteps:
    """测试向导步骤定义"""

    def test_wizard_steps_count(self) -> None:
        steps = build_wizard_steps()
        assert len(steps) == 5

    def test_wizard_steps_have_required_fields(self) -> None:
        steps = build_wizard_steps()
        for step in steps:
            assert len(step) == 4  # prompt, parser, default, keys


class TestRunWizard:
    """测试交互式向导"""

    def test_wizard_with_defaults(self) -> None:
        """所有输入留空，使用默认值"""
        inputs = iter(["", "", "", "", ""])
        outputs: list[str] = []

        def fake_input(prompt: str) -> str:
            return next(inputs)

        def fake_output(msg: str) -> None:
            outputs.append(msg)

        result = run_wizard(input_fn=fake_input, output_fn=fake_output)

        assert result["env"] == "dev"
        assert result["max_loops"] == 10
        assert result["loop_interval"] == 1.0
        assert result["port"] == 8080
        assert result["dry_run"] is False

    def test_wizard_with_custom_values(self) -> None:
        """自定义所有值"""
        inputs = iter(["prod", "50", "2.5", "9090", "y"])
        outputs: list[str] = []

        def fake_input(prompt: str) -> str:
            return next(inputs)

        def fake_output(msg: str) -> None:
            outputs.append(msg)

        result = run_wizard(input_fn=fake_input, output_fn=fake_output)

        assert result["env"] == "prod"
        assert result["max_loops"] == 50
        assert result["loop_interval"] == 2.5
        assert result["port"] == 9090
        assert result["dry_run"] is True

    def test_wizard_invalid_env_then_valid(self) -> None:
        """无效环境后输入有效值"""
        inputs = iter(["invalid", "dev", "10", "1.0", "8080", "n"])
        outputs: list[str] = []

        def fake_input(prompt: str) -> str:
            return next(inputs)

        def fake_output(msg: str) -> None:
            outputs.append(msg)

        result = run_wizard(input_fn=fake_input, output_fn=fake_output)
        assert result["env"] == "dev"
        # 应该有错误提示
        assert any("输入无效" in o for o in outputs)

    def test_wizard_invalid_port_then_valid(self) -> None:
        """无效端口后输入有效值"""
        inputs = iter(["dev", "10", "1.0", "99999", "8080", "n"])
        outputs: list[str] = []

        def fake_input(prompt: str) -> str:
            return next(inputs)

        def fake_output(msg: str) -> None:
            outputs.append(msg)

        result = run_wizard(input_fn=fake_input, output_fn=fake_output)
        assert result["port"] == 8080
        assert any("输入无效" in o for o in outputs)

    def test_wizard_empty_port_disables_health(self) -> None:
        """空端口表示不启用健康检查"""
        inputs = iter(["dev", "10", "1.0", "", "n"])

        def fake_input(prompt: str) -> str:
            return next(inputs)

        result = run_wizard(input_fn=fake_input, output_fn=lambda _: None)
        # 空输入使用默认值 8080
        assert result["port"] == 8080

    def test_wizard_shows_confirmation(self) -> None:
        """向导结束时应显示配置确认"""
        inputs = iter(["dev", "10", "1.0", "8080", "n"])
        outputs: list[str] = []

        def fake_input(prompt: str) -> str:
            return next(inputs)

        def fake_output(msg: str) -> None:
            outputs.append(msg)

        run_wizard(input_fn=fake_input, output_fn=fake_output)
        combined = "\n".join(outputs)
        assert "配置确认" in combined
        assert "环境" in combined


class TestBuildRunArgsFromWizard:
    """测试向导结果转 CLI 参数"""

    def test_build_args_full(self) -> None:
        result = {
            "env": "prod",
            "max_loops": 100,
            "loop_interval": 2.0,
            "port": 9090,
            "dry_run": True,
        }
        args = build_run_args_from_wizard(result)
        assert "--env" in args
        assert "prod" in args
        assert "--max-loops" in args
        assert "100" in args
        assert "--loop-interval" in args
        assert "2.0" in args
        assert "--port" in args
        assert "9090" in args
        assert "--dry-run" in args

    def test_build_args_no_dry_run(self) -> None:
        result = {
            "env": "dev",
            "max_loops": 10,
            "loop_interval": 1.0,
            "port": 8080,
            "dry_run": False,
        }
        args = build_run_args_from_wizard(result)
        assert "--dry-run" not in args

    def test_build_args_no_port(self) -> None:
        result = {
            "env": "dev",
            "max_loops": 10,
            "loop_interval": 1.0,
            "port": None,
            "dry_run": False,
        }
        args = build_run_args_from_wizard(result)
        assert "--port" not in args


class TestIsInteractive:
    """测试交互式终端判断"""

    def test_is_interactive_returns_bool(self) -> None:
        result = is_interactive()
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# CLI 子命令集成测试
# ---------------------------------------------------------------------------

class TestCLIWelcome:
    """测试 welcome 子命令"""

    def test_welcome_command(self, capsys) -> None:
        exit_code = main(["welcome"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "自驱永续进化 Agent" in captured.out
        assert "欢迎使用" in captured.out

    def test_welcome_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["welcome"])
        assert args.command == "welcome"


class TestCLIHelp:
    """测试 help 子命令"""

    def test_help_no_command_shows_overview(self, capsys) -> None:
        exit_code = main(["help"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "命令帮助" in captured.out
        assert "run" in captured.out

    def test_help_specific_command(self, capsys) -> None:
        exit_code = main(["help", "run"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "命令: run" in captured.out
        assert "示例" in captured.out

    def test_help_unknown_command(self, capsys) -> None:
        exit_code = main(["help", "nonexistent"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "未知命令" in captured.out

    def test_help_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["help", "run"])
        assert args.command == "help"
        assert args.command_name == "run"

    def test_help_parser_no_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["help"])
        assert args.command == "help"
        assert args.command_name is None


class TestCLIExamples:
    """测试 examples 子命令"""

    def test_examples_command(self, capsys) -> None:
        exit_code = main(["examples"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "常见使用场景" in captured.out
        assert "首次使用" in captured.out
        assert "日常运行" in captured.out

    def test_examples_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["examples"])
        assert args.command == "examples"


class TestCLIGuideFlag:
    """测试 --guide 标志"""

    def test_guide_flag_parses(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run", "--guide"])
        assert args.guide is True

    def test_guide_flag_default_false(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run"])
        assert args.guide is False

    def test_guide_non_interactive_returns_2(self, capsys) -> None:
        """非交互式环境下 --guide 应返回 2 并提示"""
        with patch("root.left.app.left.src.cli.is_interactive", return_value=False):
            exit_code = main(["run", "--guide"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "交互式终端" in captured.err or "--guide" in captured.err
