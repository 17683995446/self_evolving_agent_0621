# 用户手册

本文档面向最终用户与开发者，介绍如何快速启动、配置、监控和扩展自驱永续进化 Agent 系统。

---

## 快速开始

### 1. 克隆并安装依赖

```bash
cd /workspace/self_evolving_agent
pip install -r requirements.txt
```

### 2. 启动开发版 Agent

```bash
export PYTHONPATH=/workspace
python -m root.left.app.left.src.main
```

启动后控制台会输出每轮循环日志：

```
INFO  [main] === Loop 1 started ===
INFO  [sensory] Perceived state: metrics=2 features=2
INFO  [predict] Predictions: low=2 mid=2 high=0
INFO  [drive] Drive computed: scenario=normal total_reward=0.8234
INFO  [main] Phase1 completed performance=0.8234
...
```

按 `Ctrl+C` 可停止 Agent。

### 3. 启动生产版 Agent（本地验证）

```bash
export PYTHONPATH=/workspace
export AGENT_ENV=prod
python -m root.left.app.left.src.main_deploy
```

生产版默认启用 HTTP 健康检查，可通过以下命令验证：

```bash
curl -fsS http://localhost:8080/health
```

### 4. Docker 一键启动

```bash
cd /workspace/self_evolving_agent

# 生产配置必须位于 ConfigLoader 可找到的路径
cp root/left/app/right/cfg/right/prd/prod.yaml \
   root/left/app/right/cfg/left/dev/prod.yaml

./root/left/app/right/scripts/build.sh
./root/left/app/right/scripts/start.sh
./root/left/app/right/scripts/health_check.sh
```

---

## 配置文件说明

系统使用 YAML 配置文件，按环境隔离：

| 文件 | 环境 | 用途 |
|:---|:---|:---|
| [cfg/left/dev/dev.yaml](../cfg/left/dev/dev.yaml) | 开发 | 循环快、日志详细、便于调试 |
| [cfg/left/dev/test.yaml](../cfg/left/dev/test.yaml) | 测试 | 循环短、数据库独立、适合 CI |
| [cfg/right/prd/prod.yaml](../cfg/right/prd/prod.yaml) | 生产 | 循环慢、资源限制严格、HTTP 监控启用 |

### 配置结构

```yaml
phase1:               # Phase 1：基础自驱闭环
  sensory:            # 感知模块
    collectors:
      system:         # 系统指标采集器
        enabled: true
        interval: 1.0
        history_size: 1000
    normalizer:
      feature_order: [cpu_percent, memory_percent]
    noise_filter:
      ema_alpha: 0.3
  drive:              # 驱力引擎
    safe:             # 安全驱力
      risk_weights: { cpu_high: 0.2, memory_high: 0.3 }
      thresholds: { cpu_critical: 80.0, memory_critical: 85.0 }
    gain:             # 收益驱力
      error_history_size: 100
    eff:              # 能效驱力
      agent_cpu_limit: 20.0
      agent_memory_limit: 20.0
    weights:          # 三驱力初始权重
      safe_weight: 0.4
      gain_weight: 0.4
      eff_weight: 0.2
  prediction:         # 预测模块
    low: { ema_alpha: 0.3, trend_beta: 0.1, horizon: 1 }
    mid: { window_size: 10, horizon: 3 }
    high: { n_clusters: 5, horizon: 10 }

phase2:               # Phase 2：完整自主闭环
  task_pool:
    pool: { max_size: 100 }
  decision:
    exploration: { base_exploration_ratio: 0.3 }
  memory:
    cache: { max_cache_size: 1000 }
    store: { db_path: agent_memory.db }

phase3:               # Phase 3：进化与回滚
  evolution:
    snapshot: { max_snapshots: 5 }
    refactor: { error_threshold: 0.3, stagnation_rounds: 100 }
    gap_threshold: 0.1
    rollback_threshold: 0.1

loop_interval: 1.0    # 每轮循环间隔（秒）
max_loops: 1000       # 最大循环次数（0 表示无限）
log_level: INFO       # 日志级别
```

### 常用配置调整

| 场景 | 配置项 | 建议值 |
|:---|:---|:---|
| 加快调试 | `loop_interval` | `0.1` |
| 延长运行 | `max_loops` | `0` |
| 降低安全阈值 | `phase1.drive.safe.thresholds.cpu_critical` | `90.0` |
| 增强探索 | `phase2.decision.exploration.base_exploration_ratio` | `0.4` |
| 更保守回滚 | `phase3.evolution.rollback_threshold` | `0.05` |

---

## 指标解读

### 控制台日志关键字段

