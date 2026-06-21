"""推荐引擎

根据 Agent 当前状态、历史表现和效果验证结果，生成可执行的推荐建议。
"""
from typing import Any, Dict, Final, List

from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class Recommendation:
    """推荐项"""

    def __init__(self, title: str, reason: str, action: str, priority: float) -> None:
        self.title: str = title
        self.reason: str = reason
        self.action: str = action
        self.priority: float = priority

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "reason": self.reason,
            "action": self.action,
            "priority": self.priority,
        }


class RecommendationEngine:
    """推荐引擎"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[RecommendationEngine.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.thresholds: Dict[str, float] = {
            "cpu_high": float(config.get("cpu_high", 80.0)),
            "memory_high": float(config.get("memory_high", 80.0)),
            "disk_high": float(config.get("disk_high", 90.0)),
            "error_rate_high": float(config.get("error_rate_high", 0.1)),
            "fs_pycache_high": float(config.get("fs_pycache_high", 20.0)),
            "fs_log_high": float(config.get("fs_log_high", 5.0)),
            "fs_size_mb_high": float(config.get("fs_size_mb_high", 100.0)),
            "fs_test_ratio_low": float(config.get("fs_test_ratio_low", 0.3)),
        }
        logger.info("RecommendationEngine initialized", "recommend")

    def generate(
        self,
        state: Dict[str, Any],
        drive_state: Dict[str, Any],
        effect_summary: Dict[str, Any],
    ) -> List[Recommendation]:
        logger.debug("[RecommendationEngine.generate] start", "recommend")
        recs: List[Recommendation] = []
        recs.extend(self._check_resources(state))
        recs.extend(self._check_collected_data(state))
        recs.extend(self._check_filesystem(state))
        recs.extend(self._check_gaps(drive_state))
        recs.extend(self._check_effects(effect_summary))
        recs.sort(key=lambda r: r.priority, reverse=True)
        logger.info(f"[RecommendationEngine.generate] generated {len(recs)} recommendations", "recommend")
        return recs

    def _check_resources(self, state: Dict[str, Any]) -> List[Recommendation]:
        recs: List[Recommendation] = []
        cpu = state.get("cpu_percent", 0.0)
        memory = state.get("memory_percent", 0.0)
        disk = state.get("disk_usage", {}).get("percent", 0.0)
        if cpu > self.thresholds["cpu_high"]:
            recs.append(Recommendation(
                "CPU 使用率过高",
                f"当前 CPU {cpu:.1f}% 超过阈值 {self.thresholds['cpu_high']}%",
                "disk_cleanup / restart_service / 优化高耗时任务",
                0.9,
            ))
        if memory > self.thresholds["memory_high"]:
            recs.append(Recommendation(
                "内存使用率过高",
                f"当前内存 {memory:.1f}% 超过阈值 {self.thresholds['memory_high']}%",
                "清理缓存 / 重启服务 / 调整内存参数",
                0.85,
            ))
        if disk > self.thresholds["disk_high"]:
            recs.append(Recommendation(
                "磁盘空间不足",
                f"当前磁盘 {disk:.1f}% 超过阈值 {self.thresholds['disk_high']}%",
                "disk_cleanup / 清理日志 / 扩容磁盘",
                0.95,
            ))
        return recs

    def _check_collected_data(self, state: Dict[str, Any]) -> List[Recommendation]:
        """根据采集到的真实数据（如日志错误数）生成推荐"""
        recs: List[Recommendation] = []
        collected = state.get("collected_data", {})
        for source in collected.values():
            if not isinstance(source, dict) or not source.get("success"):
                continue
            data = source.get("data", {})
            counts = data.get("counts", {}) if isinstance(data, dict) else {}
            if not isinstance(counts, dict):
                continue
            error_count = counts.get("error", 0)
            warn_count = counts.get("warn", 0)
            total_lines = len(data.get("lines", [])) or error_count + warn_count
            error_rate = error_count / total_lines if total_lines > 0 else 0.0
            if error_count > 0 and error_rate >= self.thresholds["error_rate_high"]:
                recs.append(Recommendation(
                    f"检测到 {error_count} 条错误日志",
                    f"数据源 {source.get('name', 'unknown')} 错误率 {error_rate:.1%} 超过阈值 {self.thresholds['error_rate_high']:.1%}",
                    "log_scan / alert / restart_service",
                    0.88,
                ))
            elif warn_count > 0 and error_rate == 0.0:
                recs.append(Recommendation(
                    f"检测到 {warn_count} 条警告日志",
                    f"数据源 {source.get('name', 'unknown')} 出现警告，建议排查",
                    "log_scan / check_service",
                    0.6,
                ))
        return recs

    def _check_filesystem(self, state: Dict[str, Any]) -> List[Recommendation]:
        """根据文件系统扫描结果给出自我进化/维护建议"""
        recs: List[Recommendation] = []
        collected = state.get("collected_data", {})
        for source in collected.values():
            if not isinstance(source, dict) or not source.get("success"):
                continue
            data = source.get("data", {})
            if not isinstance(data, dict):
                continue
            # 只处理 filesystem_scan 类型的数据
            if "project_root" not in data and "py_files" not in data:
                continue
            pycache = data.get("pycache_files", 0)
            logs = data.get("log_files", 0)
            size_mb = data.get("total_size_mb", 0.0)
            py_files = data.get("py_files", 0)
            test_files = data.get("test_files", 0)
            if pycache > self.thresholds["fs_pycache_high"]:
                recs.append(Recommendation(
                    f"缓存文件过多（{pycache} 个）",
                    "__pycache__ 缓存堆积会占用空间并增加部署体积",
                    "find . -type d -name __pycache__ -exec rm -rf {} +",
                    0.7,
                ))
            if logs > self.thresholds["fs_log_high"]:
                recs.append(Recommendation(
                    f"日志文件较多（{logs} 个）",
                    "日志堆积可能影响磁盘空间与排查效率",
                    "logrotate / 清理过期日志 / 转存对象存储",
                    0.75,
                ))
            if size_mb > self.thresholds["fs_size_mb_high"]:
                recs.append(Recommendation(
                    f"项目体积较大（{size_mb:.1f} MB）",
                    "整体体积超过阈值，建议清理冗余资源",
                    "清理缓存 / 删除旧报告 / 压缩历史数据",
                    0.65,
                ))
            if py_files > 0:
                ratio = test_files / py_files
                if ratio < self.thresholds["fs_test_ratio_low"]:
                    recs.append(Recommendation(
                        f"测试覆盖不足（测试/源码比 {ratio:.1%}）",
                        f"源码文件 {py_files} 个，测试文件仅 {test_files} 个",
                        "补充单元测试 / 提高核心模块覆盖率",
                        0.8,
                    ))
            if not data.get("docs_complete", True):
                recs.append(Recommendation(
                    "文档不完整",
                    "缺少 README 或关键设计文档",
                    "补充 README / 架构文档 / 部署手册",
                    0.6,
                ))
        return recs

    def _check_gaps(self, drive_state: Dict[str, Any]) -> List[Recommendation]:
        recs: List[Recommendation] = []
        gaps = drive_state.get("gaps", {})
        if gaps.get("safe", 0.0) > 0.6:
            recs.append(Recommendation(
                "安全缺口较大",
                "系统安全/稳定性风险高于预期",
                "health_check / 加固配置 / 增加监控",
                0.8,
            ))
        if gaps.get("gain", 0.0) > 0.6:
            recs.append(Recommendation(
                "收益缺口较大",
                "性能/收益指标未达目标",
                "log_scan / adjust_config / 优化模型参数",
                0.7,
            ))
        if gaps.get("eff", 0.0) > 0.6:
            recs.append(Recommendation(
                "能效缺口较大",
                "资源消耗偏高",
                "disk_cleanup / 降低轮询频率 / 关闭非必要模块",
                0.75,
            ))
        return recs

    def _check_effects(self, effect_summary: Dict[str, Any]) -> List[Recommendation]:
        recs: List[Recommendation] = []
        latest = effect_summary.get("latest", {})
        performance = latest.get("performance")
        if performance is not None and performance < 0.3:
            recs.append(Recommendation(
                "综合表现分较低",
                f"当前 performance={performance:.2f}，建议触发回滚或调参",
                "rollback / adjust_config / 检查数据源",
                0.9,
            ))
        return recs

    def to_dict_list(self, recs: List[Recommendation]) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in recs]

    def get_state(self) -> Dict[str, Any]:
        """获取推荐引擎状态"""
        return {
            "thresholds": self.thresholds,
        }

    def reset(self) -> None:
        """重置推荐引擎"""
        logger.debug("[RecommendationEngine.reset] called", "recommend")

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[RecommendationEngine.health_check] called", "recommend")
        return all(isinstance(v, (int, float)) and v >= 0 for v in self.thresholds.values())
