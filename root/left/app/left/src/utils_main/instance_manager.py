"""多实例管理与编排

提供多个 Agent 实例的注册、控制、编排与持久化能力。

设计原则（第一性原理）：
1. 可注册：注册多个 Agent 实例（名称、环境、端口、配置覆盖）
2. 可查询：查看所有实例状态、单个实例详情
3. 可控制：启动/停止/重启单个实例
4. 可编排：批量操作多个实例（启动全部、停止全部）
5. 可持久化：实例配置持久化到 JSON 文件，重启后可恢复

实例生命周期：
- STOPPED：已停止（或未启动）
- RUNNING：运行中
- ERROR：异常停止
- UNKNOWN：状态未知
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
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

class InstanceStatus(str, Enum):
    """实例状态。"""

    STOPPED = "stopped"
    RUNNING = "running"
    ERROR = "error"
    UNKNOWN = "unknown"


STATUS_COLORS: Dict[str, Color] = {
    InstanceStatus.STOPPED.value: Color.GRAY,
    InstanceStatus.RUNNING.value: Color.GREEN,
    InstanceStatus.ERROR.value: Color.RED,
    InstanceStatus.UNKNOWN.value: Color.YELLOW,
}


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class AgentInstance:
    """Agent 实例配置。

    描述一个 Agent 实例的运行参数。
    """

    name: str
    env: str = "dev"
    port: int = 8080
    max_loops: int = 1000
    loop_interval: float = 1.0
    dry_run: bool = False
    description: str = ""
    # 运行时状态（不持久化）
    pid: Optional[int] = None
    started_at: Optional[float] = None
    status: InstanceStatus = InstanceStatus.STOPPED

    def to_dict(self, include_runtime: bool = True) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "name": self.name,
            "env": self.env,
            "port": self.port,
            "max_loops": self.max_loops,
            "loop_interval": self.loop_interval,
            "dry_run": self.dry_run,
            "description": self.description,
        }
        if include_runtime:
            data["pid"] = self.pid
            data["started_at"] = self.started_at
            data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentInstance":
        return cls(
            name=data["name"],
            env=data.get("env", "dev"),
            port=data.get("port", 8080),
            max_loops=data.get("max_loops", 1000),
            loop_interval=data.get("loop_interval", 1.0),
            dry_run=data.get("dry_run", False),
            description=data.get("description", ""),
            pid=data.get("pid"),
            started_at=data.get("started_at"),
            status=InstanceStatus(data.get("status", InstanceStatus.STOPPED.value)),
        )

    def build_command(self) -> List[str]:
        """构建启动命令。"""
        cmd = [
            sys.executable, "-m", "root.left.app.left.src.cli", "run",
            "--env", self.env,
            "--port", str(self.port),
            "--max-loops", str(self.max_loops),
            "--loop-interval", str(self.loop_interval),
        ]
        if self.dry_run:
            cmd.append("--dry-run")
        return cmd


# ---------------------------------------------------------------------------
# 实例管理器
# ---------------------------------------------------------------------------

class InstanceManager:
    """实例管理器。

    管理多个 Agent 实例的注册、控制与编排。
    """

    def __init__(self) -> None:
        self._instances: Dict[str, AgentInstance] = {}

    def register(self, instance: AgentInstance) -> None:
        """注册实例。若同名实例已存在则覆盖。"""
        self._instances[instance.name] = instance

    def unregister(self, name: str) -> bool:
        """注销实例。"""
        if name in self._instances:
            # 若实例运行中，先停止
            inst = self._instances[name]
            if inst.status == InstanceStatus.RUNNING:
                self.stop(name)
            del self._instances[name]
            return True
        return False

    def get(self, name: str) -> Optional[AgentInstance]:
        """获取实例。"""
        return self._instances.get(name)

    def list_instances(self) -> List[AgentInstance]:
        """列出所有实例。"""
        return list(self._instances.values())

    def start(self, name: str) -> Tuple[bool, str]:
        """启动实例。

        Args:
            name: 实例名

        Returns:
            (是否成功, 消息)
        """
        inst = self._instances.get(name)
        if inst is None:
            return False, f"实例不存在: {name}"
        if inst.status == InstanceStatus.RUNNING:
            return False, f"实例已在运行: {name}"

        try:
            cmd = inst.build_command()
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,  # 独立进程组
            )
            inst.pid = proc.pid
            inst.started_at = time.time()
            inst.status = InstanceStatus.RUNNING
            return True, f"实例 {name} 已启动 (PID={proc.pid})"
        except Exception as e:
            inst.status = InstanceStatus.ERROR
            return False, f"启动失败: {e}"

    def stop(self, name: str) -> Tuple[bool, str]:
        """停止实例。

        Args:
            name: 实例名

        Returns:
            (是否成功, 消息)
        """
        inst = self._instances.get(name)
        if inst is None:
            return False, f"实例不存在: {name}"
        if inst.status != InstanceStatus.RUNNING or inst.pid is None:
            inst.status = InstanceStatus.STOPPED
            return True, f"实例未运行: {name}"

        try:
            os.kill(inst.pid, signal.SIGTERM)
            inst.status = InstanceStatus.STOPPED
            inst.pid = None
            inst.started_at = None
            return True, f"实例 {name} 已停止"
        except ProcessLookupError:
            # 进程已不存在
            inst.status = InstanceStatus.STOPPED
            inst.pid = None
            inst.started_at = None
            return True, f"实例 {name} 进程已不存在，状态已重置"
        except Exception as e:
            inst.status = InstanceStatus.ERROR
            return False, f"停止失败: {e}"

    def restart(self, name: str) -> Tuple[bool, str]:
        """重启实例。"""
        inst = self._instances.get(name)
        if inst is None:
            return False, f"实例不存在: {name}"

        # 先停止（如果在运行）
        if inst.status == InstanceStatus.RUNNING:
            self.stop(name)
            time.sleep(0.5)

        return self.start(name)

    def start_all(self) -> List[Tuple[str, bool, str]]:
        """启动所有已停止的实例。

        Returns:
            [(实例名, 是否成功, 消息), ...]
        """
        results: List[Tuple[str, bool, str]] = []
        for name, inst in self._instances.items():
            if inst.status != InstanceStatus.RUNNING:
                ok, msg = self.start(name)
                results.append((name, ok, msg))
            else:
                results.append((name, True, f"实例已在运行: {name}"))
        return results

    def stop_all(self) -> List[Tuple[str, bool, str]]:
        """停止所有运行中的实例。

        Returns:
            [(实例名, 是否成功, 消息), ...]
        """
        results: List[Tuple[str, bool, str]] = []
        for name, inst in self._instances.items():
            if inst.status == InstanceStatus.RUNNING:
                ok, msg = self.stop(name)
                results.append((name, ok, msg))
            else:
                results.append((name, True, f"实例未运行: {name}"))
        return results

    def get_status(self, name: str) -> Optional[InstanceStatus]:
        """获取实例状态。"""
        inst = self._instances.get(name)
        if inst is None:
            return None
        # 检查进程是否仍在运行
        if inst.pid is not None and inst.status == InstanceStatus.RUNNING:
            try:
                os.kill(inst.pid, 0)  # 不发送信号，仅检查进程是否存在
            except ProcessLookupError:
                inst.status = InstanceStatus.STOPPED
                inst.pid = None
                inst.started_at = None
            except OSError:
                pass
        return inst.status

    def refresh_status(self) -> None:
        """刷新所有实例状态。"""
        for inst in self._instances.values():
            if inst.pid is not None and inst.status == InstanceStatus.RUNNING:
                try:
                    os.kill(inst.pid, 0)
                except ProcessLookupError:
                    inst.status = InstanceStatus.STOPPED
                    inst.pid = None
                    inst.started_at = None
                except OSError:
                    inst.status = InstanceStatus.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        """导出为字典。"""
        return {
            "instances": [inst.to_dict() for inst in self._instances.values()],
            "count": len(self._instances),
        }

    def save_to_file(self, file_path: str) -> str:
        """保存实例配置到文件。

        Args:
            file_path: 文件路径

        Returns:
            文件路径
        """
        data = {
            "version": "1.0",
            "saved_at": time.time(),
            "instances": [inst.to_dict(include_runtime=False) for inst in self._instances.values()],
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return file_path

    def load_from_file(self, file_path: str) -> int:
        """从文件加载实例配置。

        Args:
            file_path: 文件路径

        Returns:
            加载的实例数量

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 解析失败
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for inst_data in data.get("instances", []):
            inst = AgentInstance.from_dict(inst_data)
            self.register(inst)
            count += 1

        return count


