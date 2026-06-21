"""Shell 补全脚本生成

为 bash 和 zsh 生成命令补全脚本，让用户通过 Tab 键发现所有子命令与选项。

设计原则（第一性原理）：
1. 可发现性：用户无需记忆命令，Tab 即可发现
2. 自描述：补全脚本从 CLI 自身元数据生成，避免双重维护
3. 非侵入式：仅生成脚本，不自动修改用户 shell 配置
4. 可移植：支持 bash 与 zsh 两种主流 shell
"""
from __future__ import annotations

import argparse
import os
from typing import Dict, List, Optional

from root.left.app.left.src.utils_main.cli_guide import COMMAND_GUIDE


# ---------------------------------------------------------------------------
# 从 CLI 解析器提取子命令与选项信息
# ---------------------------------------------------------------------------

def extract_subcommand_info(parser: argparse.ArgumentParser) -> Dict[str, List[str]]:
    """从 argparse 解析器提取子命令及其选项。

    Args:
        parser: argparse.ArgumentParser 实例

    Returns:
        {子命令名: [选项列表]} 字典
    """
    info: Dict[str, List[str]] = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                options: List[str] = []
                for opt_action in subparser._actions:
                    if opt_action.option_strings:
                        options.extend(opt_action.option_strings)
                info[name] = options
    return info


# ---------------------------------------------------------------------------
# Shell 检测
# ---------------------------------------------------------------------------

def detect_shell() -> str:
    """检测当前用户的默认 shell。

    Returns:
        'bash' | 'zsh' | 'unknown'
    """
    shell_path = os.environ.get("SHELL", "")
    if "zsh" in shell_path:
        return "zsh"
    if "bash" in shell_path:
        return "bash"
    return "unknown"


# ---------------------------------------------------------------------------
# Bash 补全脚本生成
# ---------------------------------------------------------------------------

