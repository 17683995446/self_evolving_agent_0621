"""数据导入导出与备份恢复测试"""
from __future__ import annotations

import json
import os
import sqlite3
import time

from root.left.app.left.src.cli import main
from root.left.app.left.src.utils_main.data_backup import (
    BACKUP_VERSION,
    BackupManager,
    BackupManifest,
    DataExporter,
    DataImporter,
    DataType,
    compute_checksum,
    compute_dict_checksum,
    render_backup_list,
    render_export_summary,
    render_import_result,
    render_restore_result,
    render_verify_result,
    verify_checksum,
)


# ---------------------------------------------------------------------------
# 测试辅助
# ---------------------------------------------------------------------------

def _create_test_db(db_path: str) -> None:
    """创建测试用 SQLite 数据库。"""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("""
            CREATE TABLE states (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER,
                timestamp REAL,
                state_json TEXT,
                drive_json TEXT,
                performance REAL
            )
        """)
        conn.execute("""
            CREATE TABLE errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                loop_id INTEGER,
                timestamp REAL,
                error_type TEXT,
                error_message TEXT
            )
        """)
        conn.execute(
            "INSERT INTO states (loop_id, timestamp, state_json, drive_json, performance) VALUES (?, ?, ?, ?, ?)",
            (1, time.time(), '{"key": "value"}', '{"drive": 1}', 0.95),
        )
        conn.execute(
            "INSERT INTO errors (loop_id, timestamp, error_type, error_message) VALUES (?, ?, ?, ?)",
            (1, time.time(), "TestError", "测试错误"),
        )
        conn.commit()
    finally:
        conn.close()


def _create_test_reports(reports_dir: str) -> None:
    """创建测试报告文件。"""
    os.makedirs(reports_dir, exist_ok=True)
    with open(os.path.join(reports_dir, "test_report.json"), "w", encoding="utf-8") as f:
        json.dump({"score": 100, "passed": True}, f)


# ---------------------------------------------------------------------------
# 校验和测试
# ---------------------------------------------------------------------------

class TestChecksum:
    """测试校验和功能"""

    def test_compute_checksum(self, tmp_path):
        file_path = str(tmp_path / "test.txt")
        with open(file_path, "w") as f:
            f.write("hello world")
        checksum = compute_checksum(file_path)
        assert isinstance(checksum, str)
        assert len(checksum) == 64  # SHA256 hex

    def test_compute_checksum_consistent(self, tmp_path):
        file_path = str(tmp_path / "test.txt")
        with open(file_path, "w") as f:
            f.write("hello world")
        c1 = compute_checksum(file_path)
        c2 = compute_checksum(file_path)
        assert c1 == c2

    def test_compute_checksum_different_content(self, tmp_path):
        f1 = str(tmp_path / "a.txt")
        f2 = str(tmp_path / "b.txt")
        with open(f1, "w") as f:
            f.write("hello")
        with open(f2, "w") as f:
            f.write("world")
        assert compute_checksum(f1) != compute_checksum(f2)

    def test_compute_dict_checksum(self):
        data = {"a": 1, "b": 2}
        checksum = compute_dict_checksum(data)
        assert isinstance(checksum, str)
        assert len(checksum) == 64

    def test_compute_dict_checksum_consistent(self):
        data = {"a": 1, "b": 2}
        assert compute_dict_checksum(data) == compute_dict_checksum(data)

    def test_compute_dict_checksum_order_independent(self):
        """字典键顺序不影响校验和"""
        d1 = {"a": 1, "b": 2}
        d2 = {"b": 2, "a": 1}
        assert compute_dict_checksum(d1) == compute_dict_checksum(d2)

    def test_verify_checksum_match(self, tmp_path):
        file_path = str(tmp_path / "test.txt")
        with open(file_path, "w") as f:
            f.write("hello")
        checksum = compute_checksum(file_path)
        assert verify_checksum(file_path, checksum) is True

    def test_verify_checksum_mismatch(self, tmp_path):
        file_path = str(tmp_path / "test.txt")
        with open(file_path, "w") as f:
            f.write("hello")
        assert verify_checksum(file_path, "wrong_checksum") is False


# ---------------------------------------------------------------------------
# BackupManifest 测试
# ---------------------------------------------------------------------------

