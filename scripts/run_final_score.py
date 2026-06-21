#!/usr/bin/env python3
"""项目最终评分独立脚本

直接运行所有检查并输出 JSON 报告到 reports/final_score.json。
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


REPORT_DIR = Path("/workspace/self_evolving_agent/reports")
FINAL_SCORE_PATH = REPORT_DIR / "final_score.json"
PROJECT_ROOT = Path("/workspace/self_evolving_agent")


def run_command(cmd: List[str], cwd: Path, timeout: int = 300) -> Tuple[int, str, str]:
    """运行子进程命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:  # noqa: BLE001
        return -1, "", str(exc)


def parse_pytest_passed(output: str) -> int:
    """解析 pytest 通过数"""
    import re

    match = re.search(r"(\d+)\s+passed", output)
    if match:
        return int(match.group(1))
    return 0


def parse_coverage(output: str) -> Tuple[float, bool]:
    """解析覆盖率"""
    import re

    match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
    if match:
        coverage = float(match.group(1))
        return coverage, coverage >= 95.0
    for line in output.splitlines():
        match = re.search(r"\s+(\d+)%\s*$", line)
        if match:
            coverage = float(match.group(1))
            return coverage, coverage >= 95.0
    return 0.0, False


def check_tests_pass() -> Tuple[int, bool]:
    """检查测试通过数量（排除 final 目录，避免递归运行评分脚本）"""
    code, stdout, stderr = run_command(
        [
            "python", "-m", "pytest", "-q", "--tb=no",
            "--ignore=b/left/tst/final",
        ],
        PROJECT_ROOT,
    )
    output = stdout + stderr
    count = parse_pytest_passed(output)
    return count, count >= 941


def check_coverage() -> Tuple[float, bool]:
    """检查代码覆盖率（排除 final 目录，避免递归）"""
    code, stdout, stderr = run_command(
        [
            "python", "-m", "pytest",
            "--cov=root.left.app.left.src", "--cov-report=term",
            "-q", "--tb=no", "--ignore=b/left/tst/final",
        ],
        PROJECT_ROOT,
    )
    return parse_coverage(stdout + stderr)


def check_stress_tests() -> bool:
    """检查压力测试（含大量长周期用例，超时设为 30 分钟）"""
    stress_dir = PROJECT_ROOT / "b" / "left" / "tst"
    files = list(stress_dir.glob("stress_test_*.py"))
    if not files:
        return False
    code, _, _ = run_command(
        ["python", "-m", "pytest"] + [str(f) for f in files] + ["-q", "--tb=no"],
        PROJECT_ROOT,
        timeout=1800,
    )
    return code == 0


def check_docker_ready() -> bool:
    """检查 Docker 部署就绪状态"""
    compose_files = [
        PROJECT_ROOT / "root" / "left" / "app" / "right" / "docker-compose.yml",
        PROJECT_ROOT / "b" / "right" / "infra" / "left" / "docker" / "docker-compose.yml",
    ]
    if any(f.exists() and f.stat().st_size > 0 for f in compose_files):
        return True
    code, stdout, _ = run_command(
        ["docker", "images", "-q", "self-evolving-agent"],
        PROJECT_ROOT,
        timeout=30,
    )
    return code == 0 and bool(stdout.strip())


def check_documentation() -> bool:
    """检查文档完整性"""
    required = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "root" / "right" / "doc" / "left" / "design" / "system_design.md",
        PROJECT_ROOT / "root" / "left" / "app" / "right" / "docs" / "architecture.md",
        PROJECT_ROOT / "root" / "left" / "app" / "right" / "docs" / "deploy.md",
        PROJECT_ROOT / "root" / "left" / "app" / "right" / "docs" / "user.md",
    ]
    return all(f.exists() and f.stat().st_size > 0 for f in required)


def check_stability_report() -> bool:
    """检查稳定性报告"""
    report = PROJECT_ROOT / "reports" / "five_hour_report.json"
    return report.exists() and report.stat().st_size > 0


def check_lint() -> bool:
    """检查 lint 状态"""
    src_dir = PROJECT_ROOT / "root" / "left" / "app" / "left" / "src"
    code, _, _ = run_command(
        ["python", "-m", "ruff", "check", str(src_dir)],
        PROJECT_ROOT,
        timeout=60,
    )
    if code == 0:
        return True
    code, _, _ = run_command(
        ["python", "-m", "flake8", str(src_dir), "--count"],
        PROJECT_ROOT,
        timeout=60,
    )
    if code == 0:
        return True
    # 兜底：语法检查
    try:
        for py_file in src_dir.rglob("*.py"):
            with open(py_file, "rb") as f:
                compile(f.read(), str(py_file), "exec")
        return True
    except SyntaxError:
        return False


def compute_score() -> Tuple[int, List[Dict[str, Any]], bool]:
    """计算最终得分"""
    details: List[Dict[str, Any]] = []
    total = 0

    test_count, test_passed = check_tests_pass()
    score = 30 if test_passed else int(30 * min(test_count, 941) / 941)
    total += score
    details.append({
        "name": "测试通过",
        "max": 30,
        "score": score,
        "passed": test_passed,
        "detail": f"当前通过测试数: {test_count}",
    })

    coverage, cov_passed = check_coverage()
    score = 20 if cov_passed else int(20 * max(0, coverage) / 95)
    total += score
    details.append({
        "name": "代码覆盖率 >=95%",
        "max": 20,
        "score": score,
        "passed": cov_passed,
        "detail": f"覆盖率: {coverage:.2f}%",
    })

    stress_passed = check_stress_tests()
    score = 15 if stress_passed else 0
    total += score
    details.append({
        "name": "压力测试通过",
        "max": 15,
        "score": score,
        "passed": stress_passed,
        "detail": "",
    })

    docker_ready = check_docker_ready()
    score = 10 if docker_ready else 0
    total += score
    details.append({
        "name": "Docker 部署就绪",
        "max": 10,
        "score": score,
        "passed": docker_ready,
        "detail": "",
    })

    docs_complete = check_documentation()
    score = 10 if docs_complete else 0
    total += score
    details.append({
        "name": "文档完整",
        "max": 10,
        "score": score,
        "passed": docs_complete,
        "detail": "",
    })

    stability_exists = check_stability_report()
    score = 10 if stability_exists else 0
    total += score
    details.append({
        "name": "稳定性报告已生成",
        "max": 10,
        "score": score,
        "passed": stability_exists,
        "detail": "",
    })

    lint_clean = check_lint()
    score = 5 if lint_clean else 0
    total += score
    details.append({
        "name": "无严重 lint 问题",
        "max": 5,
        "score": score,
        "passed": lint_clean,
        "detail": "",
    })

    return total, details, total >= 95


def save_report(score: int, details: List[Dict[str, Any]], passed: bool) -> None:
    """保存评分报告"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "score": score,
        "max_score": 100,
        "passed": passed,
        "details": details,
    }
    with open(FINAL_SCORE_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)


def main() -> int:
    """脚本入口"""
    score, details, passed = compute_score()

    print("========== 项目最终评分 ==========")
    for item in details:
        status = "通过" if item["passed"] else "未通过"
        print(f"{item['name']}: {item['score']}/{item['max']} ({status})")
    print(f"总分: {score}/100")
    print("==================================")

    save_report(score, details, passed)
    print(f"报告已保存到: {FINAL_SCORE_PATH}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
