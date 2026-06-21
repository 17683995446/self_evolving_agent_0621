"""Agent 自我扫描演示

让 Agent 扫描自己的项目文件系统，根据扫描结果生成自我进化/维护策略。
运行方式:
    cd /workspace/self_evolving_agent
    PYTHONPATH=/workspace/self_evolving_agent python examples/self_scan_demo.py
"""
import os
from pathlib import Path
from typing import Any, Dict

from root.left.app.left.src.main import SelfEvolvingAgent

PROJECT_ROOT = Path("/workspace/self_evolving_agent")


def scan_project() -> Dict[str, Any]:
    """扫描项目文件系统，返回统计信息"""
    py_files = 0
    test_files = 0
    pycache_files = 0
    log_files = 0
    report_files = 0
    total_size = 0

    for root, dirs, files in os.walk(PROJECT_ROOT):
        # 跳过 .git 和超大目录，避免扫描过久
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv"}]

        rel_root = Path(root).relative_to(PROJECT_ROOT)

        # 统计 __pycache__ 里的缓存文件
        if "__pycache__" in dirs:
            pycache_dir = Path(root) / "__pycache__"
            pycache_files += len(list(pycache_dir.glob("*.pyc")))

        for filename in files:
            file_path = Path(root) / filename
            try:
                size = file_path.stat().st_size
            except OSError:
                continue
            total_size += size

            if filename.endswith(".py"):
                py_files += 1
                if filename.startswith("test_"):
                    test_files += 1
            if filename.endswith(".log"):
                log_files += 1
            if rel_root.parts[:2] == ("reports",):
                report_files += 1

    required_docs = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "root" / "right" / "doc" / "left" / "design" / "system_design.md",
        PROJECT_ROOT / "root" / "left" / "app" / "right" / "docs" / "architecture.md",
    ]
    docs_complete = all(f.exists() and f.stat().st_size > 0 for f in required_docs)

    return {
        "project_root": str(PROJECT_ROOT),
        "py_files": py_files,
        "test_files": test_files,
        "pycache_files": pycache_files,
        "log_files": log_files,
        "report_files": report_files,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "docs_complete": docs_complete,
    }


def build_config() -> Dict[str, Any]:
    """构建自我扫描配置"""
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
                        "name": "filesystem_scan",
                        "type": "callback",
                        "config": {"callback": scan_project},
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
        "action_executor": {"dry_run": True, "allowed_shell_prefixes": ["echo", "find"]},
        "approval_gate": {"mode": "auto_pass"},
        "effect_verifier": {},
        # 调低阈值，方便在演示中触发推荐
        "recommendation": {
            "fs_pycache_high": 1,
            "fs_log_high": 1,
            "fs_size_mb_high": 1,
            "fs_test_ratio_low": 0.9,
        },
        "dashboard": {},
    }


def main() -> None:
    config = build_config()
    agent = SelfEvolvingAgent(config)

    # 直接感知一次，获取文件系统扫描结果
    phase1 = agent.phase_one.step()
    report = agent.generate_dashboard_report(phase1, {"task_pool_snapshot": {}})

    scan = phase1["state"].get("collected_data", {}).get("filesystem_scan", {}).get("data", {})

    print("=" * 50)
    print("Agent 自我扫描完成")
    print(f"扫描路径: {scan.get('project_root', '')}")
    print(f"Python 源文件: {scan.get('py_files', 0)} 个")
    print(f"测试文件: {scan.get('test_files', 0)} 个")
    print(f"缓存文件: {scan.get('pycache_files', 0)} 个")
    print(f"日志文件: {scan.get('log_files', 0)} 个")
    print(f"报告文件: {scan.get('report_files', 0)} 个")
    print(f"总大小: {scan.get('total_size_mb', 0)} MB")
    print(f"文档完整: {scan.get('docs_complete', True)}")
    print("-" * 50)
    print("自我进化/维护策略:")
    for idx, rec in enumerate(report["recommendations"], start=1):
        print(f"{idx}. {rec['title']}")
        print(f"   原因: {rec['reason']}")
        print(f"   建议动作: {rec['action']}")
        print(f"   优先级: {rec['priority']:.2f}")
    if not report["recommendations"]:
        print("当前状态良好，暂无需要自我进化的策略。")
    print("=" * 50)


if __name__ == "__main__":
    main()
