"""CLI 交互式引导与帮助系统

为新用户提供渐进式发现（progressive disclosure）的引导：
- welcome: 首次使用介绍
- help: 按命令分组的详细帮助与示例
- examples: 常见使用场景
- guide: 交互式向导，逐步询问并构建运行配置

设计原则（第一性原理）：
1. 可发现性：用户无需阅读外部文档即可发现所有功能
2. 渐进式披露：先给最少信息，允许下钻获取细节
3. 可操作指引：每个错误或疑问都附带具体下一步
4. 非侵入式：交互特性为可选，不影响高级用户
"""
from __future__ import annotations

import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# 命令元数据：集中维护命令说明与示例，避免散落在多处
# ---------------------------------------------------------------------------

COMMAND_GUIDE: Dict[str, Dict[str, Any]] = {
    "run": {
        "summary": "启动 Agent 运行主循环",
        "description": (
            "加载指定环境的配置并启动 Agent 主循环。"
            "支持限制循环次数、设置端口、dry-run 模式等。"
        ),
        "examples": [
            ("基本启动（dev 环境）", "python -m root.left.app.left.src.cli run"),
            ("指定环境与循环次数", "python -m root.left.app.left.src.cli run --env prod --max-loops 100"),
            ("启用健康检查端口", "python -m root.left.app.left.src.cli run --port 8080"),
            ("试运行（不执行真实动作）", "python -m root.left.app.left.src.cli run --dry-run"),
            ("交互式向导引导", "python -m root.left.app.left.src.cli run --guide"),
        ],
    },
    "status": {
        "summary": "查询运行中 Agent 的状态",
        "description": "通过 HTTP 接口查询正在运行的 Agent 的当前状态，以 JSON 格式输出。",
        "examples": [
            ("查询默认端口", "python -m root.left.app.left.src.cli status"),
            ("查询指定端口", "python -m root.left.app.left.src.cli status --port 9090"),
        ],
    },
    "health": {
        "summary": "检查运行中 Agent 的健康状态",
        "description": "通过 HTTP 接口检查 Agent 是否健康，返回简明状态。",
        "examples": [
            ("检查默认端口", "python -m root.left.app.left.src.cli health"),
            ("检查指定端口", "python -m root.left.app.left.src.cli health --port 9090"),
        ],
    },
    "validate": {
        "summary": "校验配置文件是否合法",
        "description": "加载并校验指定环境的配置文件，不启动 Agent。适合在部署前验证配置。",
        "examples": [
            ("校验 dev 配置", "python -m root.left.app.left.src.cli validate --env dev"),
            ("校验 prod 配置", "python -m root.left.app.left.src.cli validate --env prod"),
        ],
    },
    "config": {
        "summary": "查看配置",
        "description": (
            "查看默认配置、当前环境配置或配置项说明。"
            "新用户建议先运行 --describe 了解各配置项含义。"
        ),
        "examples": [
            ("查看默认配置", "python -m root.left.app.left.src.cli config --show-defaults"),
            ("查看配置项说明", "python -m root.left.app.left.src.cli config --describe"),
            ("查看当前环境配置", "python -m root.left.app.left.src.cli config --env dev"),
        ],
    },
    "doctor": {
        "summary": "自诊断：检查环境、配置、依赖、模块是否就绪",
        "description": "执行快速自诊断，检查 Python 版本、配置、依赖与模块状态，判断 Agent 是否可以启动。",
        "examples": [
            ("运行自诊断", "python -m root.left.app.left.src.cli doctor"),
        ],
    },
    "diagnose": {
        "summary": "深度诊断 Agent 模块状态",
        "description": "对 Agent 进行 6 项深度诊断（Python、依赖、配置、模块合规、模块健康、模块状态），支持 JSON 输出。",
        "examples": [
            ("文本格式诊断", "python -m root.left.app.left.src.cli diagnose"),
            ("JSON 格式诊断", "python -m root.left.app.left.src.cli diagnose --json"),
        ],
    },
    "welcome": {
        "summary": "首次使用介绍",
        "description": "显示 Agent 简介、核心能力与快速上手指南，适合新用户首次了解系统。",
        "examples": [
            ("查看欢迎信息", "python -m root.left.app.left.src.cli welcome"),
        ],
    },
    "help": {
        "summary": "查看命令帮助",
        "description": (
            "显示所有命令的概览，或指定命令的详细说明与示例。"
            "新用户建议先运行 help 查看所有可用命令。"
        ),
        "examples": [
            ("查看所有命令", "python -m root.left.app.left.src.cli help"),
            ("查看 run 命令详情", "python -m root.left.app.left.src.cli help run"),
            ("查看 config 命令详情", "python -m root.left.app.left.src.cli help config"),
        ],
    },
    "examples": {
        "summary": "常见使用场景示例",
        "description": "按场景分类展示常用命令组合，帮助用户快速找到所需用法。",
        "examples": [
            ("查看所有示例", "python -m root.left.app.left.src.cli examples"),
        ],
    },
    "init": {
        "summary": "从模板创建配置文件",
        "description": (
            "使用预定义模板快速创建配置文件，无需手写 YAML。"
            "支持列出模板、查看模板内容、从模板创建配置。"
        ),
        "examples": [
            ("列出所有模板", "python -m root.left.app.left.src.cli init --list"),
            ("查看标准模板", "python -m root.left.app.left.src.cli init --show standard"),
            ("从模板创建 dev 配置", "python -m root.left.app.left.src.cli init --template standard --env dev"),
            ("覆盖创建生产配置", "python -m root.left.app.left.src.cli init --template production --env prod --force"),
        ],
    },
    "control": {
        "summary": "运行时控制 Agent（暂停/恢复/停止/重载/状态）",
        "description": (
            "通过 HTTP 接口控制正在运行的 Agent，支持暂停、恢复、停止、"
            "配置热重载和状态查询。需要 Agent 已启动并开启健康检查端口。"
        ),
        "examples": [
            ("查询控制状态", "python -m root.left.app.left.src.cli control status --port 8080"),
            ("暂停 Agent", "python -m root.left.app.left.src.cli control pause --port 8080"),
            ("恢复 Agent", "python -m root.left.app.left.src.cli control resume --port 8080"),
            ("停止 Agent", "python -m root.left.app.left.src.cli control stop --port 8080"),
            ("热重载配置", "python -m root.left.app.left.src.cli control reload --port 8080 --env dev"),
        ],
    },
    "docs": {
        "summary": "查看用户文档",
        "description": (
            "显示工具内用户文档，包括快速入门、命令参考、配置指南、"
            "故障排查与常见问题。无需联网或查阅外部文件。"
        ),
        "examples": [
            ("查看文档索引", "python -m root.left.app.left.src.cli docs"),
            ("快速入门指南", "python -m root.left.app.left.src.cli docs quickstart"),
            ("命令参考", "python -m root.left.app.left.src.cli docs commands"),
            ("配置指南", "python -m root.left.app.left.src.cli docs config"),
            ("故障排查", "python -m root.left.app.left.src.cli docs troubleshooting"),
            ("常见问题", "python -m root.left.app.left.src.cli docs faq"),
        ],
    },
    "logs": {
        "summary": "查看与分析日志文件",
        "description": (
            "解析日志文件，支持按级别、模块、关键字过滤，"
            "提供日志统计（级别分布、模块分布、错误/警告汇总）。"
        ),
        "examples": [
            ("查看日志", "python -m root.left.app.left.src.cli logs run_output.log"),
            ("只看错误", "python -m root.left.app.left.src.cli logs run_output.log --level ERROR"),
            ("按模块过滤", "python -m root.left.app.left.src.cli logs run_output.log --module main"),
            ("关键字搜索", "python -m root.left.app.left.src.cli logs run_output.log --keyword 启动"),
            ("最后 20 条", "python -m root.left.app.left.src.cli logs run_output.log --tail 20"),
            ("日志统计", "python -m root.left.app.left.src.cli logs run_output.log --stats"),
        ],
    },
    "report": {
        "summary": "生成运行报告",
        "description": (
            "从日志文件生成运行报告，包含日志统计、关键错误与警告。"
            "支持文本与 JSON 格式，可保存到文件。"
        ),
        "examples": [
            ("生成文本报告", "python -m root.left.app.left.src.cli report run_output.log"),
            ("生成 JSON 报告", "python -m root.left.app.left.src.cli report run_output.log --json"),
            ("带运行参数", "python -m root.left.app.left.src.cli report run_output.log --loop-count 100 --duration 3600"),
            ("保存到文件", "python -m root.left.app.left.src.cli report run_output.log --output report.txt"),
        ],
    },
    "completion": {
        "summary": "生成或安装 Shell 补全脚本",
        "description": (
            "为 bash 或 zsh 生成命令补全脚本，支持 Tab 补全子命令与选项。"
            "默认自动检测当前 shell，也可手动指定。"
        ),
        "examples": [
            ("自动检测 shell 生成补全", "python -m root.left.app.left.src.cli completion"),
            ("生成 bash 补全", "python -m root.left.app.left.src.cli completion --shell bash"),
            ("生成 zsh 补全", "python -m root.left.app.left.src.cli completion --shell zsh"),
            ("查看安装指引", "python -m root.left.app.left.src.cli completion --install"),
            ("指定命令名", "python -m root.left.app.left.src.cli completion --shell bash --command-name agent"),
        ],
    },
    "install": {
        "summary": "安装一键启动脚本",
        "description": (
            "安装 shell 包装脚本，让用户用短命令（如 agent）替代长 python 命令。"
            "安装后可直接使用 agent run、agent doctor 等短命令。"
        ),
        "examples": [
            ("查看安装指引", "python -m root.left.app.left.src.cli install"),
            ("安装到默认目录", "python -m root.left.app.left.src.cli install --install-dir ~/.local/bin"),
            ("指定命令名安装", "python -m root.left.app.left.src.cli install --command-name agent --install-dir /usr/local/bin"),
            ("覆盖安装", "python -m root.left.app.left.src.cli install --install-dir ~/.local/bin --force"),
        ],
    },
    "diff": {
        "summary": "配置差异对比与变更审计",
        "description": (
            "对比两份配置的差异，支持环境间对比、与默认配置对比、文件间对比。"
            "可生成审计报告，记录新增、删除、修改的配置项。"
        ),
        "examples": [
            ("对比两个环境", "python -m root.left.app.left.src.cli diff --env dev --against prod"),
            ("对比环境与默认配置", "python -m root.left.app.left.src.cli diff --env dev --against-defaults"),
            ("对比两个配置文件", "python -m root.left.app.left.src.cli diff --file a.yaml --file2 b.yaml"),
            ("生成审计报告", "python -m root.left.app.left.src.cli diff --audit --env dev"),
            ("JSON 格式输出", "python -m root.left.app.left.src.cli diff --env dev --against-defaults --json"),
            ("保存审计报告", "python -m root.left.app.left.src.cli diff --audit --env dev --output report.txt"),
            ("显示配置项说明", "python -m root.left.app.left.src.cli diff --env dev --against-defaults --describe"),
        ],
    },
    "benchmark": {
        "summary": "性能基准与资源占用报告",
        "description": (
            "测量 Agent 的配置加载耗时、循环耗时、内存分配性能，"
            "并采集系统信息（CPU、内存）。支持持续监控模式。"
        ),
        "examples": [
            ("运行基准测试", "python -m root.left.app.left.src.cli benchmark"),
            ("指定迭代次数", "python -m root.left.app.left.src.cli benchmark --iterations 20"),
            ("资源监控模式", "python -m root.left.app.left.src.cli benchmark --monitor"),
            ("监控采样间隔", "python -m root.left.app.left.src.cli benchmark --monitor --interval 2.0"),
            ("JSON 格式输出", "python -m root.left.app.left.src.cli benchmark --json"),
            ("保存基准报告", "python -m root.left.app.left.src.cli benchmark --output bench.txt"),
        ],
    },
    "repl": {
        "summary": "启动交互式 REPL",
        "description": (
            "启动交互式命令行界面，支持命令历史、Tab 补全与会话管理。"
            "在 REPL 中可直接输入子命令（如 run、status），无需重复输入完整前缀。"
            "支持 !history、!search、!clear 等特殊命令。"
        ),
        "examples": [
            ("启动 REPL", "python -m root.left.app.left.src.cli repl"),
            ("指定历史文件", "python -m root.left.app.left.src.cli repl --history-file ~/.my_history"),
            ("非交互式环境强制启动", "python -m root.left.app.left.src.cli repl --force"),
        ],
    },
    "alert": {
        "summary": "告警系统管理",
        "description": (
            "管理告警规则、评估指标、查看告警历史。"
            "支持 CPU/内存/错误数等指标的阈值告警，"
            "提供控制台、日志、Webhook 等通知渠道。"
        ),
        "examples": [
            ("列出告警规则", "python -m root.left.app.left.src.cli alert --list-rules"),
            ("告警系统摘要", "python -m root.left.app.left.src.cli alert --summary"),
            ("测试告警触发", "python -m root.left.app.left.src.cli alert --test"),
            ("评估指定指标", "python -m root.left.app.left.src.cli alert --evaluate '{\"cpu_percent\": 90}'"),
        ],
    },
    "schedule": {
        "summary": "定时任务调度",
        "description": (
            "管理基于 cron 表达式的定时任务。"
            "支持添加/移除/启用/禁用任务、查看下次执行时间、"
            "查看执行历史、校验与测试 cron 表达式。"
        ),
        "examples": [
            ("列出所有任务", "python -m root.left.app.left.src.cli schedule --list"),
            ("显示预设 cron", "python -m root.left.app.left.src.cli schedule --presets"),
            ("添加任务", "python -m root.left.app.left.src.cli schedule --add backup '0 2 * * *' 'echo backup'"),
            ("校验 cron 表达式", "python -m root.left.app.left.src.cli schedule --validate '*/5 * * * *'"),
            ("测试 cron 下次匹配", "python -m root.left.app.left.src.cli schedule --test '0 9 * * 1-5'"),
            ("查看下次执行", "python -m root.left.app.left.src.cli schedule --next"),
            ("查看执行历史", "python -m root.left.app.left.src.cli schedule --history"),
        ],
    },
    "data": {
        "summary": "数据导入导出与备份恢复",
        "description": (
            "管理 Agent 数据的导出、导入、备份与恢复。"
            "支持配置、状态数据库、报告的 JSON 导出导入，"
            "支持完整系统状态的 tar.gz 备份与校验和验证。"
        ),
        "examples": [
            ("导出全部数据", "python -m root.left.app.left.src.cli data --export backup.json"),
            ("导出配置", "python -m root.left.app.left.src.cli data --export config.json --type config"),
            ("导入数据", "python -m root.left.app.left.src.cli data --import backup.json"),
            ("创建备份", "python -m root.left.app.left.src.cli data --backup backup.tar.gz"),
            ("恢复备份", "python -m root.left.app.left.src.cli data --restore backup.tar.gz"),
            ("列出备份", "python -m root.left.app.left.src.cli data --list-backups"),
            ("验证备份", "python -m root.left.app.left.src.cli data --verify backup.tar.gz"),
        ],
    },
    "instance": {
        "summary": "多实例管理与编排",
        "description": (
            "管理多个 Agent 实例的注册、控制与编排。"
            "支持添加/移除实例、启动/停止/重启单个实例、"
            "批量启动/停止所有实例、保存与加载实例配置。"
        ),
        "examples": [
            ("列出所有实例", "python -m root.left.app.left.src.cli instance --list"),
            ("添加实例", "python -m root.left.app.left.src.cli instance --add agent1 --env-opt dev --port-opt 8080"),
            ("实例详情", "python -m root.left.app.left.src.cli instance --info agent1"),
            ("启动实例", "python -m root.left.app.left.src.cli instance --start agent1"),
            ("停止实例", "python -m root.left.app.left.src.cli instance --stop agent1"),
            ("启动所有实例", "python -m root.left.app.left.src.cli instance --start-all"),
            ("保存配置", "python -m root.left.app.left.src.cli instance --save instances.json"),
            ("加载配置", "python -m root.left.app.left.src.cli instance --load instances.json"),
        ],
    },
}