class TestBackupManifest:
    """测试备份清单"""

    def test_default_values(self):
        manifest = BackupManifest()
        assert manifest.version == BACKUP_VERSION
        assert manifest.created_at > 0
        assert manifest.data_types == []
        assert manifest.files == {}

    def test_to_dict(self):
        manifest = BackupManifest(
            data_types=["config", "state"],
            files={"config.json": "abc123"},
        )
        d = manifest.to_dict()
        assert d["version"] == BACKUP_VERSION
        assert "config" in d["data_types"]
        assert d["files"]["config.json"] == "abc123"

    def test_from_dict(self):
        data = {
            "version": "1.0",
            "created_at": 1000.0,
            "data_types": ["config"],
            "files": {"config.json": "abc"},
            "metadata": {"env": "dev"},
        }
        manifest = BackupManifest.from_dict(data)
        assert manifest.version == "1.0"
        assert manifest.created_at == 1000.0
        assert manifest.data_types == ["config"]
        assert manifest.files == {"config.json": "abc"}

    def test_roundtrip(self):
        original = BackupManifest(
            data_types=["config", "state"],
            files={"config.json": "abc", "state.json": "def"},
            metadata={"env": "prod"},
        )
        d = original.to_dict()
        restored = BackupManifest.from_dict(d)
        assert restored.version == original.version
        assert restored.data_types == original.data_types
        assert restored.files == original.files

    def test_to_json(self):
        manifest = BackupManifest(data_types=["config"])
        json_str = manifest.to_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["version"] == BACKUP_VERSION


# ---------------------------------------------------------------------------
# DataExporter 测试
# ---------------------------------------------------------------------------

