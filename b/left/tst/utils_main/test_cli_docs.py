"""用户文档与示例集测试"""
from __future__ import annotations

from root.left.app.left.src.cli import build_parser, main
from root.left.app.left.src.utils_main.cli_docs import (
    DOC_TOPICS,
    render_command_reference,
    render_config_guide,
    render_doc,
    render_docs_index,
    render_faq,
    render_quickstart,
    render_troubleshooting,
)


# ---------------------------------------------------------------------------
# 文档主题测试
# ---------------------------------------------------------------------------

class TestDocTopics:
    """测试文档主题定义"""

    def test_all_topics_defined(self) -> None:
        assert "quickstart" in DOC_TOPICS
        assert "commands" in DOC_TOPICS
        assert "config" in DOC_TOPICS
        assert "troubleshooting" in DOC_TOPICS
        assert "faq" in DOC_TOPICS

    def test_topic_count(self) -> None:
        assert len(DOC_TOPICS) == 5


# ---------------------------------------------------------------------------
# 快速入门测试
# ---------------------------------------------------------------------------

class TestRenderQuickstart:
    """测试快速入门渲染"""

    def test_quickstart_contains_title(self) -> None:
        text = render_quickstart()
        assert "快速入门指南" in text

    def test_quickstart_contains_steps(self) -> None:
        text = render_quickstart()
        assert "第 1 步" in text
        assert "第 2 步" in text
        assert "第 3 步" in text
        assert "第 4 步" in text
        assert "第 5 步" in text

    def test_quickstart_contains_commands(self) -> None:
        text = render_quickstart()
        assert "doctor" in text
        assert "validate" in text
        assert "run" in text
        assert "status" in text

    def test_quickstart_contains_dry_run(self) -> None:
        text = render_quickstart()
        assert "dry-run" in text
        assert "--max-loops" in text


# ---------------------------------------------------------------------------
# 命令参考测试
# ---------------------------------------------------------------------------

class TestRenderCommandReference:
    """测试命令参考渲染"""

    def test_command_reference_contains_all_commands(self) -> None:
        text = render_command_reference()
        assert "run" in text
        assert "status" in text
        assert "health" in text
        assert "validate" in text
        assert "config" in text
        assert "doctor" in text
        assert "diagnose" in text
        assert "welcome" in text
        assert "help" in text
        assert "examples" in text
        assert "init" in text
        assert "control" in text
        assert "docs" in text

    def test_command_reference_contains_examples(self) -> None:
        text = render_command_reference()
        assert "示例" in text
        assert "python -m root.left.app.left.src.cli" in text


# ---------------------------------------------------------------------------
# 配置指南测试
# ---------------------------------------------------------------------------

class TestRenderConfigGuide:
    """测试配置指南渲染"""

    def test_config_guide_contains_title(self) -> None:
        text = render_config_guide()
        assert "配置指南" in text

    def test_config_guide_contains_sections(self) -> None:
        text = render_config_guide()
        assert "配置文件位置" in text
        assert "配置层级" in text
        assert "主要配置段" in text
        assert "环境变量覆盖" in text
        assert "从模板创建配置" in text

    def test_config_guide_contains_env_var_example(self) -> None:
        text = render_config_guide()
        assert "AGENT_" in text
        assert "AGENT_LOOP_INTERVAL" in text

    def test_config_guide_contains_phase_sections(self) -> None:
        text = render_config_guide()
        assert "phase1" in text
        assert "phase2" in text
        assert "phase3" in text


# ---------------------------------------------------------------------------
# 故障排查测试
# ---------------------------------------------------------------------------

class TestRenderTroubleshooting:
    """测试故障排查渲染"""

    def test_troubleshooting_contains_title(self) -> None:
        text = render_troubleshooting()
        assert "故障排查" in text

    def test_troubleshooting_contains_problems(self) -> None:
        text = render_troubleshooting()
        assert "配置错误" in text
        assert "无法连接" in text
        assert "不健康" in text
        assert "缺少依赖" in text

    def test_troubleshooting_contains_solutions(self) -> None:
        text = render_troubleshooting()
        assert "原因" in text
        assert "解决" in text

    def test_troubleshooting_contains_more_help(self) -> None:
        text = render_troubleshooting()
        assert "获取更多帮助" in text
        assert "doctor" in text
        assert "diagnose" in text


