"""AIOps 实用场景演示

演示如何利用本 Agent 框架实现一个简单的 AIOps 场景：
- 监控本地日志文件中的 ERROR 数量
- 当错误数增加时自动生成告警任务
- 执行 dry_run 动作（不真删文件）
- 生成推荐报告

运行方式:
    cd /workspace/self_evolving_agent
    python examples/practical_aiops_demo.py
"""
import os
import tempfile
from typing import Any, Dict

from root.left.app.left.src.main import SelfEvolvingAgent


def build_config(log_path: str) -> Dict[str, Any]:
    """构建 AIOps 演示配置"""
    return {
        "loop_interval": 0.0,
        "max_loops": 5,
        "phase1": {
            "sensory": {},
            "drive": {},
            "prediction": {},
            "adjustment": {},
            "data_collector": {
                "sources": [
                    {
                        "name": "app_log",
                        "type": "log",
                        "config": {
                            "path": log_path,
                            "max_lines": 50,
                            "patterns": {"error": "ERROR", "warn": "WARN"},
                        },
                    }
                ]
            },
        },
        "phase2": {
            "task_pool": {},
            "decision": {"exploration": {"base_exploration_ratio": 0.1}},
            "memory": {},
        },
        "phase3": {"evolution": {}}, 
        "action_executor": {
            "dry_run": True,
            "allowed_shell_prefixes": ["echo", "cat", "df", "du"],
        },
        "approval_gate": {"mode": "auto_pass"},
        "effect_verifier": {},
        "recommendation": {},
        "dashboard": {},
    }


def main() -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        log_path = f.name

    try:
        # 模拟产生一些错误日志
        with open(log_path, "a", encoding="utf-8") as f:
            for _ in range(3):
                f.write("ERROR connection timeout\n")
                f.write("WARN slow query\n")

        config = build_config(log_path)
        agent = SelfEvolvingAgent(config)
        agent.run(max_loops=5)

        # 模拟新一轮错误日志涌入，供最终推荐报告使用
        with open(log_path, "a", encoding="utf-8") as f:
            for _ in range(5):
                f.write("ERROR connection timeout\n")
            for _ in range(2):
                f.write("WARN slow query\n")

        phase1 = agent.phase_one.step()
        phase2 = agent.phase_two.step(phase1, agent.loop_count, 0.0, 0.0)
        report = agent.generate_dashboard_report(phase1, phase2)

        print("=" * 50)
        print("AIOps 演示完成")
        print(f"循环次数: {agent.loop_count}")
        print(f"采集数据: {report['state'].get('collected_data', {})}")
        print(f"推荐建议: {report['recommendations']}")
        print("=" * 50)
    finally:
        if os.path.exists(log_path):
            os.remove(log_path)


if __name__ == "__main__":
    main()
