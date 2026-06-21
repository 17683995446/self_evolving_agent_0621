"""Shell 补全与一键启动脚本测试"""
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pytest

from root.left.app.left.src.cli import build_parser, main
from root.left.app.left.src.utils_main.shell_completion import (
    _build_default_subcommand_info,
    detect_shell,
    extract_subcommand_info,
    generate_bash_completion,
    generate_zsh_completion,
    get_completion_script,
    get_install_instructions,
)
from root.left.app.left.src.utils_main.startup_script import (
    generate_startup_script,
    get_install_instructions as get_startup_install_instructions,
    install_startup_script,
    render_startup_help,
)


# ---------------------------------------------------------------------------
# Shell 补全：子命令信息提取
# ---------------------------------------------------------------------------

class TestExtractSubcommandInfo:
    """测试从解析器提取子命令信息"""

    def test_extract_returns_dict(self):
        parser = build_parser()
        info = extract_subcommand_info(parser)
        assert isinstance(info, dict)
        assert len(info) > 0

    def test_extract_contains_run(self):
        parser = build_parser()
        info = extract_subcommand_info(parser)
        assert "run" in info
        assert "--env" in info["run"]
        assert "--max-loops" in info["run"]

    def test_extract_contains_completion(self):
        parser = build_parser()
        info = extract_subcommand_info(parser)
        assert "completion" in info
        assert "--shell" in info["completion"]

    def test_extract_contains_install(self):
        parser = build_parser()
        info = extract_subcommand_info(parser)
        assert "install" in info
        assert "--install-dir" in info["install"]

    def test_extract_contains_logs(self):
        parser = build_parser()
        info = extract_subcommand_info(parser)
        assert "logs" in info
        assert "--level" in info["logs"]


class TestBuildDefaultSubcommandInfo:
    """测试默认子命令信息构建"""

    def test_returns_dict(self):
        info = _build_default_subcommand_info()
        assert isinstance(info, dict)
        assert len(info) > 0

    def test_contains_run(self):
        info = _build_default_subcommand_info()
        assert "run" in info
        assert "--env" in info["run"]

    def test_contains_completion(self):
        info = _build_default_subcommand_info()
        assert "completion" in info

    def test_contains_install(self):
        info = _build_default_subcommand_info()
        assert "install" in info


# ---------------------------------------------------------------------------
# Shell 检测
# ---------------------------------------------------------------------------

class TestDetectShell:
    """测试 shell 检测"""

    def test_detect_bash(self):
        with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
            assert detect_shell() == "bash"

    def test_detect_zsh(self):
        with patch.dict(os.environ, {"SHELL": "/usr/bin/zsh"}):
            assert detect_shell() == "zsh"

    def test_detect_unknown(self):
        with patch.dict(os.environ, {"SHELL": "/bin/fish"}):
            assert detect_shell() == "unknown"

    def test_detect_empty(self):
        with patch.dict(os.environ, {"SHELL": ""}):
            assert detect_shell() == "unknown"

    def test_detect_missing(self):
        env_without_shell = {k: v for k, v in os.environ.items() if k != "SHELL"}
        with patch.dict(os.environ, env_without_shell, clear=True):
            assert detect_shell() == "unknown"


# ---------------------------------------------------------------------------
# Bash 补全脚本生成
# ---------------------------------------------------------------------------

class TestGenerateBashCompletion:
    """测试 bash 补全脚本生成"""

    def test_returns_nonempty_string(self):
        script = generate_bash_completion()
        assert isinstance(script, str)
        assert len(script) > 0

    def test_contains_complete_directive(self):
        script = generate_bash_completion(command_name="agent")
        assert "complete -F _agent_completion agent" in script

    def test_contains_function_definition(self):
        script = generate_bash_completion(command_name="agent")
        assert "_agent_completion()" in script

    def test_contains_subcommands(self):
        script = generate_bash_completion()
        assert "run" in script
        assert "status" in script
        assert "doctor" in script

    def test_contains_options_for_run(self):
        info = {"run": ["--env", "--max-loops"], "doctor": []}
        script = generate_bash_completion(subcommand_info=info)
        assert "--env" in script
        assert "--max-loops" in script

    def test_custom_command_name(self):
        script = generate_bash_completion(command_name="myagent")
        assert "complete -F _myagent_completion myagent" in script

    def test_skips_subcommands_without_options(self):
        info = {"run": ["--env"], "doctor": []}
        script = generate_bash_completion(subcommand_info=info)
        assert "run)" in script
        assert "--env" in script
        # doctor 没有选项，不应出现在 case 中
        assert "doctor)" not in script


# ---------------------------------------------------------------------------
# Zsh 补全脚本生成
# ---------------------------------------------------------------------------

