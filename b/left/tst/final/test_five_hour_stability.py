"""5 小时长期稳定性测试框架

本测试用于验证 SelfEvolvingAgent 在长期运行期间的稳定性。

时长控制：
- 默认运行 300 秒（CI / 快速回归场景），可通过环境变量
  STABILITY_DURATION_SECONDS 覆盖，生产环境建议设置为 18000（5 小时）。
- 采样间隔固定 60 秒，记录运行期关键指标。
"""
import gc
import json
import os
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Dict, List

import psutil
import pytest

from root.left.app.left.src.main import SelfEvolvingAgent
from root.left.app.left.src.utils_main.logger import logger


# 默认 300 秒，避免无环境变量时直接跑满 5 小时；生产环境设置 STABILITY_DURATION_SECONDS=18000
DEFAULT_DURATION_SECONDS = 300
SAMPLING_INTERVAL = 60.0
REPORT_PATH = "/workspace/self_evolving_agent/reports/five_hour_report.json"


class TestFiveHourStability:
    """长期稳定性测试类"""

    @pytest.mark.slow
    def test_long_term_stability(self) -> None:
        """长期运行稳定性主测试"""
        duration = self._get_duration()
        self._ensure_reports_dir()

        agent = SelfEvolvingAgent()
        records: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        start_time = time.time()
        start_loop = agent.loop_count
        initial_rss_mb: float = 0.0
        max_rss_mb: float = 0.0
        process = psutil.Process()

        # 在后台线程中运行 agent.run()，以尊重 loop_interval 的真实节奏
        run_thread = threading.Thread(target=agent.run, daemon=True)

        try:
            gc.collect()
            run_thread.start()
            initial_rss_mb = process.memory_info().rss / (1024 * 1024)
            next_sample = start_time + SAMPLING_INTERVAL

            while time.time() - start_time < duration:
                now = time.time()
                if now >= next_sample:
                    gc.collect()
                    record = self._sample(agent, process, now)
                    records.append(record)
                    if record["rss_mb"] > max_rss_mb:
                        max_rss_mb = record["rss_mb"]
                    logger.info(
                        f"Sample at {record['elapsed_seconds']}s: "
                        f"loops={record['loop_count']} rss={record['rss_mb']:.1f}MB "
                        f"cpu={record['cpu_percent']:.1f}% perf={record['performance']:.4f}",
                        "stability",
                    )
                    next_sample += SAMPLING_INTERVAL
                time.sleep(1.0)
        except Exception as exc:  # noqa: BLE001
            errors.append({
                "loop": agent.loop_count,
                "timestamp": time.time(),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            })
            logger.error(f"Long-term test framework exception: {exc}", "stability")
        finally:
            agent.stop()
            run_thread.join(timeout=10.0)

        end_time = time.time()
        elapsed = end_time - start_time
        gc.collect()
        final_rss_mb = process.memory_info().rss / (1024 * 1024)
        memory_growth_mb = final_rss_mb - initial_rss_mb
        total_loops = agent.loop_count - start_loop
        error_rate = len(errors) / max(1, total_loops)

        report = self._build_report(
            duration=duration,
            elapsed=elapsed,
            agent=agent,
            records=records,
            errors=errors,
            initial_rss_mb=initial_rss_mb,
            final_rss_mb=final_rss_mb,
            memory_growth_mb=memory_growth_mb,
            total_loops=total_loops,
            error_rate=error_rate,
        )
        self._save_report(report)

        # 断言：系统未崩溃、循环数增加、内存增长可控、错误率有界
        assert total_loops > 0, "循环数未增加"
        assert len(errors) == 0 or error_rate < 0.05, f"错误率过高: {error_rate:.4f}"
        assert memory_growth_mb < 100.0, f"内存增长超过 100MB: {memory_growth_mb:.2f}MB"

    def _get_duration(self) -> int:
        """从环境变量读取运行时长，默认 300 秒"""
        raw = os.environ.get("STABILITY_DURATION_SECONDS")
        if raw is None:
            return DEFAULT_DURATION_SECONDS
        try:
            return max(1, int(raw))
        except ValueError:
            return DEFAULT_DURATION_SECONDS

    def _ensure_reports_dir(self) -> None:
        """确保报告目录存在"""
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)

    def _sample(self, agent: SelfEvolvingAgent, process: psutil.Process, timestamp: float) -> Dict[str, Any]:
        """采集单次指标"""
        mem = process.memory_info()
        cpu_percent = process.cpu_percent()
        phase1 = agent.phase_one.step()
        performance = phase1.get("performance", 0.0)
        error_rate = agent.phase_one.prediction.get_average_error()
        task_pool_size = agent.phase_two.task_pool.get_pool_snapshot().get("total", 0)
        decision_history_len = len(agent.phase_two.decision.decision_history)

        return {
            "timestamp": timestamp,
            "elapsed_seconds": round(timestamp - process.create_time(), 2),
            "loop_count": agent.loop_count,
            "rss_mb": round(mem.rss / (1024 * 1024), 2),
            "cpu_percent": round(cpu_percent, 2),
            "performance": round(performance, 4),
            "error_rate": round(error_rate, 4),
            "task_pool_size": task_pool_size,
            "decision_history_len": decision_history_len,
        }

    def _build_report(
        self,
        duration: int,
        elapsed: float,
        agent: SelfEvolvingAgent,
        records: List[Dict[str, Any]],
        errors: List[Dict[str, Any]],
        initial_rss_mb: float,
        final_rss_mb: float,
        memory_growth_mb: float,
        total_loops: int,
        error_rate: float,
    ) -> Dict[str, Any]:
        """生成最终报告"""
        return {
            "test_name": "five_hour_stability",
            "created_at": datetime.now().isoformat(),
            "config": {
                "requested_duration_seconds": duration,
                "actual_elapsed_seconds": round(elapsed, 2),
                "sampling_interval_seconds": SAMPLING_INTERVAL,
                "duration_source": "STABILITY_DURATION_SECONDS env var" if os.environ.get("STABILITY_DURATION_SECONDS") else "default",
            },
            "summary": {
                "total_loops": total_loops,
                "final_loop_count": agent.loop_count,
                "error_count": len(errors),
                "error_rate": round(error_rate, 6),
                "initial_rss_mb": round(initial_rss_mb, 2),
                "final_rss_mb": round(final_rss_mb, 2),
                "memory_growth_mb": round(memory_growth_mb, 2),
                "max_recorded_rss_mb": round(max((r["rss_mb"] for r in records), default=0.0), 2),
            },
            "records": records,
            "errors": errors,
            "passed": len(errors) == 0 and memory_growth_mb < 100.0 and total_loops > 0,
        }

    def _save_report(self, report: Dict[str, Any]) -> None:
        """持久化报告到 JSON"""
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"Long-term stability report saved to {REPORT_PATH}", "stability")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
