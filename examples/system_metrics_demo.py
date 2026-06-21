"""系统真实指标采集演示

让 Agent 直接读取本机 CPU、内存、磁盘、网络指标，并根据指标生成推荐。
运行方式:
    cd /workspace/self_evolving_agent
    PYTHONPATH=/workspace/self_evolving_agent python examples/system_metrics_demo.py
"""
from typing import Any, Dict

from root.left.app.left.src.main import SelfEvolvingAgent


def build_config() -> Dict[str, Any]:
    return {
        "loop_interval": 0.0,
        "max_loops": 0,
        "phase1": {
            "sensory": {},
            "drive": {},
            "prediction": {},
            "adjustment": {},
            "data_collector": {
                "sources": [
                    {
                        "name": "system_metrics",
                        "type": "system",
                        "config": {"metrics": ["cpu", "memory", "disk", "network"], "interval": 0.0},
                    }
                ]
            },
        },
        "phase2": {"task_pool": {}, "decision": {}, "memory": {}},
        "phase3": {"evolution": {}},
        "action_executor": {"dry_run": True},
        "approval_gate": {"mode": "auto_pass"},
        "effect_verifier": {},
        "recommendation": {
            "cpu_high": 50.0,
            "memory_high": 50.0,
            "disk_high": 50.0,
        },
        "dashboard": {},
    }


def main() -> None:
    config = build_config()
    agent = SelfEvolvingAgent(config)
    phase1 = agent.phase_one.step()
    report = agent.generate_dashboard_report(phase1, {"task_pool_snapshot": {}})

    metrics = (
        phase1["state"]
        .get("collected_data", {})
        .get("system_metrics", {})
        .get("data", {})
    )

    print("=" * 50)
    print("系统真实指标采集完成")
    print(f"CPU 使用率: {metrics.get('cpu_percent', 0)}%")
    print(f"内存使用率: {metrics.get('memory_percent', 0)}%")
    print(f"磁盘使用率: {metrics.get('disk_percent', 0)}%")
    print(f"网络发送: {metrics.get('network_bytes_sent', 0)} bytes")
    print(f"网络接收: {metrics.get('network_bytes_recv', 0)} bytes")
    print("-" * 50)
    print("基于真实指标的推荐:")
    if report["recommendations"]:
        for idx, rec in enumerate(report["recommendations"], start=1):
            print(f"{idx}. {rec['title']} (优先级 {rec['priority']:.2f})")
            print(f"   建议: {rec['action']}")
    else:
        print("当前系统指标正常，无需处理。")
    print("=" * 50)


if __name__ == "__main__":
    main()