class TestGenerateZshCompletion:
    """测试 zsh 补全脚本生成"""

    def test_returns_nonempty_string(self):
        script = generate_zsh_completion()
        assert isinstance(script, str)
        assert len(script) > 0

    def test_contains_compdef(self):
        script = generate_zsh_completion(command_name="agent")
        assert "#compdef agent" in script

    def test_contains_function_definition(self):
        script = generate_zsh_completion(command_name="agent")
        assert "_agent()" in script

    def test_contains_subcommands(self):
        script = generate_zsh_completion()
        assert "run" in script
        assert "status" in script

    def test_contains_describe(self):
        script = generate_zsh_completion()
        assert "_describe" in script

    def test_custom_command_name(self):
        script = generate_zsh_completion(command_name="myagent")
        assert "#compdef myagent" in script
        assert "_myagent()" in script

    def test_contains_options_for_run(self):
        info = {"run": ["--env", "--max-loops"], "doctor": []}
        script = generate_zsh_completion(subcommand_info=info)
        assert "--env" in script
        assert "--max-loops" in script


# ---------------------------------------------------------------------------
# 补全脚本获取
# ---------------------------------------------------------------------------

class TestGetCompletionScript:
    """测试补全脚本获取"""

    def test_bash(self):
        script = get_completion_script("bash")
        assert "complete -F" in script

    def test_zsh(self):
        script = get_completion_script("zsh")
        assert "#compdef" in script

    def test_case_insensitive(self):
        script = get_completion_script("BASH")
        assert "complete -F" in script

    def test_unsupported_shell(self):
        with pytest.raises(ValueError, match="不支持"):
            get_completion_script("fish")

    def test_custom_command_name(self):
        script = get_completion_script("bash", command_name="myagent")
        assert "myagent" in script


# ---------------------------------------------------------------------------
# 补全安装指引
# ---------------------------------------------------------------------------

class TestGetInstallInstructions:
    """测试补全安装指引"""

    def test_bash(self):
        instructions = get_install_instructions("bash")
        assert ".bashrc" in instructions
        assert "completion --shell bash" in instructions

    def test_zsh(self):
        instructions = get_install_instructions("zsh")
        assert ".zshrc" in instructions
        assert "completion --shell zsh" in instructions

    def test_custom_command_name(self):
        instructions = get_install_instructions("bash", command_name="myagent")
        assert "myagent" in instructions

    def test_unsupported_shell(self):
        instructions = get_install_instructions("fish")
        assert "不支持" in instructions


# ---------------------------------------------------------------------------
# 启动脚本生成
# ---------------------------------------------------------------------------

class TestGenerateStartupScript:
    """测试启动脚本生成"""

    def test_returns_nonempty_string(self):
        script = generate_startup_script()
        assert isinstance(script, str)
        assert len(script) > 0

    def test_contains_shebang(self):
        script = generate_startup_script()
        assert script.startswith("#!/usr/bin/env bash")

    def test_contains_python_module(self):
        script = generate_startup_script()
        assert "root.left.app.left.src.cli" in script

    def test_contains_exec(self):
        script = generate_startup_script()
        assert "exec python -m" in script

    def test_contains_pythonpath(self):
        script = generate_startup_script()
        assert "PYTHONPATH" in script

    def test_custom_command_name(self):
        script = generate_startup_script(command_name="myagent")
        assert "myagent" in script

    def test_custom_project_root_var(self):
        script = generate_startup_script(project_root_var="MY_ROOT")
        assert "MY_ROOT" in script


# ---------------------------------------------------------------------------
# 启动脚本安装
# ---------------------------------------------------------------------------

