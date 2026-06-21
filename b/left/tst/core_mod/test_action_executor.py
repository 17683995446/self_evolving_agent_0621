"""动作执行器测试"""
import os
import tempfile


from root.left.app.left.src.core_mod.action_executor import ActionExecutor, ActionResult


class TestActionResult:
    """ActionResult 测试"""

    def test_to_dict(self) -> None:
        result = ActionResult(success=True, action_type="shell", stdout="ok", returncode=0)
        d = result.to_dict()
        assert d["success"] is True
        assert d["action_type"] == "shell"
        assert d["stdout"] == "ok"


class TestActionExecutorShell:
    """Shell 动作测试"""

    def test_shell_dry_run(self) -> None:
        executor = ActionExecutor({"dry_run": True})
        result = executor.execute({"action_type": "shell", "command": "echo hello"})
        assert result.success is True
        assert "[dry_run]" in result.stdout

    def test_shell_real_echo(self) -> None:
        executor = ActionExecutor({"dry_run": False})
        result = executor.execute({"action_type": "shell", "command": "echo hello"})
        assert result.success is True
        assert result.returncode == 0
        assert "hello" in result.stdout

    def test_shell_blocked_command(self) -> None:
        executor = ActionExecutor({"dry_run": False})
        result = executor.execute({"action_type": "shell", "command": "rm -rf / tmp"})
        assert result.success is False
        assert "Blocked" in result.error

    def test_shell_not_allowed_prefix(self) -> None:
        executor = ActionExecutor({"dry_run": False, "allowed_shell_prefixes": ["echo"]})
        result = executor.execute({"action_type": "shell", "command": "cat /etc/hosts"})
        assert result.success is False
        assert "not in allowed list" in result.error

    def test_shell_empty_command(self) -> None:
        executor = ActionExecutor({"dry_run": False})
        result = executor.execute({"action_type": "shell", "command": ""})
        assert result.success is False


class TestActionExecutorHttp:
    """HTTP 动作测试"""

    def test_http_get_dry_run(self) -> None:
        executor = ActionExecutor({"dry_run": True})
        result = executor.execute({"action_type": "http_get", "url": "http://localhost:8080/health"})
        assert result.success is True
        assert "[dry_run]" in result.stdout

    def test_http_get_blocked_host(self) -> None:
        executor = ActionExecutor({"dry_run": False})
        result = executor.execute({"action_type": "http_get", "url": "http://example.com/"})
        assert result.success is False
        assert "not in allowed list" in result.error


class TestActionExecutorApproval:
    """审批门集成测试"""

    def test_destructive_auto_reject(self) -> None:
        executor = ActionExecutor({"dry_run": False, "approval_gate": {"mode": "auto_reject"}})
        result = executor.execute({"action_type": "file_delete", "path": "/tmp/x"})
        assert result.success is False
        assert "rejected" in result.error.lower()

    def test_destructive_auto_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "x.txt")
            with open(path, "w") as f:
                f.write("x")
            executor = ActionExecutor({"dry_run": False, "approval_gate": {"mode": "auto_pass"}})
            result = executor.execute({"action_type": "file_delete", "path": path})
            assert result.success is True


class TestActionExecutorFile:
    """文件动作测试"""

    def test_file_write_read_delete(self) -> None:
        executor = ActionExecutor({"dry_run": False})
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            write_result = executor.execute({"action_type": "file_write", "path": path, "content": "hello"})
            assert write_result.success is True

            read_result = executor.execute({"action_type": "file_read", "path": path})
            assert read_result.success is True
            assert read_result.data == "hello"

            delete_result = executor.execute({"action_type": "file_delete", "path": path})
            assert delete_result.success is True
            assert not os.path.exists(path)

    def test_file_blocked_path(self) -> None:
        executor = ActionExecutor({"dry_run": False})
        result = executor.execute({"action_type": "file_read", "path": "/etc/passwd"})
        assert result.success is False
        assert "blocked" in result.error.lower()


class TestActionExecutorNoop:
    """Noop 动作测试"""

    def test_noop(self) -> None:
        executor = ActionExecutor({})
        result = executor.execute({"action_type": "noop"})
        assert result.success is True

    def test_unknown_action(self) -> None:
        executor = ActionExecutor({})
        result = executor.execute({"action_type": "magic"})
        assert result.success is False
        assert "Unknown" in result.error
