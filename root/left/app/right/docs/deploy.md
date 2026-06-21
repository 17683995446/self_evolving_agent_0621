# 部署文档

本文档覆盖自驱永续进化 Agent 系统的本地开发运行、Docker 容器化部署以及生产环境上线检查。

---

## 环境要求

| 依赖 | 版本 | 说明 |
|:---|:---|:---|
| Python | 3.11+ | 运行 Agent 与测试套件 |
| numpy | >=1.24.0 | 数值计算 |
| pyyaml | >=6.0 | 配置解析 |
| psutil | >=5.9.0 | 系统指标采集 |
| pytest | >=7.4.0 | 测试框架 |
| pytest-cov | >=4.1.0 | 覆盖率统计 |
| Docker | 最新稳定版 | 容器化部署（可选） |
| Docker Compose | 最新稳定版 | 一键启动（可选） |

所有 Python 依赖已写入项目根目录 [`requirements.txt`](../../../../../requirements.txt)。

---

## 本地运行

### 开发模式（推荐用于调试）

开发入口为 [`main.py`](../../left/src/main.py)，默认加载 `dev.yaml`，循环间隔 1.0s，最大 1000 轮。

```bash
export PYTHONPATH=/workspace
python -m root.left.app.left.src.main
```

### 生产模式（本地验证）

生产入口为 [`main_deploy.py`](../../left/src/main_deploy.py)，默认根据环境变量 `AGENT_ENV` 加载配置。

```bash
export PYTHONPATH=/workspace
export AGENT_ENV=prod
python -m root.left.app.left.src.main_deploy
```

生产入口特性：

- 注册 `SIGTERM` / `SIGINT` 信号处理器，支持优雅停机。
- 根据 `health_check.enabled` 自动启动 HTTP 服务。
- `max_loops: 0` 在配置中表示无限循环。

### 配置路径说明

`ConfigLoader` 按 `{environment}` 查找文件：

```
cfg/left/dev/{environment}.yaml
```

当前仓库中：

| 环境 | 实际文件路径 |
|:---|:---|
| dev | [cfg/left/dev/dev.yaml](../cfg/left/dev/dev.yaml) |
| test | [cfg/left/dev/test.yaml](../cfg/left/dev/test.yaml) |
| prod | [cfg/right/prd/prod.yaml](../cfg/right/prd/prod.yaml) |

生产部署前，必须将 `cfg/right/prd/prod.yaml` 复制或软链接到 `cfg/left/dev/prod.yaml`，否则 `AGENT_ENV=prod` 启动会报 `ConfigurationError: Config file not found`。

```bash
cp root/left/app/right/cfg/right/prd/prod.yaml \
   root/left/app/right/cfg/left/dev/prod.yaml
```

---

## Docker 部署

### 方式一：使用脚本（推荐）

项目提供 [`scripts/build.sh`](../scripts/build.sh)、[`scripts/start.sh`](../scripts/start.sh)、[`scripts/stop.sh`](../scripts/start.sh) 三个脚本。

```bash
cd /workspace/self_evolving_agent

# 运行测试并构建镜像
./root/left/app/right/scripts/build.sh

# 启动容器
./root/left/app/right/scripts/start.sh

# 健康检查
./root/left/app/right/scripts/health_check.sh

# 停止容器
./root/left/app/right/scripts/stop.sh
```

### 方式二：手动 Docker Compose

```bash
cd /workspace/self_evolving_agent

# 确保生产配置可用
cp root/left/app/right/cfg/right/prd/prod.yaml \
   root/left/app/right/cfg/left/dev/prod.yaml

# 构建并启动
docker-compose -f root/left/app/right/docker-compose.yml up --build -d

# 验证
curl -fsS http://localhost:8080/health
```

### Docker Compose 配置摘要

[docker-compose.yml](../docker-compose.yml) 关键参数：

| 参数 | 值 | 说明 |
|:---|:---|:---|
| 镜像 | `self-evolving-agent:latest` | 由 [Dockerfile](../Dockerfile) 构建 |
| 环境变量 | `AGENT_ENV=prod` | 加载生产配置 |
| 端口映射 | `8080:8080` | HTTP 健康检查端口 |
| 资源限制 | `mem_limit: 1024m` / `cpus: 1.0` | 限制单容器资源 |
| 持久化卷 | `agent_data` / `agent_logs` | 数据与日志持久化 |
| 健康检查 | `curl -f http://localhost:8080/health` | 每 30s 检测一次 |

