# API 文档

本文档描述自驱永续进化 Agent 系统暴露的两类接口：

1. **HTTP 端点**：由 [`deploy_server.py`](../../left/src/deploy_server.py) 提供，用于健康检查、指标采集与状态查询。
2. **Python 类 API**：由 [`main.py`](../../left/src/main.py) 与 [`main_deploy.py`](../../left/src/main_deploy.py) 提供，用于在代码中驱动 Agent 生命周期。

---

## HTTP 端点

生产入口 `ProductionAgent` 启动后会根据配置自动启动 HTTP 服务，默认监听 `0.0.0.0:8080`。

| 端点 | 方法 | 状态码 | 说明 |
|:---|:---:|:---:|:---|
| `/health` | GET | 200 / 503 | Agent 是否正在运行 |
| `/metrics` | GET | 200 | 当前循环次数与运行状态 |
| `/state` | GET | 200 / 503 / 500 | Agent 完整状态（配置、循环计数、运行标志） |

### `/health`

判断 Agent 主循环是否健康运行。

**请求示例**

```bash
curl -fsS http://localhost:8080/health
```

**响应模式（HTTP 200）**

```json
{
  "status": "healthy",
  "loop_count": 42
}
```

**响应模式（HTTP 503）**

```json
{
  "status": "unhealthy",
  "loop_count": 0
}
```

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `status` | string | `healthy` 或 `unhealthy` |
| `loop_count` | int | 已完成的循环次数 |

### `/metrics`

返回最小化运行指标，适合 Prometheus / Grafana 等外部采集器轮询。

**请求示例**

```bash
curl -fsS http://localhost:8080/metrics
```

**响应模式（HTTP 200）**

```json
{
  "loop_count": 42,
  "running": true
}
```

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `loop_count` | int | 已完成的循环次数 |
| `running` | bool | Agent 是否处于运行状态 |

### `/state`

返回 `ProductionAgent.get_state()` 的完整结果，包含当前配置与运行状态。

**请求示例**

```bash
curl -fsS http://localhost:8080/state
```

**响应模式（HTTP 200）**

```json
{
  "running": true,
  "loop_count": 42,
  "config": {
    "phase1": { ... },
    "phase2": { ... },
    "phase3": { ... },
    "loop_interval": 5.0,
    "max_loops": 0,
    "log_level": "INFO",
    "health_check": { "enabled": true, "port": 8080, "path": "/health" },
    "metrics": { "enabled": true, "port": 8080, "path": "/metrics" }
  }
}
```

**错误响应（HTTP 503）**

```json
{
  "error": "agent not initialized"
}
```

**错误响应（HTTP 500）**

```json
{
  "error": "<异常消息>"
}
```

---

## Python 类 API

### `SelfEvolvingAgent`

开发版 Agent 主控类，位于 [`main.py`](../../left/src/main.py)。

#### `__init__(config=None)`

初始化 Agent。`config` 为 `None` 时自动加载 `dev` 环境配置。

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `config` | `Dict[str, Any] \| None` | `None` | 完整配置字典，结构与 `dev.yaml` 一致 |

#### `run(max_loops=None)`

启动主循环。

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `max_loops` | `int \| None` | `None` | `None` 表示无限循环；否则达到次数后自动停止 |

#### `stop()`

将 `running` 标志置为 `False`，使主循环在下次迭代时退出。

#### 使用示例

```python
from root.left.app.left.src.main import SelfEvolvingAgent

agent = SelfEvolvingAgent()
try:
    agent.run(max_loops=100)
except KeyboardInterrupt:
    agent.stop()
```

---

### `ProductionAgent`

生产级 Agent 主控类，位于 [`main_deploy.py`](../../left/src/main_deploy.py)。

#### `__init__(config=None)`

初始化生产 Agent。`config` 为 `None` 时读取环境变量 `AGENT_ENV` 加载对应配置（默认 `dev`）。

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `config` | `Dict[str, Any] \| None` | `None` | 完整配置字典；生产环境建议通过 `AGENT_ENV=prod` 加载 |

#### `start_server()`

根据配置启动 HTTP 健康服务。仅当 `health_check.enabled` 为 `true` 时生效。

#### `run(max_loops=None)`