class TestDataExporter:
    """测试数据导出器"""

    def test_export_config(self, tmp_path):
        exporter = DataExporter(str(tmp_path))
        data = exporter.export_config("dev")
        assert data["type"] == DataType.CONFIG.value
        assert data["env"] == "dev"
        assert "config" in data
        assert "exported_at" in data

    def test_export_state_no_db(self, tmp_path):
        exporter = DataExporter(str(tmp_path))
        data = exporter.export_state()
        assert data["type"] == DataType.STATE.value
        assert data["states"] == []
        assert data["errors"] == []
        assert "不存在" in data.get("note", "")

    def test_export_state_with_db(self, tmp_path):
        db_path = str(tmp_path / "agent_memory.db")
        _create_test_db(db_path)
        exporter = DataExporter(str(tmp_path))
        data = exporter.export_state(db_path)
        assert data["type"] == DataType.STATE.value
        assert data["state_count"] == 1
        assert data["error_count"] == 1
        assert len(data["states"]) == 1
        assert len(data["errors"]) == 1

    def test_export_reports_empty(self, tmp_path):
        exporter = DataExporter(str(tmp_path))
        data = exporter.export_reports()
        assert data["type"] == DataType.REPORTS.value
        assert data["report_count"] == 0

    def test_export_reports_with_files(self, tmp_path):
        _create_test_reports(str(tmp_path / "reports"))
        exporter = DataExporter(str(tmp_path))
        data = exporter.export_reports()
        assert data["report_count"] == 1
        assert "test_report.json" in data["reports"]

    def test_export_all(self, tmp_path):
        exporter = DataExporter(str(tmp_path))
        data = exporter.export_all("dev")
        assert data["type"] == DataType.ALL.value
        assert "config" in data
        assert "state" in data
        assert "reports" in data
        assert data["version"] == BACKUP_VERSION

    def test_export_to_file(self, tmp_path):
        exporter = DataExporter(str(tmp_path))
        output_path = str(tmp_path / "export.json")
        result_path = exporter.export_to_file(output_path, DataType.CONFIG, "dev")
        assert result_path == output_path
        assert os.path.exists(output_path)
        with open(output_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["type"] == DataType.CONFIG.value


# ---------------------------------------------------------------------------
# DataImporter 测试
# ---------------------------------------------------------------------------

class TestDataImporter:
    """测试数据导入器"""

    def test_load_export_file(self, tmp_path):
        file_path = str(tmp_path / "test.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump({"type": "config", "config": {"key": "value"}}, f)
        importer = DataImporter(str(tmp_path))
        data = importer.load_export_file(file_path)
        assert data["type"] == "config"

    def test_load_export_file_not_found(self, tmp_path):
        importer = DataImporter(str(tmp_path))
        try:
            importer.load_export_file(str(tmp_path / "nonexistent.json"))
            assert False, "应抛出 FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_import_config(self, tmp_path):
        importer = DataImporter(str(tmp_path))
        data = {"config": {"key": "value", "nested": {"a": 1}}}
        path = importer.import_config(data, "test")
        assert os.path.exists(path)
        assert path.endswith("test.yaml")

    def test_import_config_missing_field(self, tmp_path):
        importer = DataImporter(str(tmp_path))
        try:
            importer.import_config({"no_config": True}, "dev")
            assert False, "应抛出 ValueError"
        except ValueError:
            pass

    def test_import_state(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        importer = DataImporter(str(tmp_path))
        data = {
            "states": [
                {"loop_id": 1, "timestamp": 1000.0, "state_json": "{}", "drive_json": "{}", "performance": 0.9},
            ],
            "errors": [
                {"loop_id": 1, "timestamp": 1000.0, "error_type": "Err", "error_message": "msg"},
            ],
        }
        result_path = importer.import_state(data, db_path)
        assert os.path.exists(result_path)
        # 验证数据
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM states")
            assert cursor.fetchone()[0] == 1
            cursor = conn.execute("SELECT COUNT(*) FROM errors")
            assert cursor.fetchone()[0] == 1
        finally:
            conn.close()

    def test_import_state_missing_field(self, tmp_path):
        importer = DataImporter(str(tmp_path))
        try:
            importer.import_state({"no_states": True}, str(tmp_path / "test.db"))
            assert False, "应抛出 ValueError"
        except ValueError:
            pass

    def test_import_reports(self, tmp_path):
        importer = DataImporter(str(tmp_path))
        data = {
            "reports": {
                "report1.json": {"score": 100},
                "report2.json": {"score": 90},
            }
        }
        count = importer.import_reports(data)
        assert count == 2
        assert os.path.exists(str(tmp_path / "reports" / "report1.json"))
        assert os.path.exists(str(tmp_path / "reports" / "report2.json"))

    def test_import_reports_missing_field(self, tmp_path):
        importer = DataImporter(str(tmp_path))
        try:
            importer.import_reports({"no_reports": True})
            assert False, "应抛出 ValueError"
        except ValueError:
            pass

    def test_import_from_file_config(self, tmp_path):
        # 先导出
        exporter = DataExporter(str(tmp_path))
        export_path = str(tmp_path / "config.json")
        exporter.export_to_file(export_path, DataType.CONFIG, "dev")

        # 再导入
        importer = DataImporter(str(tmp_path))
        result = importer.import_from_file(export_path, "imported")
        assert len(result["imported"]) == 1
        assert result["imported"][0]["type"] == "config"

    def test_import_from_file_reports(self, tmp_path):
        # 创建报告
        _create_test_reports(str(tmp_path / "reports"))
        # 导出
        exporter = DataExporter(str(tmp_path))
        export_path = str(tmp_path / "reports.json")
        exporter.export_to_file(export_path, DataType.REPORTS, "dev")

        # 导入到新位置
        importer = DataImporter(str(tmp_path))
        result = importer.import_from_file(export_path)
        assert len(result["imported"]) == 1
        assert result["imported"][0]["type"] == "reports"


# ---------------------------------------------------------------------------
# BackupManager 测试
# ---------------------------------------------------------------------------

class TestBackupManager:
    """测试备份管理器"""

    def test_create_and_restore_backup(self, tmp_path):
        # 准备数据
        _create_test_reports(str(tmp_path / "reports"))
        db_path = str(tmp_path / "agent_memory.db")
        _create_test_db(db_path)

        # 创建备份
        manager = BackupManager(str(tmp_path))
        backup_path = str(tmp_path / "backup.tar.gz")
        manager.create_backup(backup_path, env="dev")
        assert os.path.exists(backup_path)

        # 验证备份
        verify_result = manager.verify_backup(backup_path)
        assert verify_result["valid"] is True

        # 恢复到新目录
        restore_dir = str(tmp_path / "restored")
        os.makedirs(restore_dir)
        restore_manager = BackupManager(restore_dir)
        result = restore_manager.restore_backup(backup_path, "dev")
        assert len(result["restored"]) > 0

    def test_create_backup_specific_types(self, tmp_path):
        manager = BackupManager(str(tmp_path))
        backup_path = str(tmp_path / "backup.tar.gz")
        manager.create_backup(backup_path, data_types=[DataType.CONFIG], env="dev")
        assert os.path.exists(backup_path)

        # 验证只包含 config
        verify_result = manager.verify_backup(backup_path)
        assert verify_result["valid"] is True
        assert "config" in verify_result["data_types"]

    def test_verify_backup_not_found(self, tmp_path):
        manager = BackupManager(str(tmp_path))
        result = manager.verify_backup(str(tmp_path / "nonexistent.tar.gz"))
        assert result["valid"] is False
        assert "不存在" in result["error"]

    def test_verify_backup_invalid_file(self, tmp_path):
        # 创建无效的 tar.gz 文件
        file_path = str(tmp_path / "invalid.tar.gz")
        with open(file_path, "wb") as f:
            f.write(b"not a tar.gz file")
        manager = BackupManager(str(tmp_path))
        result = manager.verify_backup(file_path)
        assert result["valid"] is False

    def test_restore_backup_not_found(self, tmp_path):
        manager = BackupManager(str(tmp_path))
        try:
            manager.restore_backup(str(tmp_path / "nonexistent.tar.gz"))
            assert False, "应抛出 FileNotFoundError"
        except FileNotFoundError:
            pass

    def test_list_backups_empty(self, tmp_path):
        manager = BackupManager(str(tmp_path))
        backups = manager.list_backups()
        assert backups == []

    def test_list_backups_with_files(self, tmp_path):
        # 创建备份目录
        backups_dir = str(tmp_path / "backups")
        os.makedirs(backups_dir)

        # 创建几个备份文件
        for name in ["backup1.tar.gz", "backup2.tar.gz", "other.txt"]:
            with open(os.path.join(backups_dir, name), "wb") as f:
                f.write(b"dummy")

        manager = BackupManager(str(tmp_path))
        backups = manager.list_backups(backups_dir)
        assert len(backups) == 2  # 只计 .tar.gz
        names = [b["name"] for b in backups]
        assert "backup1.tar.gz" in names
        assert "backup2.tar.gz" in names

    def test_list_backups_nonexistent_dir(self, tmp_path):
        manager = BackupManager(str(tmp_path))
        backups = manager.list_backups(str(tmp_path / "nonexistent"))
        assert backups == []

    def test_backup_roundtrip_integrity(self, tmp_path):
        """备份-恢复往返完整性测试"""
        # 准备数据
        _create_test_reports(str(tmp_path / "reports"))
        db_path = str(tmp_path / "agent_memory.db")
        _create_test_db(db_path)

        # 创建备份
        manager = BackupManager(str(tmp_path))
        backup_path = str(tmp_path / "full_backup.tar.gz")
        manager.create_backup(backup_path, env="dev")

        # 恢复到新目录
        restore_dir = str(tmp_path / "restored")
        os.makedirs(restore_dir)
        restore_manager = BackupManager(restore_dir)
        result = restore_manager.restore_backup(backup_path, "dev")

        # 验证恢复的数据
        restored_types = [r["type"] for r in result["restored"]]
        assert "config" in restored_types
        assert "reports" in restored_types


# ---------------------------------------------------------------------------
# 渲染测试
# ---------------------------------------------------------------------------

class TestRenderExportSummary:
    """测试导出摘要渲染"""

    def test_render(self):
        data = {
            "type": "config",
            "env": "dev",
            "exported_at": time.time(),
            "config": {"key": "value"},
        }
        result = render_export_summary(data)
        assert "导出数据摘要" in result
        assert "config" in result

    def test_render_with_state(self):
        data = {
            "type": "state",
            "exported_at": time.time(),
            "state_count": 10,
            "error_count": 2,
        }
        result = render_export_summary(data)
        assert "10" in result
        assert "2" in result


class TestRenderBackupList:
    """测试备份列表渲染"""

    def test_empty(self):
        result = render_backup_list([])
        assert "无备份文件" in result

    def test_with_backups(self):
        backups = [
            {"name": "backup1.tar.gz", "size": 1024, "created_at": time.time()},
            {"name": "backup2.tar.gz", "size": 2048, "created_at": time.time()},
        ]
        result = render_backup_list(backups)
        assert "备份文件" in result
        assert "backup1.tar.gz" in result
        assert "backup2.tar.gz" in result


class TestRenderVerifyResult:
    """测试验证结果渲染"""

    def test_valid(self):
        result_data = {
            "valid": True,
            "version": "1.0",
            "created_at": time.time(),
            "data_types": ["config", "state"],
            "files": [
                {"file": "config.json", "valid": True, "checksum": "abc123def456"},
            ],
        }
        result = render_verify_result(result_data)
        assert "通过" in result
        assert "config.json" in result

    def test_invalid(self):
        result_data = {
            "valid": False,
            "error": "文件损坏",
        }
        result = render_verify_result(result_data)
        assert "失败" in result
        assert "文件损坏" in result


class TestRenderRestoreResult:
    """测试恢复结果渲染"""

    def test_empty(self):
        result = render_restore_result({"restored": []})
        assert "恢复结果" in result
        assert "0" in result

    def test_with_items(self):
        result_data = {
            "restored": [
                {"type": "config", "path": "/path/to/config.yaml"},
                {"type": "reports", "count": 3},
            ]
        }
        result = render_restore_result(result_data)
        assert "config" in result
        assert "reports" in result


class TestRenderImportResult:
    """测试导入结果渲染"""

    def test_empty(self):
        result = render_import_result({"imported": []})
        assert "导入结果" in result

    def test_with_items(self):
        result_data = {
            "imported": [
                {"type": "config", "path": "/path/to/config.yaml"},
            ]
        }
        result = render_import_result(result_data)
        assert "config" in result


# ---------------------------------------------------------------------------
# CLI 集成测试
# ---------------------------------------------------------------------------

class TestCLIData:
    """测试 data 子命令"""

    def test_data_no_args_shows_help(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = main(["data"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "用法" in captured.out

    def test_data_export_config(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        output_file = str(tmp_path / "config_export.json")
        rc = main(["data", "--export", output_file, "--type", "config"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已导出" in captured.out
        assert os.path.exists(output_file)

    def test_data_export_all(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        output_file = str(tmp_path / "all_export.json")
        rc = main(["data", "--export", output_file, "--type", "all"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已导出" in captured.out
        assert os.path.exists(output_file)

    def test_data_import(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # 先导出
        export_file = str(tmp_path / "config.json")
        main(["data", "--export", export_file, "--type", "config"])
        capsys.readouterr()  # 清空输出
        # 再导入
        rc = main(["data", "--import", export_file, "--env", "imported"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已从" in captured.out

    def test_data_backup_and_verify(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backup_file = str(tmp_path / "backup.tar.gz")
        # 创建备份
        rc = main(["data", "--backup", backup_file])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已创建备份" in captured.out
        assert os.path.exists(backup_file)
        # 验证备份
        rc = main(["data", "--verify", backup_file])
        captured = capsys.readouterr()
        assert rc == 0
        assert "通过" in captured.out

    def test_data_list_backups_empty(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = main(["data", "--list-backups"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "无备份文件" in captured.out

    def test_data_list_backups_with_files(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        backups_dir = str(tmp_path / "backups")
        os.makedirs(backups_dir)
        # 创建备份文件
        with open(os.path.join(backups_dir, "test.tar.gz"), "wb") as f:
            f.write(b"dummy")
        rc = main(["data", "--list-backups", "--dir", backups_dir])
        captured = capsys.readouterr()
        assert rc == 0
        assert "test.tar.gz" in captured.out

    def test_data_verify_nonexistent(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = main(["data", "--verify", str(tmp_path / "nonexistent.tar.gz")])
        captured = capsys.readouterr()
        assert rc == 1
        assert "失败" in captured.out

    def test_data_restore(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # 创建备份
        backup_file = str(tmp_path / "backup.tar.gz")
        main(["data", "--backup", backup_file])
        capsys.readouterr()
        # 恢复
        rc = main(["data", "--restore", backup_file])
        captured = capsys.readouterr()
        assert rc == 0
        assert "已从" in captured.out

    def test_data_restore_nonexistent(self, capsys, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        rc = main(["data", "--restore", str(tmp_path / "nonexistent.tar.gz")])
        captured = capsys.readouterr()
        assert rc == 2
        assert "错误" in captured.err


# ---------------------------------------------------------------------------
# 帮助系统集成
# ---------------------------------------------------------------------------

class TestHelpIntegration:
    """测试帮助系统是否包含 data 命令"""

    def test_help_all_contains_data(self, capsys):
        rc = main(["help"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "data" in captured.out

    def test_help_data(self, capsys):
        rc = main(["help", "data"])
        captured = capsys.readouterr()
        assert rc == 0
        assert "data" in captured.out
        assert "备份" in captured.out or "导入" in captured.out
