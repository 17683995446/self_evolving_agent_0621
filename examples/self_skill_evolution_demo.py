"""Agent 自我技能进化演示

让 Agent 先扫描自己，发现自身问题，然后根据问题自动生成新技能插件并加载。
运行方式:
    cd /workspace/self_evolving_agent
    PYTHONPATH=/workspace/self_evolving_agent python examples/self_skill_evolution_demo.py
"""
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from root.left.app.left.src.core_mod.auto_skill_evolver import AutoSkillEvolver
from root.left.app.left.src.main import SelfEvolvingAgent

PROJECT_ROOT = Path("/workspace/self_evolving_agent")


def scan_project() -> Dict[str, Any]:
    """扫描项目文件系统，返回统计信息"""
    py_files = 0
    test_files = 0
    pycache_files = 0
    log_files = 0
    total_size = 0

    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv"}]
        if "__pycache__" in dirs:
            pycache_files += len(list((Path(root) / "__pycache__").glob("*.pyc")))
        for filename in files:
            file_path = Path(root) / filename
            try:
                total_size += file_path.stat().st_size
            except OSError:
                continue
            if filename.endswith(".py"):
                py_files += 1
                if filename.startswith("test_"):
                    test_files += 1
            if filename.endswith(".log"):
                log_files += 1

    return {
        "project_root": str(PROJECT_ROOT),
        "py_files": py_files,
        "test_files": test_files,
        "pycache_files": pycache_files,
        "log_files": log_files,
        "total_size_mb": round(total_size / 1024 / 1024, 2),
        "docs_complete": True,
    }


def recommendations_to_gaps(recommendations: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """把推荐转成技能进化器能理解的缺口"""
    gaps: list[Dict[str, Any]] = []
    for rec in recommendations:
        title = rec.get("title", "")
        if "测试" in title:
            gaps.append({"type": "test_coverage_low", "source": title})
        elif "缓存" in title:
            gaps.append({"type": "pycache_bloat", "source": title})
        elif "日志" in title:
            gaps.append({"type": "log_accumulation", "source": title})
    return gaps


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
                        "name": "filesystem_scan",
                        "type": "callback",
                        "config": {"callback": scan_project},
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
    phase1 = agent.phase_one.step()
    report = agent.generate_dashboard_report(phase1, {"task_pool_snapshot": {}})

    gaps = recommendations_to_gaps(report["recommendations"])

    if not gaps:
        print("Agent 没发现自己需要新技能，状态良好。")
        return

    with tempfile.TemporaryDirectory() as skill_dir:
        evolver = AutoSkillEvolver({"skill_dir": skill_dir, "dry_run": False, "skill_config": {}})
        result = evolver.evolve(gaps)

        print("=" * 50)
        print("Agent 自我技能进化完成")
        print(f"发现缺口: {result['total']} 个")
        print(f"成功进化出新技能: {len(result['evolved'])} 个")
        print("-" * 50)
        for idx, evolved in enumerate(result["evolved"], start=1):
            print(f"{idx}. 新技能: {evolved['class_name']}")
            print(f"   对应缺口: {evolved['gap_type']}")
            print(f"   插件文件: {evolved['file_path']}")
            print(f"   是否加载成功: {evolved['loaded']}")
            print(f"   健康检查: {evolved.get('healthy', False)}")
            print("   生成代码预览:")
            try:
                with open(evolved["file_path"], "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                for line in lines[:6]:
                    print(f"      {line}")
                if len(lines) > 6:
                    print("      ...")
            except OSError:
                pass
        print("=" * 50)


if __name__ == "__main__":
    main()