启动 HTTP 服务后进入主循环，并注册 `SIGTERM` / `SIGINT` 信号处理器实现优雅停机。

| 参数 | 类型 | 默认值 | 说明 |
|:---|:---|:---|:---|
| `max_loops` | `int \| None` | `None` | `None` 表示无限循环；配置文件中 `max_loops: 0` 同样视为无限 |

#### `stop()`

停止主循环并关闭 HTTP 服务。

#### `get_state()`

返回当前运行状态字典，字段与 `/state` HTTP 端点一致。

#### 使用示例

```python
import os
from root.left.app.left.src.main_deploy import ProductionAgent

os.environ["AGENT_ENV"] = "prod"
agent = ProductionAgent()
agent.run()
```

---

## Phase 核心 API

### `PhaseOneCore`

执行 Phase 1：感知 → 驱力 → 预测 → 性能评估。

#### `step() -> Dict[str, Any]`

返回结果结构：

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `state` | `Dict[str, Any]` | 感知模块输出的系统状态 |
| `predictions` | `Dict[PredictionLevel, List[Dict]]` | 低 / 中 / 高三层预测结果 |
| `drive_state` | `Dict[str, Any]` | 驱力引擎输出的缺口、权重、场景、奖励 |
| `performance` | `float` | 综合性能得分 |

---

### `PhaseTwoCore`

执行 Phase 2：任务生成 → 决策 → 记忆记录。

#### `step(phase1_result, loop_count, agent_cpu, agent_memory) -> Dict[str, Any]`

| 参数 | 类型 | 说明 |
|:---|:---|:---|
| `phase1_result` | `Dict[str, Any]` | Phase 1 输出 |
| `loop_count` | `int` | 当前循环计数 |
| `agent_cpu` | `float` | Agent 自身 CPU 占用百分比 |
| `agent_memory` | `float` | Agent 自身内存占用百分比 |

返回结果结构：

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `decision` | `Dict[str, Any]` | 是否探索、选中任务、可用资源容量 |
| `task_pool_snapshot` | `Dict[str, int]` | 任务池总数 / pending / running / completed / failed / frozen |
| `memory_recent` | `List[Dict]` | 最近 10 条记忆记录 |

#### `should_pause(phase1_result) -> bool`

当安全缺口过大时返回 `True`，建议暂停本次循环。

---

### `PhaseThreeCore`

执行 Phase 3：进化 → 快照 → 评审。

#### `step(current_config, phase1_result, phase2_result) -> Dict[str, Any]`

| 参数 | 类型 | 说明 |
|:---|:---|:---|
| `current_config` | `Dict[str, Any]` | 当前生效配置 |
| `phase1_result` | `Dict[str, Any]` | Phase 1 输出 |
| `phase2_result` | `Dict[str, Any]` | Phase 2 输出 |

返回结果结构：

| 字段 | 类型 | 说明 |
|:---|:---|:---|
| `evolution_result` | `Dict[str, Any]` | 是否调整、新配置、预测 Gap、快照数量 |
| `performance_history` | `List[float]` | 历史性能得分 |
| `should_rollback` | `bool` | 是否触发回滚 |
| `best_snapshot` | `Dict[str, Any] \| None` | 最佳快照（含配置与性能） |

---

## curl 命令速查

```bash
# 健康检查
curl -fsS http://localhost:8080/health

# 运行指标
curl -fsS http://localhost:8080/metrics

# 完整状态
curl -fsS http://localhost:8080/state

# 带超时与重试的健康检查
for i in {1..5}; do
  curl -fsS http://localhost:8080/health && break
  sleep 2
done
```

---

## 错误码与异常

| 异常类 | 来源 | 典型场景 |
|:---|:---|:---|
| `AgentException` | `main.py` / `main_deploy.py` | 主循环捕获到的 Agent 级错误 |
| `ValidationError` | `validators.py` | 配置或入参校验失败 |
| `ConfigurationError` | `config_loader.py` | 配置文件缺失或解析失败 |
| `DecisionException` | `decide.py` | 资源限制超限 |
| `EvolutionException` | `evolve.py` | 进化过程中出现非法状态 |
| `TaskPoolException` | `task.py` | 任务池操作异常 |

所有异常定义见 [`utils_main/exceptions.py`](../../left/src/utils_main/exceptions.py)。