# 按场景分类的示例（用于 examples 子命令）
SCENARIO_EXAMPLES: List[Dict[str, Any]] = [
    {
        "category": "首次使用",
        "items": [
            ("1. 查看系统介绍", "python -m root.left.app.left.src.cli welcome"),
            ("2. 查看快速入门文档", "python -m root.left.app.left.src.cli docs quickstart"),
            ("3. 运行自诊断确认环境就绪", "python -m root.left.app.left.src.cli doctor"),
            ("4. 校验配置", "python -m root.left.app.left.src.cli validate --env dev"),
            ("5. 启动 Agent（试运行）", "python -m root.left.app.left.src.cli run --dry-run --max-loops 3"),
        ],
    },
    {
        "category": "日常运行",
        "items": [
            ("启动 Agent（dev 环境）", "python -m root.left.app.left.src.cli run --env dev"),
            ("启动 Agent（生产环境）", "python -m root.left.app.left.src.cli run --env prod"),
            ("无限循环运行", "python -m root.left.app.left.src.cli run --max-loops 0"),
            ("查看运行状态", "python -m root.left.app.left.src.cli status --port 8080"),
            ("检查健康", "python -m root.left.app.left.src.cli health --port 8080"),
        ],
    },
    {
        "category": "配置管理",
        "items": [
            ("查看默认配置", "python -m root.left.app.left.src.cli config --show-defaults"),
            ("查看配置项说明", "python -m root.left.app.left.src.cli config --describe"),
            ("查看当前环境配置", "python -m root.left.app.left.src.cli config --env dev"),
            ("校验配置", "python -m root.left.app.left.src.cli validate --env dev"),
            ("列出配置模板", "python -m root.left.app.left.src.cli init --list"),
            ("从模板创建配置", "python -m root.left.app.left.src.cli init --template standard --env dev"),
        ],
    },
    {
        "category": "运行时控制",
        "items": [
            ("查询控制状态", "python -m root.left.app.left.src.cli control status --port 8080"),
            ("暂停 Agent", "python -m root.left.app.left.src.cli control pause --port 8080"),
            ("恢复 Agent", "python -m root.left.app.left.src.cli control resume --port 8080"),
            ("停止 Agent", "python -m root.left.app.left.src.cli control stop --port 8080"),
            ("热重载配置", "python -m root.left.app.left.src.cli control reload --port 8080 --env dev"),
        ],
    },
    {
        "category": "故障排查",
        "items": [
            ("快速自诊断", "python -m root.left.app.left.src.cli doctor"),
            ("深度诊断（文本）", "python -m root.left.app.left.src.cli diagnose"),
            ("深度诊断（JSON）", "python -m root.left.app.left.src.cli diagnose --json"),
            ("查看故障排查文档", "python -m root.left.app.left.src.cli docs troubleshooting"),
            ("查看常见问题", "python -m root.left.app.left.src.cli docs faq"),
        ],
    },
]