| 字段 | 示例 | 含义 |
|:---|:---|:---|
| `performance` | `0.8234` | Phase 1 综合性能得分，越高越好 |
| `scenario` | `normal` | 当前场景：`normal` / `stable_idle` / `resource_tight` / `emergency` |
| `total_reward` | `0.8234` | 安全、收益、能效三驱力平均奖励 |
| `tasks` | `total=2` | Phase 2 生成的任务总数 |
| `should_rollback` | `False` | Phase 3 是否触发配置回滚 |

### HTTP 指标

| 端点 | 关键字段 | 说明 |
|:---|:---|:---|
| `/health` | `status` | `healthy` 表示主循环正在运行 |
| `/metrics` | `loop_count` | 循环计数，长期应保持增长 |
| `/state` | `config` | 当前生效配置，可用于审计 |

### 性能得分计算

```
performance = total_reward * 0.7 + (1 - error_rate) * 0.3
```

- `total_reward` 来自驱力引擎，反映系统整体健康度。
- `error_rate` 来自预测模块，反映预测误差。
- 得分范围理论为 `[0, 1]`，实际受限于指标噪声。

---

## 运行测试

### 全量测试

```bash
python -m pytest b/left/tst/ -q
```

### 指定模块测试

```bash
python -m pytest b/left/tst/core_mod/test_sensory.py -v
python -m pytest b/left/tst/core_mod/test_drive.py -v
```

### 覆盖率测试

```bash
python -m pytest b/left/tst/ \
  --cov=root.left.app.left.src \
  --cov-report=term-missing \
  --cov-fail-under=95
```

### 压力测试

```bash
python -m pytest b/left/tst/stress/ -v
```

### 稳定性与最终验收测试

```bash
python -m pytest b/left/tst/final/ -v
```

当前测试成就：941 个测试通过，代码覆盖率 100%。

---

## 如何扩展：插件开发指南

系统通过 [`utils_main/interfaces.py`](../../left/src/utils_main/interfaces.py) 提供插件化能力。

### 步骤 1：创建模块文件

在 `root/left/app/left/src/core_mod/` 下新建文件，例如 `my_plugin.py`：

```python
from typing import Any, Dict
from root.left.app.left.src.utils_main.interfaces import BaseModule

class MyPlugin(BaseModule):
    def __init__(self, config: Dict[str, Any]) -> None:
        super().__init__(config)
        self.value = config.get("value", 0)

    def get_state(self) -> Dict[str, Any]:
        return {"value": self.value}

    def reset(self) -> None:
        self.value = 0
```

### 步骤 2：动态加载

```python
from root.left.app.left.src.utils_main.interfaces import ModuleRegistry, PluginLoader

registry = ModuleRegistry()
loader = PluginLoader(registry)
loader.load_from_path(
    name="my_plugin",
    module_path="/workspace/self_evolving_agent/root/left/app/left/src/core_mod/my_plugin.py",
    class_name="MyPlugin"
)
```

### 步骤 3：通过配置组装

```python
from root.left.app.left.src.utils_main.interfaces import DIContainer, ConfigAssembler

container = DIContainer(registry)
assembler = ConfigAssembler(registry, container)
blueprint = {
    "my_slot": {"module": "my_plugin", "config": {"value": 42}}
}
modules = assembler.assemble(blueprint)
```

### 扩展规范

- 所有类必须继承 `BaseModule` 或实现 `ModuleProtocol`。
- 必须实现 `get_state()`、`reset()`、`health_check()`。
- 函数尽量不超过 7 行，强制类型注解。
- 新增模块必须配套单元测试，覆盖正常值 / 空入参 / 边界极值 / 非法格式四类用例。

---

## 核心概念

- **缺口（Gap）**：目标状态与当前状态的差值，永远不为 0，是系统自驱演进的动力来源。
- **驱力（Drive）**：安全 / 收益 / 能效三大原生驱力，分别对应系统稳定性、预测准确性和资源效率。
- **探索（Explore）**：30% 概率随机选择任务，避免陷入局部最优；紧急场景下自动降为 0%。
- **利用（Exploit）**：70% 概率按缺口加权优先级选择最优任务。
- **进化（Evolution）**：Phase 3 根据性能历史自动调整配置，并通过快照机制实现回滚。
- **回滚（Rollback）**：当性能下降超过阈值时，恢复到历史最佳配置快照。

---

## 常用操作速查

```bash
# 开发运行
export PYTHONPATH=/workspace
python -m root.left.app.left.src.main

# 生产运行
export PYTHONPATH=/workspace
export AGENT_ENV=prod
python -m root.left.app.left.src.main_deploy

# 健康检查
curl -fsS http://localhost:8080/health

# 全量测试
python -m pytest b/left/tst/ -q

# 覆盖率
pytest --cov=root.left.app.left.src --cov-fail-under=95

# Docker 启动
docker-compose -f root/left/app/right/docker-compose.yml up --build -d
```