def generate_bash_completion(
    command_name: str = "agent",
    subcommand_info: Optional[Dict[str, List[str]]] = None,
) -> str:
    """生成 bash 补全脚本。

    Args:
        command_name: 命令名（如 agent）
        subcommand_info: 子命令及其选项信息，None 时从 COMMAND_GUIDE 推导

    Returns:
        bash 补全脚本字符串
    """
    if subcommand_info is None:
        subcommand_info = _build_default_subcommand_info()

    subcommands = " ".join(subcommand_info.keys())
    func_name = f"_{command_name}_completion"

    lines: List[str] = []
    lines.append(f"# {command_name} bash 补全脚本")
    lines.append(f"# 安装方法: source <({command_name} completion --shell bash)")
    lines.append("# 或追加到 ~/.bashrc 后重启终端")
    lines.append("")
    lines.append(f"{func_name}() {{")
    lines.append("    local cur prev words cword")
    lines.append("    _init_completion 2>/dev/null || {")
    lines.append("        cur=\"${COMP_WORDS[COMP_CWORD]}\"")
    lines.append("        prev=\"${COMP_WORDS[COMP_CWORD-1]}\"")
    lines.append("    }")
    lines.append("")
    lines.append(f"    local subcommands=\"{subcommands}\"")
    lines.append("")
    lines.append("    # 第一个参数：补全子命令")
    lines.append("    if [ $COMP_CWORD -eq 1 ]; then")
    lines.append("        COMPREPLY=($(compgen -W \"$subcommands\" -- \"$cur\"))")
    lines.append("        return 0")
    lines.append("    fi")
    lines.append("")
    lines.append("    local subcommand=${COMP_WORDS[1]}")
    lines.append("")
    lines.append("    # 后续参数：按子命令补全选项")
    lines.append("    case \"$subcommand\" in")
    for cmd, opts in subcommand_info.items():
        if not opts:
            continue
        opt_str = " ".join(opts)
        lines.append(f"        {cmd})")
        lines.append(f"            COMPREPLY=($(compgen -W \"{opt_str}\" -- \"$cur\"))")
        lines.append("            return 0")
        lines.append("            ;;")
    lines.append("        *)")
    lines.append("            return 0")
    lines.append("            ;;")
    lines.append("    esac")
    lines.append("}")
    lines.append("")
    lines.append(f"complete -F {func_name} {command_name}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Zsh 补全脚本生成
# ---------------------------------------------------------------------------

def generate_zsh_completion(
    command_name: str = "agent",
    subcommand_info: Optional[Dict[str, List[str]]] = None,
) -> str:
    """生成 zsh 补全脚本。

    Args:
        command_name: 命令名（如 agent）
        subcommand_info: 子命令及其选项信息，None 时从 COMMAND_GUIDE 推导

    Returns:
        zsh 补全脚本字符串
    """
    if subcommand_info is None:
        subcommand_info = _build_default_subcommand_info()

    func_name = f"_{command_name}"

    lines: List[str] = []
    lines.append(f"#compdef {command_name}")
    lines.append(f"# {command_name} zsh 补全脚本")
    lines.append(f"# 安装方法: eval \"$({command_name} completion --shell zsh)\"")
    lines.append("# 或追加到 ~/.zshrc 后重启终端")
    lines.append("")
    lines.append(f"{func_name}() {{")
    lines.append("    local -a subcommands")
    lines.append("    subcommands=(")
    for cmd in subcommand_info.keys():
        summary = COMMAND_GUIDE.get(cmd, {}).get("summary", "")
        # 转义单引号
        summary = summary.replace("'", "'\\''")
        lines.append(f"        '{cmd}:{summary}'")
    lines.append("    )")
    lines.append("")
    lines.append("    if (( CURRENT == 2 )); then")
    lines.append("        _describe 'command' subcommands")
    lines.append("        return 0")
    lines.append("    fi")
    lines.append("")
    lines.append("    local subcommand=$words[2]")
    lines.append("    case \"$subcommand\" in")
    for cmd, opts in subcommand_info.items():
        if not opts:
            continue
        lines.append(f"        {cmd})")
        opt_args = " ".join(f"'{o}'" for o in opts)
        lines.append(f"            _arguments {opt_args}")
        lines.append("            ;;")
    lines.append("        *)")
    lines.append("            ;;")
    lines.append("    esac")
    lines.append("}")
    lines.append("")
    lines.append(f"{func_name} \"$@\"")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 补全脚本获取与安装指引
# ---------------------------------------------------------------------------

def get_completion_script(
    shell: str,
    command_name: str = "agent",
    subcommand_info: Optional[Dict[str, List[str]]] = None,
) -> str:
    """获取指定 shell 的补全脚本。

    Args:
        shell: 'bash' 或 'zsh'
        command_name: 命令名
        subcommand_info: 子命令信息

    Returns:
        补全脚本字符串

    Raises:
        ValueError: 不支持的 shell
    """
    shell = shell.lower()
    if shell == "bash":
        return generate_bash_completion(command_name, subcommand_info)
    if shell == "zsh":
        return generate_zsh_completion(command_name, subcommand_info)
    raise ValueError(f"不支持的 shell: {shell}（仅支持 bash/zsh）")


def get_install_instructions(shell: str, command_name: str = "agent") -> str:
    """获取补全安装指引。

    Args:
        shell: 'bash' 或 'zsh'
        command_name: 命令名

    Returns:
        安装指引文本
    """
    shell = shell.lower()
    if shell == "bash":
        rc_file = os.path.expanduser("~/.bashrc")
        return (
            f"请将以下命令添加到 {rc_file}：\n"
            f'  eval "$({command_name} completion --shell bash)"\n'
            f"或直接追加补全脚本：\n"
            f"  {command_name} completion --shell bash >> {rc_file}\n"
            f"添加后执行 source {rc_file} 或重启终端生效。"
        )
    if shell == "zsh":
        rc_file = os.path.expanduser("~/.zshrc")
        return (
            f"请将以下命令添加到 {rc_file}：\n"
            f'  eval "$({command_name} completion --shell zsh)"\n'
            f"或直接追加补全脚本：\n"
            f"  {command_name} completion --shell zsh >> {rc_file}\n"
            f"添加后执行 source {rc_file} 或重启终端生效。"
        )
    return f"不支持的 shell: {shell}（仅支持 bash/zsh）"


# ---------------------------------------------------------------------------
# 默认子命令信息（从 COMMAND_GUIDE 推导）
# ---------------------------------------------------------------------------

def _build_default_subcommand_info() -> Dict[str, List[str]]:
    """从 COMMAND_GUIDE 构建默认子命令信息。

    当无法从解析器提取时使用此回退方案。
    选项列表基于已知 CLI 定义。
    """
    return {
        "run": ["--env", "--max-loops", "--loop-interval", "--port", "--dry-run", "--guide", "-h"],
        "status": ["--port", "-h"],
        "health": ["--port", "-h"],
        "validate": ["--env", "-h"],
        "config": ["--show-defaults", "--describe", "--env", "-h"],
        "doctor": ["-h"],
        "diagnose": ["--json", "-h"],
        "welcome": ["-h"],
        "help": ["-h"],
        "examples": ["-h"],
        "init": ["--list", "--show", "--template", "--env", "--force", "-h"],
        "control": ["--port", "--env", "-h"],
        "docs": ["-h"],
        "logs": ["--level", "--module", "--keyword", "--tail", "--stats", "--no-module", "-h"],
        "report": ["--env", "--loop-count", "--duration", "--health", "--json", "--output", "-h"],
        "completion": ["--shell", "--install", "--command-name", "-h"],
        "install": ["--command-name", "--install-dir", "--force", "-h"],
    }
