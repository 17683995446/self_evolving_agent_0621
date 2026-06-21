"""统一命令行入口测试"""
import json

from root.left.app.left.src.cli import build_parser, main


class TestCLIParser:
    """测试 CLI 参数解析"""

    def test_no_command_prints_help(self, capsys) -> None:
        exit_code = main([])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "self-evolving-agent" in captured.out

    def test_run_command_parses_args(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run", "--env", "test", "--max-loops", "5", "--port", "9090"])
        assert args.command == "run"
        assert args.env == "test"
        assert args.max_loops == 5
        assert args.port == 9090

    def test_run_command_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run"])
        assert args.env == "dev"
        assert args.max_loops is None
        assert args.port is None
        assert args.dry_run is False

    def test_status_command_parses_port(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["status", "--port", "3000"])
        assert args.command == "status"
        assert args.port == 3000

    def test_health_command_default_port(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["health"])
        assert args.command == "health"
        assert args.port == 8080

    def test_validate_command_parses_env(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["validate", "--env", "test"])
        assert args.command == "validate"
        assert args.env == "test"

    def test_config_command_show_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["config", "--show-defaults"])
        assert args.command == "config"
        assert args.show_defaults is True

    def test_doctor_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["doctor"])
        assert args.command == "doctor"


class TestCLIValidate:
    """测试 validate 子命令"""

    def test_validate_dev_success(self, capsys) -> None:
        exit_code = main(["validate", "--env", "dev"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "配置校验通过" in captured.out

    def test_validate_invalid_env_fails(self, capsys) -> None:
        exit_code = main(["validate", "--env", "nonexistent_env"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "[config]" in captured.err


class TestCLIConfig:
    """测试 config 子命令"""

    def test_config_show_defaults(self, capsys) -> None:
        exit_code = main(["config", "--show-defaults"])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert "phase1" in data
        assert "loop_interval" in data

    def test_config_show_current(self, capsys) -> None:
        exit_code = main(["config", "--env", "dev"])
        captured = capsys.readouterr()
        assert exit_code == 0
        data = json.loads(captured.out)
        assert "phase1" in data

    def test_config_describe(self, capsys) -> None:
        exit_code = main(["config", "--describe"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "配置项说明" in captured.out
        assert "loop_interval" in captured.out


class TestCLIDoctor:
    """测试 doctor 子命令"""

    def test_doctor_runs(self, capsys) -> None:
        main(["doctor"])
        captured = capsys.readouterr()
        assert "=== Agent 自诊断 ===" in captured.out
        assert "Python 版本" in captured.out
        assert "核心依赖" in captured.out


class TestCLIDiagnose:
    """测试 diagnose 子命令"""

    def test_diagnose_text_output(self, capsys) -> None:
        exit_code = main(["diagnose"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "自诊断报告" in captured.out
        assert "python_version" in captured.out
        assert "modules_health" in captured.out

    def test_diagnose_json_output(self, capsys) -> None:
        exit_code = main(["diagnose", "--json"])
        captured = capsys.readouterr()
        assert exit_code == 0
        import json
        data = json.loads(captured.out)
        assert "all_passed" in data
        assert "items" in data
        assert data["total"] == 6


class TestCLIStatus:
    """测试 status 子命令"""

    def test_status_connection_refused(self, capsys) -> None:
        exit_code = main(["status", "--port", "1"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "无法连接" in captured.err


class TestCLIHealth:
    """测试 health 子命令"""

    def test_health_connection_refused(self, capsys) -> None:
        exit_code = main(["health", "--port", "1"])
        captured = capsys.readouterr()
        assert exit_code == 1
        assert "无法连接" in captured.err


class TestCLIRun:
    """测试 run 子命令"""

    def test_run_with_invalid_env_returns_2(self, capsys) -> None:
        exit_code = main(["run", "--env", "nonexistent_env"])
        captured = capsys.readouterr()
        assert exit_code == 2
        assert "[config]" in captured.err

    def test_run_with_max_loops(self, capsys) -> None:
        exit_code = main(["run", "--env", "dev", "--max-loops", "1", "--loop-interval", "0.0"])
        assert exit_code == 0
