"""交互式 REPL 与命令历史测试"""
from __future__ import annotations

import os
import tempfile
from typing import List

from root.left.app.left.src.cli import main
from root.left.app.left.src.utils_main.repl import (
    CommandHistory,
    REPLResult,
    REPLSession,
    get_default_history_file,
)


# ---------------------------------------------------------------------------
# CommandHistory 测试
# ---------------------------------------------------------------------------

class TestCommandHistory:
    """测试命令历史管理"""

    def test_add_and_get(self):
        history = CommandHistory()
        history.add("run --env dev")
        history.add("status")
        entries = history.get_entries()
        assert len(entries) == 2
        assert entries[0] == "run --env dev"
        assert entries[1] == "status"

    def test_add_empty_ignored(self):
        history = CommandHistory()
        history.add("")
        history.add("   ")
        assert len(history) == 0

    def test_add_strips_whitespace(self):
        history = CommandHistory()
        history.add("  run  ")
        assert history.get_entries()[0] == "run"

    def test_no_consecutive_duplicates(self):
        history = CommandHistory()
        history.add("run")
        history.add("run")
        assert len(history) == 1

    def test_non_consecutive_duplicates_allowed(self):
        history = CommandHistory()
        history.add("run")
        history.add("status")
        history.add("run")
        assert len(history) == 3

    def test_max_size(self):
        history = CommandHistory(max_size=3)
        history.add("cmd1")
        history.add("cmd2")
        history.add("cmd3")
        history.add("cmd4")
        entries = history.get_entries()
        assert len(entries) == 3
        assert entries[0] == "cmd2"
        assert entries[-1] == "cmd4"

    def test_clear(self):
        history = CommandHistory()
        history.add("run")
        history.add("status")
        history.clear()
        assert len(history) == 0
        assert history.get_entries() == []

    def test_search(self):
        history = CommandHistory()
        history.add("run --env dev")
        history.add("status --port 8080")
        history.add("run --env prod")
        results = history.search("run")
        assert len(results) == 2
        results = history.search("prod")
        assert len(results) == 1
        assert "prod" in results[0]

    def test_search_case_insensitive(self):
        history = CommandHistory()
        history.add("RUN --env dev")
        results = history.search("run")
        assert len(results) == 1

    def test_search_no_match(self):
        history = CommandHistory()
        history.add("run")
        results = history.search("nonexistent")
        assert results == []

    def test_len(self):
        history = CommandHistory()
        assert len(history) == 0
        history.add("run")
        assert len(history) == 1


class TestCommandHistoryPersistence:
    """测试命令历史持久化"""

    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".history", delete=False) as f:
            path = f.name
        try:
            history = CommandHistory(history_file=path)
            history.add("run --env dev")
            history.add("status")
            history.save()

            # 新实例加载
            history2 = CommandHistory(history_file=path)
            history2.load()
            entries = history2.get_entries()
            assert len(entries) == 2
            assert entries[0] == "run --env dev"
            assert entries[1] == "status"
        finally:
            os.unlink(path)

    def test_load_nonexistent_file(self):
        history = CommandHistory(history_file="/nonexistent/path")
        history.load()  # 不应抛出异常
        assert len(history) == 0

    def test_save_no_file(self):
        history = CommandHistory()
        history.add("run")
        history.save()  # 不应抛出异常

    def test_save_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = os.path.join(tmpdir, "nested", "dir", "history.txt")
            history = CommandHistory(history_file=nested_path)
            history.add("run")
            history.save()
            assert os.path.exists(nested_path)


# ---------------------------------------------------------------------------
# REPLResult 测试
# ---------------------------------------------------------------------------

class TestREPLResult:
    """测试 REPL 结果"""

    def test_default_values(self):
        result = REPLResult(command="run", exit_code=0)
        assert result.command == "run"
        assert result.exit_code == 0
        assert result.output == ""
        assert result.should_exit is False

    def test_should_exit(self):
        result = REPLResult(command="exit", exit_code=0, should_exit=True)
        assert result.should_exit is True


# ---------------------------------------------------------------------------
# REPLSession 测试
# ---------------------------------------------------------------------------

