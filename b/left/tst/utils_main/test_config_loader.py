"""配置加载器单元测试"""
import pytest
from root.left.app.left.src.utils_main.config_loader import (
    DEFAULT_CONFIG,
    ConfigDescriber,
    ConfigHelper,
    ConfigLoader,
)
from root.left.app.left.src.utils_main.exceptions import ConfigurationError


class TestConfigLoader:
    """测试ConfigLoader"""

    def test_normal_dev(self) -> None:
        config = ConfigLoader.load_config("dev")
        assert "phase1" in config

    def test_empty_string(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigLoader.load_config("")

    def test_boundary_invalid_env(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigLoader.load_config("invalid_env")

    def test_invalid_format_none(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigLoader.load_config(None)

    def test_load_config_merges_defaults(self) -> None:
        config = ConfigLoader.load_config("dev")
        assert config["loop_interval"] == 1.0
        assert config["phase1"]["sensory"]["noise_filter"]["ema_alpha"] == 0.3

    def test_load_config_file_overrides_defaults(self) -> None:
        config = ConfigLoader.load_config("test")
        assert config["loop_interval"] == 0.1
        assert config["phase2"]["memory"]["store"]["db_path"] == "agent_memory_test.db"

    def test_load_config_env_override(self, monkeypatch) -> None:
        monkeypatch.setenv("AGENT_loop_interval", "2.5")
        monkeypatch.setenv("AGENT_phase1__sensory__noise_filter__ema_alpha", "0.9")
        config = ConfigLoader.load_config("dev")
        assert config["loop_interval"] == 2.5
        assert config["phase1"]["sensory"]["noise_filter"]["ema_alpha"] == 0.9

    def test_load_config_env_override_bool(self, monkeypatch) -> None:
        monkeypatch.setenv("AGENT_phase1__adjustment__enabled", "false")
        config = ConfigLoader.load_config("dev")
        assert config["phase1"]["adjustment"]["enabled"] is False

    def test_empty_yaml_file_uses_defaults(self, tmp_path, monkeypatch) -> None:
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("\n")
        monkeypatch.setattr(
            ConfigLoader,
            "_get_config_path",
            lambda env: str(empty_file)
        )
        config = ConfigLoader.load_config("empty")
        assert config["loop_interval"] == DEFAULT_CONFIG["loop_interval"]
        assert config["phase1"]["sensory"]["noise_filter"]["ema_alpha"] == 0.3


class TestConfigHelper:
    """测试ConfigHelper"""

    def test_get_existing_path(self) -> None:
        value = ConfigHelper.get(DEFAULT_CONFIG, "phase1.sensory.noise_filter.ema_alpha")
        assert value == 0.3

    def test_get_missing_path_returns_default(self) -> None:
        value = ConfigHelper.get(DEFAULT_CONFIG, "phase1.missing.key", default="fallback")
        assert value == "fallback"

    def test_get_nested_existing(self) -> None:
        value = ConfigHelper.get_nested(
            DEFAULT_CONFIG,
            ["phase2", "memory", "store", "db_path"]
        )
        assert value == "agent_memory.db"

    def test_get_nested_missing_returns_default(self) -> None:
        value = ConfigHelper.get_nested(
            DEFAULT_CONFIG,
            ["phase2", "missing", "key"],
            default=42
        )
        assert value == 42


class TestConfigDescriber:
    """测试ConfigDescriber"""

    def test_describe_existing(self) -> None:
        result = ConfigDescriber.describe("loop_interval")
        assert result is not None
        assert result[0] == "float"
        assert "间隔" in result[1]

    def test_describe_nonexistent(self) -> None:
        result = ConfigDescriber.describe("nonexistent.key")
        assert result is None

    def test_describe_all_returns_list(self) -> None:
        items = ConfigDescriber.describe_all()
        assert len(items) > 10
        first = items[0]
        assert "path" in first
        assert "type" in first
        assert "description" in first
        assert "default" in first

    def test_describe_all_includes_key_configs(self) -> None:
        items = ConfigDescriber.describe_all()
        paths = [item["path"] for item in items]
        assert "loop_interval" in paths
        assert "max_loops" in paths
        assert "log_level" in paths
        assert "phase2.memory.store.db_path" in paths

    def test_to_text_contains_sections(self) -> None:
        text = ConfigDescriber.to_text()
        assert "=== Agent 配置项说明 ===" in text
        assert "loop_interval" in text
        assert "类型" in text
        assert "说明" in text
        assert "环境变量" in text
