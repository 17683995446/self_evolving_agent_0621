"""真实数据源采集器

支持日志文件、HTTP 端点、本地文件、系统指标、自定义回调等多种数据源的
安全采集，为 Agent 提供真实运行数据。
"""
import os
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Final, List, Optional, Set

import psutil

from root.left.app.left.src.utils_main.exceptions import SafetyBoundaryException
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import Validator


class CollectorResult:
    """采集结果"""

    def __init__(self, name: str, success: bool, data: Any = None, error: str = "") -> None:
        self.name: str = name
        self.success: bool = success
        self.data: Any = data
        self.error: str = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }


class BaseCollector(ABC):
    """采集器基类"""

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        self.name: str = name
        self.config: Final[Dict[str, Any]] = config

    @abstractmethod
    def collect(self) -> CollectorResult:
        raise NotImplementedError


class LogCollector(BaseCollector):
    """日志采集器：按行读取文件尾部并统计匹配模式"""

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.path: str = str(config.get("path", ""))
        self.max_lines: int = int(config.get("max_lines", 100))
        self.patterns: Dict[str, str] = dict(config.get("patterns", {}))
        self._last_position: int = 0

    def collect(self) -> CollectorResult:
        logger.debug(f"[LogCollector.collect] path={self.path}", "data")
        if not self.path or not os.path.isfile(self.path):
            return CollectorResult(self.name, True, {"lines": [], "counts": {}})
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                if size < self._last_position:
                    self._last_position = 0
                f.seek(self._last_position)
                lines = []
                for _ in range(self.max_lines):
                    line = f.readline()
                    if not line:
                        break
                    lines.append(line.rstrip("\n"))
                self._last_position = f.tell()
            counts = {name: sum(1 for line in lines if pattern in line) for name, pattern in self.patterns.items()}
            return CollectorResult(self.name, True, {"lines": lines, "counts": counts})
        except Exception as exc:
            return CollectorResult(self.name, False, error=str(exc))


