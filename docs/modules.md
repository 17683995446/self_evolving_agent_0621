# 模块清单

本文档列出自驱永续进化 Agent 系统的所有模块，包括核心模块、基础设施模块和入口点。

系统采用满二叉树目录规范，所有源码位于 `root/left/app/left/src/`。

## 核心模块（Core Modules）

当前已实现 29 个核心源码模块，架构预留第 30 个扩展槽位，可通过 [`interfaces.py`](../root/left/app/left/src/utils_main/interfaces.py) 中的 `PluginLoader` 动态加载。

### Phase 1：基础自驱闭环

| 模块名称 | 文件路径 | 功能简述 | 关键类 |
|:---|:---|:---|:---|
| 环境感知 | [root/left/app/left/src/core_mod/sensory.py](../root/left/app/left/src/core_mod/sensory.py) | 采集系统指标、标准化处理、噪声过滤 | `SensoryModule` |
| 驱力引擎 | [root/left/app/left/src/core_mod/drive.py](../root/left/app/left/src/core_mod/drive.py) | 计算安全、收益、能效三大驱力与动态权重 | `DriveEngine` |
| 预测模块 | [root/left/app/left/src/core_mod/predict.py](../root/left/app/left/src/core_mod/predict.py) | 三层预测：低层 EMA、中层岭回归、高层聚类 | `PredictionModule` |
| Phase 1 核心 | [root/left/app/left/src/core_mod/phase_one.py](../root/left/app/left/src/core_mod/phase_one.py) | 整合感知、驱力、预测，输出性能评估 | `PhaseOneCore` |

### Phase 2：完整自主闭环

| 模块名称 | 文件路径 | 功能简述 | 关键类 |
|:---|:---|:---|:---|
| 任务池 | [root/left/app/left/src/core_mod/task.py](../root/left/app/left/src/core_mod/task.py) | 任务生成、优先级调度、执行与重试 | `TaskPoolModule` |
| 决策模块 | [root/left/app/left/src/core_mod/decide.py](../root/left/app/left/src/core_mod/decide.py) | 70% 利用 + 30% 探索双决策机制 | `DecisionModule` |
| 记忆模块 | [root/left/app/left/src/core_mod/memory.py](../root/left/app/left/src/core_mod/memory.py) | 状态缓存与 SQLite 持久化 | `MemoryModule` |
| Phase 2 核心 | [root/left/app/left/src/core_mod/phase_two.py](../root/left/app/left/src/core_mod/phase_two.py) | 整合任务生成、决策、记忆记录 | `PhaseTwoCore` |

### Phase 3：进化与回滚

| 模块名称 | 文件路径 | 功能简述 | 关键类 |
|:---|:---|:---|:---|
| 进化模块 | [root/left/app/left/src/core_mod/evolve.py](../root/left/app/left/src/core_mod/evolve.py) | 快照管理、重构引擎、特征引擎、评审引擎 | `EvolutionModule` |
| Phase 3 核心 | [root/left/app/left/src/core_mod/phase_three.py](../root/left/app/left/src/core_mod/phase_three.py) | 整合进化、性能历史、回滚判断 | `PhaseThreeCore` |

### 认知增强层

| 模块名称 | 文件路径 | 功能简述 | 关键类 |
|:---|:---|:---|:---|
| 自适应学习 | [root/left/app/left/src/core_mod/learn.py](../root/left/app/left/src/core_mod/learn.py) | 增量 SGD、自动特征工程、模型选择、过拟合检测 | `AdaptiveLearner` |
| 因果推理 | [root/left/app/left/src/core_mod/causal.py](../root/left/app/left/src/core_mod/causal.py) | 因果图、干预模拟、反事实分析、ATE 估计 | `CausalModule` |
| 元学习 | [root/left/app/left/src/core_mod/meta.py](../root/left/app/left/src/core_mod/meta.py) | 任务嵌入、元参数优化、迁移学习、快速适应 | `MetaLearner` |
| 对抗鲁棒性 | [root/left/app/left/src/core_mod/adversarial.py](../root/left/app/left/src/core_mod/adversarial.py) | 对抗扰动、防御平滑、纳什均衡、欺骗检测 | `AdversarialModule` |
| 形式化验证 | [root/left/app/left/src/core_mod/verify.py](../root/left/app/left/src/core_mod/verify.py) | 安全不变式、活性属性、决策追踪、特征归因 | `VerificationModule` |
| 分层抽象 | [root/left/app/left/src/core_mod/abstract.py](../root/left/app/left/src/core_mod/abstract.py) | 概念节点、模式聚类、分层抽象、概念形成 | `AbstractionModule` |
| 价值对齐 | [root/left/app/left/src/core_mod/alignment.py](../root/left/app/left/src/core_mod/alignment.py) | 价值评估、伦理约束、偏差检测、公平性审计 | `AlignmentModule` |

### 协作扩展层

| 模块名称 | 文件路径 | 功能简述 | 关键类 |
|:---|:---|:---|:---|
| 多 Agent 协作 | [root/left/app/left/src/core_mod/collab.py](../root/left/app/left/src/core_mod/collab.py) | 消息总线、状态同步、任务分片、Gossip 配置传播 | `CollaborationModule` |
| 外部系统集成 | [root/left/app/left/src/core_mod/external.py](../root/left/app/left/src/core_mod/external.py) | HTTP 客户端、幂等性存储、消息队列、文件系统适配 | `ExternalIntegrationModule` |
| 安全边界 | [root/left/app/left/src/core_mod/security.py](../root/left/app/left/src/core_mod/security.py) | 输入消毒、敏感数据过滤、速率限制、资源守卫 | `SecurityModule` |
| 运维监控 | [root/left/app/left/src/core_mod/ops.py](../root/left/app/left/src/core_mod/ops.py) | 健康检查、指标收集、依赖检查、优雅停机、热更新 | `OpsModule` |
| 分布式共识 | [root/left/app/left/src/core_mod/consensus.py](../root/left/app/left/src/core_mod/consensus.py) | 类 Raft 共识、拜占庭容错、冲突解析 | `DistributedStateModule` |
| 社交智能 | [root/left/app/left/src/core_mod/social.py](../root/left/app/left/src/core_mod/social.py) | 情感识别、社交情境分析、共情模型、关系追踪 | `SocialIntelligenceModule` |

