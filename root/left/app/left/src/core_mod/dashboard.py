"""仪表盘/报告生成器

将 Agent 运行状态、推荐建议、效果验证汇总为可读报告，
支持 JSON 与 Markdown 两种输出格式。
"""
import json
from typing import Any, Dict, Final, List

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class Dashboard:
    """仪表盘报告生成器"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[Dashboard.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        logger.info("Dashboard initialized", "dashboard")

    def build_report(
        self,
        state: Dict[str, Any],
        drive_state: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
        effect_summary: Dict[str, Any],
        task_pool_snapshot: Dict[str, Any],
        loop_count: int,
    ) -> Dict[str, Any]:
        logger.debug("[Dashboard.build_report] start", "dashboard")
        return {
            "loop_count": loop_count,
            "state": state,
            "drive_state": drive_state,
            "recommendations": recommendations,
            "effect_summary": effect_summary,
            "task_pool": task_pool_snapshot,
            "generated_at": self._timestamp(),
        }

    def build_summary(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """从完整报告提取关键摘要，便于用户快速查看。"""
        state = report.get("state", {})
        recs = report.get("recommendations", [])
        pool = report.get("task_pool", {})
        return {
            "loop_count": report.get("loop_count", 0),
            "cpu_percent": state.get("cpu_percent", "N/A"),
            "memory_percent": state.get("memory_percent", "N/A"),
            "recommendation_count": len(recs),
            "top_recommendation": recs[0]["title"] if recs else None,
            "task_pool_total": pool.get("total", 0),
            "task_pool_pending": pool.get("pending", 0),
            "generated_at": report.get("generated_at", ""),
        }

    def to_json(self, report: Dict[str, Any]) -> str:
        return json.dumps(report, ensure_ascii=False, indent=2, default=str)

    def to_markdown(self, report: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("# Agent 运行仪表盘")
        lines.append("")
        lines.append(f"- **循环次数**: {report['loop_count']}")
        lines.append(f"- **生成时间**: {report['generated_at']}")
        lines.append("")
        lines.append("## 系统状态")
        lines.append("")
        state = report.get("state", {})
        lines.append(f"- CPU: {state.get('cpu_percent', 'N/A')}%")
        lines.append(f"- 内存: {state.get('memory_percent', 'N/A')}%")
        lines.append("")
        lines.append("## 推荐建议")
        lines.append("")
        for rec in report.get("recommendations", []):
            lines.append(f"### {rec['title']} (priority={rec['priority']})")
            lines.append(f"- 原因: {rec['reason']}")
            lines.append(f"- 建议动作: {rec['action']}")
            lines.append("")
        if not report.get("recommendations"):
            lines.append("当前无高优先级建议。")
            lines.append("")
        lines.append("## 任务池")
        lines.append("")
        pool = report.get("task_pool", {})
        for key, value in pool.items():
            lines.append(f"- {key}: {value}")
        lines.append("")
        return "\n".join(lines)

    def to_summary_text(self, report: Dict[str, Any]) -> str:
        """生成单行摘要文本，适合终端输出。"""
        summary = self.build_summary(report)
        cpu = summary["cpu_percent"]
        mem = summary["memory_percent"]
        cpu_str = f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else str(cpu)
        mem_str = f"{mem:.1f}%" if isinstance(mem, (int, float)) else str(mem)
        rec = summary["top_recommendation"] or "无"
        return (
            f"循环={summary['loop_count']} | "
            f"CPU={cpu_str} | 内存={mem_str} | "
            f"建议={summary['recommendation_count']}条(顶: {rec}) | "
            f"任务={summary['task_pool_total']}"
        )

    def _timestamp(self) -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def get_state(self) -> Dict[str, Any]:
        """获取仪表盘状态"""
        return {
            "config_keys": list(self.config.keys()),
        }

    def reset(self) -> None:
        """重置仪表盘"""
        logger.debug("[Dashboard.reset] called", "dashboard")

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[Dashboard.health_check] called", "dashboard")
        return True
