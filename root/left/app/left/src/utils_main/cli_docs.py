"""CLI 工具内文档系统

提供通过 CLI 访问的用户文档，包括快速入门、命令参考、配置指南、
故障排查与常见问题。文档在代码内维护，确保与代码同步。

设计原则（第一性原理）：
1. 工具内文档：用户无需离开 CLI 即可获取文档
2. 全面示例：覆盖所有常见用例，可直接复制使用
3. 可发现：文档从 help/welcome 链接进入
4. 可维护：文档从单一数据源生成
"""
from __future__ import annotations

from typing import Any, Dict, List

from root.left.app.left.src.utils_main.cli_guide import COMMAND_GUIDE


# ---------------------------------------------------------------------------
# 文档主题定义
# ---------------------------------------------------------------------------

DOC_TOPICS: Dict[str, str] = {
    "quickstart": "快速入门指南",
    "commands": "命令参考",
    "config": "配置指南",
    "troubleshooting": "故障排查",
    "faq": "常见问题",
}


# ---------------------------------------------------------------------------
# 快速入门
# ---------------------------------------------------------------------------

def render_quickstart() -> str:
    """渲染快速入门指南。"""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  快速入门指南")
    lines.append("=" * 60)
    lines.append("")
    lines.append("本指南帮助你在 5 分钟内启动并运行 Agent。")
    lines.append("")
    lines.append("【第 1 步：环境检查】")
    lines.append("  运行自诊断，确认环境就绪:")
    lines.append("  $ python -m root.left.app.left.src.cli doctor")
    lines.append("")
    lines.append("  所有检查项显示 ✓ 即表示环境正常。")
    lines.append("")
    lines.append("【第 2 步：校验配置】")
    lines.append("  校验默认 dev 环境配置:")
    lines.append("  $ python -m root.left.app.left.src.cli validate --env dev")
    lines.append("")
    lines.append("【第 3 步：试运行】")
    lines.append("  以 dry-run 模式试运行 3 个循环:")
    lines.append("  $ python -m root.left.app.left.src.cli run --dry-run --max-loops 3")
    lines.append("")
    lines.append("  dry-run 模式不会执行真实操作，适合验证流程。")
    lines.append("")
    lines.append("【第 4 步：正式启动】")
    lines.append("  启动 Agent（dev 环境，10 个循环）:")
    lines.append("  $ python -m root.left.app.left.src.cli run --env dev --max-loops 10")
    lines.append("")
    lines.append("  如需持续运行，使用 --max-loops 0（无限循环）。")
    lines.append("")
    lines.append("【第 5 步：监控运行】")
    lines.append("  启动时添加 --port 参数开启 HTTP 监控:")
    lines.append("  $ python -m root.left.app.left.src.cli run --port 8080")
    lines.append("")
    lines.append("  然后可以查询状态:")
    lines.append("  $ python -m root.left.app.left.src.cli status --port 8080")
    lines.append("  $ python -m root.left.app.left.src.cli health --port 8080")
    lines.append("")
    lines.append("【下一步】")
    lines.append("  - 查看命令帮助: python -m root.left.app.left.src.cli help")
    lines.append("  - 查看使用示例: python -m root.left.app.left.src.cli examples")
    lines.append("  - 从模板创建配置: python -m root.left.app.left.src.cli init --list")
    lines.append("  - 查看配置说明: python -m root.left.app.left.src.cli config --describe")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令参考（自动生成）
# ---------------------------------------------------------------------------