# ---------------------------------------------------------------------------
# 常见问题测试
# ---------------------------------------------------------------------------

class TestRenderFAQ:
    """测试常见问题渲染"""

    def test_faq_contains_title(self) -> None:
        text = render_faq()
        assert "常见问题" in text
        assert "FAQ" in text

    def test_faq_contains_questions(self) -> None:
        text = render_faq()
        assert "dry-run" in text
        assert "持续运行" in text
        assert "修改配置" in text
        assert "暂停和恢复" in text

    def test_faq_contains_answers(self) -> None:
        text = render_faq()
        assert "A:" in text
        assert "Q:" in text


# ---------------------------------------------------------------------------
# 文档索引测试
# ---------------------------------------------------------------------------

class TestRenderDocsIndex:
    """测试文档索引渲染"""

    def test_index_contains_title(self) -> None:
        text = render_docs_index()
        assert "用户文档" in text

    def test_index_lists_all_topics(self) -> None:
        text = render_docs_index()
        for key, title in DOC_TOPICS.items():
            assert key in text
            assert title in text

    def test_index_contains_usage(self) -> None:
        text = render_docs_index()
        assert "cli docs" in text
        assert "使用方法" in text


# ---------------------------------------------------------------------------
# 文档分发测试
# ---------------------------------------------------------------------------

class TestRenderDoc:
    """测试文档分发函数"""

    def test_render_doc_quickstart(self) -> None:
        text = render_doc("quickstart")
        assert "快速入门" in text

    def test_render_doc_commands(self) -> None:
        text = render_doc("commands")
        assert "命令参考" in text

    def test_render_doc_config(self) -> None:
        text = render_doc("config")
        assert "配置指南" in text

    def test_render_doc_troubleshooting(self) -> None:
        text = render_doc("troubleshooting")
        assert "故障排查" in text

    def test_render_doc_faq(self) -> None:
        text = render_doc("faq")
        assert "常见问题" in text

    def test_render_doc_unknown_returns_index(self) -> None:
        text = render_doc("nonexistent")
        assert "用户文档" in text

    def test_render_doc_empty_returns_index(self) -> None:
        text = render_doc("")
        assert "用户文档" in text


# ---------------------------------------------------------------------------
# CLI docs 子命令测试
# ---------------------------------------------------------------------------

class TestCLIDocsParser:
    """测试 docs 子命令参数解析"""

    def test_docs_parser_no_topic(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["docs"])
        assert args.command == "docs"
        assert args.topic is None

    def test_docs_parser_with_topic(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["docs", "quickstart"])
        assert args.topic == "quickstart"


class TestCLIDocsCommand:
    """测试 docs 子命令执行"""

    def test_docs_no_topic_shows_index(self, capsys) -> None:
        exit_code = main(["docs"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "用户文档" in captured.out

    def test_docs_quickstart(self, capsys) -> None:
        exit_code = main(["docs", "quickstart"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "快速入门" in captured.out

    def test_docs_commands(self, capsys) -> None:
        exit_code = main(["docs", "commands"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "命令参考" in captured.out

    def test_docs_config(self, capsys) -> None:
        exit_code = main(["docs", "config"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "配置指南" in captured.out

    def test_docs_troubleshooting(self, capsys) -> None:
        exit_code = main(["docs", "troubleshooting"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "故障排查" in captured.out

    def test_docs_faq(self, capsys) -> None:
        exit_code = main(["docs", "faq"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "常见问题" in captured.out

    def test_docs_unknown_topic_shows_index(self, capsys) -> None:
        exit_code = main(["docs", "nonexistent"])
        captured = capsys.readouterr()
        assert exit_code == 0
        assert "用户文档" in captured.out