class TestInstallStartupScript:
    """测试启动脚本安装"""

    def test_install_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = install_startup_script(
                command_name="testagent",
                install_dir=tmpdir,
            )
            assert os.path.exists(path)
            assert path == os.path.join(tmpdir, "testagent")

    def test_install_content_is_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = install_startup_script(
                command_name="testagent",
                install_dir=tmpdir,
            )
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            assert "python -m root.left.app.left.src.cli" in content

    def test_install_sets_executable_permission(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = install_startup_script(
                command_name="testagent",
                install_dir=tmpdir,
            )
            assert os.access(path, os.X_OK)

    def test_install_existing_without_force_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_startup_script(command_name="testagent", install_dir=tmpdir)
            with pytest.raises(FileExistsError):
                install_startup_script(command_name="testagent", install_dir=tmpdir)

    def test_install_with_force_overwrites(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_startup_script(command_name="testagent", install_dir=tmpdir)
            path = install_startup_script(
                command_name="testagent",
                install_dir=tmpdir,
                force=True,
            )
            assert os.path.exists(path)

    def test_install_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "nested", "bin")
            path = install_startup_script(
                command_name="testagent",
                install_dir=nested_dir,
            )
            assert os.path.exists(path)


# ---------------------------------------------------------------------------
# 启动脚本安装指引
# ---------------------------------------------------------------------------

class TestGetStartupInstallInstructions:
    """测试启动脚本安装指引"""

    def test_returns_nonempty_string(self):
        instructions = get_startup_install_instructions("agent")
        assert isinstance(instructions, str)
        assert len(instructions) > 0

    def test_contains_command_name(self):
        instructions = get_startup_install_instructions("myagent")
        assert "myagent" in instructions

    def test_contains_install_dir(self):
        instructions = get_startup_install_instructions("agent", install_dir="/custom/bin")
        assert "/custom/bin" in instructions

    def test_default_install_dir(self):
        instructions = get_startup_install_instructions("agent")
        assert ".local/bin" in instructions


# ---------------------------------------------------------------------------
# 启动帮助渲染
# ---------------------------------------------------------------------------

class TestRenderStartupHelp:
    """测试启动帮助渲染"""

    def test_returns_nonempty_string(self):
        help_text = render_startup_help()
        assert isinstance(help_text, str)
        assert len(help_text) > 0

    def test_contains_usage_example(self):
        help_text = render_startup_help()
        assert "agent run" in help_text or "python -m" in help_text

    def test_contains_subcommands(self):
        help_text = render_startup_help()
        assert "run" in help_text
        assert "doctor" in help_text


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLICompletion:
    """测试 completion 子命令"""

    def test_completion_bash(self, capsys):
        rc = main(["completion", "--shell", "bash"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "complete -F" in captured.out

    def test_completion_zsh(self, capsys):
        rc = main(["completion", "--shell", "zsh"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "#compdef" in captured.out

    def test_completion_custom_name(self, capsys):
        rc = main(["completion", "--shell", "bash", "--command-name", "myagent"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "myagent" in captured.out

    def test_completion_install(self, capsys):
        rc = main(["completion", "--shell", "bash", "--install"])
        captured = capsys.readouterr()
        assert rc == 0
        assert ".bashrc" in captured.out

    def test_completion_install_zsh(self, capsys):
        rc = main(["completion", "--shell", "zsh", "--install"])
        captured = capsys.readouterr()
        assert rc == 0
        assert ".zshrc" in captured.out

    def test_completion_auto_detect_bash(self, capsys, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        rc = main(["completion"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "complete -F" in captured.out

    def test_completion_auto_detect_zsh(self, capsys, monkeypatch):
        monkeypatch.setenv("SHELL", "/usr/bin/zsh")
        rc = main(["completion"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "#compdef" in captured.out

    def test_completion_auto_detect_unknown(self, capsys, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/fish")
        rc = main(["completion"])
        captured = capsys.readouterr()
        assert rc == 2
        assert "无法自动检测" in captured.err


class TestCLIInstall:
    """测试 install 子命令"""

    def test_install_no_args_shows_help(self, capsys):
        rc = main(["install"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "安装" in captured.out or "install" in captured.out.lower()

    def test_install_to_directory(self, capsys, tmp_path):
        install_dir = str(tmp_path / "bin")
        rc = main([
            "install",
            "--command-name", "testagent",
            "--install-dir", install_dir,
        ])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已安装" in captured.out
        assert os.path.exists(os.path.join(install_dir, "testagent"))

    def test_install_existing_without_force(self, capsys, tmp_path):
        install_dir = str(tmp_path / "bin")
        # 第一次安装
        main(["install", "--command-name", "testagent", "--install-dir", install_dir])
        # 第二次安装应失败
        rc = main([
            "install",
            "--command-name", "testagent",
            "--install-dir", install_dir,
        ])
        captured = capsys.readouterr()
        assert rc == 2
        assert "已存在" in captured.err

    def test_install_with_force(self, capsys, tmp_path):
        install_dir = str(tmp_path / "bin")
        # 第一次安装
        main(["install", "--command-name", "testagent", "--install-dir", install_dir])
        # 用 --force 覆盖
        rc = main([
            "install",
            "--command-name", "testagent",
            "--install-dir", install_dir,
            "--force",
        ])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已安装" in captured.out


# ---------------------------------------------------------------------------
# 帮助系统集成
# ---------------------------------------------------------------------------

class TestHelpIntegration:
    """测试帮助系统是否包含新命令"""

    def test_help_all_contains_completion(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "completion" in captured.out

    def test_help_all_contains_install(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "install" in captured.out

    def test_help_completion(self, capsys):
        rc = main(["help", "completion"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "completion" in captured.out
        assert "bash" in captured.out or "zsh" in captured.out

    def test_help_install(self, capsys):
        rc = main(["help", "install"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "install" in captured.out
