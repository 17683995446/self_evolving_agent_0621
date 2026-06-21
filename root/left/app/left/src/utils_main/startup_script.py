"""一键启动脚本生成

生成 shell 包装脚本，让用户用短命令（如 `agent`）替代长 python 命令。

设计原则（第一性原理）：
1. 零摩擦：一条短命令即可启动，无需记忆长模块路径
2. 自包含：脚本自动定位项目根目录与 Python 解释器
3. 非侵入式：不自动写入系统目录，需用户显式安装
4. 可移植：支持 bash/zsh 通用语法
"""
from __future__ import annotations

import os
from typing import Optional

from root.left.app.left.src.utils_main.cli_guide import COMMAND_GUIDE


# CLI 模块路径
CLI_MODULE = "root.left.app.left.src.cli"


def generate_startup_script(
    command_name: str = "agent",
    project_root_var: str = "AGENT_PROJECT_ROOT",
) -> str:
    """生成 shell 启动包装脚本。

    生成的脚本会：
    1. 自动定位项目根目录（通过环境变量或脚本位置推断）
    2. 设置 PYTHONPATH
    3. 调用 Python CLI 模块

    Args:
        command_name: 命令名（如 agent）
        project_root_var: 项目根目录环境变量名

    Returns:
        shell 脚本字符串
    """
    lines: list[str] = []
    lines.append("#!/usr/bin/env bash")
    lines.append(f"# {command_name} - 自驱永续进化 Agent 一键启动脚本")
    lines.append(f"# 自动生成的包装脚本，调用 {CLI_MODULE}")
    lines.append("")
    lines.append("# 自动定位项目根目录")
    lines.append(f'if [ -n "${project_root_var}" ]; then')
    lines.append(f'    PROJECT_ROOT="${project_root_var}"')
    lines.append("else")
    lines.append("    # 通过脚本位置推断项目根目录")
    lines.append('    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"')
    lines.append('    PROJECT_ROOT="$SCRIPT_DIR"')
    lines.append("fi")
    lines.append("")
    lines.append("# 设置 PYTHONPATH")
    lines.append('export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"')
    lines.append("")
    lines.append("# 调用 Python CLI")
    lines.append(f'exec python -m {CLI_MODULE} "$@"')
    return "\n".join(lines)


def get_install_instructions(
    command_name: str = "agent",
    install_dir: Optional[str] = None,
) -> str:
    """获取启动脚本安装指引。

    Args:
        command_name: 命令名
        install_dir: 安装目录，默认 ~/.local/bin

    Returns:
        安装指引文本
    """
    if install_dir is None:
        install_dir = os.path.expanduser("~/.local/bin")

    return (
        f"请执行以下步骤安装 {command_name} 命令：\n"
        f"\n"
        f"1. 创建安装目录（如不存在）：\n"
        f"   mkdir -p {install_dir}\n"
        f"\n"
        f"2. 生成启动脚本：\n"
        f"   {command_name} install --command-name {command_name} --install-dir {install_dir}\n"
        f"\n"
        f"3. 确保 {install_dir} 在 PATH 中（添加到 ~/.bashrc 或 ~/.zshrc）：\n"
        f"   export PATH=\"{install_dir}:$PATH\"\n"
        f"\n"
        f"4. 重启终端或 source 配置后即可使用：\n"
        f"   {command_name} run --env dev\n"
        f"   {command_name} doctor\n"
        f"   {command_name} --help"
    )


def install_startup_script(
    command_name: str = "agent",
    install_dir: Optional[str] = None,
    force: bool = False,
) -> str:
    """安装启动脚本到指定目录。

    Args:
        command_name: 命令名
        install_dir: 安装目录，默认 ~/.local/bin
        force: 是否覆盖已有文件

    Returns:
        安装的脚本路径

    Raises:
        FileExistsError: 文件已存在且 force=False
    """
    if install_dir is None:
        install_dir = os.path.expanduser("~/.local/bin")

    os.makedirs(install_dir, exist_ok=True)
    script_path = os.path.join(install_dir, command_name)

    if os.path.exists(script_path) and not force:
        raise FileExistsError(
            f"文件已存在: {script_path}（使用 --force 覆盖）"
        )

    content = generate_startup_script(command_name)
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(content)

    # 设置可执行权限
    os.chmod(script_path, 0o755)
    return script_path


def render_startup_help() -> str:
    """渲染启动脚本帮助信息。"""
    lines: list[str] = []
    lines.append("一键启动脚本使用说明")
    lines.append("")
    lines.append("安装后可用短命令替代长 python 命令：")
    lines.append("")
    lines.append("  替代前: python -m root.left.app.left.src.cli run --env dev")
    lines.append("  替代后: agent run --env dev")
    lines.append("")
    lines.append("可用子命令:")
    for name, info in COMMAND_GUIDE.items():
        lines.append(f"  {name:<12} {info['summary']}")
    lines.append("")
    lines.append("安装方法: agent install --command-name agent")
    return "\n".join(lines)
