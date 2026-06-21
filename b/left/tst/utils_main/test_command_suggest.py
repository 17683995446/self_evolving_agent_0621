"""智能命令建议与拼写纠正测试"""
from __future__ import annotations

from root.left.app.left.src.cli import main
from root.left.app.left.src.utils_main.command_suggest import (
    CommandFrequency,
    format_did_you_mean,
    levenshtein_distance,
    render_suggestions,
    similarity_score,
    suggest_commands,
    suggest_options,
)


# ---------------------------------------------------------------------------
# 编辑距离测试
# ---------------------------------------------------------------------------

class TestLevenshteinDistance:
    """测试编辑距离计算"""

    def test_identical_strings(self):
        assert levenshtein_distance("hello", "hello") == 0

    def test_empty_string(self):
        assert levenshtein_distance("", "abc") == 3
        assert levenshtein_distance("abc", "") == 3

    def test_single_substitution(self):
        assert levenshtein_distance("cat", "bat") == 1

    def test_single_insertion(self):
        assert levenshtein_distance("cat", "cats") == 1

    def test_single_deletion(self):
        assert levenshtein_distance("cats", "cat") == 1

    def test_completely_different(self):
        assert levenshtein_distance("abc", "xyz") == 3

    def test_case_sensitive(self):
        assert levenshtein_distance("ABC", "abc") == 3

    def test_both_empty(self):
        assert levenshtein_distance("", "") == 0


# ---------------------------------------------------------------------------
# 相似度分数测试
# ---------------------------------------------------------------------------

class TestSimilarityScore:
    """测试相似度分数计算"""

    def test_identical(self):
        assert similarity_score("run", "run") == 1.0

    def test_case_insensitive(self):
        assert similarity_score("RUN", "run") == 1.0

    def test_completely_different(self):
        score = similarity_score("abc", "xyz")
        assert 0.0 <= score < 0.5

    def test_similar(self):
        score = similarity_score("runn", "run")
        assert score > 0.7

    def test_substring_bonus(self):
        # "run" 是 "running" 的子串
        score = similarity_score("run", "running")
        assert score > 0.5

    def test_common_prefix_bonus(self):
        score = similarity_score("st", "status")
        assert score > 0.4

    def test_empty_strings(self):
        assert similarity_score("", "") == 1.0

    def test_one_empty(self):
        score = similarity_score("abc", "")
        assert score < 0.5

    def test_score_range(self):
        """相似度分数应在 [0, 1] 范围内"""
        test_pairs = [
            ("hello", "world"),
            ("run", "run"),
            ("status", "stat"),
            ("help", "halp"),
        ]
        for s1, s2 in test_pairs:
            score = similarity_score(s1, s2)
            assert 0.0 <= score <= 1.0


# ---------------------------------------------------------------------------
# 命令建议测试
# ---------------------------------------------------------------------------

class TestSuggestCommands:
    """测试命令建议"""

    def test_exact_match(self):
        suggestions = suggest_commands("run")
        assert len(suggestions) > 0
        assert suggestions[0][0] == "run"
        assert suggestions[0][1] == 1.0

    def test_typo_suggestion(self):
        # "stat" 应该建议 "status"
        suggestions = suggest_commands("stat")
        assert any(cmd == "status" for cmd, _ in suggestions)

    def test_close_typo(self):
        # "halp" 应该建议 "help"
        suggestions = suggest_commands("halp")
        assert any(cmd == "help" for cmd, _ in suggestions)

    def test_no_match(self):
        # 完全不相关的输入
        suggestions = suggest_commands("xyzabc123", threshold=0.9)
        assert len(suggestions) == 0

    def test_threshold_filtering(self):
        # 高阈值应过滤掉低相似度建议
        low_threshold = suggest_commands("st", threshold=0.1)
        high_threshold = suggest_commands("st", threshold=0.9)
        assert len(low_threshold) >= len(high_threshold)

    def test_max_suggestions(self):
        suggestions = suggest_commands("run", max_suggestions=1)
        assert len(suggestions) <= 1

    def test_sorted_by_score(self):
        suggestions = suggest_commands("st")
        scores = [score for _, score in suggestions]
        assert scores == sorted(scores, reverse=True)

    def test_custom_candidates(self):
        suggestions = suggest_commands(
            "abc",
            candidates=["abc", "abd", "xyz"],
            threshold=0.5,
        )
        assert any(cmd == "abc" for cmd, _ in suggestions)
        assert any(cmd == "abd" for cmd, _ in suggestions)

    def test_returns_tuples(self):
        suggestions = suggest_commands("run")
        for cmd, score in suggestions:
            assert isinstance(cmd, str)
            assert isinstance(score, float)


# ---------------------------------------------------------------------------
# 选项建议测试
# ---------------------------------------------------------------------------

class TestSuggestOptions:
    """测试选项建议"""

    def test_option_suggestion(self):
        suggestions = suggest_options(
            "--env",
            candidates=["--env", "--port", "--help"],
        )
        assert any(opt == "--env" for opt, _ in suggestions)

    def test_typo_option(self):
        suggestions = suggest_options(
            "--en",
            candidates=["--env", "--port", "--help"],
            threshold=0.3,
        )
        assert any(opt == "--env" for opt, _ in suggestions)

    def test_no_match(self):
        suggestions = suggest_options(
            "--xyz",
            candidates=["--env", "--port"],
            threshold=0.9,
        )
        assert len(suggestions) == 0


