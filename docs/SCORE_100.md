# 100-Point Quality Gate

本文件定义自驱永续进化 Agent 系统的 100 分质量门禁标准，并记录当前成就状态。

---

## 评分维度与当前状态

`b/left/tst/final/test_final_score.py` 按以下 7 个维度自动评分，目标为总分 >= 95。

| 维度 | 满分 | 标准 | 当前状态 | 是否达标 |
|:---|:---:|:---|:---|:---:|
| 测试通过 | 30 | 非 final 目录下测试用例 >= 941 个通过 | 959 个测试通过，得 30/30 | 是 |
| 代码覆盖率 | 20 | 覆盖率 >= 95% | 覆盖率 96%，得 20/20 | 是 |
| 压力测试 | 15 | `stress_test_*.py` 全部通过 | 59 个压力测试全部通过，得 15/15 | 是 |
| Docker 部署就绪 | 10 | `docker-compose.yml` 存在或镜像已构建 | `root/left/app/right/docker-compose.yml` 有效 | 是 |
| 文档完整 | 10 | README + 系统架构 + 部署 + 用户手册存在且非空 | 全部文档已就绪，得 10/10 | 是 |
| 稳定性报告 | 10 | `reports/five_hour_report.json` 存在且非空 | 报告已生成，得 10/10 | 是 |
| 无严重 lint 问题 | 5 | `ruff check src` 通过 | 0 个 lint 错误，得 5/5 | 是 |
| **合计** | **100** | — | **当前 100/100** | — |

---

## 详细说明

### 1. 测试通过（30/30）

评分命令：

```bash
python -m pytest -q --tb=no --ignore=b/left/tst/final
```

当前结果：959 个测试通过，满足 >= 941 的门禁要求。

### 2. 代码覆盖率（20/20）

评分命令：

```bash
python -m pytest --cov=root.left.app.left.src --cov-report=term -q --tb=no --ignore=b/left/tst/final
```

当前结果：覆盖率 96%，满足 >= 95% 的门禁要求。

README 徽章显示覆盖率 96%。

### 3. 压力测试（15/15）

评分命令：

```bash
python -m pytest b/left/tst/stress_test_*.py -q --tb=no
```

当前结果：59 个压力测试全部通过。可通过以下命令单独运行各类压力测试：

```bash
python -m pytest b/left/tst/stress_test_quick.py -v
python -m pytest b/left/tst/stress_test_long_run.py -v
python -m pytest b/left/tst/stress_test_consistency_perf.py -v
python -m pytest b/left/tst/stress_test_fault_tolerance.py -v
python -m pytest b/left/tst/stress_test_long_term_evolution.py -v
```

### 4. Docker 部署就绪（10/10）

检查项：

- [root/left/app/right/docker-compose.yml](../root/left/app/right/docker-compose.yml) 存在且有效。
- [root/left/app/right/Dockerfile](../root/left/app/right/Dockerfile) 存在。

### 5. 文档完整（10/10）

评分器检查以下文档：

| 文档 | 路径 | 状态 |
|:---|:---|:---:|
| 项目总览 | [README.md](../README.md) | 已就绪 |
| 系统架构 | [root/right/doc/left/design/system_design.md](../root/right/doc/left/design/system_design.md) | 已就绪 |
| 架构设计 | [root/left/app/right/docs/architecture.md](../root/left/app/right/docs/architecture.md) | 已就绪 |
| 部署手册 | [root/left/app/right/docs/deploy.md](../root/left/app/right/docs/deploy.md) | 已就绪 |
| 用户手册 | [root/left/app/right/docs/user.md](../root/left/app/right/docs/user.md) | 已就绪 |

此外，本次文档增强还补充了：

- [docs/modules.md](modules.md)：30 个核心模块完整清单。
- [docs/SCORE_100.md](SCORE_100.md)：本评分报告。
- [root/left/app/right/docs/api.md](../root/left/app/right/docs/api.md)：HTTP 端点与 Python API 详细说明。

### 6. 稳定性报告（10/10）

报告文件：[reports/five_hour_report.json](../reports/five_hour_report.json)

当前报告结果：`passed: true`

关键指标：

- 运行时长：300 秒（默认验证模式）
- 完成循环：263 次
- 错误数：0
- 内存增长：约 99 MB

完整 5 小时（18000 秒）连续运行可通过以下命令启动：

```bash
STABILITY_DURATION_SECONDS=18000 python -m pytest b/left/tst/final/test_five_hour_stability.py -v
```

### 7. 无严重 lint 问题（5/5）

评分命令：

```bash
python -m ruff check root/left/app/left/src
```

当前结果：0 个 lint 错误，`ruff check` 全部通过。

---

## 达标结论

当前 `test_final_score.py` 评分为 **100/100**，已达成 100 分目标。全部 7 个质量维度均达标：

| 维度 | 得分 |
|:---|:---:|
| 测试通过 | 30/30 |
| 代码覆盖率 | 20/20 |
| 压力测试 | 15/15 |
| Docker 部署就绪 | 10/10 |
| 文档完整 | 10/10 |
| 稳定性报告 | 10/10 |
| 无严重 lint 问题 | 5/5 |
| **合计** | **100/100** |

---

## 验证命令汇总

```bash
# 测试通过数（排除 final，避免递归评分）
python -m pytest -q --tb=no --ignore=b/left/tst/final

# 覆盖率（需先安装 pytest-cov）
pip install pytest-cov>=4.1.0
python -m pytest --cov=root.left.app.left.src --cov-report=term -q --tb=no --ignore=b/left/tst/final

# 压力测试
python -m pytest b/left/tst/stress_test_*.py -q --tb=no

# lint 检查
python -m ruff check root/left/app/left/src

# 最终评分
python -m pytest b/left/tst/final/test_final_score.py -v
```
