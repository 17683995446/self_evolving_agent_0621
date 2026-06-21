"""任务模板测试"""

import pytest

from root.left.app.left.src.core_mod.task_templates import TaskTemplate, TaskTemplateRegistry


class TestTaskTemplate:
    """任务模板单元测试"""

    def test_build_payload(self) -> None:
        template = TaskTemplate("test", "shell", {"command": "echo hi"})
        payload = template.build_payload({"timeout": 10})
        assert payload["action_type"] == "shell"
        assert payload["command"] == "echo hi"
        assert payload["timeout"] == 10


class TestTaskTemplateRegistry:
    """模板注册表测试"""

    def test_list_templates(self) -> None:
        registry = TaskTemplateRegistry({})
        names = registry.list_templates()
        assert "disk_cleanup" in names
        assert "health_check" in names
        assert "send_alert" in names

    def test_build_payload(self) -> None:
        registry = TaskTemplateRegistry({})
        payload = registry.build_payload("disk_cleanup", {})
        assert payload["action_type"] == "shell"
        assert "df -h" in payload["command"]

    def test_custom_template(self) -> None:
        config = {
            "custom_templates": {
                "my_cmd": {
                    "action_type": "shell",
                    "default_payload": {"command": "whoami"},
                }
            }
        }
        registry = TaskTemplateRegistry(config)
        payload = registry.build_payload("my_cmd", {})
        assert payload["action_type"] == "shell"
        assert payload["command"] == "whoami"

    def test_unknown_template(self) -> None:
        registry = TaskTemplateRegistry({})
        with pytest.raises(KeyError):
            registry.build_payload("not_exist", {})
