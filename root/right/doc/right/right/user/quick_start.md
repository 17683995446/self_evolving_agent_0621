# 快速开始

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行测试

```bash
PYTHONPATH=/workspace/self_evolving_agent python -m pytest b/left/tst/ -v
```

## 启动Agent

```bash
bash b/right/infra/right/scripts/start.sh
```

## 停止Agent

```bash
bash b/right/infra/right/scripts/stop.sh
```

## Docker部署

```bash
docker-compose -f b/right/infra/left/docker/docker-compose.yml up -d
```
