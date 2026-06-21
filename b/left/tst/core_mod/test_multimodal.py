"""跨模态感知融合模块测试"""

from root.left.app.left.src.core_mod.multimodal import (
    CrossModalEncoder,
    ModalityAlignment,
    MultiModalFusion,
    SensorFusionModule,
)


class TestCrossModalEncoder:
    """CrossModalEncoder 单元测试"""

    def test_init_normal(self) -> None:
        enc = CrossModalEncoder({"output_dim": 8})
        assert enc.output_dim == 8

    def test_encode(self) -> None:
        enc = CrossModalEncoder({"output_dim": 4})
        result = enc.encode("numeric", [1.0, 2.0, 3.0])
        assert len(result) == 4

    def test_encode_pad(self) -> None:
        enc = CrossModalEncoder({"output_dim": 4})
        enc.encode("numeric", [1.0, 2.0, 3.0])
        result = enc.encode("numeric", [1.0])
        assert len(result) == 4

    def test_encode_truncate(self) -> None:
        enc = CrossModalEncoder({"output_dim": 4})
        enc.encode("numeric", [1.0, 2.0])
        result = enc.encode("numeric", [1.0, 2.0, 3.0, 4.0, 5.0])
        assert len(result) == 4

    def test_encode_new_modality(self) -> None:
        enc = CrossModalEncoder({"output_dim": 4})
        result = enc.encode("text", [0.5, 0.5])
        assert len(result) == 4
        assert "text" in enc.encoders

    def test_get_state(self) -> None:
        enc = CrossModalEncoder({})
        enc.encode("a", [1.0])
        s = enc.get_state()
        assert s["output_dim"] == 16
        assert "a" in s["modalities"]


class TestModalityAlignment:
    """ModalityAlignment 单元测试"""

    def test_init_normal(self) -> None:
        ma = ModalityAlignment({"time_window": 2.0})
        assert ma.time_window == 2.0

    def test_ingest_and_align(self) -> None:
        ma = ModalityAlignment({"time_window": 1.0})
        ma.ingest("camera", 1.0, [1.0, 2.0])
        ma.ingest("lidar", 1.1, [3.0, 4.0])
        result = ma.align(1.0)
        assert "camera" in result
        assert "lidar" in result

    def test_align_outside_window(self) -> None:
        ma = ModalityAlignment({"time_window": 0.5})
        ma.ingest("camera", 1.0, [1.0])
        ma.ingest("lidar", 2.0, [2.0])
        result = ma.align(1.0)
        assert "camera" in result
        assert "lidar" not in result

    def test_align_empty(self) -> None:
        ma = ModalityAlignment({})
        result = ma.align(0.0)
        assert result == {}

    def test_trim(self) -> None:
        ma = ModalityAlignment({})
        for i in range(105):
            ma.ingest("s", float(i), [float(i)])
        assert len(ma.streams["s"]) == 100

    def test_get_state(self) -> None:
        ma = ModalityAlignment({})
        ma.ingest("s", 1.0, [1.0])
        s = ma.get_state()
        assert s["stream_count"] == 1


class TestMultiModalFusion:
    """MultiModalFusion 单元测试"""

    def test_init_normal(self) -> None:
        mf = MultiModalFusion({"fusion_dim": 8})
        assert mf.fusion_dim == 8

    def test_fuse(self) -> None:
        mf = MultiModalFusion({"fusion_dim": 4})
        embeddings = {
            "a": [1.0, 0.0, 0.0, 0.0],
            "b": [0.0, 1.0, 0.0, 0.0],
        }
        result = mf.fuse(embeddings)
        assert len(result) == 4

    def test_fuse_empty(self) -> None:
        mf = MultiModalFusion({"fusion_dim": 4})
        result = mf.fuse({})
        assert result == [0.0, 0.0, 0.0, 0.0]

    def test_fuse_pad(self) -> None:
        mf = MultiModalFusion({"fusion_dim": 4})
        result = mf.fuse({"a": [1.0]})
        assert len(result) == 4

    def test_fuse_with_weights(self) -> None:
        mf = MultiModalFusion({"fusion_dim": 2, "weights": {"a": 0.8, "b": 0.2}})
        result = mf.fuse({"a": [1.0, 0.0], "b": [0.0, 1.0]})
        assert len(result) == 2

    def test_update_weight(self) -> None:
        mf = MultiModalFusion({})
        mf.update_weight("a", 0.7)
        assert mf.weights["a"] == 0.7

    def test_update_weight_clip(self) -> None:
        mf = MultiModalFusion({})
        mf.update_weight("a", 1.5)
        assert mf.weights["a"] == 1.0

    def test_get_state(self) -> None:
        mf = MultiModalFusion({"fusion_dim": 4})
        s = mf.get_state()
        assert s["fusion_dim"] == 4


class TestSensorFusionModule:
    """SensorFusionModule 集成测试"""

    def test_init_normal(self) -> None:
        mod = SensorFusionModule({})
        assert mod.encoder is not None
        assert mod.alignment is not None
        assert mod.fusion is not None

    def test_ingest_and_fuse(self) -> None:
        mod = SensorFusionModule({})
        mod.ingest("camera", 1.0, [1.0, 2.0, 3.0])
        mod.ingest("lidar", 1.05, [4.0, 5.0])
        result = mod.fuse_at(1.0)
        assert "camera" in result["aligned_modalities"]
        assert "lidar" in result["aligned_modalities"]
        assert len(result["fused"]) == 16

    def test_fuse_at_no_data(self) -> None:
        mod = SensorFusionModule({})
        result = mod.fuse_at(0.0)
        assert result["aligned_modalities"] == []
        assert result["fused"] == [0.0] * 16

    def test_encode(self) -> None:
        mod = SensorFusionModule({"encoder": {"output_dim": 4}})
        result = mod.encode("test", [1.0, 2.0])
        assert len(result) == 4

    def test_get_state(self) -> None:
        mod = SensorFusionModule({})
        mod.ingest("s", 1.0, [1.0])
        s = mod.get_state()
        assert "encoder" in s
        assert "alignment" in s
        assert "fusion" in s

    def test_boundary_empty_data(self) -> None:
        mod = SensorFusionModule({})
        mod.ingest("s", 1.0, [])
        result = mod.fuse_at(1.0)
        assert "s" in result["aligned_modalities"]

    def test_boundary_large_data(self) -> None:
        mod = SensorFusionModule({"encoder": {"output_dim": 4}, "fusion": {"fusion_dim": 4}})
        data = [float(i) for i in range(100)]
        mod.ingest("s", 1.0, data)
        result = mod.fuse_at(1.0)
        assert len(result["fused"]) == 4
