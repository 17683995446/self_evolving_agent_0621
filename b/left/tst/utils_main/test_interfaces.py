"""模块接口标准与插件系统测试"""
import pytest

from root.left.app.left.src.utils_main.interfaces import (
    BaseModule, ModuleRegistry, DIContainer, ConfigAssembler, PluginLoader,
)
from root.left.app.left.src.utils_main.exceptions import ModuleNotFoundException, ValidationError


class DummyModule(BaseModule):
    """测试用虚拟模块"""

    def __init__(self, config):
        super().__init__(config)
        self.value = config.get("value", 0)

    def get_state(self):
        return {"value": self.value}

    def reset(self):
        self.value = 0


class AnotherModule(BaseModule):
    """另一个测试模块"""

    def __init__(self, config):
        super().__init__(config)
        self.name = config.get("name", "default")

    def get_state(self):
        return {"name": self.name}

    def reset(self):
        self.name = "default"


class BadClass:
    """不继承BaseModule的类"""
    pass


class TestModuleRegistry:
    """测试模块注册表"""

    def test_normal_register_and_get(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        cls = reg.get("dummy")
        assert cls is DummyModule

    def test_list_modules(self) -> None:
        reg = ModuleRegistry()
        reg.register("a", DummyModule)
        reg.register("b", AnotherModule)
        assert sorted(reg.list_modules()) == ["a", "b"]

    def test_has(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        assert reg.has("dummy") is True
        assert reg.has("missing") is False

    def test_unregister(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        reg.unregister("dummy")
        assert reg.has("dummy") is False

    def test_get_not_found(self) -> None:
        reg = ModuleRegistry()
        with pytest.raises(ModuleNotFoundException):
            reg.get("missing")

    def test_register_invalid_class(self) -> None:
        reg = ModuleRegistry()
        with pytest.raises(ValidationError):
            reg.register("bad", BadClass)


class TestDIContainer:
    """测试依赖注入容器"""

    def test_normal_resolve(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        container = DIContainer(reg)
        instance = container.resolve("dummy", {"value": 42})
        assert isinstance(instance, DummyModule)
        assert instance.value == 42

    def test_singleton(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        container = DIContainer(reg)
        container.register_singleton("dummy")
        a = container.resolve("dummy", {"value": 1})
        b = container.resolve("dummy", {"value": 2})
        assert a is b
        assert a.value == 1

    def test_non_singleton(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        container = DIContainer(reg)
        a = container.resolve("dummy", {"value": 1})
        b = container.resolve("dummy", {"value": 2})
        assert a is not b

    def test_get_instance(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        container = DIContainer(reg)
        container.resolve("dummy", {"value": 1})
        assert container.get_instance("dummy") is None

    def test_clear(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        container = DIContainer(reg)
        container.register_singleton("dummy")
        container.resolve("dummy", {})
        container.clear()
        assert container.get_instance("dummy") is None


class TestConfigAssembler:
    """测试配置驱动组装器"""

    def test_normal_assemble(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        reg.register("another", AnotherModule)
        container = DIContainer(reg)
        assembler = ConfigAssembler(reg, container)
        blueprint = {
            "slot_a": {"module": "dummy", "config": {"value": 10}},
            "slot_b": {"module": "another", "config": {"name": "test"}},
        }
        assembled = assembler.assemble(blueprint)
        assert len(assembled) == 2
        assert assembled["slot_a"].value == 10
        assert assembled["slot_b"].name == "test"

    def test_singleton_assemble(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        container = DIContainer(reg)
        assembler = ConfigAssembler(reg, container)
        blueprint = {
            "slot_a": {"module": "dummy", "config": {"value": 1}, "singleton": True},
            "slot_b": {"module": "dummy", "config": {"value": 2}, "singleton": True},
        }
        assembled = assembler.assemble(blueprint)
        assert assembled["slot_a"] is assembled["slot_b"]

    def test_validate_blueprint(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        container = DIContainer(reg)
        assembler = ConfigAssembler(reg, container)
        errors = assembler.validate_blueprint({
            "slot_a": {"module": "dummy"},
            "slot_b": {"module": "missing"},
            "slot_c": {},
        })
        assert len(errors) == 2

    def test_validate_pass(self) -> None:
        reg = ModuleRegistry()
        reg.register("dummy", DummyModule)
        container = DIContainer(reg)
        assembler = ConfigAssembler(reg, container)
        errors = assembler.validate_blueprint({
            "slot_a": {"module": "dummy"},
        })
        assert len(errors) == 0


class TestBaseModule:
    """测试模块基类"""

    def test_lifecycle(self) -> None:
        mod = DummyModule({"value": 5})
        assert mod.get_state()["value"] == 5
        assert mod.health_check() is True
        mod.reset()
        assert mod.get_state()["value"] == 0

    def test_config_required(self) -> None:
        with pytest.raises(ValidationError):
            DummyModule(None)


class TestPluginLoader:
    """测试插件加载器"""

    def test_load_not_found(self) -> None:
        reg = ModuleRegistry()
        loader = PluginLoader(reg)
        result = loader.load_from_path("test", "/nonexistent.py", "TestClass")
        assert result is False

    def test_is_loaded(self) -> None:
        reg = ModuleRegistry()
        loader = PluginLoader(reg)
        assert loader.is_loaded("test") is False