class HttpCollector(BaseCollector):
    """HTTP 采集器：拉取 JSON/YAML 指标"""

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.url: str = str(config.get("url", ""))
        self.timeout: float = float(config.get("timeout", 5.0))
        self.allowed_hosts: List[str] = list(config.get("allowed_hosts", ["localhost", "127.0.0.1"]))

    def collect(self) -> CollectorResult:
        logger.debug(f"[HttpCollector.collect] url={self.url}", "data")
        if not self.url:
            return CollectorResult(self.name, True, data={})
        try:
            self._validate_url(self.url)
            with urllib.request.urlopen(self.url, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            return CollectorResult(self.name, True, data={"status": resp.status, "body": body[:2000]})
        except Exception as exc:
            return CollectorResult(self.name, False, error=str(exc))

    def _validate_url(self, url: str) -> None:
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        if self.allowed_hosts and host not in self.allowed_hosts:
            raise SafetyBoundaryException(
                f"HTTP collector host not allowed: {host}",
                boundary="http_host",
                attempted_action=url,
            )


class FileCollector(BaseCollector):
    """文件采集器：读取文件元数据与内容摘要"""

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.path: str = str(config.get("path", ""))
        self.max_bytes: int = int(config.get("max_bytes", 1024))
        self.blocked_paths: List[str] = list(config.get("blocked_paths", ["/etc/passwd", "/etc/shadow"]))

    def collect(self) -> CollectorResult:
        logger.debug(f"[FileCollector.collect] path={self.path}", "data")
        if not self.path or not os.path.isfile(self.path):
            return CollectorResult(self.name, True, data={"exists": False})
        try:
            self._validate_path(self.path)
            stat = os.stat(self.path)
            with open(self.path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(self.max_bytes)
            return CollectorResult(
                self.name,
                True,
                data={
                    "exists": True,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "content_preview": content,
                },
            )
        except Exception as exc:
            return CollectorResult(self.name, False, error=str(exc))

    def _validate_path(self, path: str) -> None:
        for blocked in self.blocked_paths:
            if path == blocked or path.startswith(blocked):
                raise SafetyBoundaryException(
                    f"File collector path blocked: {path}",
                    boundary="file_path",
                    attempted_action=path,
                )


class SystemMetricsCollector(BaseCollector):
    """系统指标采集器：基于 psutil 采集 CPU/内存/磁盘/网络

    让 Agent 能直接感知运行主机的真实状态。
    """

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.metrics: Set[str] = set(config.get("metrics", ["cpu", "memory", "disk", "network"]))
        self.interval: float = float(config.get("interval", 0.1))

    def collect(self) -> CollectorResult:
        logger.debug(f"[SystemMetricsCollector.collect] metrics={self.metrics}", "data")
        data: Dict[str, Any] = {"metrics": list(self.metrics)}
        try:
            if "cpu" in self.metrics:
                data["cpu_percent"] = psutil.cpu_percent(interval=self.interval)
                data["cpu_count"] = psutil.cpu_count()
            if "memory" in self.metrics:
                mem = psutil.virtual_memory()
                data["memory_percent"] = mem.percent
                data["memory_available_mb"] = round(mem.available / 1024 / 1024, 2)
            if "disk" in self.metrics:
                disk = psutil.disk_usage("/")
                data["disk_percent"] = disk.percent
                data["disk_free_gb"] = round(disk.free / 1024 / 1024 / 1024, 2)
            if "network" in self.metrics:
                net = psutil.net_io_counters()
                data["network_bytes_sent"] = net.bytes_sent
                data["network_bytes_recv"] = net.bytes_recv
            return CollectorResult(self.name, True, data=data)
        except Exception as exc:
            return CollectorResult(self.name, False, error=str(exc))


class CallbackCollector(BaseCollector):
    """回调采集器：执行用户注册的函数获取指标"""

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        super().__init__(name, config)
        self.callback: Optional[Callable[[], Any]] = config.get("callback")

    def collect(self) -> CollectorResult:
        logger.debug(f"[CallbackCollector.collect] name={self.name}", "data")
        if self.callback is None:
            return CollectorResult(self.name, True, data=None)
        try:
            data = self.callback()
            return CollectorResult(self.name, True, data=data)
        except Exception as exc:
            return CollectorResult(self.name, False, error=str(exc))


class DataCollectorModule:
    """数据采集模块主控"""

    def __init__(self, config: Dict[str, Any]) -> None:
        logger.debug("[DataCollectorModule.__init__] start")
        Validator.require_type(config, dict, "config")
        self.config: Final[Dict[str, Any]] = config
        self.collectors: List[BaseCollector] = []
        self._init_collectors()
        logger.info(f"DataCollectorModule initialized with {len(self.collectors)} collectors", "data")

    def _init_collectors(self) -> None:
        sources = self.config.get("sources", [])
        for source in sources:
            name = source.get("name", f"collector_{len(self.collectors)}")
            kind = source.get("type", "")
            cfg = source.get("config", {})
            collector: Optional[BaseCollector] = None
            if kind == "log":
                collector = LogCollector(name, cfg)
            elif kind == "http":
                collector = HttpCollector(name, cfg)
            elif kind == "file":
                collector = FileCollector(name, cfg)
            elif kind == "system":
                collector = SystemMetricsCollector(name, cfg)
            elif kind == "callback":
                collector = CallbackCollector(name, cfg)
            if collector:
                self.collectors.append(collector)

    def collect_all(self) -> Dict[str, Any]:
        logger.debug("[DataCollectorModule.collect_all] start", "data")
        results: Dict[str, Any] = {}
        for collector in self.collectors:
            result = collector.collect()
            results[collector.name] = result.to_dict()
        logger.info(f"DataCollectorModule collected {len(results)} sources", "data")
        return results

    def register_callback(self, name: str, callback: Callable[[], Any]) -> None:
        self.collectors.append(CallbackCollector(name, {"callback": callback}))

    def get_state(self) -> Dict[str, Any]:
        """获取数据采集模块状态"""
        return {
            "collector_count": len(self.collectors),
            "collector_names": [c.name for c in self.collectors],
        }

    def reset(self) -> None:
        """重置数据采集模块"""
        logger.debug("[DataCollectorModule.reset] called", "data")
        self.collectors.clear()

    def health_check(self) -> bool:
        """健康检查"""
        logger.debug("[DataCollectorModule.health_check] called", "data")
        return all(hasattr(c, "collect") and callable(getattr(c, "collect")) for c in self.collectors)
