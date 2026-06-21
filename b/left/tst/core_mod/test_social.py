"""情感计算与社交智能模块测试"""

from root.left.app.left.src.core_mod.social import (
    EmotionRecognizer,
    EmpathyModel,
    RelationshipTracker,
    SocialContextAnalyzer,
    SocialIntelligenceModule,
)


class TestEmotionRecognizer:
    """EmotionRecognizer 单元测试"""

    def test_init_normal(self) -> None:
        er = EmotionRecognizer({"threshold": 0.4})
        assert er.threshold == 0.4

    def test_recognize(self) -> None:
        er = EmotionRecognizer({})
        result = er.recognize({"valence": 0.8, "arousal": 0.7})
        assert "emotion" in result
        assert "confidence" in result

    def test_recognize_negative(self) -> None:
        er = EmotionRecognizer({})
        result = er.recognize({"valence": -0.8, "arousal": 0.6})
        assert result["emotion"] == "anger"

    def test_recognize_low_arousal(self) -> None:
        er = EmotionRecognizer({})
        result = er.recognize({"valence": 0.2, "arousal": 0.1})
        assert result["emotion"] == "neutral"

    def test_history_trim(self) -> None:
        er = EmotionRecognizer({"max_history": 2})
        for i in range(5):
            er.recognize({"valence": float(i) * 0.1, "arousal": 0.5})
        assert len(er.history) == 2

    def test_get_state(self) -> None:
        er = EmotionRecognizer({})
        s = er.get_state()
        assert s["history_size"] == 0


class TestSocialContextAnalyzer:
    """SocialContextAnalyzer 单元测试"""

    def test_init_normal(self) -> None:
        sca = SocialContextAnalyzer({"context_window": 5})
        assert sca.context_window == 5

    def test_analyze(self) -> None:
        sca = SocialContextAnalyzer({})
        sca.observe({"speaker": "A", "content": "hello", "valence": 0.5})
        sca.observe({"speaker": "B", "content": "hi", "valence": 0.3})
        result = sca.analyze()
        assert "avg_valence" in result
        assert "participant_count" in result
        assert result["participant_count"] == 2

    def test_analyze_empty(self) -> None:
        sca = SocialContextAnalyzer({})
        result = sca.analyze()
        assert result["avg_valence"] == 0.0
        assert result["participant_count"] == 0

    def test_trim(self) -> None:
        sca = SocialContextAnalyzer({})
        for i in range(105):
            sca.observe({"speaker": "A", "content": "x", "valence": 0.0})
        assert len(sca.interactions) == 100

    def test_get_state(self) -> None:
        sca = SocialContextAnalyzer({})
        s = sca.get_state()
        assert s["interaction_count"] == 0


class TestEmpathyModel:
    """EmpathyModel 单元测试"""

    def test_init_normal(self) -> None:
        em = EmpathyModel({"empathy_factor": 0.6})
        assert em.empathy_factor == 0.6

    def test_respond(self) -> None:
        em = EmpathyModel({})
        result = em.respond({"emotion": "joy", "intensity": 0.8})
        assert "response_emotion" in result
        assert "response_intensity" in result
        assert result["response_intensity"] > 0.0

    def test_respond_negative(self) -> None:
        em = EmpathyModel({})
        result = em.respond({"emotion": "sadness", "intensity": 0.9})
        assert result["response_emotion"] == "comfort"
        assert result["response_intensity"] > 0.0

    def test_respond_unknown(self) -> None:
        em = EmpathyModel({})
        result = em.respond({"emotion": "xyz", "intensity": 0.5})
        assert result["response_emotion"] == "neutral"

    def test_get_state(self) -> None:
        em = EmpathyModel({})
        s = em.get_state()
        assert s["empathy_factor"] == 0.5


class TestRelationshipTracker:
    """RelationshipTracker 单元测试"""

    def test_init_normal(self) -> None:
        rt = RelationshipTracker({"decay_rate": 0.01})
        assert rt.decay_rate == 0.01

    def test_interact(self) -> None:
        rt = RelationshipTracker({})
        rt.interact("A", "B", 0.5)
        assert ("A", "B") in rt.relationships
        assert rt.relationships[("A", "B")] == 0.5

    def test_interact_accumulate(self) -> None:
        rt = RelationshipTracker({})
        rt.interact("A", "B", 0.3)
        rt.interact("A", "B", 0.4)
        assert rt.relationships[("A", "B")] == 0.7

    def test_interact_clip(self) -> None:
        rt = RelationshipTracker({})
        for _ in range(20):
            rt.interact("A", "B", 0.5)
        assert rt.relationships[("A", "B")] == 1.0

    def test_get_relationship(self) -> None:
        rt = RelationshipTracker({})
        assert rt.get_relationship("A", "B") == 0.0
        rt.interact("A", "B", 0.5)
        assert rt.get_relationship("A", "B") == 0.5

    def test_decay(self) -> None:
        rt = RelationshipTracker({"decay_rate": 0.1})
        rt.interact("A", "B", 1.0)
        rt.decay()
        assert rt.get_relationship("A", "B") < 1.0

    def test_get_state(self) -> None:
        rt = RelationshipTracker({})
        rt.interact("A", "B", 0.5)
        s = rt.get_state()
        assert s["relationship_count"] == 1


class TestSocialIntelligenceModule:
    """SocialIntelligenceModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = SocialIntelligenceModule({})
        assert mod.emotion is not None
        assert mod.context is not None
        assert mod.empathy is not None
        assert mod.relationships is not None

    def test_perceive_and_respond(self) -> None:
        mod = SocialIntelligenceModule({})
        result = mod.perceive_and_respond({
            "speaker": "Alice",
            "content": "great news",
            "valence": 0.9,
            "arousal": 0.8,
        })
        assert "emotion" in result
        assert "response" in result
        assert "context" in result
        assert result["emotion"]["emotion"] == "joy"

    def test_perceive_negative(self) -> None:
        mod = SocialIntelligenceModule({})
        result = mod.perceive_and_respond({
            "speaker": "Bob",
            "content": "bad day",
            "valence": -0.8,
            "arousal": 0.5,
        })
        assert result["emotion"]["emotion"] == "sadness"
        assert result["response"]["response_emotion"] == "comfort"

    def test_track_relationship(self) -> None:
        mod = SocialIntelligenceModule({})
        mod.track_relationship("A", "B", 0.5)
        assert mod.relationships.get_relationship("A", "B") == 0.5

    def test_get_state(self) -> None:
        mod = SocialIntelligenceModule({})
        s = mod.get_state()
        assert "emotion" in s
        assert "context" in s
        assert "empathy" in s
        assert "relationships" in s

    def test_boundary_empty_input(self) -> None:
        mod = SocialIntelligenceModule({})
        result = mod.perceive_and_respond({})
        assert "emotion" in result
        assert result["emotion"]["emotion"] == "neutral"

    def test_boundary_missing_fields(self) -> None:
        mod = SocialIntelligenceModule({})
        result = mod.perceive_and_respond({"speaker": "X"})
        assert "emotion" in result
        assert "response" in result
