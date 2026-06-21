"""智能命令建议与拼写纠正

当用户输入未知命令或选项时，基于相似度算法提供最可能的正确建议。

设计原则（第一性原理）：
1. 可发现性：用户输错时主动建议，减少挫败感
2. 可理解性：建议附带相似度与理由
3. 非侵入式：仅在命令未识别时触发
4. 可学习：基于编辑距离与子串匹配综合排序
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from root.left.app.left.src.utils_main.cli_guide import COMMAND_GUIDE


# ---------------------------------------------------------------------------
# 相似度算法
# ---------------------------------------------------------------------------

def levenshtein_distance(s1: str, s2: str) -> int:
    """计算两个字符串的编辑距离（Levenshtein 距离）。

    Args:
        s1: 第一个字符串
        s2: 第二个字符串

    Returns:
        编辑距离（插入/删除/替换的最小操作数）
    """
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def similarity_score(s1: str, s2: str) -> float:
    """计算两个字符串的相似度分数（0.0 ~ 1.0）。

    综合考虑编辑距离与子串匹配。

    Args:
        s1: 第一个字符串
        s2: 第二个字符串

    Returns:
        相似度分数，1.0 表示完全相同
    """
    s1_lower = s1.lower()
    s2_lower = s2.lower()

    if s1_lower == s2_lower:
        return 1.0

    max_len = max(len(s1_lower), len(s2_lower))
    if max_len == 0:
        return 1.0

    # 编辑距离归一化
    distance = levenshtein_distance(s1_lower, s2_lower)
    distance_score = 1.0 - (distance / max_len)

    # 子串匹配加分
    substring_bonus = 0.0
    if s1_lower in s2_lower or s2_lower in s1_lower:
        substring_bonus = 0.2
    elif _common_prefix(s1_lower, s2_lower) >= 2:
        substring_bonus = 0.1

    return min(1.0, distance_score + substring_bonus)


def _common_prefix(s1: str, s2: str) -> int:
    """计算两个字符串的公共前缀长度。"""
    i = 0
    while i < len(s1) and i < len(s2) and s1[i] == s2[i]:
        i += 1
    return i


# ---------------------------------------------------------------------------
# 命令建议
# ---------------------------------------------------------------------------

def suggest_commands(
    user_input: str,
    candidates: Optional[List[str]] = None,
    threshold: float = 0.4,
    max_suggestions: int = 3,
) -> List[Tuple[str, float]]:
    """为用户输入的命令提供建议。

    Args:
        user_input: 用户输入的（错误）命令
        candidates: 候选命令列表，None 时使用 COMMAND_GUIDE 的键
        threshold: 最小相似度阈值
        max_suggestions: 最大建议数

    Returns:
        (命令名, 相似度分数) 列表，按相似度降序
    """
    if candidates is None:
        candidates = list(COMMAND_GUIDE.keys())

    scored: List[Tuple[str, float]] = []
    for cmd in candidates:
        score = similarity_score(user_input, cmd)
        if score >= threshold:
            scored.append((cmd, score))

    # 按相似度降序排序
    scored.sort(key=lambda x: -x[1])
    return scored[:max_suggestions]


def suggest_options(
    user_input: str,
    candidates: List[str],
    threshold: float = 0.4,
    max_suggestions: int = 3,
) -> List[Tuple[str, float]]:
    """为用户输入的选项提供建议。

    Args:
        user_input: 用户输入的（错误）选项
        candidates: 候选选项列表
        threshold: 最小相似度阈值
        max_suggestions: 最大建议数

    Returns:
        (选项名, 相似度分数) 列表，按相似度降序
    """
    return suggest_commands(
        user_input,
        candidates=candidates,
        threshold=threshold,
        max_suggestions=max_suggestions,
    )


# ---------------------------------------------------------------------------
# 建议渲染
# ---------------------------------------------------------------------------

def render_suggestions(
    user_input: str,
    suggestions: List[Tuple[str, float]],
    is_option: bool = False,
) -> str:
    """渲染建议为可读文本。

    Args:
        user_input: 用户输入的（错误）命令/选项
        suggestions: 建议列表
        is_option: 是否为选项建议（影响措辞）

    Returns:
        可读文本
    """
    from root.left.app.left.src.utils_main.cli_formatter import Color, colorize

    if not suggestions:
        kind = "选项" if is_option else "命令"
        return f"未知{kind}: {user_input}"

    kind = "选项" if is_option else "命令"
    lines: List[str] = []
    lines.append(colorize(f"未知{kind}: {user_input}", Color.YELLOW))
    lines.append("")
    lines.append("您是不是想输入:")

    for cmd, score in suggestions:
        # 获取命令说明
        summary = COMMAND_GUIDE.get(cmd, {}).get("summary", "")
        score_pct = int(score * 100)
        summary_display = f" - {summary}" if summary else ""
        lines.append(f"  {colorize(cmd, Color.GREEN)} (相似度 {score_pct}%){summary_display}")

    return "\n".join(lines)


def format_did_you_mean(
    user_input: str,
    candidates: Optional[List[str]] = None,
    is_option: bool = False,
    threshold: float = 0.4,
) -> str:
    """格式化 "您是不是想输入" 提示。

    Args:
        user_input: 用户输入
        candidates: 候选列表
        is_option: 是否为选项
        threshold: 相似度阈值

    Returns:
        格式化的提示文本，无建议时返回空字符串
    """
    suggestions = suggest_commands(
        user_input,
        candidates=candidates,
        threshold=threshold,
    )
    if not suggestions:
        return ""
    return render_suggestions(user_input, suggestions, is_option=is_option)


# ---------------------------------------------------------------------------
# 命令频率统计（用于排序优化）
# ---------------------------------------------------------------------------

class CommandFrequency:
    """命令使用频率统计。

    基于历史使用频率对建议排序，常用命令优先。
    """

    def __init__(self) -> None:
        self._counts: Dict[str, int] = {}

    def record(self, command: str) -> None:
        """记录命令使用。"""
        command = command.strip().lower()
        if command:
            self._counts[command] = self._counts.get(command, 0) + 1

    def get_count(self, command: str) -> int:
        """获取命令使用次数。"""
        return self._counts.get(command.strip().lower(), 0)

    def suggest_with_frequency(
        self,
        user_input: str,
        candidates: Optional[List[str]] = None,
        threshold: float = 0.4,
        max_suggestions: int = 3,
    ) -> List[Tuple[str, float]]:
        """结合频率的建议。

        相似度为主，频率为辅（频率高的在相似度相同时优先）。
        """
        if candidates is None:
            candidates = list(COMMAND_GUIDE.keys())

        scored: List[Tuple[str, float, int]] = []
        for cmd in candidates:
            score = similarity_score(user_input, cmd)
            if score >= threshold:
                freq = self.get_count(cmd)
                scored.append((cmd, score, freq))

        # 按相似度降序，频率降序
        scored.sort(key=lambda x: (-x[1], -x[2]))
        return [(cmd, score) for cmd, score, _ in scored[:max_suggestions]]

    def clear(self) -> None:
        """清空频率统计。"""
        self._counts.clear()

    def to_dict(self) -> Dict[str, int]:
        """导出频率统计。"""
        return dict(self._counts)