# ---------------------------------------------------------------------------
# 输出函数
# ---------------------------------------------------------------------------

def render_welcome() -> str:
    """渲染欢迎信息。"""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  自驱永续进化 Agent - 欢迎使用")
    lines.append("=" * 60)
    lines.append("")
    lines.append("本系统是一个能够自主感知、决策、进化、验证的智能体，")
    lines.append("支持多阶段循环运行、健康监控、配置管理与自诊断。")
    lines.append("")
    lines.append("【核心能力】")
    lines.append("  - 自主循环运行（感知 -> 决策 -> 执行 -> 验证 -> 进化）")
    lines.append("  - 多环境配置管理（dev/test/prod）")
    lines.append("  - HTTP 健康检查与状态查询")
    lines.append("  - 深度自诊断（6 项检查）")
    lines.append("  - 用户友好错误提示与修复建议")
    lines.append("")
    lines.append("【快速上手】")
    lines.append("  1. 查看示例:    python -m root.left.app.left.src.cli examples")
    lines.append("  2. 自诊断:      python -m root.left.app.left.src.cli doctor")
    lines.append("  3. 启动试运行:  python -m root.left.app.left.src.cli run --dry-run --max-loops 3")
    lines.append("  4. 正式启动:    python -m root.left.app.left.src.cli run --env dev")
    lines.append("")
    lines.append("【获取帮助】")
    lines.append("  查看所有命令:   python -m root.left.app.left.src.cli --help")
    lines.append("  查看命令详情:   python -m root.left.app.left.src.cli help <命令>")
    lines.append("  查看使用示例:   python -m root.left.app.left.src.cli examples")
    lines.append("")
    lines.append("=" * 60)
    return "\n".join(lines)


