# 模块接口文档

## SensoryModule

### perceive() -> Dict[str, Any]
采集环境状态，返回标准化特征向量。

### get_current_state() -> Optional[Dict[str, Any]]
获取当前状态。

## DriveEngine

### compute(state, error, agent_metrics) -> Dict[str, Any]
计算驱力状态，返回奖励和缺口。

### should_interrupt(drive_state) -> bool
判断是否需要中断当前任务。

## PredictionModule

### predict(state) -> Dict[PredictionLevel, List[Dict]]
生成三层预测结果。

### evaluate(predictions, actual) -> List[Dict]
评估预测误差。

## TaskPoolModule

### generate_and_enqueue(drive_state) -> int
生成任务并入队，返回任务数量。

### get_next_task() -> Optional[Task]
获取下一个待执行任务。

## DecisionModule

### decide(task_pool, drive_state, history, loop, cpu, memory) -> Dict[str, Any]
做出决策，返回选择的任务。

## MemoryModule

### record_state(loop_id, state, drive, performance) -> None
记录状态到缓存和数据库。

### get_recent_states(count) -> List[Dict]
获取最近状态记录。

## EvolutionModule

### evolve(config, history, predictions, state, error_rate) -> Dict[str, Any]
执行进化逻辑，返回是否调整配置。

### should_rollback(performance) -> bool
判断是否需要回滚。