### 感知融合层

| 模块名称 | 文件路径 | 功能简述 | 关键类 |
|:---|:---|:---|:---|
| 跨模态感知融合 | [root/left/app/left/src/core_mod/multimodal.py](../root/left/app/left/src/core_mod/multimodal.py) | 跨模态编码、时间对齐、加权融合 | `SensorFusionModule` |
| 复杂环境模拟 | [root/left/app/left/src/core_mod/simulate.py](../root/left/app/left/src/core_mod/simulate.py) | 环境模拟、沙箱推演、反事实规划、风险评估 | `SimulationModule` |
| 神经符号混合推理 | [root/left/app/left/src/core_mod/hybrid.py](../root/left/app/left/src/core_mod/hybrid.py) | 逻辑解析、符号推理、神经符号桥接、规则归纳 | `HybridInferenceModule` |
| 自主目标生成 | [root/left/app/left/src/core_mod/autonomous.py](../root/left/app/left/src/core_mod/autonomous.py) | 内在奖励、好奇心驱动、目标生成、动机涌现 | `AutonomousGoalModule` |
| 自我建模 | [root/left/app/left/src/core_mod/selfaware.py](../root/left/app/left/src/core_mod/selfaware.py) | 自我模型、置信度估计、内省引擎、元认知控制 | `SelfAwarenessModule` |
| 终身学习 | [root/left/app/left/src/core_mod/lifelong.py](../root/left/app/left/src/core_mod/lifelong.py) | 经验回放、弹性权重巩固、知识蒸馏、渐进神经网络 | `LifelongLearningModule` |

### 扩展槽位

| 模块名称 | 文件路径 | 功能简述 | 关键类 |
|:---|:---|:---|:---|
| 扩展槽位 | `root/left/app/left/src/core_mod/` | 预留模块化扩展位置，可通过 `PluginLoader.load_from_path` 动态加载外部模块 | 自定义继承 `BaseModule` |

## 基础设施模块（Utils）

| 模块名称 | 文件路径 | 功能简述 | 关键类 |
|:---|:---|:---|:---|
| 接口标准与插件系统 | [root/left/app/left/src/utils_main/interfaces.py](../root/left/app/left/src/utils_main/interfaces.py) | 定义 `ModuleProtocol`、`BaseModule`、模块注册表、依赖注入容器、配置组装器、插件加载器 | `ModuleRegistry`、`DIContainer`、`ConfigAssembler`、`PluginLoader` |
| 异常体系 | [root/left/app/left/src/utils_main/exceptions.py](../root/left/app/left/src/utils_main/exceptions.py) | 严格异常层次结构，覆盖配置、验证、感知、决策、记忆、进化、安全等错误 | `AgentException`、`ValidationError`、`ConfigurationError` |
| 全局常量 | [root/left/app/left/src/utils_main/constants.py](../root/left/app/left/src/utils_main/constants.py) | 枚举定义：指标类型、驱力类型、任务类型、任务状态、预测层级、场景类型、调整类型、错误码 | `MetricType`、`DriveType`、`TaskType`、`PredictionLevel`、`ErrorCode` |
| 严格验证器 | [root/left/app/left/src/utils_main/validators.py](../root/left/app/left/src/utils_main/validators.py) | 类型、非空、范围、正数、非负等基础校验，以及三阶段配置验证 | `Validator`、`ConfigValidator` |
| 日志系统 | [root/left/app/left/src/utils_main/logger.py](../root/left/app/left/src/utils_main/logger.py) | Agent 专用单例日志器，支持模块前缀 | `AgentLogger` |
| 配置加载器 | [root/left/app/left/src/utils_main/config_loader.py](../root/left/app/left/src/utils_main/config_loader.py) | 按环境加载 YAML 配置文件 | `ConfigLoader` |

## 入口点

| 模块名称 | 文件路径 | 功能简述 | 关键类/函数 |
|:---|:---|:---|:---|
| 开发入口 | [root/left/app/left/src/main.py](../root/left/app/left/src/main.py) | 开发版 Agent 调度入口，加载 dev 配置并运行三阶段循环 | `SelfEvolvingAgent`、`main()` |
| 生产入口 | [root/left/app/left/src/main_deploy.py](../root/left/app/left/src/main_deploy.py) | 生产级入口，支持信号处理、HTTP 健康服务、优雅停机 | `ProductionAgent`、`main()` |
| 部署服务 | [root/left/app/left/src/deploy_server.py](../root/left/app/left/src/deploy_server.py) | 暴露 `/health`、`/metrics`、`/state` HTTP 端点 | `DeployServer`、`HealthHandler` |

## 模块扩展指南

1. 新建模块文件于 `root/left/app/left/src/core_mod/`。
2. 继承 `BaseModule` 或实现 `ModuleProtocol`。
3. 实现 `get_state()`、`reset()`、`health_check()` 生命周期方法。
4. 通过 `PluginLoader.load_from_path(name, module_path, class_name)` 在运行时加载。
5. 在配置文件中声明模块插槽，由 `ConfigAssembler` 自动组装。