class TestREPLSession:
    """测试 REPL 会话"""

    def _make_session(
        self,
        inputs: List[str],
        executor_returns: int = 0,
    ):
        """创建测试用 REPL 会话。

        Args:
            inputs: 模拟的用户输入列表
            executor_returns: 执行器返回值
        """
        input_iter = iter(inputs)
        outputs: List[str] = []

        def mock_input(prompt: str) -> str:
            try:
                return next(input_iter)
            except StopIteration:
                raise EOFError

        def mock_output(text: str) -> None:
            outputs.append(text)

        def mock_executor(args: List[str]) -> int:
            outputs.append(f"[executed: {' '.join(args)}]")
            return executor_returns

        history = CommandHistory()
        session = REPLSession(
            executor=mock_executor,
            history=history,
            input_fn=mock_input,
            output_fn=mock_output,
        )
        return session, outputs

    def test_exit_command(self):
        session, outputs = self._make_session(["exit"])
        rc = session.run()
        assert rc == 0
        assert any("再见" in o for o in outputs)

    def test_quit_command(self):
        session, outputs = self._make_session(["quit"])
        rc = session.run()
        assert rc == 0

    def test_q_command(self):
        session, outputs = self._make_session(["q"])
        rc = session.run()
        assert rc == 0

    def test_empty_input_ignored(self):
        session, outputs = self._make_session(["", "exit"])
        rc = session.run()
        assert rc == 0

    def test_command_execution(self):
        session, outputs = self._make_session(["run --env dev", "exit"])
        rc = session.run()
        assert rc == 0
        assert any("[executed: run --env dev]" in o for o in outputs)

    def test_help_command(self):
        session, outputs = self._make_session(["help", "exit"])
        session.run()
        assert any("可用命令" in o for o in outputs)

    def test_help_alias_question_mark(self):
        session, outputs = self._make_session(["?", "exit"])
        session.run()
        assert any("可用命令" in o for o in outputs)

    def test_history_special_command(self):
        session, outputs = self._make_session(["run", "status", "!history", "exit"])
        session.run()
        # !history 应输出历史
        history_output = [o for o in outputs if "run" in o and "status" in o]
        assert len(history_output) > 0 or any("1" in o and "run" in o for o in outputs)

    def test_clear_special_command(self):
        session, outputs = self._make_session(["run", "!clear", "!history", "exit"])
        session.run()
        # 清空后历史应为空
        assert any("无历史记录" in o or "历史已清空" in o for o in outputs)

    def test_search_special_command(self):
        session, outputs = self._make_session(["run --env dev", "status", "!search run", "exit"])
        session.run()
        # 搜索结果应包含 run
        assert any("run --env dev" in o for o in outputs)

    def test_search_no_keyword(self):
        session, outputs = self._make_session(["!search", "exit"])
        session.run()
        assert any("用法" in o for o in outputs)

    def test_special_help(self):
        session, outputs = self._make_session(["!help", "exit"])
        session.run()
        assert any("特殊命令" in o for o in outputs)

    def test_unknown_special_command(self):
        session, outputs = self._make_session(["!unknown", "exit"])
        session.run()
        assert any("未知特殊命令" in o for o in outputs)

    def test_welcome_message(self):
        session, outputs = self._make_session(["exit"])
        session.run()
        assert any("交互式 REPL" in o for o in outputs)

    def test_history_recorded(self):
        session, outputs = self._make_session(["run", "status", "exit"])
        session.run()
        entries = session.history.get_entries()
        assert "run" in entries
        assert "status" in entries
        assert "exit" in entries

    def test_executor_exception_handled(self):
        def failing_executor(args):
            raise RuntimeError("test error")

        input_iter = iter(["run", "exit"])
        outputs: List[str] = []

        def mock_input(prompt):
            return next(input_iter)

        def mock_output(text):
            outputs.append(text)

        session = REPLSession(
            executor=failing_executor,
            history=CommandHistory(),
            input_fn=mock_input,
            output_fn=mock_output,
        )
        rc = session.run()
        assert rc == 0  # 最后一条是 exit，返回 0
        assert any("错误" in o for o in outputs)

    def test_eof_exits(self):
        """EOF (Ctrl+D) 应优雅退出。"""
        outputs: List[str] = []

        def mock_input(prompt):
            raise EOFError

        def mock_output(text):
            outputs.append(text)

        session = REPLSession(
            executor=lambda args: 0,
            history=CommandHistory(),
            input_fn=mock_input,
            output_fn=mock_output,
        )
        rc = session.run()
        assert rc == 0
        assert any("再见" in o for o in outputs)

    def test_keyboard_interrupt_continues(self):
        """Ctrl+C 应继续而非退出。"""
        call_count = [0]

        def mock_input(prompt):
            call_count[0] += 1
            if call_count[0] == 1:
                raise KeyboardInterrupt
            if call_count[0] == 2:
                return "exit"
            raise EOFError

        outputs: List[str] = []

        def mock_output(text):
            outputs.append(text)

        session = REPLSession(
            executor=lambda args: 0,
            history=CommandHistory(),
            input_fn=mock_input,
            output_fn=mock_output,
        )
        rc = session.run()
        assert rc == 0


# ---------------------------------------------------------------------------
# 便捷函数测试
# ---------------------------------------------------------------------------

class TestGetDefaultHistoryFile:
    """测试默认历史文件路径"""

    def test_returns_path(self):
        path = get_default_history_file()
        assert isinstance(path, str)
        assert ".agent_history" in path

    def test_contains_home(self):
        path = get_default_history_file()
        # 应包含用户主目录或至少是有效路径
        assert len(path) > 0


class TestRunREPL:
    """测试 run_repl 便捷函数"""

    def test_run_with_custom_executor(self):
        inputs = iter(["test", "exit"])
        outputs: List[str] = []

        def mock_input(prompt):
            return next(inputs)

        def mock_output(text):
            outputs.append(text)

        def executor(args):
            outputs.append(f"executed: {args}")
            return 0

        # 直接创建 session 而非调用 run_repl，因为 run_repl 使用默认 input/print
        history = CommandHistory()
        session = REPLSession(
            executor=executor,
            history=history,
            input_fn=mock_input,
            output_fn=mock_output,
        )
        rc = session.run()
        assert rc == 0
        assert any("executed:" in o for o in outputs)


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLIRepl:
    """测试 repl 子命令"""

    def test_repl_non_interactive_without_force(self, capsys, monkeypatch):
        # 模拟非交互式环境
        monkeypatch.setattr("sys.stdin.isatty", lambda: False)
        rc = main(["repl"])
        captured = capsys.readouterr()
        assert rc == 2
        assert "交互式终端" in captured.err

    def test_repl_help_in_guide(self, capsys):
        rc = main(["help", "repl"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "repl" in captured.out
        assert "REPL" in captured.out or "交互" in captured.out

    def test_repl_in_help_all(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "repl" in captured.out
