"""主入口补充测试"""
from root.left.app.left.src.main import main, SelfEvolvingAgent
from root.left.app.left.src.utils_main.exceptions import AgentException


class TestMainExtra:
    """测试main函数"""

    def test_main_keyboard_interrupt(self, monkeypatch) -> None:
        def mock_init(*args, **kwargs):
            class FakeAgent:
                def run(self, max_loops=None):
                    raise KeyboardInterrupt()
                def stop(self):
                    pass
            return FakeAgent()
        monkeypatch.setattr(SelfEvolvingAgent, "__init__", lambda self, config=None: None)
        monkeypatch.setattr(SelfEvolvingAgent, "run", lambda self, max_loops=None: (_ for _ in ()).throw(KeyboardInterrupt()))
        monkeypatch.setattr(SelfEvolvingAgent, "stop", lambda self: None)
        main()

    def test_main_agent_exception(self, monkeypatch) -> None:
        monkeypatch.setattr(SelfEvolvingAgent, "__init__", lambda self, config=None: None)
        monkeypatch.setattr(SelfEvolvingAgent, "run", lambda self, max_loops=None: (_ for _ in ()).throw(AgentException("test", 0)))
        monkeypatch.setattr(SelfEvolvingAgent, "stop", lambda self: None)
        main()
