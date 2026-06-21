"""Agent 自诊断工具

对 Agent 的环境、配置、模块合规性、模块健康状态进行全面检查，
生成用户可读的诊断报告，帮助快速定位问题。
"""
from typing import Any, Dict, List

from root.left.app.left.src.utils_main.module_inspector import ModuleComplianceInspector


class DiagnosticItem:
    """单项诊断结果"""

    def __init__(self, name: str, passed: bool, message: str, detail: str = "") -> None:
        self.name = name
        self.passed = passed
        self.message = message
        self.detail = detail

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "message": self.message,
            "detail": self.detail,
        }


class HealthDiagnoser:
    """Agent 健康诊断器"""

    def __init__(self) -> None:
        self.inspector = ModuleComplianceInspector()

    def run_full_diagnosis(self, agent: Any) -> List[DiagnosticItem]:
        """对 Agent 进行全面诊断，返回诊断项列表。"""
        results: List[DiagnosticItem] = []
        results.append(self._check_python())
        results.append(self._check_dependencies())
        results.append(self._check_config(agent))
        results.append(self._check_modules_compliance(agent))
        results.append(self._check_modules_health(agent))
        results.append(self._check_modules_state(agent))
        return results

    def _check_python(self) -> DiagnosticItem:
        import sys
        version = sys.version_info
        if version >= (3, 10):
            return DiagnosticItem(
                "python_version", True,
                f"Python {version.major}.{version.minor}.{version.micro}",
            )
        return DiagnosticItem(
            "python_version", False,
            f"需要 3.10+，当前 {version.major}.{version.minor}",
        )

    def _check_dependencies(self) -> DiagnosticItem:
        missing: List[str] = []
        for dep in ["yaml", "psutil"]:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
        if missing:
            return DiagnosticItem(
                "dependencies", False,
                f"缺少依赖: {', '.join(missing)}",
                "请运行: pip install " + " ".join(missing),
            )
        return DiagnosticItem("dependencies", True, "所有核心依赖已安装")

    def _check_config(self, agent: Any) -> DiagnosticItem:
        config = getattr(agent, "config", None)
        if config is None:
            return DiagnosticItem("config", False, "Agent 配置为空")
        required_sections = ["phase1", "phase2", "phase3"]
        missing = [s for s in required_sections if s not in config]
        if missing:
            return DiagnosticItem(
                "config", False,
                f"配置缺少必要段: {missing}",
            )
        return DiagnosticItem("config", True, "配置结构完整")

    def _check_modules_compliance(self, agent: Any) -> DiagnosticItem:
        if not hasattr(agent, "get_core_modules"):
            return DiagnosticItem(
                "modules_compliance", False,
                "Agent 不支持 get_core_modules",
            )
        modules = agent.get_core_modules()
        violations = self.inspector.list_violations(modules)
        if violations:
            names = [v.name for v in violations]
            return DiagnosticItem(
                "modules_compliance", False,
                f"不合规模块: {names}",
                str([v.to_dict() for v in violations]),
            )
        return DiagnosticItem(
            "modules_compliance", True,
            f"全部 {len(modules)} 个模块合规",
        )

    def _check_modules_health(self, agent: Any) -> DiagnosticItem:
        if not hasattr(agent, "get_core_modules"):
            return DiagnosticItem(
                "modules_health", False,
                "Agent 不支持 get_core_modules",
            )
        modules = agent.get_core_modules()
        unhealthy: List[str] = []
        for name, module in modules.items():
            try:
                if hasattr(module, "health_check"):
                    if not module.health_check():
                        unhealthy.append(name)
            except Exception as e:
                unhealthy.append(f"{name}(异常: {e})")
        if unhealthy:
            return DiagnosticItem(
                "modules_health", False,
                f"不健康模块: {unhealthy}",
            )
        return DiagnosticItem(
            "modules_health", True,
            f"全部 {len(modules)} 个模块健康",
        )

    def _check_modules_state(self, agent: Any) -> DiagnosticItem:
        if not hasattr(agent, "get_core_modules"):
            return DiagnosticItem(
                "modules_state", False,
                "Agent 不支持 get_core_modules",
            )
        modules = agent.get_core_modules()
        errors: List[str] = []
        for name, module in modules.items():
            try:
                if hasattr(module, "get_state"):
                    state = module.get_state()
                    if not isinstance(state, dict):
                        errors.append(f"{name}(返回非dict)")
            except Exception as e:
                errors.append(f"{name}(异常: {e})")
        if errors:
            return DiagnosticItem(
                "modules_state", False,
                f"状态获取异常: {errors}",
            )
        return DiagnosticItem(
            "modules_state", True,
            f"全部 {len(modules)} 个模块状态正常",
        )

    def format_report(self, items: List[DiagnosticItem]) -> str:
        """格式化诊断报告为用户可读文本（表格格式）。"""
        from root.left.app.left.src.utils_main.cli_formatter import (
            Color,
            colorize,
            format_pass_fail,
            render_section,
            render_table,
        )

        lines: List[str] = []
        lines.append("=== Agent 自诊断报告 ===")
        lines.append("")

        # 表格化诊断结果
        headers = ["检查项", "状态", "详情"]
        rows = []
        for item in items:
            status_sym = format_pass_fail(item.passed)
            status_text = "PASS" if item.passed else "FAIL"
            rows.append([item.name, f"{status_sym} {status_text}", item.message])

        lines.append(render_table(headers, rows))
        lines.append("")

        # 详情（仅显示失败项的 detail）
        failed_items = [i for i in items if not i.passed and i.detail]
        if failed_items:
            lines.append(render_section("修复建议"))
            for item in failed_items:
                lines.append(f"  {item.name}: {item.detail}")
            lines.append("")

        all_passed = all(i.passed for i in items)
        if all_passed:
            lines.append(colorize("所有检查通过，Agent 运行正常。", Color.GREEN))
        else:
            failed = [i for i in items if not i.passed]
            lines.append(
                colorize(f"共 {len(failed)} 项检查失败，请根据上述提示修复。", Color.RED)
            )
        return "\n".join(lines)

    def to_dict(self, items: List[DiagnosticItem]) -> Dict[str, Any]:
        """将诊断结果转为字典。"""
        return {
            "all_passed": all(i.passed for i in items),
            "total": len(items),
            "passed": sum(1 for i in items if i.passed),
            "failed": sum(1 for i in items if not i.passed),
            "items": [i.to_dict() for i in items],
        }
