"""自动技能进化模块

让 Agent 根据自身发现的缺口，自动生成并加载新的技能插件。
类似于：机器人发现自己不会拧螺丝，就自动给自己加装一个拧螺丝的手臂。
"""
import os
from typing import Any, Dict, List, Optional

from root.left.app.left.src.utils_main.interfaces import ModuleRegistry, PluginLoader
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class SkillTemplate:
    """技能模板

    每个模板定义了：遇到什么缺口、生成什么插件代码、插件类名是什么。
    """

    def __init__(
        self,
        gap_type: str,
        class_name: str,
        module_name: str,
        source_code: str,
    ) -> None:
        self.gap_type = gap_type
        self.class_name = class_name
        self.module_name = module_name
        self.source_code = source_code


# 预置技能模板库
SKILL_TEMPLATES: Dict[str, SkillTemplate] = {
    "test_coverage_low": SkillTemplate(
        gap_type="test_coverage_low",
        class_name="CoverageBoosterSkill",
        module_name="coverage_booster_skill",
        source_code='''"""自动覆盖率提升技能"""
from typing import Any, Dict, List

from root.left.app.left.src.utils_main.interfaces import BaseModule


class CoverageBoosterSkill(BaseModule):
    """扫描源码目录，找出缺少测试的模块并给出建议。"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.scan_root = config.get("scan_root", ".")

    def get_state(self) -> Dict[str, Any]:
        return {"scan_root": self.scan_root, "healthy": True}

    def reset(self) -> None:
        pass

    def suggest_targets(self) -> List[str]:
        """简单示例：返回需要补测试的模块列表"""
        return ["core_mod/recommendation_engine", "core_mod/action_executor"]
''',
    ),
    "log_accumulation": SkillTemplate(
        gap_type="log_accumulation",
        class_name="LogRotatorSkill",
        module_name="log_rotator_skill",
        source_code='''"""日志自动轮转技能"""
from typing import Any, Dict

from root.left.app.left.src.utils_main.interfaces import BaseModule


class LogRotatorSkill(BaseModule):
    """发现日志堆积时，给出轮转建议。"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.log_dir = config.get("log_dir", ".")

    def get_state(self) -> Dict[str, Any]:
        return {"log_dir": self.log_dir, "healthy": True}

    def reset(self) -> None:
        pass

    def plan_rotation(self) -> Dict[str, Any]:
        return {"action": "rotate", "target": self.log_dir, "retention_days": 7}
''',
    ),
    "pycache_bloat": SkillTemplate(
        gap_type="pycache_bloat",
        class_name="CacheCleanerSkill",
        module_name="cache_cleaner_skill",
        source_code='''"""缓存清理技能"""
from typing import Any, Dict, List

from root.left.app.left.src.utils_main.interfaces import BaseModule


class CacheCleanerSkill(BaseModule):
    """扫描 __pycache__ 目录并给出清理建议。"""

    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.target_root = config.get("target_root", ".")

    def get_state(self) -> Dict[str, Any]:
        return {"target_root": self.target_root, "healthy": True}

    def reset(self) -> None:
        pass

    def find_targets(self) -> List[str]:
        return [f"{self.target_root}/__pycache__"]
''',
    ),
}


class AutoSkillEvolver:
    """自动技能进化器

    根据系统缺口，自动生成、加载并验证新技能插件。
    """

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[AutoSkillEvolver.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config = config
        self.skill_dir: str = config.get("skill_dir", "./skills")
        self.dry_run: bool = config.get("dry_run", True)
        self.registry = ModuleRegistry()
        self.plugin_loader = PluginLoader(self.registry)
        os.makedirs(self.skill_dir, exist_ok=True)
        logger.info(f"AutoSkillEvolver initialized skill_dir={self.skill_dir}", "skill")

    def evolve(self, gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """根据缺口列表进化技能"""
        logger.debug(f"[AutoSkillEvolver.evolve] gaps={len(gaps)}", "skill")
        evolved: List[Dict[str, Any]] = []
        for gap in gaps:
            result = self._try_evolve_one(gap)
            if result:
                evolved.append(result)
        logger.info(f"[AutoSkillEvolver.evolve] evolved={len(evolved)}", "skill")
        return {"evolved": evolved, "total": len(gaps)}

    def _try_evolve_one(self, gap: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        gap_type = gap.get("type", "")
        template = SKILL_TEMPLATES.get(gap_type)
        if template is None:
            logger.debug(f"[AutoSkillEvolver._try_evolve_one] no template for {gap_type}", "skill")
            return None

        file_path = os.path.join(self.skill_dir, f"{template.module_name}.py")
        if self.dry_run:
            logger.info(f"[AutoSkillEvolver._try_evolve_one] dry_run would generate {file_path}", "skill")
            return {
                "gap_type": gap_type,
                "module_name": template.module_name,
                "class_name": template.class_name,
                "file_path": file_path,
                "loaded": False,
                "dry_run": True,
            }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(template.source_code)
            loaded = self.plugin_loader.load_from_path(
                template.module_name,
                file_path,
                template.class_name,
            )
            healthy = False
            if loaded:
                instance = self.registry.get(template.module_name)(self.config.get("skill_config", {}))
                healthy = instance.health_check()
            return {
                "gap_type": gap_type,
                "module_name": template.module_name,
                "class_name": template.class_name,
                "file_path": file_path,
                "loaded": loaded,
                "healthy": healthy,
                "dry_run": False,
            }
        except Exception as exc:
            logger.error(f"[AutoSkillEvolver._try_evolve_one] failed gap={gap_type} error={exc}", "skill")
            return {
                "gap_type": gap_type,
                "module_name": template.module_name,
                "file_path": file_path,
                "loaded": False,
                "error": str(exc),
                "dry_run": False,
            }

    def list_available_templates(self) -> List[str]:
        return list(SKILL_TEMPLATES.keys())

    def is_skill_loaded(self, name: str) -> bool:
        return self.plugin_loader.is_loaded(name)

    def get_state(self) -> Dict[str, Any]:
        """获取技能进化器状态"""
        return {
            "skill_dir": self.skill_dir,
            "dry_run": self.dry_run,
            "available_templates": self.list_available_templates(),
        }

    def reset(self) -> None:
        """重置技能进化器"""
        logger.debug("[AutoSkillEvolver.reset] called", "skill")

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[AutoSkillEvolver.health_check] called", "skill")
        return os.path.isdir(self.skill_dir)
