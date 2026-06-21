"""自愈动作 Playbook 测试"""
import os
import tempfile
from typing import Any, Dict

from root.left.app.left.src.core_mod.action_executor import ActionExecutor
from root.left.app.left.src.core_mod.action_playbook import (
    ActionPlaybook,
    PlaybookRegistry,
    PlaybookRunner,
    build_default_playbooks,
)


class TestActionPlaybook:
    """测试 Playbook 匹配"""

    def test_matches_by_title(self) -> None:
        pb = ActionPlaybook("test", "测试", ["缓存"], [])
        assert pb.matches({"title": "缓存文件过多"}) is True
        assert pb.matches({"title": "内存不足"}) is False


class TestPlaybookRegistry:
    """测试注册表"""

    def test_default_playbooks(self) -> None:
        registry = build_default_playbooks()
        assert "pycache_cleanup" in registry.list()
        assert "log_cleanup" in registry.list()

    def test_find_match(self) -> None:
        registry = build_default_playbooks()
        rec: Dict[str, Any] = {"title": "缓存文件过多", "action": "find ..."}
        matched = registry.find_match(rec)
        assert matched is not None
        assert matched.playbook_id == "pycache_cleanup"


class TestPlaybookRunner:
    """测试 Playbook 执行器"""

    def test_dry_run_pycache_cleanup(self) -> None:
        executor = ActionExecutor({"dry_run": True, "allowed_shell_prefixes": ["find", "echo"]})
        registry = build_default_playbooks()
        runner = PlaybookRunner(registry, executor)
        recs: list[Dict[str, Any]] = [{"title": "缓存文件过多"}]
        results = runner.run(recs)
        assert len(results) == 1
        assert results[0]["playbook_id"] == "pycache_cleanup"
        assert results[0]["success"] is True
        assert "[dry_run]" in results[0]["steps"][0]["stdout"]

    def test_real_pycache_cleanup_in_temp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pycache = os.path.join(tmpdir, "__pycache__")
            os.makedirs(pycache)
            with open(os.path.join(pycache, "foo.cpython-312.pyc"), "w") as f:
                f.write("x")

            executor = ActionExecutor({
                "dry_run": False,
                "allowed_shell_prefixes": ["find"],
                "approval_gate": {"mode": "auto_pass"},
            })
            registry = PlaybookRegistry()
            registry.register(ActionPlaybook(
                playbook_id="pycache_cleanup",
                name="清理缓存",
                triggers=["缓存"],
                steps=[{"action_type": "shell", "command": f"find {tmpdir} -type d -name __pycache__ -exec rm -rf {{}} +"}],
            ))
            runner = PlaybookRunner(registry, executor)
            results = runner.run([{"title": "缓存文件过多"}], context={"target_root": tmpdir})
            assert len(results) == 1
            assert results[0]["success"] is True
            assert not os.path.exists(pycache)

    def test_effect_verification(self) -> None:
        executor = ActionExecutor({"dry_run": True, "allowed_shell_prefixes": ["echo"]})
        registry = build_default_playbooks()
        runner = PlaybookRunner(registry, executor)
        recs: list[Dict[str, Any]] = [{"title": "日志文件较多"}]
        context: Dict[str, Any] = {"metrics": {"log_files": 10}}
        results = runner.run(recs, context)
        assert len(results) == 1
        assert results[0]["effect"]["metric"] == "log_files"
        assert results[0]["effect"]["before"] == 10
        assert results[0]["effect"]["after"] == 10

    def test_unmatched_recommendation(self) -> None:
        executor = ActionExecutor({})
        registry = build_default_playbooks()
        runner = PlaybookRunner(registry, executor)
        results = runner.run([{"title": "未知问题"}])
        assert len(results) == 0