# ---------------------------------------------------------------------------
# 渲染
# ---------------------------------------------------------------------------

def _format_timestamp(ts: Optional[float]) -> str:
    """格式化时间戳。"""
    if ts is None:
        return "-"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def _format_status(status: InstanceStatus) -> str:
    """格式化状态。"""
    return colorize(status.value, STATUS_COLORS.get(status.value, Color.GRAY))


def render_instances(instances: List[AgentInstance]) -> str:
    """渲染实例列表。"""
    if not instances:
        return "无实例。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"Agent 实例（共 {len(instances)} 个）"))
    lines.append(render_divider())
    lines.append("")

    rows: List[List[str]] = []
    for inst in instances:
        rows.append([
            inst.name,
            inst.env,
            str(inst.port),
            _format_status(inst.status),
            str(inst.pid) if inst.pid else "-",
            _format_timestamp(inst.started_at),
        ])

    lines.append(render_table(
        ["名称", "环境", "端口", "状态", "PID", "启动时间"],
        rows,
    ))
    return "\n".join(lines)


def render_instance_detail(instance: AgentInstance) -> str:
    """渲染实例详情。"""
    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"实例详情: {instance.name}"))
    lines.append(render_divider())
    lines.append("")

    lines.append(render_key_value([
        ("名称", instance.name),
        ("环境", instance.env),
        ("端口", instance.port),
        ("最大循环数", instance.max_loops),
        ("循环间隔", f"{instance.loop_interval}s"),
        ("试运行", "是" if instance.dry_run else "否"),
        ("说明", instance.description or "-"),
        ("状态", _format_status(instance.status)),
        ("PID", instance.pid if instance.pid else "-"),
        ("启动时间", _format_timestamp(instance.started_at)),
    ]))

    lines.append("")
    lines.append("启动命令:")
    lines.append("  " + " ".join(instance.build_command()))

    return "\n".join(lines)


def render_operation_results(results: List[Tuple[str, bool, str]]) -> str:
    """渲染批量操作结果。"""
    if not results:
        return "无操作。"

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section(f"操作结果（共 {len(results)} 项）"))
    lines.append(render_divider())
    lines.append("")

    rows: List[List[str]] = []
    for name, ok, msg in results:
        status = colorize("成功", Color.GREEN) if ok else colorize("失败", Color.RED)
        rows.append([name, status, msg])

    lines.append(render_table(["实例", "结果", "消息"], rows))
    return "\n".join(lines)


def render_summary(manager: InstanceManager) -> str:
    """渲染管理器摘要。"""
    instances = manager.list_instances()
    running = sum(1 for i in instances if i.status == InstanceStatus.RUNNING)
    stopped = sum(1 for i in instances if i.status == InstanceStatus.STOPPED)
    error = sum(1 for i in instances if i.status == InstanceStatus.ERROR)

    lines: List[str] = []
    lines.append(render_divider())
    lines.append(render_section("实例管理器摘要"))
    lines.append(render_divider())
    lines.append("")

    lines.append(render_key_value([
        ("实例总数", len(instances)),
        ("运行中", running),
        ("已停止", stopped),
        ("错误", error),
    ]))

    return "\n".join(lines)
