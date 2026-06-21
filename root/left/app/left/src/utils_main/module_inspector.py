"""模块合规检查器

确保所有核心模块都遵循统一的 ModuleProtocol 接口：
- get_state：可获取状态
- reset：可重置
- health_check：可做健康检查

类似于给每个电子元器件做引脚检测，插上去之前先确认引脚对得上。
"""
from typing import Any, Dict, List, Tuple

from root.left.app.left.src.utils_main.logger import logger


class ModuleComplianceReport:
    """模块合规报告"""

    def __init__(self, name: str, passed: bool, missing: List[str]) -> None:
        self.name = name
        self.passed = passed
        self.missing = missing

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "missing": self.missing,
        }


class ModuleComplianceInspector:
    """模块合规检查器"""

    REQUIRED_METHODS: Tuple[str, ...] = ("get_state", "reset", "health_check")

    def inspect(self, name: str, module: Any) -> ModuleComplianceReport:
        """检查单个模块是否合规"""
        logger.debug(f"[ModuleComplianceInspector.inspect] name={name}", "inspector")
        missing: List[str] = []
        for method in self.REQUIRED_METHODS:
            if not hasattr(module, method):
                missing.append(method)
            else:
                attr = getattr(module, method)
                if not callable(attr):
                    missing.append(f"{method}(not callable)")
        passed = len(missing) == 0
        return ModuleComplianceReport(name, passed, missing)

    def inspect_many(self, modules: Dict[str, Any]) -> List[ModuleComplianceReport]:
        """批量检查多个模块"""
        return [self.inspect(name, module) for name, module in modules.items()]

    def is_fully_compliant(self, modules: Dict[str, Any]) -> bool:
        """判断所有模块是否全部合规"""
        return all(report.passed for report in self.inspect_many(modules))

    def list_violations(self, modules: Dict[str, Any]) -> List[ModuleComplianceReport]:
        """列出不合规的模块"""
        return [report for report in self.inspect_many(modules) if not report.passed]
