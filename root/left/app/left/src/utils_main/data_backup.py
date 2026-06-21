"""数据导入导出与备份恢复

提供配置、状态、报告等数据的导出、导入、备份与恢复能力。

设计原则（第一性原理）：
1. 可导出：将系统数据导出为可移植的 JSON 格式
2. 可导入：从导出文件恢复数据到系统
3. 可备份：将完整系统状态打包为 tar.gz 归档
4. 可恢复：从备份归档恢复系统状态
5. 可校验：通过 SHA256 校验和验证文件完整性

数据类型：
- config：配置文件（YAML 转 JSON 导出）
- state：SQLite 状态数据库（states/errors 表导出为 JSON）
- reports：报告文件（reports/ 目录下 JSON 文件）
- all：以上全部

备份格式：
- 单文件 tar.gz 归档
- 内含 manifest.json 描述备份内容与校验和
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tarfile
import tempfile
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from root.left.app.left.src.utils_main.cli_formatter import (
    Color,
    colorize,
    render_divider,
    render_key_value,
    render_section,
    render_table,
)


# ---------------------------------------------------------------------------
# 枚举与常量
# ---------------------------------------------------------------------------

class DataType(str, Enum):
    """数据类型。"""

    CONFIG = "config"
    STATE = "state"
    REPORTS = "reports"
    ALL = "all"


class ExportFormat(str, Enum):
    """导出格式。"""

    JSON = "json"


BACKUP_VERSION = "1.0"
MANIFEST_FILENAME = "manifest.json"


# ---------------------------------------------------------------------------
# 校验和
# ---------------------------------------------------------------------------

def compute_checksum(file_path: str) -> str:
    """计算文件 SHA256 校验和。

    Args:
        file_path: 文件路径

    Returns:
        十六进制校验和字符串
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_dict_checksum(data: Dict[str, Any]) -> str:
    """计算字典数据的 SHA256 校验和。

    Args:
        data: 字典数据

    Returns:
        十六进制校验和字符串
    """
    content = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def verify_checksum(file_path: str, expected: str) -> bool:
    """验证文件校验和。

    Args:
        file_path: 文件路径
        expected: 预期校验和

    Returns:
        是否匹配
    """
    actual = compute_checksum(file_path)
    return actual == expected


# ---------------------------------------------------------------------------
# 备份清单
# ---------------------------------------------------------------------------