### Dockerfile 摘要

[Dockerfile](../Dockerfile) 基于 `python:3.11-slim`，主要步骤：

1. 安装 `curl` 与 `requirements.txt` 中的 Python 依赖。
2. 复制源码到 `/app/root/left/app/left/src`。
3. 复制配置到 `/app/root/left/app/right/cfg`。
4. 设置 `PYTHONPATH=/app` 与 `AGENT_ENV=prod`。
5. 默认执行 `python -m root.left.app.left.src.main_deploy`。

### 纯 Docker 运行

```bash
docker run -d --name self_evolving_agent \
  -p 8080:8080 \
  -e AGENT_ENV=prod \
  -e PYTHONPATH=/app \
  -v agent_data:/app/data \
  -v agent_logs:/app/logs \
  --restart unless-stopped \
  --memory=1024m \
  --cpus=1.0 \
  self-evolving-agent:latest
```

---

## 生产检查单

上线前请逐项确认：

| 检查项 | 要求 | 验证命令 |
|:---|:---|:---|
| 全量测试通过 | `b/left/tst/` 全部通过 | `python -m pytest b/left/tst/ -q` |
| 覆盖率达标 | >= 95%（当前 100%） | `pytest --cov=root.left.app.left.src --cov-fail-under=95` |
| 压力测试通过 | `stress/` 与 `final/` 通过 | `python -m pytest b/left/tst/stress/ b/left/tst/final/ -v` |
| 生产配置就位 | `cfg/left/dev/prod.yaml` 存在 | `ls root/left/app/right/cfg/left/dev/prod.yaml` |
| Docker 镜像可构建 | 无构建错误 | `./root/left/app/right/scripts/build.sh` |
| 健康检查可达 | `/health` 返回 200 | `curl -fsS http://localhost:8080/health` |
| 资源限制生效 | 容器内存 / CPU 受限 | `docker stats self_evolving_agent` |
| 日志持久化 | `agent_logs` 卷挂载 | `docker volume inspect agent_logs` |
| 优雅停机 | `SIGTERM` 后资源释放 | `docker stop -t 30 self_evolving_agent` |

---

## 故障排查

### 启动时报 `Config file not found: cfg/left/dev/prod.yaml`

**原因**：`AGENT_ENV=prod` 时 `ConfigLoader` 在 `cfg/left/dev/` 目录下查找 `prod.yaml`，但生产配置文件当前位于 `cfg/right/prd/prod.yaml`。

**解决**：

```bash
cp root/left/app/right/cfg/right/prd/prod.yaml \
   root/left/app/right/cfg/left/dev/prod.yaml
```

### `/health` 返回 503

**原因**：Agent 尚未完成初始化或主循环已停止。

**解决**：

1. 查看容器日志：`docker logs self_evolving_agent`
2. 确认 `health_check.enabled` 为 `true`。
3. 等待容器 `start_period`（10s）结束后再检查。

### 循环不推进或卡在 Phase 1

**原因**：安全缺口 `safe_gap > 0.7` 触发暂停。

**解决**：检查系统 CPU / 内存是否过高，或调整 `phase1.drive.safe.thresholds` 中的临界值。

### Docker 构建失败

**原因**：`requirements.txt` 不在构建上下文根目录，或 Docker 守护进程不可达。

**解决**：

1. 确保在项目根目录 `/workspace/self_evolving_agent` 执行构建。
2. 验证 Docker 服务状态：`docker info`
3. 手动构建：`docker build -f root/left/app/right/Dockerfile -t self-evolving-agent:latest .`

### 测试覆盖率达到 100% 但生产运行异常

**原因**：生产配置与开发配置差异较大（如 `loop_interval`、`max_loops`、`health_check` 等）。

**解决**：对比 `dev.yaml` 与 `prod.yaml`，确认所有必填字段完整且路径正确。

---

## 运维命令速查

```bash
# 查看日志
docker logs -f self_evolving_agent

# 查看资源使用
docker stats self_evolving_agent

# 重启服务
./root/left/app/right/scripts/stop.sh
./root/left/app/right/scripts/start.sh

# 手动触发健康检查
./root/left/app/right/scripts/health_check.sh

# 进入容器排查
docker exec -it self_evolving_agent /bin/bash
```