def render_help_all() -> str:
    """渲染所有命令的概览帮助。"""
    lines: List[str] = []
    lines.append("自驱永续进化 Agent - 命令帮助")
    lines.append("")
    lines.append("可用命令:")
    for name, info in COMMAND_GUIDE.items():
        lines.append(f"  {name:<12} {info['summary']}")
    lines.append("")
    lines.append("提示: 使用 'help <命令>' 查看该命令的详细说明与示例。")
    lines.append("      使用 'examples' 查看按场景分类的常用用法。")
    return "\n".join(lines)


def render_help_command(command: str) -> str:
    """渲染单个命令的详细帮助。"""
    info = COMMAND_GUIDE.get(command)
    if info is None:
        return (
            f"未知命令: {command}\n"
            f"可用命令: {', '.join(COMMAND_GUIDE.keys())}"
        )
    lines: List[str] = []
    lines.append(f"命令: {command}")
    lines.append(f"说明: {info['summary']}")
    lines.append(f"详情: {info['description']}")
    lines.append("")
    lines.append("示例:")
    for desc, cmd in info["examples"]:
        lines.append(f"  # {desc}")
        lines.append(f"  {cmd}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_examples() -> str:
    """渲染按场景分类的示例。"""
    lines: List[str] = []
    lines.append("自驱永续进化 Agent - 常见使用场景")
    lines.append("")
    for scenario in SCENARIO_EXAMPLES:
        lines.append(f"【{scenario['category']}】")
        for desc, cmd in scenario["items"]:
            lines.append(f"  {desc}")
            lines.append(f"    {cmd}")
        lines.append("")
    return "\n".join(lines).rstrip()


# ---------------------------------------------------------------------------
# 交互式向导
# ---------------------------------------------------------------------------

# 向导步骤定义：每步包含 (提示, 解析函数, 默认值, 配置键路径)
WizardStep = Tuple[str, Callable[[str], Any], Any, Tuple[str, ...]]


def _parse_env(value: str) -> str:
    """解析环境名称。"""
    value = value.strip().lower()
    if value not in ("dev", "test", "prod"):
        raise ValueError("环境必须是 dev、test 或 prod")
    return value


def _parse_int_or_zero(value: str) -> Optional[int]:
    """解析整数，0 表示无限。"""
    value = value.strip()
    if not value:
        return None
    n = int(value)
    if n < 0:
        raise ValueError("循环次数不能为负数")
    return n


def _parse_float_positive(value: str) -> Optional[float]:
    """解析正浮点数。"""
    value = value.strip()
    if not value:
        return None
    f = float(value)
    if f < 0:
        raise ValueError("间隔不能为负数")
    return f


def _parse_port(value: str) -> Optional[int]:
    """解析端口号。"""
    value = value.strip()
    if not value:
        return None
    port = int(value)
    if not (1 <= port <= 65535):
        raise ValueError("端口范围 1-65535")
    return port


def _parse_bool(value: str) -> bool:
    """解析布尔值。"""
    value = value.strip().lower()
    if value in ("y", "yes", "true", "1", "是"):
        return True
    if value in ("n", "no", "false", "0", "否", ""):
        return False
    raise ValueError("请输入 y/n")


def build_wizard_steps() -> List[WizardStep]:
    """构建向导步骤列表。"""
    return [
        ("请选择环境 [dev/test/prod] (默认 dev): ", _parse_env, "dev", ("env",)),
        ("请输入最大循环次数 (0=无限, 默认 10): ", _parse_int_or_zero, 10, ("max_loops",)),
        ("请输入循环间隔秒数 (默认 1.0): ", _parse_float_positive, 1.0, ("loop_interval",)),
        ("请输入健康检查端口 (留空=不启用, 默认 8080): ", _parse_port, 8080, ("port",)),
        ("是否启用 dry-run 模式? [y/N]: ", _parse_bool, False, ("dry_run",)),
    ]


def run_wizard(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> Dict[str, Any]:
    """运行交互式向导，返回用户选择的配置。

    Args:
        input_fn: 输入函数（可注入用于测试）
        output_fn: 输出函数（可注入用于测试）

    Returns:
        包含 env, max_loops, loop_interval, port, dry_run 的字典
    """
    output_fn("=" * 50)
    output_fn("  Agent 启动向导")
    output_fn("=" * 50)
    output_fn("请根据提示输入配置，直接回车使用默认值。")
    output_fn("")

    result: Dict[str, Any] = {}
    steps = build_wizard_steps()

    for prompt, parser, default, _keys in steps:
        while True:
            try:
                raw = input_fn(prompt)
                if raw.strip() == "":
                    value = default
                else:
                    value = parser(raw)
                break
            except ValueError as e:
                output_fn(f"  输入无效: {e}，请重新输入。")

        # 将值存入结果
        if _keys == ("env",):
            result["env"] = value
        elif _keys == ("max_loops",):
            result["max_loops"] = value
        elif _keys == ("loop_interval",):
            result["loop_interval"] = value
        elif _keys == ("port",):
            result["port"] = value
        elif _keys == ("dry_run",):
            result["dry_run"] = value

    output_fn("")
    output_fn("配置确认:")
    output_fn(f"  环境:         {result['env']}")
    output_fn(f"  最大循环次数: {result['max_loops']}")
    output_fn(f"  循环间隔:     {result['loop_interval']}s")
    port_display = result["port"] if result["port"] else "不启用"
    output_fn(f"  健康检查端口: {port_display}")
    output_fn(f"  dry-run 模式: {'是' if result['dry_run'] else '否'}")
    output_fn("")
    return result


def build_run_args_from_wizard(wizard_result: Dict[str, Any]) -> List[str]:
    """将向导结果转换为 CLI 参数列表。"""
    args: List[str] = []
    args.extend(["--env", str(wizard_result["env"])])
    if wizard_result.get("max_loops") is not None:
        args.extend(["--max-loops", str(wizard_result["max_loops"])])
    if wizard_result.get("loop_interval") is not None:
        args.extend(["--loop-interval", str(wizard_result["loop_interval"])])
    if wizard_result.get("port"):
        args.extend(["--port", str(wizard_result["port"])])
    if wizard_result.get("dry_run"):
        args.append("--dry-run")
    return args


def is_interactive() -> bool:
    """判断当前是否为交互式终端（stdin 是否连接到 tty）。"""
    return sys.stdin.isatty() and sys.stdout.isatty()