# ---------------------------------------------------------------------------
# 建议渲染测试
# ---------------------------------------------------------------------------

class TestRenderSuggestions:
    """测试建议渲染"""

    def test_with_suggestions(self):
        suggestions = [("run", 0.9), ("status", 0.5)]
        result = render_suggestions("rn", suggestions)
        assert "rn" in result
        assert "run" in result
        assert "您是不是想输入" in result

    def test_no_suggestions(self):
        result = render_suggestions("xyz", [])
        assert "未知" in result
        assert "xyz" in result

    def test_option_rendering(self):
        suggestions = [("--env", 0.9)]
        result = render_suggestions("--en", suggestions, is_option=True)
        assert "选项" in result

    def test_command_rendering(self):
        suggestions = [("run", 0.9)]
        result = render_suggestions("rn", suggestions, is_option=False)
        assert "命令" in result

    def test_includes_summary(self):
        suggestions = [("run", 0.9)]
        result = render_suggestions("rn", suggestions)
        # run 命令应有说明
        assert "启动" in result or "运行" in result

    def test_includes_score(self):
        suggestions = [("run", 0.9)]
        result = render_suggestions("rn", suggestions)
        assert "90%" in result or "相似度" in result


# ---------------------------------------------------------------------------
# format_did_you_mean 测试
# ---------------------------------------------------------------------------

class TestFormatDidYouMean:
    """测试 did-you-mean 格式化"""

    def test_with_suggestion(self):
        result = format_did_you_mean("stat")
        assert "status" in result
        assert "您是不是想输入" in result

    def test_no_suggestion(self):
        result = format_did_you_mean("xyzabc123", threshold=0.9)
        assert result == ""

    def test_typo(self):
        result = format_did_you_mean("halp")
        assert "help" in result


# ---------------------------------------------------------------------------
# CommandFrequency 测试
# ---------------------------------------------------------------------------

class TestCommandFrequency:
    """测试命令频率统计"""

    def test_record_and_get(self):
        freq = CommandFrequency()
        freq.record("run")
        freq.record("run")
        freq.record("status")
        assert freq.get_count("run") == 2
        assert freq.get_count("status") == 1

    def test_case_insensitive(self):
        freq = CommandFrequency()
        freq.record("RUN")
        freq.record("run")
        assert freq.get_count("run") == 2

    def test_empty_command_ignored(self):
        freq = CommandFrequency()
        freq.record("")
        freq.record("   ")
        assert freq.get_count("") == 0

    def test_unknown_command(self):
        freq = CommandFrequency()
        assert freq.get_count("unknown") == 0

    def test_clear(self):
        freq = CommandFrequency()
        freq.record("run")
        freq.clear()
        assert freq.get_count("run") == 0

    def test_to_dict(self):
        freq = CommandFrequency()
        freq.record("run")
        freq.record("status")
        d = freq.to_dict()
        assert d["run"] == 1
        assert d["status"] == 1

    def test_suggest_with_frequency(self):
        freq = CommandFrequency()
        freq.record("status")
        freq.record("status")
        # status 频率高，在相似度相近时应优先
        suggestions = freq.suggest_with_frequency("stat")
        assert len(suggestions) > 0
        # status 应在建议中
        cmds = [cmd for cmd, _ in suggestions]
        assert "status" in cmds

    def test_frequency_doesnt_override_similarity(self):
        freq = CommandFrequency()
        freq.record("doctor")  # doctor 频率高
        # 但 "stat" 与 "status" 更相似
        suggestions = freq.suggest_with_frequency("stat", threshold=0.3)
        if suggestions:
            # status 应排在 doctor 前面（相似度更高）
            cmds = [cmd for cmd, _ in suggestions]
            if "status" in cmds and "doctor" in cmds:
                assert cmds.index("status") < cmds.index("doctor")


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLISuggestion:
    """测试 CLI 中的智能建议"""

    def test_unknown_command_suggests(self, capsys):
        # "stat" 应建议 "status"
        rc = main(["stat"])
        captured = capsys.readouterr()
        assert rc == 2
        assert "status" in captured.err
        assert "您是不是想输入" in captured.err

    def test_unknown_command_no_suggestion(self, capsys):
        # 完全不相关的命令不应有建议
        rc = main(["xyzabc123456"])
        capsys.readouterr()
        # 无建议时也返回 2
        assert rc == 2

    def test_typo_help(self, capsys):
        rc = main(["halp"])
        captured = capsys.readouterr()
        assert rc == 2
        assert "help" in captured.err

    def test_valid_command_not_intercepted(self, capsys):
        # 有效命令不应被拦截
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "命令帮助" in captured.out or "可用命令" in captured.out

    def test_option_not_intercepted(self, capsys):
        # 以 - 开头的参数不应被拦截
        rc = main(["--help"])
        capsys.readouterr()
        assert rc == 0

    def test_suggestion_includes_hint(self, capsys):
        main(["stat"])
        captured = capsys.readouterr()
        assert "提示" in captured.err
        assert "help" in captured.err
