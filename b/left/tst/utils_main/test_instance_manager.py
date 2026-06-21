"""多实例管理与编排测试"""
from __future__ import annotations

import json
import os

from root.left.app.left.src.cli import main
from root.left.app.left.src.utils_main.instance_manager import (
    AgentInstance,
    InstanceManager,
    InstanceStatus,
    render_instance_detail,
    render_instances,
    render_operation_results,
    render_summary,
)


# ---------------------------------------------------------------------------
# AgentInstance 测试
# ---------------------------------------------------------------------------

class TestAgentInstance:
    """测试 Agent 实例"""

    def test_default_values(self):
        inst = AgentInstance(name="test")
        assert inst.name == "test"
        assert inst.env == "dev"
        assert inst.port == 8080
        assert inst.max_loops == 1000
        assert inst.loop_interval == 1.0
        assert inst.dry_run is False
        assert inst.status == InstanceStatus.STOPPED
        assert inst.pid is None

    def test_to_dict(self):
        inst = AgentInstance(
            name="test",
            env="prod",
            port=9090,
            max_loops=500,
            description="测试实例",
        )
        d = inst.to_dict()
        assert d["name"] == "test"
        assert d["env"] == "prod"
        assert d["port"] == 9090
        assert d["max_loops"] == 500
        assert d["description"] == "测试实例"
        assert d["status"] == "stopped"

    def test_to_dict_no_runtime(self):
        inst = AgentInstance(name="test")
        d = inst.to_dict(include_runtime=False)
        assert "pid" not in d
        assert "status" not in d
        assert "started_at" not in d

    def test_from_dict(self):
        data = {
            "name": "test",
            "env": "prod",
            "port": 9090,
            "max_loops": 500,
            "loop_interval": 2.0,
            "dry_run": True,
            "description": "测试",
        }
        inst = AgentInstance.from_dict(data)
        assert inst.name == "test"
        assert inst.env == "prod"
        assert inst.port == 9090
        assert inst.dry_run is True

    def test_from_dict_defaults(self):
        data = {"name": "test"}
        inst = AgentInstance.from_dict(data)
        assert inst.env == "dev"
        assert inst.port == 8080

    def test_roundtrip(self):
        original = AgentInstance(
            name="test",
            env="prod",
            port=9090,
            max_loops=500,
            dry_run=True,
            description="测试",
        )
        d = original.to_dict()
        restored = AgentInstance.from_dict(d)
        assert restored.name == original.name
        assert restored.env == original.env
        assert restored.port == original.port
        assert restored.dry_run == original.dry_run

    def test_build_command(self):
        inst = AgentInstance(name="test", env="prod", port=9090, max_loops=100)
        cmd = inst.build_command()
        assert "run" in cmd
        assert "--env" in cmd
        assert "prod" in cmd
        assert "--port" in cmd
        assert "9090" in cmd

    def test_build_command_dry_run(self):
        inst = AgentInstance(name="test", dry_run=True)
        cmd = inst.build_command()
        assert "--dry-run" in cmd

    def test_build_command_no_dry_run(self):
        inst = AgentInstance(name="test", dry_run=False)
        cmd = inst.build_command()
        assert "--dry-run" not in cmd


# ---------------------------------------------------------------------------
# InstanceManager 测试
# ---------------------------------------------------------------------------

