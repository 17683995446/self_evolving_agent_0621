"""项目最终评分测试

按 100 分制对项目成熟度进行量化评估，目标 >= 95 分。
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from root.left.app.left.src.utils_main.logger import logger


REPORT_DIR = Path("/workspace/self_evolving_agent/reports")
FINAL_SCORE_PATH = REPORT_DIR / "final_score.json"
PROJECT_ROOT = Path("/workspace/self_evolving_agent")


class TestFinalScore:
    """最终评分测试类"""

    def test_final_score(self) -> None:
        """计算并校验项目最终得分"""
        score, details, passed = self._compute_score()

        print("\n========== 项目最终评分 ==========")
        for item in details:
            status = "通过" if item["passed"] else "未通过"
            print(f"{item['name']}: {item['score']}/{item['max']} ({status})")
        print(f"总分: {score}/100")
        print("==================================\n")

        self._save_report(score, details, passed)
        assert score >= 95, f"最终得分 {score} 未达到 95 分目标"

    def _compute_score(self) -> Tuple[int, List[Dict[str, Any]], bool]:
        """计算各维度得分"""
        details: List[Dict[str, Any]] = []
        total = 0

        # 1. 测试通过数量（25 分）：以 941 为基准
        test_count, test_passed = self._check_tests_pass()
        score = 25 if test_passed else int(25 * min(test_count, 941) / 941)
        total += score
        details.append({
            "name": "测试通过",
            "max": 25,
            "score": score,
            "passed": test_passed,
            "detail": f"当前通过测试数: {test_count}",
        })

        # 2. 覆盖率 >= 95%（20 分）
        coverage, cov_passed = self._check_coverage()
        score = 20 if cov_passed else int(20 * max(0, coverage) / 95)
        total += score
        details.append({
            "name": "代码覆盖率 >=95%",
            "max": 20,
            "score": score,
            "passed": cov_passed,
            "detail": f"覆盖率: {coverage:.2f}%",
        })

        # 3. 压力测试通过（10 分）
        stress_passed = self._check_stress_tests()
        score = 10 if stress_passed else 0
        total += score
        details.append({
            "name": "压力测试通过",
            "max": 10,
            "score": score,
            "passed": stress_passed,
            "detail": "",
        })

        # 4. Docker 部署就绪（10 分）：存在镜像或 docker-compose.yml 有效
        docker_ready = self._check_docker_ready()
        score = 10 if docker_ready else 0
        total += score
        details.append({
            "name": "Docker 部署就绪",
            "max": 10,
            "score": score,
            "passed": docker_ready,
            "detail": "",
        })

        # 5. 文档完整（10 分）：README + 核心 docs 存在
        docs_complete = self._check_documentation()
        score = 10 if docs_complete else 0
        total += score
        details.append({
            "name": "文档完整",
            "max": 10,
            "score": score,
            "passed": docs_complete,
            "detail": "",
        })

        # 6. 稳定性报告已生成（10 分）
        stability_report_exists = self._check_stability_report()
        score = 10 if stability_report_exists else 0
        total += score
        details.append({
            "name": "稳定性报告已生成",
            "max": 10,
            "score": score,
            "passed": stability_report_exists,
            "detail": "",
        })

        # 7. 无严重 lint 问题（5 分）
        lint_clean = self._check_lint()
        score = 5 if lint_clean else 0
        total += score
        details.append({
            "name": "无严重 lint 问题",
            "max": 5,
            "score": score,
            "passed": lint_clean,
            "detail": "",
        })

        # 8. 实用能力建设（10 分）
        practical_ready = self._check_practical_utility()
        score = 10 if practical_ready else 0
        total += score
        details.append({
            "name": "实用能力建设",
            "max": 10,
            "score": score,
            "passed": practical_ready,
            "detail": "",
        })

        passed = total >= 95
        return total, details, passed

    def _check_tests_pass(self) -> Tuple[int, bool]:
        """检查测试通过数量（排除 final 目录，避免递归运行评分测试）"""
        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest", "-q", "--tb=no",
                    "--ignore=b/left/tst/final",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + result.stderr
            count = self._parse_pytest_passed(output)
            return count, count >= 941
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"检查测试通过数失败: {exc}", "score")
            return 0, False

    def _parse_pytest_passed(self, output: str) -> int:
        """解析 pytest 简短输出中的通过数"""
        import re
        match = re.search(r"(\d+)\s+passed", output)
        if match:
            return int(match.group(1))
        return 0

    def _check_coverage(self) -> Tuple[float, bool]:
        """检查代码覆盖率（排除 final 目录，避免递归）"""
        try:
            result = subprocess.run(
                [
                    sys.executable, "-m", "pytest",
                    "--cov=root.left.app.left.src", "--cov-report=term",
                    "-q", "--tb=no", "--ignore=b/left/tst/final",
                ],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=300,
            )
            output = result.stdout + result.stderr
            return self._parse_coverage(output)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"检查覆盖率失败: {exc}", "score")
            return 0.0, False

    def _parse_coverage(self, output: str) -> Tuple[float, bool]:
        """解析 coverage 输出"""
        import re
        # 匹配 TOTAL 行，例如 "TOTAL 1234 45 96%"
        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", output)
        if match:
            coverage = float(match.group(1))
            return coverage, coverage >= 95.0
        # 匹配单个模块行
        for line in output.splitlines():
            match = re.search(r"\s+(\d+)%\s*$", line)
            if match:
                coverage = float(match.group(1))
                return coverage, coverage >= 95.0
        return 0.0, False

    def _check_stress_tests(self) -> bool:
        """检查压力测试是否通过（含大量长周期用例，超时设为 30 分钟）"""
        stress_dir = PROJECT_ROOT / "b" / "left" / "tst"
        files = list(stress_dir.glob("stress_test_*.py"))
        if not files:
            return False
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest"] + [str(f) for f in files] + ["-q", "--tb=no"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=1800,
            )
            return result.returncode == 0
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"检查压力测试失败: {exc}", "score")
            return False

    def _check_docker_ready(self) -> bool:
        """检查 Docker 部署就绪状态"""
        compose_files = [
            PROJECT_ROOT / "root" / "left" / "app" / "right" / "docker-compose.yml",
            PROJECT_ROOT / "b" / "right" / "infra" / "left" / "docker" / "docker-compose.yml",
        ]
        if any(f.exists() and f.stat().st_size > 0 for f in compose_files):
            return True
        try:
            result = subprocess.run(
                ["docker", "images", "-q", "self-evolving-agent"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            return bool(result.stdout.strip())
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"检查 Docker 镜像失败: {exc}", "score")
            return False

    def _check_documentation(self) -> bool:
        """检查文档是否完整"""
        required = [
            PROJECT_ROOT / "README.md",
            PROJECT_ROOT / "root" / "right" / "doc" / "left" / "design" / "system_design.md",
            PROJECT_ROOT / "root" / "left" / "app" / "right" / "docs" / "architecture.md",
            PROJECT_ROOT / "root" / "left" / "app" / "right" / "docs" / "deploy.md",
            PROJECT_ROOT / "root" / "left" / "app" / "right" / "docs" / "user.md",
        ]
        return all(f.exists() and f.stat().st_size > 0 for f in required)

    def _check_stability_report(self) -> bool:
        """检查稳定性报告是否已生成"""
        report = PROJECT_ROOT / "reports" / "five_hour_report.json"
        return report.exists() and report.stat().st_size > 0

    def _check_lint(self) -> bool:
        """检查是否存在严重 lint 问题"""
        # 优先使用 ruff，退而求其次使用 flake8，最差用 py_compile 做基础语法检查
        try:
            result = subprocess.run(
                [sys.executable, "-m", "ruff", "check", str(PROJECT_ROOT / "root" / "left" / "app" / "left" / "src")],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except FileNotFoundError:
            pass
        try:
            result = subprocess.run(
                ["python", "-m", "flake8", str(PROJECT_ROOT / "root" / "left" / "app" / "left" / "src"), "--count"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            return result.returncode == 0
        except FileNotFoundError:
            pass
        # 兜底：仅验证语法
        try:
            for py_file in (PROJECT_ROOT / "root" / "left" / "app" / "left" / "src").rglob("*.py"):
                with open(py_file, "rb") as f:
                    compile(f.read(), str(py_file), "exec")
            return True
        except SyntaxError:
            return False

    def _check_practical_utility(self) -> bool:
        """检查实用能力建设是否就绪

        校验真实场景所需的行动、数据、任务、审批、效果、推荐、看板模块
        以及对应测试和示例脚本均存在且可导入。
        """
        required_modules = [
            "root.left.app.left.src.core_mod.action_executor",
            "root.left.app.left.src.core_mod.data_collector",
            "root.left.app.left.src.core_mod.task_templates",
            "root.left.app.left.src.core_mod.approval_gate",
            "root.left.app.left.src.core_mod.effect_verifier",
            "root.left.app.left.src.core_mod.recommendation_engine",
            "root.left.app.left.src.core_mod.dashboard",
        ]
        for module in required_modules:
            try:
                __import__(module)
            except Exception:  # noqa: BLE001
                return False

        required_tests = [
            PROJECT_ROOT / "b" / "left" / "tst" / "core_mod" / "test_action_executor.py",
            PROJECT_ROOT / "b" / "left" / "tst" / "core_mod" / "test_data_collector.py",
            PROJECT_ROOT / "b" / "left" / "tst" / "core_mod" / "test_task_templates.py",
            PROJECT_ROOT / "b" / "left" / "tst" / "core_mod" / "test_approval_gate.py",
            PROJECT_ROOT / "b" / "left" / "tst" / "core_mod" / "test_effect_verifier.py",
            PROJECT_ROOT / "b" / "left" / "tst" / "core_mod" / "test_recommendation_engine.py",
            PROJECT_ROOT / "b" / "left" / "tst" / "core_mod" / "test_dashboard.py",
        ]
        if not all(f.exists() and f.stat().st_size > 0 for f in required_tests):
            return False

        demo = PROJECT_ROOT / "examples" / "practical_aiops_demo.py"
        if not demo.exists() or demo.stat().st_size == 0:
            return False

        return True

    def _save_report(self, score: int, details: List[Dict[str, Any]], passed: bool) -> None:
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