@dataclass
class BackupManifest:
    """备份清单。

    描述备份的元数据与内容。
    """

    version: str = BACKUP_VERSION
    created_at: float = field(default_factory=time.time)
    data_types: List[str] = field(default_factory=list)
    files: Dict[str, str] = field(default_factory=dict)  # 文件名 -> 校验和
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "data_types": self.data_types,
            "files": self.files,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BackupManifest":
        return cls(
            version=data.get("version", BACKUP_VERSION),
            created_at=data.get("created_at", 0.0),
            data_types=data.get("data_types", []),
            files=data.get("files", {}),
            metadata=data.get("metadata", {}),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 数据导出
# ---------------------------------------------------------------------------

class DataExporter:
    """数据导出器。

    将系统数据导出为可移植的 JSON 格式。
    """

    def __init__(self, base_dir: str = ".") -> None:
        """初始化导出器。

        Args:
            base_dir: 项目根目录（包含配置、数据库、报告等）
        """
        self.base_dir = os.path.abspath(base_dir)

    def export_config(self, env: str = "dev") -> Dict[str, Any]:
        """导出配置。

        Args:
            env: 环境名

        Returns:
            配置数据字典

        Raises:
            FileNotFoundError: 配置文件不存在
        """
        from root.left.app.left.src.utils_main.config_loader import ConfigLoader

        config = ConfigLoader.load_config(env)
        return {
            "type": DataType.CONFIG.value,
            "env": env,
            "config": config,
            "exported_at": time.time(),
        }

    def export_state(self, db_path: Optional[str] = None) -> Dict[str, Any]:
        """导出 SQLite 状态数据。

        Args:
            db_path: 数据库路径，默认 base_dir/agent_memory.db

        Returns:
            状态数据字典
        """
        if db_path is None:
            db_path = os.path.join(self.base_dir, "agent_memory.db")

        if not os.path.exists(db_path):
            return {
                "type": DataType.STATE.value,
                "db_path": db_path,
                "states": [],
                "errors": [],
                "exported_at": time.time(),
                "note": "数据库文件不存在",
            }

        conn = sqlite3.connect(db_path)
        try:
            conn.row_factory = sqlite3.Row
            states: List[Dict[str, Any]] = []
            errors: List[Dict[str, Any]] = []

            # 导出 states 表
            try:
                cursor = conn.execute("SELECT * FROM states ORDER BY id")
                for row in cursor:
                    states.append(dict(row))
            except sqlite3.Error:
                pass  # 表不存在

            # 导出 errors 表
            try:
                cursor = conn.execute("SELECT * FROM errors ORDER BY id")
                for row in cursor:
                    errors.append(dict(row))
            except sqlite3.Error:
                pass

            return {
                "type": DataType.STATE.value,
                "db_path": db_path,
                "states": states,
                "errors": errors,
                "state_count": len(states),
                "error_count": len(errors),
                "exported_at": time.time(),
            }
        finally:
            conn.close()

    def export_reports(self) -> Dict[str, Any]:
        """导出报告文件。

        Returns:
            报告数据字典
        """
        reports_dir = os.path.join(self.base_dir, "reports")
        reports: Dict[str, Any] = {}

        if os.path.isdir(reports_dir):
            for name in os.listdir(reports_dir):
                if name.endswith(".json"):
                    file_path = os.path.join(reports_dir, name)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            reports[name] = json.load(f)
                    except (json.JSONDecodeError, OSError):
                        reports[name] = {"error": "无法读取文件"}

        return {
            "type": DataType.REPORTS.value,
            "reports": reports,
            "report_count": len(reports),
            "exported_at": time.time(),
        }

    def export_all(self, env: str = "dev") -> Dict[str, Any]:
        """导出所有数据。

        Args:
            env: 环境名

        Returns:
            完整导出数据字典
        """
        return {
            "type": DataType.ALL.value,
            "version": BACKUP_VERSION,
            "exported_at": time.time(),
            "config": self.export_config(env),
            "state": self.export_state(),
            "reports": self.export_reports(),
        }

    def export_to_file(
        self,
        output_path: str,
        data_type: DataType = DataType.ALL,
        env: str = "dev",
    ) -> str:
        """导出数据到文件。

        Args:
            output_path: 输出文件路径
            data_type: 数据类型
            env: 环境名

        Returns:
            实际输出路径
        """
        if data_type == DataType.CONFIG:
            data = self.export_config(env)
        elif data_type == DataType.STATE:
            data = self.export_state()
        elif data_type == DataType.REPORTS:
            data = self.export_reports()
        else:
            data = self.export_all(env)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return output_path


# ---------------------------------------------------------------------------
# 数据导入
# ---------------------------------------------------------------------------

class DataImporter:
    """数据导入器。

    从 JSON 文件导入数据到系统。
    """

    def __init__(self, base_dir: str = ".") -> None:
        """初始化导入器。

        Args:
            base_dir: 项目根目录
        """
        self.base_dir = os.path.abspath(base_dir)

    def load_export_file(self, file_path: str) -> Dict[str, Any]:
        """加载导出文件。

        Args:
            file_path: 导出文件路径

        Returns:
            数据字典

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 解析失败
        """
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def import_config(self, data: Dict[str, Any], env: str = "dev") -> str:
        """导入配置。

        将配置数据写入 YAML 文件。

        Args:
            data: 配置数据
            env: 目标环境名

        Returns:
            写入的文件路径

        Raises:
            ValueError: 数据格式无效
        """
        if "config" not in data:
            raise ValueError("数据中缺少 config 字段")

        import yaml

        config = data["config"]
        config_dir = os.path.join(self.base_dir, "root", "left", "app", "right", "cfg", "left", "dev")
        os.makedirs(config_dir, exist_ok=True)
        file_path = os.path.join(config_dir, f"{env}.yaml")

        with open(file_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

        return file_path

    def import_state(self, data: Dict[str, Any], db_path: Optional[str] = None) -> str:
        """导入状态数据到 SQLite。

        Args:
            data: 状态数据
            db_path: 数据库路径，默认 base_dir/agent_memory.db

        Returns:
            数据库路径

        Raises:
            ValueError: 数据格式无效
        """
        if "states" not in data or "errors" not in data:
            raise ValueError("数据中缺少 states 或 errors 字段")

        if db_path is None:
            db_path = os.path.join(self.base_dir, "agent_memory.db")

        conn = sqlite3.connect(db_path)
        try:
            # 创建表（如果不存在）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loop_id INTEGER,
                    timestamp REAL,
                    state_json TEXT,
                    drive_json TEXT,
                    performance REAL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS errors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    loop_id INTEGER,
                    timestamp REAL,
                    error_type TEXT,
                    error_message TEXT
                )
            """)

            # 导入 states
            for state in data.get("states", []):
                conn.execute(
                    "INSERT INTO states (loop_id, timestamp, state_json, drive_json, performance) VALUES (?, ?, ?, ?, ?)",
                    (
                        state.get("loop_id"),
                        state.get("timestamp"),
                        state.get("state_json"),
                        state.get("drive_json"),
                        state.get("performance"),
                    ),
                )

            # 导入 errors
            for error in data.get("errors", []):
                conn.execute(
                    "INSERT INTO errors (loop_id, timestamp, error_type, error_message) VALUES (?, ?, ?, ?)",
                    (
                        error.get("loop_id"),
                        error.get("timestamp"),
                        error.get("error_type"),
                        error.get("error_message"),
                    ),
                )

            conn.commit()
            return db_path
        finally:
            conn.close()

    def import_reports(self, data: Dict[str, Any]) -> int:
        """导入报告文件。

        Args:
            data: 报告数据

        Returns:
            导入的文件数量

        Raises:
            ValueError: 数据格式无效
        """
        if "reports" not in data:
            raise ValueError("数据中缺少 reports 字段")

        reports_dir = os.path.join(self.base_dir, "reports")
        os.makedirs(reports_dir, exist_ok=True)

        count = 0
        for name, content in data["reports"].items():
            file_path = os.path.join(reports_dir, name)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            count += 1

        return count

    def import_from_file(self, file_path: str, env: str = "dev") -> Dict[str, Any]:
        """从文件导入数据。

        Args:
            file_path: 导出文件路径
            env: 目标环境名

        Returns:
            导入结果字典
        """
        data = self.load_export_file(file_path)
        results: Dict[str, Any] = {"imported": []}

        data_type = data.get("type", DataType.ALL.value)

        if data_type == DataType.CONFIG.value:
            path = self.import_config(data, env)
            results["imported"].append({"type": "config", "path": path})
        elif data_type == DataType.STATE.value:
            path = self.import_state(data)
            results["imported"].append({"type": "state", "path": path})
        elif data_type == DataType.REPORTS.value:
            count = self.import_reports(data)
            results["imported"].append({"type": "reports", "count": count})
        else:
            # ALL
            if "config" in data:
                path = self.import_config(data["config"], env)
                results["imported"].append({"type": "config", "path": path})
            if "state" in data:
                path = self.import_state(data["state"])
                results["imported"].append({"type": "state", "path": path})
            if "reports" in data:
                count = self.import_reports(data["reports"])
                results["imported"].append({"type": "reports", "count": count})

        return results


# ---------------------------------------------------------------------------
# 备份管理器
# ---------------------------------------------------------------------------

class BackupManager:
    """备份管理器。

    创建和恢复 tar.gz 备份归档。
    """

    def __init__(self, base_dir: str = ".") -> None:
        """初始化备份管理器。

        Args:
            base_dir: 项目根目录
        """
        self.base_dir = os.path.abspath(base_dir)
        self.exporter = DataExporter(base_dir)
        self.importer = DataImporter(base_dir)

    def create_backup(
        self,
        output_path: str,
        data_types: Optional[List[DataType]] = None,
        env: str = "dev",
    ) -> str:
        """创建备份。

        Args:
            output_path: 输出 tar.gz 文件路径
            data_types: 要备份的数据类型列表，默认全部
            env: 环境名

        Returns:
            实际输出路径
        """
        if data_types is None:
            data_types = [DataType.CONFIG, DataType.STATE, DataType.REPORTS]

        manifest = BackupManifest(
            data_types=[dt.value for dt in data_types],
            metadata={"env": env, "base_dir": self.base_dir},
        )

        # 创建临时目录存放导出文件
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 导出各类型数据
            for data_type in data_types:
                export_path = os.path.join(tmp_dir, f"{data_type.value}.json")
                self.exporter.export_to_file(export_path, data_type, env)
                checksum = compute_checksum(export_path)
                manifest.files[f"{data_type.value}.json"] = checksum

            # 写入清单
            manifest_path = os.path.join(tmp_dir, MANIFEST_FILENAME)
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(manifest.to_json())

            # 创建 tar.gz 归档
            with tarfile.open(output_path, "w:gz") as tar:
                for name in os.listdir(tmp_dir):
                    file_path = os.path.join(tmp_dir, name)
                    tar.add(file_path, arcname=name)

        return output_path

    def restore_backup(self, backup_path: str, env: str = "dev") -> Dict[str, Any]:
        """从备份恢复。

        Args:
            backup_path: 备份文件路径
            env: 目标环境名

        Returns:
            恢复结果字典

        Raises:
            FileNotFoundError: 备份文件不存在
            ValueError: 备份文件无效或校验失败
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"备份文件不存在: {backup_path}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            # 解压归档
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(tmp_dir)

            # 读取清单
            manifest_path = os.path.join(tmp_dir, MANIFEST_FILENAME)
            if not os.path.exists(manifest_path):
                raise ValueError("备份文件缺少 manifest.json")

            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = BackupManifest.from_dict(json.load(f))

            # 校验文件完整性
            for filename, expected_checksum in manifest.files.items():
                file_path = os.path.join(tmp_dir, filename)
                if not os.path.exists(file_path):
                    raise ValueError(f"备份缺少文件: {filename}")
                if not verify_checksum(file_path, expected_checksum):
                    raise ValueError(f"文件校验失败: {filename}")

            # 导入数据
            results: Dict[str, Any] = {"restored": [], "manifest": manifest.to_dict()}

            for filename in manifest.files:
                file_path = os.path.join(tmp_dir, filename)
                data = self.importer.load_export_file(file_path)

                if filename == f"{DataType.CONFIG.value}.json":
                    path = self.importer.import_config(data, env)
                    results["restored"].append({"type": "config", "path": path})
                elif filename == f"{DataType.STATE.value}.json":
                    path = self.importer.import_state(data)
                    results["restored"].append({"type": "state", "path": path})
                elif filename == f"{DataType.REPORTS.value}.json":
                    count = self.importer.import_reports(data)
                    results["restored"].append({"type": "reports", "count": count})

            return results

    def verify_backup(self, backup_path: str) -> Dict[str, Any]:
        """验证备份完整性。

        Args:
            backup_path: 备份文件路径

        Returns:
            验证结果字典
        """
        if not os.path.exists(backup_path):
            return {"valid": False, "error": "备份文件不存在"}

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.extractall(tmp_dir)

                manifest_path = os.path.join(tmp_dir, MANIFEST_FILENAME)
                if not os.path.exists(manifest_path):
                    return {"valid": False, "error": "缺少 manifest.json"}

                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = BackupManifest.from_dict(json.load(f))

                verified_files: List[Dict[str, Any]] = []
                all_valid = True

                for filename, expected_checksum in manifest.files.items():
                    file_path = os.path.join(tmp_dir, filename)
                    if not os.path.exists(file_path):
                        verified_files.append({
                            "file": filename,
                            "valid": False,
                            "error": "文件不存在",
                        })
                        all_valid = False
                        continue

                    actual_checksum = compute_checksum(file_path)
                    is_valid = actual_checksum == expected_checksum
                    verified_files.append({
                        "file": filename,
                        "valid": is_valid,
                        "checksum": actual_checksum,
                    })
                    if not is_valid:
                        all_valid = False

                return {
                    "valid": all_valid,
                    "version": manifest.version,
                    "created_at": manifest.created_at,
                    "data_types": manifest.data_types,
                    "files": verified_files,
                }
        except (tarfile.TarError, json.JSONDecodeError, OSError) as e:
            return {"valid": False, "error": str(e)}

    def list_backups(self, directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出目录中的备份文件。

        Args:
            directory: 目录路径，默认 base_dir/backups

        Returns:
            备份信息列表
        """
        if directory is None:
            directory = os.path.join(self.base_dir, "backups")

        if not os.path.isdir(directory):
            return []

        backups: List[Dict[str, Any]] = []
        for name in sorted(os.listdir(directory)):
            if name.endswith(".tar.gz") or name.endswith(".tgz"):
                file_path = os.path.join(directory, name)
                stat = os.stat(file_path)
                backups.append({
                    "name": name,
                    "path": file_path,
                    "size": stat.st_size,
                    "created_at": stat.st_mtime,
                })

        return backups


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def _format_timestamp(ts: float) -> str:
    """格式化时间戳。"""
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _format_size(size: int) -> str:
    """格式化文件大小。"""
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def render_export_summary(data: Dict[str, Any]) -> str:
    """渲染导出数据摘要。"""
    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("导出数据摘要"))
    lines.append(render_divider())
    lines.append("")

    pairs: List[Tuple[str, Any]] = [
        ("类型", data.get("type", "unknown")),
        ("导出时间", _format_timestamp(data.get("exported_at", 0))),
    ]

    if "env" in data:
        pairs.append(("环境", data["env"]))
    if "state_count" in data:
        pairs.append(("状态记录数", data["state_count"]))
    if "error_count" in data:
        pairs.append(("错误记录数", data["error_count"]))
    if "report_count" in data:
        pairs.append(("报告数", data["report_count"]))
    if "config" in data:
        pairs.append(("配置项数", len(data["config"])))

    pairs.append(("校验和", compute_dict_checksum(data)))

    lines.append(render_key_value(pairs))
    return "\n".join(lines)


def render_backup_list(backups: List[Dict[str, Any]]) -> str:
    """渲染备份列表。"""
    if not backups:
        return "无备份文件。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"备份文件（共 {len(backups)} 个）"))
    lines.append(render_divider())
    lines.append("")

    rows: List[List[str]] = []
    for b in backups:
        rows.append([
            b["name"],
            _format_size(b["size"]),
            _format_timestamp(b["created_at"]),
        ])

    lines.append(render_table(["名称", "大小", "创建时间"], rows))
    return "\n".join(lines)


def render_verify_result(result: Dict[str, Any]) -> str:
    """渲染验证结果。"""
    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("备份验证结果"))
    lines.append(render_divider())
    lines.append("")

    if not result.get("valid", False):
        status = colorize("失败", Color.RED)
        lines.append(f"状态: {status}")
        if "error" in result:
            lines.append(f"错误: {result['error']}")
        return "\n".join(lines)

    status = colorize("通过", Color.GREEN)
    lines.append(f"状态: {status}")
    lines.append("")

    pairs: List[Tuple[str, Any]] = [
        ("版本", result.get("version", "unknown")),
        ("创建时间", _format_timestamp(result.get("created_at", 0))),
        ("数据类型", ", ".join(result.get("data_types", []))),
    ]
    lines.append(render_key_value(pairs))
    lines.append("")

    # 文件验证详情
    files = result.get("files", [])
    if files:
        rows: List[List[str]] = []
        for f in files:
            status = colorize("✓", Color.GREEN) if f.get("valid") else colorize("✗", Color.RED)
            rows.append([f.get("file", ""), status, f.get("checksum", "")[:16] + "..."])

        lines.append(render_table(["文件", "状态", "校验和"], rows))

    return "\n".join(lines)


def render_restore_result(result: Dict[str, Any]) -> str:
    """渲染恢复结果。"""
    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("恢复结果"))
    lines.append(render_divider())
    lines.append("")

    restored = result.get("restored", [])
    lines.append(f"恢复项数: {len(restored)}")
    lines.append("")

    if restored:
        rows: List[List[str]] = []
        for r in restored:
            rtype = r.get("type", "unknown")
            if "path" in r:
                detail = r["path"]
            elif "count" in r:
                detail = f"{r['count']} 个文件"
            else:
                detail = "-"
            rows.append([rtype, detail])

        lines.append(render_table(["类型", "详情"], rows))

    return "\n".join(lines)


def render_import_result(result: Dict[str, Any]) -> str:
    """渲染导入结果。"""
    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("导入结果"))
    lines.append(render_divider())
    lines.append("")

    imported = result.get("imported", [])
    lines.append(f"导入项数: {len(imported)}")
    lines.append("")

    if imported:
        rows: List[List[str]] = []
        for r in imported:
            rtype = r.get("type", "unknown")
            if "path" in r:
                detail = r["path"]
            elif "count" in r:
                detail = f"{r['count']} 个文件"
            else:
                detail = "-"
            rows.append([rtype, detail])

        lines.append(render_table(["类型", "详情"], rows))

    return "\n".join(lines)