class TestInstanceManager:
    """测试实例管理器"""

    def test_register_and_get(self):
        manager = InstanceManager()
        inst = AgentInstance(name="test")
        manager.register(inst)
        assert manager.get("test") is not None
        assert len(manager.list_instances()) == 1

    def test_register_overwrite(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test", port=8080))
        manager.register(AgentInstance(name="test", port=9090))
        assert len(manager.list_instances()) == 1
        assert manager.get("test").port == 9090

    def test_unregister(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test"))
        assert manager.unregister("test") is True
        assert manager.get("test") is None

    def test_unregister_nonexistent(self):
        manager = InstanceManager()
        assert manager.unregister("nope") is False

    def test_list_instances_empty(self):
        manager = InstanceManager()
        assert manager.list_instances() == []

    def test_list_instances_multiple(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="a"))
        manager.register(AgentInstance(name="b"))
        assert len(manager.list_instances()) == 2

    def test_get_nonexistent(self):
        manager = InstanceManager()
        assert manager.get("nope") is None

    def test_start_nonexistent(self):
        manager = InstanceManager()
        ok, msg = manager.start("nope")
        assert ok is False
        assert "不存在" in msg

    def test_stop_nonexistent(self):
        manager = InstanceManager()
        ok, msg = manager.stop("nope")
        assert ok is False
        assert "不存在" in msg

    def test_stop_not_running(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test"))
        ok, msg = manager.stop("test")
        assert ok is True
        assert "未运行" in msg

    def test_restart_nonexistent(self):
        manager = InstanceManager()
        ok, msg = manager.restart("nope")
        assert ok is False
        assert "不存在" in msg

    def test_get_status_nonexistent(self):
        manager = InstanceManager()
        assert manager.get_status("nope") is None

    def test_get_status_stopped(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test"))
        status = manager.get_status("test")
        assert status == InstanceStatus.STOPPED

    def test_to_dict(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test"))
        d = manager.to_dict()
        assert d["count"] == 1
        assert len(d["instances"]) == 1

    def test_save_and_load(self, tmp_path):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test1", env="dev", port=8080))
        manager.register(AgentInstance(name="test2", env="prod", port=9090))

        file_path = str(tmp_path / "instances.json")
        manager.save_to_file(file_path)
        assert os.path.exists(file_path)

        # 加载到新管理器
        new_manager = InstanceManager()
        count = new_manager.load_from_file(file_path)
        assert count == 2
        assert new_manager.get("test1") is not None
        assert new_manager.get("test2") is not None
        assert new_manager.get("test1").port == 8080
        assert new_manager.get("test2").env == "prod"

    def test_load_nonexistent_file(self, tmp_path):
        manager = InstanceManager()
        try:
            manager.load_from_file(str(tmp_path / "nonexistent.json"))
            assert False, "应抛出 FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_save_creates_valid_json(self, tmp_path):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test", description="测试"))
        file_path = str(tmp_path / "instances.json")
        manager.save_to_file(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "version" in data
        assert "instances" in data
        assert len(data["instances"]) == 1
        assert data["instances"][0]["name"] == "test"

    def test_save_excludes_runtime(self, tmp_path):
        """保存时应排除运行时状态"""
        manager = InstanceManager()
        inst = AgentInstance(name="test", pid=12345, status=InstanceStatus.RUNNING)
        manager.register(inst)
        file_path = str(tmp_path / "instances.json")
        manager.save_to_file(file_path)

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        inst_data = data["instances"][0]
        assert "pid" not in inst_data
        assert "status" not in inst_data

    def test_start_all_empty(self):
        manager = InstanceManager()
        results = manager.start_all()
        assert results == []

    def test_stop_all_empty(self):
        manager = InstanceManager()
        results = manager.stop_all()
        assert results == []

    def test_stop_all_with_stopped(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test"))
        results = manager.stop_all()
        assert len(results) == 1
        assert results[0][0] == "test"
        assert results[0][1] is True  # 已停止也算成功

    def test_refresh_status(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="test"))
        manager.refresh_status()
        # 不应抛出异常
        assert manager.get("test").status == InstanceStatus.STOPPED


# ---------------------------------------------------------------------------
# 渲染测试
# ---------------------------------------------------------------------------

class TestRenderInstances:
    """测试实例列表渲染"""

    def test_empty(self):
        result = render_instances([])
        assert "无实例" in result

    def test_with_instances(self):
        instances = [
            AgentInstance(name="test1", env="dev", port=8080),
            AgentInstance(name="test2", env="prod", port=9090),
        ]
        result = render_instances(instances)
        assert "Agent 实例" in result
        assert "test1" in result
        assert "test2" in result

    def test_running_status(self):
        inst = AgentInstance(name="test", status=InstanceStatus.RUNNING, pid=12345)
        result = render_instances([inst])
        assert "test" in result


class TestRenderInstanceDetail:
    """测试实例详情渲染"""

    def test_basic(self):
        inst = AgentInstance(name="test", env="prod", port=9090, description="测试实例")
        result = render_instance_detail(inst)
        assert "实例详情" in result
        assert "test" in result
        assert "prod" in result
        assert "9090" in result
        assert "测试实例" in result

    def test_includes_command(self):
        inst = AgentInstance(name="test")
        result = render_instance_detail(inst)
        assert "启动命令" in result
        assert "run" in result


class TestRenderOperationResults:
    """测试操作结果渲染"""

    def test_empty(self):
        result = render_operation_results([])
        assert "无操作" in result

    def test_with_results(self):
        results = [
            ("inst1", True, "已启动"),
            ("inst2", False, "失败"),
        ]
        result = render_operation_results(results)
        assert "操作结果" in result
        assert "inst1" in result
        assert "inst2" in result


class TestRenderSummary:
    """测试摘要渲染"""

    def test_empty(self):
        manager = InstanceManager()
        result = render_summary(manager)
        assert "实例管理器摘要" in result
        assert "0" in result

    def test_with_instances(self):
        manager = InstanceManager()
        manager.register(AgentInstance(name="a"))
        manager.register(AgentInstance(name="b"))
        result = render_summary(manager)
        assert "2" in result


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLIInstance:
    """测试 instance 子命令"""

    def test_instance_no_args_shows_help(self, capsys):
        rc = main(["instance"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "用法" in captured.out

    def test_instance_list_empty(self, capsys):
        rc = main(["instance", "--list"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无实例" in captured.out

    def test_instance_summary(self, capsys):
        rc = main(["instance", "--summary"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "实例管理器摘要" in captured.out

    def test_instance_add(self, capsys):
        rc = main(["instance", "--add", "test_inst", "--env-opt", "dev", "--port-opt", "9090"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已添加实例" in captured.out
        assert "test_inst" in captured.out

    def test_instance_add_with_dry_run(self, capsys):
        rc = main(["instance", "--add", "test_inst", "--dry-run-opt", "--desc", "测试"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已添加实例" in captured.out

    def test_instance_remove_nonexistent(self, capsys):
        rc = main(["instance", "--remove", "nonexistent"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "错误" in captured.err

    def test_instance_info_nonexistent(self, capsys):
        rc = main(["instance", "--info", "nonexistent"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "错误" in captured.err

    def test_instance_start_nonexistent(self, capsys):
        rc = main(["instance", "--start", "nonexistent"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "不存在" in captured.out

    def test_instance_stop_nonexistent(self, capsys):
        rc = main(["instance", "--stop", "nonexistent"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "不存在" in captured.out

    def test_instance_restart_nonexistent(self, capsys):
        rc = main(["instance", "--restart", "nonexistent"])
        captured = capsys.readouterr()
        assert rc == 1
        assert "不存在" in captured.out

    def test_instance_start_all_empty(self, capsys):
        rc = main(["instance", "--start-all"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无操作" in captured.out

    def test_instance_stop_all_empty(self, capsys):
        rc = main(["instance", "--stop-all"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无操作" in captured.out

    def test_instance_save_and_load(self, capsys, tmp_path):
        file_path = str(tmp_path / "instances.json")
        # 保存
        rc = main(["instance", "--save", file_path])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已保存" in captured.out
        assert os.path.exists(file_path)
        # 加载
        rc = main(["instance", "--load", file_path])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已从" in captured.out

    def test_instance_load_nonexistent(self, capsys, tmp_path):
        rc = main(["instance", "--load", str(tmp_path / "nonexistent.json")])
        captured = capsys.readouterr()
        assert rc == 2
        assert "错误" in captured.err


# ---------------------------------------------------------------------------
# 帮助系统集成
# ---------------------------------------------------------------------------

class TestHelpIntegration:
    """测试帮助系统是否包含 instance 命令"""

    def test_help_all_contains_instance(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "instance" in captured.out

    def test_help_instance(self, capsys):
        rc = main(["help", "instance"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "instance" in captured.out
        assert "实例" in captured.out
