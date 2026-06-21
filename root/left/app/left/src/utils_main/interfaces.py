"""模块接口标准与插件系统

设计目标：像乐高/电子元器件那样模块化、接口化、可扩展。
核心原则：
1. 所有模块实现统一接口（ModuleProtocol）
2. 模块通过注册表按名称查找（Registry）
3. 依赖自动注入（DI Container）
4. 配置驱动组装（ConfigAssembler）
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Final, List, Optional, Protocol, Type, TypeVar

from root.left.app.left.src.utils_main.exceptions import ModuleNotFoundException, ValidationError
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class ModuleProtocol(Protocol):
    """模块标准接口协议

    所有可插拔模块必须实现的接口。
    类似于电子元器件的引脚标准——只要引脚对得上，就能插上去。
    """

    def __init__(self, config: Dict[str, Any]) -> None: ...

    def get_state(self) -> Dict[str, Any]:
        """获取模块当前状态（用于序列化/监控）"""
        ...

    def reset(self) -> None:
        """重置模块到初始状态"""
        ...

    def health_check(self) -> bool:
        """模块健康检查"""
        ...


class BaseModule(ABC):
    """模块抽象基类

    所有模块的基类，强制实现标准生命周期。
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError

    def health_check(self) -> bool:
        return True


T = TypeVar("T", bound=BaseModule)


class ModuleRegistry:
    """模块注册表

    类似于电子元器件的型号目录——按型号查找元器件。
    """

    def __init__(self) -> None:
        logger.debug("[ModuleRegistry.__init__] start")
        self._modules: Dict[str, Type[BaseModule]] = {}
        logger.info("ModuleRegistry initialized", "interfaces")

    def register(self, name: str, module_cls: Type[BaseModule]) -> None:
        logger.debug(f"[ModuleRegistry.register] name={name} cls={module_cls.__name__}")
        if not issubclass(module_cls, BaseModule):
            raise ValidationError(f"Module {module_cls.__name__} must inherit BaseModule")
        self._modules[name] = module_cls
        logger.info(f"[ModuleRegistry.register] registered={name}", "interfaces")

    def unregister(self, name: str) -> None:
        logger.debug(f"[ModuleRegistry.unregister] name={name}")
        self._modules.pop(name, None)

    def get(self, name: str) -> Type[BaseModule]:
        logger.debug(f"[ModuleRegistry.get] name={name}")
        cls = self._modules.get(name)
        if cls is None:
            raise ModuleNotFoundException(f"Module '{name}' not found in registry")
        return cls

    def list_modules(self) -> List[str]:
        result = list(self._modules.keys())
        logger.debug(f"[ModuleRegistry.list_modules] count={len(result)}")
        return result

    def has(self, name: str) -> bool:
        result = name in self._modules
        logger.debug(f"[ModuleRegistry.has] name={name} result={result}")
        return result


class DIContainer:
    """依赖注入容器

    自动解析模块间的依赖关系，按需实例化。
    类似于电路板的自动布线——引脚对引脚自动连接。
    """

    def __init__(self, registry: ModuleRegistry) -> None:
        logger.debug("[DIContainer.__init__] start")
        self.registry = registry
        self._instances: Dict[str, BaseModule] = {}
        self._singletons: set = set()
        logger.info("DIContainer initialized", "interfaces")

    def register_singleton(self, name: str) -> None:
        logger.debug(f"[DIContainer.register_singleton] name={name}")
        self._singletons.add(name)

    def resolve(self, name: str, config: Dict[str, Any]) -> BaseModule:
        logger.debug(f"[DIContainer.resolve] name={name}")
        if name in self._singletons and name in self._instances:
            logger.debug(f"[DIContainer.resolve] singleton reuse={name}")
            return self._instances[name]
        cls = self.registry.get(name)
        instance = cls(config)
        if name in self._singletons:
            self._instances[name] = instance
        logger.debug(f"[DIContainer.resolve] instance created={name}")
        return instance

    def get_instance(self, name: str) -> Optional[BaseModule]:
        return self._instances.get(name)

    def clear(self) -> None:
        logger.debug("[DIContainer.clear] start")
        self._instances.clear()


class ConfigAssembler:
    """配置驱动组装器

    通过配置文件声明式组装系统，无需硬编码。
    类似于乐高说明书——按步骤拼装模块。
    """

    def __init__(self, registry: ModuleRegistry, container: DIContainer) -> None:
        logger.debug("[ConfigAssembler.__init__] start")
        self.registry = registry
        self.container = container
        logger.info("ConfigAssembler initialized", "interfaces")

    def assemble(self, blueprint: Dict[str, Any]) -> Dict[str, BaseModule]:
        logger.debug("[ConfigAssembler.assemble] start")
        assembled: Dict[str, BaseModule] = {}
        for slot_name, spec in blueprint.items():
            module_name = spec.get("module")
            config = spec.get("config", {})
            singleton = spec.get("singleton", False)
            logger.debug(f"[ConfigAssembler.assemble] slot={slot_name} module={module_name}")
            if singleton:
                self.container.register_singleton(module_name)
            instance = self.container.resolve(module_name, config)
            assembled[slot_name] = instance
        logger.info(f"[ConfigAssembler.assemble] assembled={len(assembled)} modules", "interfaces")
        return assembled

    def validate_blueprint(self, blueprint: Dict[str, Any]) -> List[str]:
        logger.debug("[ConfigAssembler.validate_blueprint] start")
        errors: List[str] = []
        for slot_name, spec in blueprint.items():
            module_name = spec.get("module")
            if not module_name:
                errors.append(f"Slot '{slot_name}' missing 'module'")
            elif not self.registry.has(module_name):
                errors.append(f"Module '{module_name}' not registered")
        logger.debug(f"[ConfigAssembler.validate_blueprint] errors={len(errors)}")
        return errors


class PluginLoader:
    """插件加载器

    支持运行时动态加载外部模块。
    类似于USB热插拔——插入即用。
    """

    def __init__(self, registry: ModuleRegistry) -> None:
        logger.debug("[PluginLoader.__init__] start")
        self.registry = registry
        self._loaded: Dict[str, bool] = {}
        logger.info("PluginLoader initialized", "interfaces")

    def load_from_path(self, name: str, module_path: str, class_name: str) -> bool:
        logger.debug(f"[PluginLoader.load_from_path] name={name} path={module_path}")
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(name, module_path)
            if spec is None or spec.loader is None:
                logger.error(f"[PluginLoader.load_from_path] cannot load spec={name}")
                return False
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls = getattr(mod, class_name)
            self.registry.register(name, cls)
            self._loaded[name] = True
            logger.info(f"[PluginLoader.load_from_path] loaded={name}", "interfaces")
            return True
        except Exception as e:
            logger.error(f"[PluginLoader.load_from_path] failed={name} error={e}", "interfaces")
            return False

    def is_loaded(self, name: str) -> bool:
        return self._loaded.get(name, False)
