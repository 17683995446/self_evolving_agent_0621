"""自愈动作 Playbook 演示

让 Agent 发现缓存/日志/测试等问题后，自动匹配并执行自愈 Playbook。
默认 dry_run=True，只打印会执行什么，不会真的删东西。
运行方式:
    cd /workspace/self_evolving_agent
    PYTHONPATH=/workspace/self_evolving_agent \
        /workspace/self_evolving_agent/.venv/bin/python examples/self_healing_demo.py
"""
from typing import Any, Dict

from root.left.app.left.src.core_mod.action_executor import ActionExecutor
from root.left.app.left.src.core_mod.action_playbook import PlaybookRunner, build_default_playbooks


def main() -> None:
    # 模拟推荐引擎给出的 4 条建议
    recommendations: list[Dict[str, Any]] = [
        {"title": "缓存文件过多（123 个）", "reason": "__pycache__ 堆积", "action": "清理缓存", "priority": 0.7},
        {"title": "日志文件较多（5 个）", "reason": "日志堆积", "action": "清理日志", "priority": 0.75},
        {"title": "测试覆盖不足", "reason": "测试比例低", "action": "补测试", "priority": 0.8},
        {"title": "未知问题", "reason": "没有匹配 playbook", "action": "忽略", "priority": 0.5},
    ]

    # dry_run=True：只演练，不真正执行删除
    executor = ActionExecutor({
        "dry_run": True,
        "allowed_shell_prefixes": ["find", "echo"],
        "approval_gate": {"mode": "auto_pass"},
    })
    registry = build_default_playbooks()
    runner = PlaybookRunner(registry, executor)

    results = runner.run(recommendations)

    print("=" * 60)
    print("自愈动作 Playbook 演练完成")
    print(f"匹配到 {len(results)} 个 Playbook")
    print("-" * 60)
    for idx, res in enumerate(results, start=1):
        print(f"{idx}. {res['playbook_name']}（对应：{res['recommendation_title']}）")
        print(f"   执行成功: {res['success']}")
        for step in res["steps"]:
            print(f"   命令: {step['stdout']}")
        if res.get("effect"):
            eff = res["effect"]
            print(f"   效果: {eff['metric']} before={eff['before']} after={eff['after']} improved={eff['improved']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
