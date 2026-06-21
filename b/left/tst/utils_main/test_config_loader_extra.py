"""配置加载器补充测试"""
import pytest
from root.left.app.left.src.utils_main.config_loader import ConfigLoader
from root.left.app.left.src.utils_main.exceptions import ConfigurationError


class TestConfigLoaderExtra:
    """测试ConfigLoader额外路径"""

    def test_load_config_file_not_found(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigLoader.load_config("nonexistent_env_12345")

    def test_load_config_none(self) -> None:
        with pytest.raises(ConfigurationError):
            ConfigLoader.load_config(None)
