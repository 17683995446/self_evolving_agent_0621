#!/usr/bin/env bash
# 5 小时长期稳定性测试运行脚本
# 设置 STABILITY_DURATION_SECONDS=18000 以跑满 5 小时

set -euo pipefail

PROJECT_ROOT="/workspace/self_evolving_agent"
DURATION="${STABILITY_DURATION_SECONDS:-18000}"
REPORT_DIR="${PROJECT_ROOT}/reports"
REPORT_PATH="${REPORT_DIR}/five_hour_report.json"

echo "============================================"
echo "启动长期稳定性测试"
echo "运行时长: ${DURATION} 秒"
echo "报告路径: ${REPORT_PATH}"
echo "============================================"

mkdir -p "${REPORT_DIR}"

STABILITY_DURATION_SECONDS="${DURATION}" \
  python -m pytest "${PROJECT_ROOT}/b/left/tst/final/test_five_hour_stability.py" \
  -v --tb=short

echo "============================================"
echo "长期稳定性测试完成"
if [ -f "${REPORT_PATH}" ]; then
  echo "报告已生成: ${REPORT_PATH}"
else
  echo "警告: 未找到报告文件"
fi