def render_command_reference() -> str:
    """渲染命令参考文档（从 COMMAND_GUIDE 自动生成）。"""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  命令参考")
    lines.append("=" * 60)
    lines.append("")
    lines.append("以下是所有可用命令的详细说明与示例。")
    lines.append("")

    for name, info in COMMAND_GUIDE.items():
        lines.append(f"■ {name}")
        lines.append(f"  说明: {info['summary']}")
        lines.append(f"  详情: {info['description']}")
        lines.append("  示例:")
        for desc, cmd in info["examples"]:
            lines.append(f"    # {desc}")
            lines.append(f"    {cmd}")
        lines.append("")

    lines.append("提示: 使用 'help <命令>' 可查看单命令的简明帮助。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 配置指南
# ---------------------------------------------------------------------------

def render_config_guide() -> str:
    """渲染配置指南。"""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  配置指南")
    lines.append("=" * 60)
    lines.append("")
    lines.append("Agent 使用 YAML 配置文件，支持多环境（dev/test/prod）。")
    lines.append("")
    lines.append("【配置文件位置】")
    lines.append("  配置文件位于: right/cfg/left/dev/<环境名>.yaml")
    lines.append("  例如: dev.yaml, test.yaml, prod.yaml")
    lines.append("")
    lines.append("【配置层级】")
    lines.append("  配置按以下优先级合并（后者覆盖前者）:")
    lines.append("  1. 内置默认配置 (DEFAULT_CONFIG)")
    lines.append("  2. 环境配置文件 (YAML)")
    lines.append("  3. 环境变量覆盖 (AGENT_* 前缀)")
    lines.append("")
    lines.append("【主要配置段】")
    lines.append("  - phase1: 感知与驱力层（采集器、驱力、预测）")
    lines.append("  - phase2: 决策与记忆层（任务池、决策、缓存）")
    lines.append("  - phase3: 进化层（快照、重构、回滚）")
    lines.append("  - loop_interval: 主循环间隔（秒）")
    lines.append("  - max_loops: 最大循环次数（0=无限）")
    lines.append("  - log_level: 日志级别 (DEBUG/INFO/WARNING/ERROR)")
    lines.append("  - health_check: HTTP 健康检查端点配置")
    lines.append("  - action_executor: 动作执行器配置（dry_run 等）")
    lines.append("")
    lines.append("【环境变量覆盖】")
    lines.append("  使用 AGENT_ 前缀的环境变量可覆盖任意配置项，")
    lines.append("  用 __ 分隔层级。例如:")
    lines.append("  $ export AGENT_LOOP_INTERVAL=0.5")
    lines.append("  $ export AGENT_PHASE2__MEMORY__STORE__DB_PATH=/tmp/agent.db")
    lines.append("  $ export AGENT_LOG_LEVEL=DEBUG")
    lines.append("")
    lines.append("【从模板创建配置】")
    lines.append("  无需手写 YAML，使用模板快速创建:")
    lines.append("  $ python -m root.left.app.left.src.cli init --list")
    lines.append("  $ python -m root.left.app.left.src.cli init --template standard --env dev")
    lines.append("")
    lines.append("【查看配置】")
    lines.append("  查看默认配置: cli config --show-defaults")
    lines.append("  查看配置说明: cli config --describe")
    lines.append("  查看当前配置: cli config --env dev")
    lines.append("  校验配置:     cli validate --env dev")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 故障排查
# ---------------------------------------------------------------------------

def render_troubleshooting() -> str:
    """渲染故障排查指南。"""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  故障排查")
    lines.append("=" * 60)
    lines.append("")
    lines.append("常见问题与解决方案。")
    lines.append("")

    problems: List[Dict[str, Any]] = [
        {
            "problem": "Agent 启动失败：配置错误",
            "cause": "配置文件不存在或格式错误",
            "solution": (
                "1. 运行 'cli validate --env <环境>' 查看具体错误\n"
                "2. 运行 'cli config --show-defaults' 查看默认配置\n"
                "3. 运行 'cli init --template standard --env <环境>' 从模板创建配置"
            ),
        },
        {
            "problem": "无法连接到 Agent",
            "cause": "Agent 未启动或端口不正确",
            "solution": (
                "1. 确认 Agent 已启动: 检查进程是否存在\n"
                "2. 确认端口正确: 'cli status --port <端口>'\n"
                "3. 确认健康检查已启用: 启动时添加 --port 参数"
            ),
        },
        {
            "problem": "Agent 运行但不健康",
            "cause": "模块异常或资源不足",
            "solution": (
                "1. 运行 'cli diagnose' 进行深度诊断\n"
                "2. 检查日志中的 ERROR 级别消息\n"
                "3. 运行 'cli doctor' 检查环境"
            ),
        },
        {
            "problem": "缺少依赖包",
            "cause": "未安装所需 Python 依赖",
            "solution": (
                "1. 运行 'cli doctor' 查看缺少哪些依赖\n"
                "2. 安装依赖: pip install -r requirements.txt\n"
                "3. 核心依赖: yaml (PyYAML), psutil"
            ),
        },
        {
            "problem": "Python 版本不兼容",
            "cause": "Python 版本低于 3.10",
            "solution": (
                "1. 检查 Python 版本: python --version\n"
                "2. 升级到 Python 3.10 或更高版本\n"
                "3. 建议使用 pyenv 管理多版本 Python"
            ),
        },
        {
            "problem": "配置热重载失败",
            "cause": "新配置文件格式错误或缺少必要段",
            "solution": (
                "1. 先用 'cli validate --env <环境>' 校验新配置\n"
                "2. 确认配置包含 phase1/phase2/phase3 段\n"
                "3. 修正后重新执行 'cli control reload --port <端口>'"
            ),
        },
    ]

    for i, p in enumerate(problems, 1):
        lines.append(f"【问题 {i}: {p['problem']}】")
        lines.append(f"  原因: {p['cause']}")
        lines.append("  解决:")
        for line in p["solution"].split("\n"):
            lines.append(f"    {line}")
        lines.append("")

    lines.append("【获取更多帮助】")
    lines.append("  运行 'cli doctor' 进行全面自诊断")
    lines.append("  运行 'cli diagnose' 进行深度模块诊断")
    lines.append("  运行 'cli help <命令>' 查看命令详细帮助")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 常见问题
# ---------------------------------------------------------------------------

def render_faq() -> str:
    """渲染常见问题。"""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  常见问题 (FAQ)")
    lines.append("=" * 60)
    lines.append("")

    faqs: List[Dict[str, str]] = [
        {
            "q": "Q: dry-run 模式是什么？",
            "a": (
                "A: dry-run 模式下，Agent 会执行完整的感知-决策-进化流程，\n"
                "   但不会执行真实的动作（如文件操作、API 调用等）。\n"
                "   适合测试和验证流程，不会对系统产生影响。"
            ),
        },
        {
            "q": "Q: 如何让 Agent 持续运行？",
            "a": (
                "A: 使用 --max-loops 0 参数启动:\n"
                "   cli run --max-loops 0\n"
                "   Agent 将无限循环运行，直到收到停止信号（Ctrl+C 或 control stop）。"
            ),
        },
        {
            "q": "Q: 如何在运行时修改配置？",
            "a": (
                "A: 1. 修改配置文件\n"
                "   2. 通过 CLI 发送热重载命令:\n"
                "      cli control reload --port <端口> --env <环境>\n"
                "   注意: 热重载会重新初始化所有模块，建议先暂停 Agent。"
            ),
        },
        {
            "q": "Q: 如何暂停和恢复 Agent？",
            "a": (
                "A: 暂停: cli control pause --port <端口>\n"
                "   恢复: cli control resume --port <端口>\n"
                "   暂停后 Agent 停止执行循环但保持运行状态，可随时恢复。"
            ),
        },
        {
            "q": "Q: dev/test/prod 环境有什么区别？",
            "a": (
                "A: 这只是配置文件的名称区分，你可以为每个环境创建不同的配置文件。\n"
                "   通常 dev 用于开发（dry-run、短间隔），\n"
                "   prod 用于生产（真实执行、长间隔、启用健康检查）。"
            ),
        },
        {
            "q": "Q: 如何查看 Agent 的运行状态？",
            "a": (
                "A: 1. 查看控制状态: cli control status --port <端口>\n"
                "   2. 查看详细状态: cli status --port <端口>\n"
                "   3. 查看健康: cli health --port <端口>\n"
                "   4. 查看摘要: 访问 http://localhost:<端口>/summary"
            ),
        },
        {
            "q": "Q: 配置模板有哪些？",
            "a": (
                "A: 运行 'cli init --list' 查看所有模板:\n"
                "   - minimal: 最小化配置，快速验证\n"
                "   - standard: 标准配置，日常开发\n"
                "   - production: 生产配置，启用健康检查\n"
                "   - high-frequency: 高频监控配置"
            ),
        },
        {
            "q": "Q: 如何查看所有可用命令？",
            "a": (
                "A: 1. 查看命令概览: cli help\n"
                "   2. 查看单命令详情: cli help <命令>\n"
                "   3. 查看使用示例: cli examples\n"
                "   4. 查看欢迎信息: cli welcome"
            ),
        },
    ]

    for faq in faqs:
        lines.append(faq["q"])
        for line in faq["a"].split("\n"):
            lines.append(line)
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 文档索引
# ---------------------------------------------------------------------------

def render_docs_index() -> str:
    """渲染文档索引（目录）。"""
    lines: List[str] = []
    lines.append("=" * 60)
    lines.append("  用户文档")
    lines.append("=" * 60)
    lines.append("")
    lines.append("可用文档主题:")
    lines.append("")
    for key, title in DOC_TOPICS.items():
        lines.append(f"  {key:<20} {title}")
    lines.append("")
    lines.append("使用方法: cli docs <主题>")
    lines.append("例如: cli docs quickstart")
    lines.append("")
    lines.append("或查看其他帮助命令:")
    lines.append("  cli welcome    - 查看欢迎信息")
    lines.append("  cli help       - 查看命令帮助")
    lines.append("  cli examples   - 查看使用示例")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 文档渲染分发
# ---------------------------------------------------------------------------

def render_doc(topic: str) -> str:
    """根据主题渲染对应文档。

    Args:
        topic: 文档主题名称

    Returns:
        文档文本，主题不存在时返回索引
    """
    renderers = {
        "quickstart": render_quickstart,
        "commands": render_command_reference,
        "config": render_config_guide,
        "troubleshooting": render_troubleshooting,
        "faq": render_faq,
    }
    renderer = renderers.get(topic)
    if renderer is None:
        return render_docs_index()
    return renderer()
