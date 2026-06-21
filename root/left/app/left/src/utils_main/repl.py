"""交互式 REPL 与命令历史

提供交互式命令行界面，支持命令历史、自动补全与会话管理。

设计原则（第一性原理）：
1. 可交互：用户在单一会话中连续执行命令，无需重复输入前缀
2. 可回溯：命令历史持久化，跨会话可用
3. 可发现：REPL 内提供帮助与命令列表
4. 非侵入式：REPL 是可选入口，不影响正常 CLI 使用
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, List, Optional

from root.left.app.left.src.utils_main.cli_formatter import (
    Color,
    colorize,
    render_divider,
    render_section,
)
from root.left.app.left.src.utils_main.cli_guide import COMMAND_GUIDE


# ---------------------------------------------------------------------------
# 命令历史
# ---------------------------------------------------------------------------

class CommandHistory:
    """命令历史管理。

    负责在内存中维护命令历史，并可选持久化到文件。
    """

    DEFAULT_MAX_SIZE = 1000

    def __init__(
        self,
        history_file: Optional[str] = None,
        max_size: int = DEFAULT_MAX_SIZE,
    ):
        """初始化命令历史。

        Args:
            history_file: 历史文件路径，None 表示不持久化
            max_size: 最大历史条数
        """
        self.history_file = history_file
        self.max_size = max_size
        self._entries: List[str] = []

    def load(self) -> None:
        """从文件加载历史。"""
        if not self.history_file or not os.path.exists(self.history_file):
            return
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                self._entries = [
                    line.rstrip("\n") for line in f
                    if line.strip()
                ]
        except OSError:
            pass

    def save(self) -> None:
        """保存历史到文件。"""
        if not self.history_file:
            return
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.history_file)), exist_ok=True)
            with open(self.history_file, "w", encoding="utf-8") as f:
                for entry in self._entries:
                    f.write(entry + "\n")
        except OSError:
            pass

    def add(self, command: str) -> None:
        """添加命令到历史。"""
        command = command.strip()
        if not command:
            return
        # 避免连续重复
        if self._entries and self._entries[-1] == command:
            return
        self._entries.append(command)
        # 超出容量时丢弃最旧的
        if len(self._entries) > self.max_size:
            self._entries = self._entries[-self.max_size:]

    def get_entries(self) -> List[str]:
        """获取所有历史条目。"""
        return list(self._entries)

    def clear(self) -> None:
        """清空历史。"""
        self._entries.clear()

    def search(self, keyword: str) -> List[str]:
        """按关键字搜索历史。"""
        keyword_lower = keyword.lower()
        return [e for e in self._entries if keyword_lower in e.lower()]

    def __len__(self) -> int:
        return len(self._entries)


# ---------------------------------------------------------------------------
# REPL 会话
# ---------------------------------------------------------------------------

@dataclass
class REPLResult:
    """REPL 命令执行结果。"""

    command: str
    exit_code: int
    output: str = ""
    should_exit: bool = False


class REPLSession:
    """交互式 REPL 会话。"""

    PROMPT = "agent> "
    EXIT_COMMANDS = {"exit", "quit", "q", ":q"}
    HELP_COMMANDS = {"help", "?", "h"}

    def __init__(
        self,
        executor: Callable[[List[str]], int],
        history: Optional[CommandHistory] = None,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
    ):
        """初始化 REPL 会话。

        Args:
            executor: 命令执行函数，接收参数列表，返回退出码
            history: 命令历史管理器
            input_fn: 输入函数（可注入用于测试）
            output_fn: 输出函数（可注入用于测试）
        """
        self.executor = executor
        self.history = history or CommandHistory()
        self.input_fn = input_fn
        self.output_fn = output_fn
        self._running = False

    def run(self) -> int:
        """运行 REPL 主循环。

        Returns:
            最终退出码
        """
        self._running = True
        self._setup_readline()
        self._print_welcome()

        last_exit_code = 0
        while self._running:
            try:
                line = self.input_fn(self.PROMPT)
            except EOFError:
                self.output_fn("")
                break
            except KeyboardInterrupt:
                self.output_fn("")
                continue

            result = self.execute(line)
            last_exit_code = result.exit_code
            if result.should_exit:
                break

        self._print_farewell()
        self.history.save()
        return last_exit_code

    def execute(self, line: str) -> REPLResult:
        """执行单行命令。

        Args:
            line: 用户输入行

        Returns:
            REPLResult
        """
        line = line.strip()
        if not line:
            return REPLResult(command="", exit_code=0)

        # 记录历史
        self.history.add(line)

        # 检查退出命令
        if line.lower() in self.EXIT_COMMANDS:
            self._running = False
            return REPLResult(command=line, exit_code=0, should_exit=True)

        # 检查特殊命令
        if line.startswith("!"):
            return self._handle_special(line)

        # 检查帮助命令
        if line.lower() in self.HELP_COMMANDS:
            self._print_help()
            return REPLResult(command=line, exit_code=0)

        # 普通命令：委托给执行器
        args = line.split()
        try:
            exit_code = self.executor(args)
            return REPLResult(command=line, exit_code=exit_code)
        except SystemExit as e:
            # argparse 在错误时调用 sys.exit，捕获它
            return REPLResult(command=line, exit_code=e.code or 2)
        except Exception as e:
            self.output_fn(colorize(f"错误: {e}", Color.RED))
            return REPLResult(command=line, exit_code=1)

    def _handle_special(self, line: str) -> REPLResult:
        """处理 ! 开头的特殊命令。"""
        parts = line[1:].split(None, 1)
        special = parts[0].lower() if parts else ""

        if special == "history":
            entries = self.history.get_entries()
            if not entries:
                self.output_fn("(无历史记录)")
            else:
                for i, entry in enumerate(entries, 1):
                    self.output_fn(f"  {i:>4}  {entry}")
            return REPLResult(command=line, exit_code=0)

        if special == "clear":
            self.history.clear()
            self.output_fn(colorize("历史已清空", Color.GREEN))
            return REPLResult(command=line, exit_code=0)

        if special == "search":
            keyword = parts[1] if len(parts) > 1 else ""
            if not keyword:
                self.output_fn("用法: !search <关键字>")
                return REPLResult(command=line, exit_code=2)
            results = self.history.search(keyword)
            if not results:
                self.output_fn(f"(未找到匹配 '{keyword}' 的历史)")
            else:
                for entry in results:
                    self.output_fn(f"  {entry}")
            return REPLResult(command=line, exit_code=0)

        if special == "help":
            self._print_special_help()
            return REPLResult(command=line, exit_code=0)

        self.output_fn(colorize(f"未知特殊命令: !{special}", Color.RED))
        self.output_fn("输入 !help 查看可用特殊命令")
        return REPLResult(command=line, exit_code=2)

    def _setup_readline(self) -> None:
        """配置 readline 以支持历史导航。"""
        try:
            import readline
            # 设置历史文件
            if self.history.history_file:
                readline.set_history_length(self.history.max_size)
                try:
                    readline.read_history_file(self.history.history_file)
                except OSError:
                    pass
            # 添加补全
            readline.set_completer(self._completer)
            readline.parse_and_bind("tab: complete")
        except ImportError:
            pass

    def _completer(self, text: str, state: int) -> Optional[str]:
        """Tab 补全函数。"""
        commands = list(COMMAND_GUIDE.keys()) + list(self.EXIT_COMMANDS) + ["!history", "!clear", "!search", "!help"]
        matches = [cmd for cmd in commands if cmd.startswith(text)]
        if state < len(matches):
            return matches[state]
        return None

    def _print_welcome(self) -> None:
        """打印欢迎信息。"""
        self.output_fn(render_divider())
        self.output_fn(render_section("Agent 交互式 REPL"))
        self.output_fn(render_divider())
        self.output_fn("")
        self.output_fn("输入命令执行，输入 help 查看帮助，输入 exit 退出。")
        self.output_fn("特殊命令以 ! 开头（!help 查看详情）。")
        self.output_fn("")

    def _print_farewell(self) -> None:
        """打印告别信息。"""
        self.output_fn("")
        self.output_fn(colorize("再见！", Color.CYAN))

    def _print_help(self) -> None:
        """打印帮助信息。"""
        self.output_fn("")
        self.output_fn(render_section("可用命令"))
        for name, info in COMMAND_GUIDE.items():
            self.output_fn(f"  {name:<12} {info['summary']}")
        self.output_fn("")
        self.output_fn(render_section("特殊命令"))
        self.output_fn("  !history       查看命令历史")
        self.output_fn("  !search <关键字>  搜索历史")
        self.output_fn("  !clear         清空历史")
        self.output_fn("  !help          查看特殊命令帮助")
        self.output_fn("")
        self.output_fn(render_section("退出"))
        self.output_fn("  exit / quit / q  退出 REPL")
        self.output_fn("")

    def _print_special_help(self) -> None:
        """打印特殊命令帮助。"""
        self.output_fn("")
        self.output_fn(render_section("特殊命令"))
        self.output_fn("  !history         查看所有命令历史")
        self.output_fn("  !search <关键字>   按关键字搜索历史")
        self.output_fn("  !clear           清空命令历史")
        self.output_fn("  !help            显示此帮助")
        self.output_fn("")


# ---------------------------------------------------------------------------
# 便捷函数
# ---------------------------------------------------------------------------

def get_default_history_file() -> str:
    """获取默认历史文件路径。"""
    home = os.path.expanduser("~")
    return os.path.join(home, ".agent_history")


def run_repl(
    history_file: Optional[str] = None,
    executor: Optional[Callable[[List[str]], int]] = None,
) -> int:
    """启动交互式 REPL。

    Args:
        history_file: 历史文件路径，None 使用默认
        executor: 命令执行函数，None 使用默认 CLI

    Returns:
        退出码
    """
    if history_file is None:
        history_file = get_default_history_file()

    if executor is None:
        executor = _default_executor

    history = CommandHistory(history_file=history_file)
    history.load()

    session = REPLSession(executor=executor, history=history)
    return session.run()


def _default_executor(args: List[str]) -> int:
    """默认命令执行器：委托给 CLI main。"""
    from root.left.app.left.src.cli import main as cli_main
    return cli_main(args)
