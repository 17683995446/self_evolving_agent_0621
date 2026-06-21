"""统一命令行入口

提供一键启动、状态查询、配置校验、健康检查等子命令，
让用户无需了解内部模块结构即可使用 Agent。

用法示例:
    python -m root.left.app.left.src.cli run --env dev --max-loops 10
    python -m root.left.app.left.src.cli status --port 8080
    python -m root.left.app.left.src.cli validate --env dev
    python -m root.left.app.left.src.cli doctor
    python -m root.left.app.left.src.cli config --show-defaults
    python -m root.left.app.left.src.cli welcome
    python -m root.left.app.left.src.cli help run
    python -m root.left.app.left.src.cli examples
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from root.left.app.left.src.utils_main.cli_guide import (
    build_run_args_from_wizard,
    is_interactive,
    render_examples,
    render_help_all,
    render_help_command,
    render_welcome,
    run_wizard,
)
from root.left.app.left.src.utils_main.config_loader import DEFAULT_CONFIG, ConfigDescriber, ConfigLoader
from root.left.app.left.src.utils_main.exceptions import (
    AgentException,
    ConfigurationError,
)
from root.left.app.left.src.utils_main.health_diagnoser import HealthDiagnoser
from root.left.app.left.src.utils_main.logger import logger
from root.left.app.left.src.utils_main.validators import ConfigValidator


def _load_and_validate(env: str) -> Dict[str, Any]:
    """加载并校验配置，失败时抛出友好错误。"""
    config = ConfigLoader.load_config(env)
    ConfigValidator.validate_config(config)
    return config


def cmd_run(args: argparse.Namespace) -> int:
    """启动 Agent 运行主循环。"""
    from root.left.app.left.src.main_deploy import ProductionAgent

    # 交互式向导模式：先收集配置，再重新解析参数
    if getattr(args, "guide", False):
        if not is_interactive():
            print("错误: --guide 需要交互式终端，当前环境不支持。", file=sys.stderr)
            print("提示: 请直接指定参数，例如:", file=sys.stderr)
            print("  python -m root.left.app.left.src.cli run --env dev --max-loops 10", file=sys.stderr)
            return 2
        wizard_result = run_wizard()
        wizard_args = build_run_args_from_wizard(wizard_result)
        parser = build_parser()
        args = parser.parse_args(["run"] + wizard_args)

    try:
        config = _load_and_validate(args.env)
        if args.dry_run:
            config.setdefault("action_executor", {})["dry_run"] = True
        if args.port is not None:
            config.setdefault("health_check", {})["enabled"] = True
            config["health_check"]["port"] = args.port
        if args.max_loops is not None:
            config["max_loops"] = args.max_loops
        if args.loop_interval is not None:
            config["loop_interval"] = args.loop_interval

        agent = ProductionAgent(config)
        logger.info(f"Agent 启动: env={args.env} max_loops={args.max_loops}", "cli")
        max_loops = args.max_loops
        if max_loops == 0:
            max_loops = None
        agent.run(max_loops=max_loops)
        agent.close()
        return 0
    except ConfigurationError as e:
        print(e.format_for_user(), file=sys.stderr)
        _print_config_hint(args.env)
        return 2
    except AgentException as e:
        print(e.format_for_user(), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止...", file=sys.stderr)
        return 0


def cmd_status(args: argparse.Namespace) -> int:
    """查询运行中 Agent 的状态。"""
    url = f"http://127.0.0.1:{args.port}/state"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        print(json.dumps(body, ensure_ascii=False, indent=2))
        return 0
    except urllib.error.URLError:
        print(f"无法连接到 Agent (端口 {args.port})，请确认 Agent 是否正在运行。", file=sys.stderr)
        return 1
    except urllib.error.HTTPError as e:
        print(f"Agent 返回错误: {e.code} {e.reason}", file=sys.stderr)
        return 1


def cmd_health(args: argparse.Namespace) -> int:
    """检查运行中 Agent 的健康状态。"""
    from root.left.app.left.src.utils_main.cli_formatter import format_status_label

    url = f"http://127.0.0.1:{args.port}/health"
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = json.loads(resp.read().decode())
        status = body.get("status", "unknown")
        status_display = format_status_label(status)
        if status == "healthy":
            print(f"Agent {status_display} (循环次数: {body.get('loop_count', 0)})")
            return 0
        else:
            print(f"Agent {status_display}: {body}", file=sys.stderr)
            return 1
    except urllib.error.URLError:
        print(f"无法连接到 Agent (端口 {args.port})，请确认 Agent 是否正在运行。", file=sys.stderr)
        return 1


def cmd_validate(args: argparse.Namespace) -> int:
    """校验配置文件是否合法。"""
    from root.left.app.left.src.utils_main.cli_formatter import (
        Color,
        colorize,
        render_key_value,
    )

    try:
        config = _load_and_validate(args.env)
        print(colorize(f"配置校验通过: env={args.env}", Color.GREEN))
        print("")
        print(render_key_value([
            ("loop_interval", config.get("loop_interval")),
            ("max_loops", config.get("max_loops")),
            ("log_level", config.get("log_level")),
        ]))
        return 0
    except ConfigurationError as e:
        print(e.format_for_user(), file=sys.stderr)
        _print_config_hint(args.env)
        return 2
    except AgentException as e:
        print(e.format_for_user(), file=sys.stderr)
        return 2


def cmd_config(args: argparse.Namespace) -> int:
    """查看配置。"""
    if args.show_defaults:
        print(json.dumps(DEFAULT_CONFIG, ensure_ascii=False, indent=2))
        return 0
    if args.describe:
        print(ConfigDescriber.to_text())
        return 0
    try:
        config = _load_and_validate(args.env)
        print(json.dumps(config, ensure_ascii=False, indent=2))
        return 0
    except ConfigurationError as e:
        print(e.format_for_user(), file=sys.stderr)
        return 2


def cmd_doctor(args: argparse.Namespace) -> int:
    """自诊断：检查环境、配置、依赖、模块是否就绪。"""
    from root.left.app.left.src.main import SelfEvolvingAgent
    from root.left.app.left.src.utils_main.cli_formatter import (
        Color,
        colorize,
        format_pass_fail,
        render_table,
    )

    print("=== Agent 自诊断 ===")
    print("")
    diagnoser = HealthDiagnoser()

    # 收集所有检查结果
    check_rows: List[List[str]] = []

    ok, msg = _check_python_version()
    check_rows.append(["Python 版本", f"{format_pass_fail(ok)} {'OK' if ok else 'FAIL'}", msg])
    all_ok = ok

    ok, msg = _check_config("dev")
    check_rows.append(["配置(dev)", f"{format_pass_fail(ok)} {'OK' if ok else 'FAIL'}", msg])
    all_ok = all_ok and ok

    ok, msg = _check_dependencies()
    check_rows.append(["核心依赖", f"{format_pass_fail(ok)} {'OK' if ok else 'FAIL'}", msg])
    all_ok = all_ok and ok

    try:
        agent = SelfEvolvingAgent()
        items = diagnoser.run_full_diagnosis(agent)
        for item in items:
            status_sym = format_pass_fail(item.passed)
            status_text = "OK" if item.passed else "FAIL"
            check_rows.append([item.name, f"{status_sym} {status_text}", item.message])
            if not item.passed:
                all_ok = False
        agent.close()
    except Exception as e:
        check_rows.append(["模块检查", f"{format_pass_fail(False)} FAIL", str(e)])
        all_ok = False

    # 渲染表格
    print(render_table(["检查项", "状态", "详情"], check_rows))
    print("")

    print("=== 诊断完成 ===")
    if all_ok:
        print(colorize("所有检查通过，Agent 可以启动。", Color.GREEN))
        return 0
    else:
        print(colorize("存在检查失败项，请根据上述提示修复。", Color.RED), file=sys.stderr)
        return 1


def cmd_diagnose(args: argparse.Namespace) -> int:
    """对运行中或新建的 Agent 进行深度诊断。"""
    from root.left.app.left.src.main import SelfEvolvingAgent

    try:
        agent = SelfEvolvingAgent()
        diagnoser = HealthDiagnoser()
        items = diagnoser.run_full_diagnosis(agent)
        if args.json:
            print(json.dumps(diagnoser.to_dict(items), ensure_ascii=False, indent=2))
        else:
            print(diagnoser.format_report(items))
        agent.close()
        return 0 if all(i.passed for i in items) else 1
    except Exception as e:
        print(f"诊断失败: {e}", file=sys.stderr)
        return 1


def cmd_welcome(args: argparse.Namespace) -> int:
    """显示首次使用介绍。"""
    print(render_welcome())
    return 0


def cmd_help(args: argparse.Namespace) -> int:
    """显示命令帮助。"""
    if args.command_name:
        print(render_help_command(args.command_name))
    else:
        print(render_help_all())
    return 0


def cmd_examples(args: argparse.Namespace) -> int:
    """显示常见使用场景示例。"""
    print(render_examples())
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """从模板创建配置文件。"""
    from root.left.app.left.src.utils_main.cli_formatter import (
        Color,
        colorize,
        render_table,
    )
    from root.left.app.left.src.utils_main.config_templates import (
        list_templates,
        render_template,
        save_template,
    )

    # 列出模板
    if args.list:
        print("可用配置模板:")
        print("")
        templates = list_templates()
        rows = [[t["name"], t["description"]] for t in templates]
        print(render_table(["模板名", "说明"], rows))
        return 0

    # 显示模板内容
    if args.show:
        try:
            print(render_template(args.show))
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 2

    # 从模板创建配置文件
    if args.template:
        try:
            force = args.force
            path = save_template(args.template, args.env, force=force)
            print(colorize(f"配置文件已创建: {path}", Color.GREEN))
            print(f"  模板: {args.template}")
            print(f"  环境: {args.env}")
            print("")
            print("下一步:")
            print(f"  校验配置: python -m root.left.app.left.src.cli validate --env {args.env}")
            print(f"  启动 Agent: python -m root.left.app.left.src.cli run --env {args.env}")
            return 0
        except ValueError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 2
        except FileExistsError as e:
            print(f"错误: {e}", file=sys.stderr)
            print("提示: 使用 --force 覆盖已有文件。", file=sys.stderr)
            return 2

    # 无参数时显示帮助
    print("用法: init [--list | --show <模板> | --template <模板> --env <环境>]")
    print("")
    print("示例:")
    print("  init --list                          列出所有可用模板")
    print("  init --show standard                 查看标准模板内容")
    print("  init --template standard --env dev   从标准模板创建 dev 配置")
    print("  init --template production --env prod --force  覆盖创建")
    return 0


def cmd_control(args: argparse.Namespace) -> int:
    """运行时控制运行中的 Agent（暂停/恢复/停止/重载/状态）。"""
    from root.left.app.left.src.utils_main.cli_formatter import (
        Color,
        colorize,
        format_status_label,
        render_key_value,
    )

    action = args.action
    port = args.port

    if action == "status":
        url = f"http://127.0.0.1:{port}/control/status"
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = json.loads(resp.read().decode())
            print(render_key_value([
                ("运行中", format_status_label("running" if body.get("running") else "stopped")),
                ("暂停", format_status_label("paused" if body.get("paused") else "running")),
                ("循环次数", body.get("loop_count", 0)),
            ]))
            return 0
        except urllib.error.URLError:
            print(f"无法连接到 Agent (端口 {port})，请确认 Agent 是否正在运行。", file=sys.stderr)
            return 1

    # POST 操作
    url = f"http://127.0.0.1:{port}/control/{action}"
    data = None
    if action == "reload":
        env = args.env if args.env else "dev"
        data = json.dumps({"env": env}).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=data, method="POST")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode())
        if body.get("success"):
            print(colorize(body.get("message", "操作成功"), Color.GREEN))
            return 0
        else:
            print(colorize(body.get("message", "操作失败"), Color.RED), file=sys.stderr)
            return 1
    except urllib.error.URLError:
        print(f"无法连接到 Agent (端口 {port})，请确认 Agent 是否正在运行。", file=sys.stderr)
        return 1
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode())
            print(f"Agent 返回错误: {e.code} - {err_body.get('error', e.reason)}", file=sys.stderr)
        except Exception:
            print(f"Agent 返回错误: {e.code} {e.reason}", file=sys.stderr)
        return 1


def cmd_docs(args: argparse.Namespace) -> int:
    """显示用户文档。"""
    from root.left.app.left.src.utils_main.cli_docs import render_doc

    topic = args.topic if args.topic else ""
    print(render_doc(topic))
    return 0


def cmd_logs(args: argparse.Namespace) -> int:
    """查看与分析日志文件。"""
    from root.left.app.left.src.utils_main.cli_formatter import Color, colorize
    from root.left.app.left.src.utils_main.log_report import (
        compute_stats,
        filter_entries,
        parse_log_file,
        render_entries,
        render_stats,
    )

    log_file = args.file
    if not os.path.exists(log_file):
        print(colorize(f"错误: 日志文件不存在: {log_file}", Color.RED), file=sys.stderr)
        return 1

    try:
        entries = parse_log_file(log_file)
    except Exception as e:
        print(colorize(f"错误: 读取日志失败: {e}", Color.RED), file=sys.stderr)
        return 1

    if not entries:
        print("日志文件为空或无有效日志条目。")
        return 0

    # 统计模式
    if args.stats:
        stats = compute_stats(entries)
        print(render_stats(stats))
        return 0

    # 过滤
    filtered = filter_entries(
        entries,
        level=args.level,
        module=args.module,
        keyword=args.keyword,
        limit=args.tail,
    )

    if not filtered:
        print("无匹配的日志条目。")
        return 0

    print(render_entries(filtered, show_module=not args.no_module))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """生成运行报告。"""
    from root.left.app.left.src.utils_main.cli_formatter import Color, colorize
    from root.left.app.left.src.utils_main.log_report import generate_report, save_report

    log_file = args.file
    if not os.path.exists(log_file):
        print(colorize(f"错误: 日志文件不存在: {log_file}", Color.RED), file=sys.stderr)
        return 1

    try:
        report = generate_report(
            log_file_path=log_file,
            env=args.env,
            loop_count=args.loop_count,
            duration_seconds=args.duration,
            health_status=args.health,
        )
    except Exception as e:
        print(colorize(f"错误: 生成报告失败: {e}", Color.RED), file=sys.stderr)
        return 1

    if args.json:
        print(report.to_json())
    else:
        print(report.to_text())

    # 保存到文件
    if args.output:
        try:
            fmt = "json" if args.json else "text"
            save_report(report, args.output, fmt=fmt)
            print(colorize(f"报告已保存: {args.output}", Color.GREEN), file=sys.stderr)
        except Exception as e:
            print(colorize(f"错误: 保存报告失败: {e}", Color.RED), file=sys.stderr)
            return 1

    return 0


def cmd_completion(args: argparse.Namespace) -> int:
    """生成或安装 Shell 补全脚本。"""
    from root.left.app.left.src.utils_main.cli_formatter import (
        Color,
        colorize,
        render_section,
    )
    from root.left.app.left.src.utils_main.shell_completion import (
        detect_shell,
        get_completion_script,
        get_install_instructions,
    )

    shell = args.shell
    if shell is None:
        shell = detect_shell()
        if shell == "unknown":
            print(colorize("无法自动检测 shell，请指定 --shell bash 或 --shell zsh", Color.RED), file=sys.stderr)
            return 2

    command_name = args.command_name

    # 安装模式：打印安装指引
    if args.install:
        print(render_section(f"{command_name} 补全安装指引 ({shell})"))
        print("")
        print(get_install_instructions(shell, command_name))
        return 0

    # 默认：打印补全脚本
    try:
        script = get_completion_script(shell, command_name)
        print(script)
        return 0
    except ValueError as e:
        print(colorize(f"错误: {e}", Color.RED), file=sys.stderr)
        return 2


def cmd_install(args: argparse.Namespace) -> int:
    """安装一键启动脚本到指定目录。"""
    from root.left.app.left.src.utils_main.cli_formatter import (
        Color,
        colorize,
        render_section,
    )
    from root.left.app.left.src.utils_main.startup_script import (
        get_install_instructions,
        install_startup_script,
        render_startup_help,
    )

    command_name = args.command_name
    install_dir = args.install_dir

    # 无参数时显示帮助
    if not install_dir:
        print(render_startup_help())
        print("")
        print(render_section("安装指引"))
        print("")
        print(get_install_instructions(command_name))
        return 0

    try:
        path = install_startup_script(
            command_name=command_name,
            install_dir=install_dir,
            force=args.force,
        )
        print(colorize(f"启动脚本已安装: {path}", Color.GREEN))
        print(f"  命令名: {command_name}")
        print(f"  安装目录: {install_dir}")
        print("")
        print("下一步:")
        print(f"  确保 {install_dir} 在 PATH 中")
        print(f"  运行 {command_name} --help 查看可用命令")
        return 0
    except FileExistsError as e:
        print(colorize(f"错误: {e}", Color.RED), file=sys.stderr)
        print("提示: 使用 --force 覆盖已有文件。", file=sys.stderr)
        return 2
    except OSError as e:
        print(colorize(f"错误: 安装失败: {e}", Color.RED), file=sys.stderr)
        return 1


def cmd_diff(args: argparse.Namespace) -> int:
    """配置差异对比与变更审计。"""
    from root.left.app.left.src.utils_main.cli_formatter import Color, colorize
    from root.left.app.left.src.utils_main.config_diff import (
        diff_against_defaults,
        diff_envs,
        diff_files,
        generate_audit_report,
        render_diff,
        save_audit_report,
    )

    # 审计模式
    if args.audit:
        try:
            config = _load_and_validate(args.env)
            report = generate_audit_report(config, env=args.env)
            if args.json:
                print(report.to_json())
            else:
                print(report.to_text())
            if args.output:
                fmt = "json" if args.json else "text"
                save_audit_report(report, args.output, fmt=fmt)
                print(colorize(f"审计报告已保存: {args.output}", Color.GREEN), file=sys.stderr)
            return 0
        except Exception as e:
            print(colorize(f"错误: 生成审计报告失败: {e}", Color.RED), file=sys.stderr)
            return 1

    # 文件对比模式
    if args.file and args.file2:
        try:
            diffs = diff_files(args.file, args.file2)
        except FileNotFoundError as e:
            print(colorize(f"错误: {e}", Color.RED), file=sys.stderr)
            return 1
        except Exception as e:
            print(colorize(f"错误: 解析配置文件失败: {e}", Color.RED), file=sys.stderr)
            return 1
        if args.json:
            import json
            print(json.dumps([d.to_dict() for d in diffs], ensure_ascii=False, indent=2, default=str))
        else:
            print(render_diff(diffs, show_description=args.describe))
        return 0

    # 环境对比模式
    if args.against:
        try:
            diffs = diff_envs(args.env, args.against)
        except Exception as e:
            print(colorize(f"错误: 加载配置失败: {e}", Color.RED), file=sys.stderr)
            return 1
        if args.json:
            import json
            print(json.dumps([d.to_dict() for d in diffs], ensure_ascii=False, indent=2, default=str))
        else:
            print(render_diff(diffs, show_description=args.describe))
        return 0

    # 对比默认配置
    if args.against_defaults:
        try:
            config = _load_and_validate(args.env)
            diffs = diff_against_defaults(config)
        except Exception as e:
            print(colorize(f"错误: 加载配置失败: {e}", Color.RED), file=sys.stderr)
            return 1
        if args.json:
            import json
            print(json.dumps([d.to_dict() for d in diffs], ensure_ascii=False, indent=2, default=str))
        else:
            print(render_diff(diffs, show_description=args.describe))
        return 0

    # 无参数时显示帮助
    print("用法: diff [选项]")
    print("")
    print("对比模式:")
    print("  diff --env dev --against prod          对比两个环境")
    print("  diff --env dev --against-defaults      对比环境与默认配置")
    print("  diff --file a.yaml --file2 b.yaml      对比两个配置文件")
    print("  diff --audit --env dev                 生成审计报告")
    print("")
    print("通用选项:")
    print("  --describe                             显示配置项说明")
    print("  --json                                 以 JSON 格式输出")
    print("  --output FILE                          保存报告到文件")
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    """性能基准与资源占用报告。"""
    from root.left.app.left.src.utils_main.cli_formatter import Color, colorize
    from root.left.app.left.src.utils_main.benchmark import (
        render_resource_samples,
        run_benchmark,
        sample_resources,
        save_benchmark_report,
    )

    # 监控模式
    if args.monitor:
        samples = []
        interval = args.interval if args.interval and args.interval > 0 else 1.0
        count = args.iterations if args.iterations and args.iterations > 0 else 10
        try:
            for _ in range(count):
                samples.append(sample_resources())
                time.sleep(interval)
        except KeyboardInterrupt:
            pass
        if args.json:
            import json
            print(json.dumps([s.to_dict() for s in samples], ensure_ascii=False, indent=2))
        else:
            print(render_resource_samples(samples))
        return 0

    # 基准测试模式
    try:
        report = run_benchmark(iterations=args.iterations or 10, env=args.env)
        if args.json:
            print(report.to_json())
        else:
            print(report.to_text())
        if args.output:
            fmt = "json" if args.json else "text"
            save_benchmark_report(report, args.output, fmt=fmt)
            print(colorize(f"基准报告已保存: {args.output}", Color.GREEN), file=sys.stderr)
        return 0
    except Exception as e:
        print(colorize(f"错误: 基准测试失败: {e}", Color.RED), file=sys.stderr)
        return 1


def cmd_repl(args: argparse.Namespace) -> int:
    """启动交互式 REPL。"""
    from root.left.app.left.src.utils_main.cli_formatter import Color, colorize
    from root.left.app.left.src.utils_main.repl import REPLSession, CommandHistory, get_default_history_file

    history_file = args.history_file or get_default_history_file()

    # 非交互式环境检查
    if not sys.stdin.isatty() and not args.force:
        print(colorize("错误: REPL 需要交互式终端，当前环境不支持。", Color.RED), file=sys.stderr)
        print("提示: 使用 --force 可在非交互式环境强制启动。", file=sys.stderr)
        return 2

    def executor(cli_args: List[str]) -> int:
        return main(cli_args)

    history = CommandHistory(history_file=history_file)
    history.load()

    session = REPLSession(executor=executor, history=history)
    return session.run()


def cmd_alert(args: argparse.Namespace) -> int:
    """告警系统管理。"""
    from root.left.app.left.src.utils_main.alert_system import (
        AlertManager,
        ConsoleNotifier,
        create_default_rules,
        render_alert_summary,
        render_alerts,
        render_rules,
    )

    manager = AlertManager()

    # 加载默认规则
    for rule in create_default_rules():
        manager.add_rule(rule)

    if args.list_rules:
        print(render_rules(manager.get_rules()))
        return 0

    if args.summary:
        print(render_alert_summary(manager))
        return 0

    if args.test:
        # 测试模式：模拟指标触发告警
        manager.add_notifier(ConsoleNotifier())
        test_metrics = {
            "cpu_percent": 90.0,
            "memory_percent": 70.0,
            "error_count": 15,
        }
        print("测试指标:", test_metrics)
        print("")
        alerts = manager.evaluate(test_metrics)
        if alerts:
            print(render_alerts(alerts))
        else:
            print("无告警触发。")
        return 0

    if args.evaluate:
        # 评估模式：解析用户提供的指标
        try:
            metrics = json.loads(args.evaluate)
        except json.JSONDecodeError as e:
            print(f"错误: 指标 JSON 解析失败: {e}", file=sys.stderr)
            return 2
        manager.add_notifier(ConsoleNotifier())
        alerts = manager.evaluate(metrics)
        if alerts:
            print(render_alerts(alerts))
        else:
            print("无告警触发。")
        return 0

    # 无参数时显示帮助
    print("用法: alert [选项]")
    print("")
    print("选项:")
    print("  --list-rules              列出所有告警规则")
    print("  --summary                 显示告警系统摘要")
    print("  --test                    用测试指标触发告警")
    print("  --evaluate METRICS_JSON   评估指定指标是否触发告警")
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    """定时任务调度管理。"""
    from root.left.app.left.src.utils_main.scheduler import (
        CronExpression,
        CronParseError,
        ScheduledTask,
        Scheduler,
        render_history,
        render_next_runs,
        render_presets,
        render_scheduler_summary,
        render_tasks,
    )

    if args.list:
        scheduler = Scheduler()
        print(render_tasks(scheduler.get_tasks()))
        return 0

    if args.presets:
        print(render_presets())
        return 0

    if args.summary:
        scheduler = Scheduler()
        print(render_scheduler_summary(scheduler))
        return 0

    if args.add:
        name, cron, command = args.add
        try:
            scheduler = Scheduler()
            task = ScheduledTask(name=name, cron=cron, command=command)
            scheduler.add_task(task)
            print(f"已添加任务: {name}")
            print(render_tasks([task]))
            return 0
        except CronParseError as e:
            print(f"错误: cron 表达式无效: {e}", file=sys.stderr)
            return 2

    if args.remove:
        scheduler = Scheduler()
        if scheduler.remove_task(args.remove):
            print(f"已移除任务: {args.remove}")
            return 0
        print(f"错误: 任务不存在: {args.remove}", file=sys.stderr)
        return 1

    if args.enable:
        scheduler = Scheduler()
        if scheduler.enable_task(args.enable):
            print(f"已启用任务: {args.enable}")
            return 0
        print(f"错误: 任务不存在: {args.enable}", file=sys.stderr)
        return 1

    if args.disable:
        scheduler = Scheduler()
        if scheduler.disable_task(args.disable):
            print(f"已禁用任务: {args.disable}")
            return 0
        print(f"错误: 任务不存在: {args.disable}", file=sys.stderr)
        return 1

    if args.next:
        scheduler = Scheduler()
        print(render_next_runs(scheduler.get_tasks()))
        return 0

    if args.history:
        scheduler = Scheduler()
        print(render_history(scheduler.get_history()))
        return 0

    if args.validate:
        try:
            cron = CronExpression.parse(args.validate)
            print(f"cron 表达式有效: {args.validate}")
            print(f"  分钟: {cron.minute}")
            print(f"  小时: {cron.hour}")
            print(f"  日:   {cron.day}")
            print(f"  月:   {cron.month}")
            print(f"  周:   {cron.weekday}")
            return 0
        except CronParseError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 2

    if args.test:
        try:
            cron = CronExpression.parse(args.test)
            now = datetime.now()
            nxt = cron.next_run(now)
            print(f"cron 表达式: {args.test}")
            print(f"当前时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"下次执行: {nxt.strftime('%Y-%m-%d %H:%M:%S')}")
            return 0
        except CronParseError as e:
            print(f"错误: {e}", file=sys.stderr)
            return 2

    # 无参数时显示帮助
    print("用法: schedule [选项]")
    print("")
    print("选项:")
    print("  --list                       列出所有定时任务")
    print("  --presets                    显示预设 cron 表达式")
    print("  --summary                    显示调度器摘要")
    print("  --add NAME CRON COMMAND      添加任务")
    print("  --remove NAME                移除任务")
    print("  --enable NAME                启用任务")
    print("  --disable NAME               禁用任务")
    print("  --next                       显示下次执行时间")
    print("  --history                    显示执行历史")
    print("  --validate CRON              校验 cron 表达式")
    print("  --test CRON                  测试 cron 表达式下次匹配时间")
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    """数据导入导出与备份恢复。"""
    from root.left.app.left.src.utils_main.data_backup import (
        BackupManager,
        DataExporter,
        DataImporter,
        DataType,
        render_backup_list,
        render_export_summary,
        render_import_result,
        render_restore_result,
        render_verify_result,
    )

    base_dir = os.getcwd()

    if args.export:
        exporter = DataExporter(base_dir)
        data_type = DataType(args.type)
        try:
            exporter.export_to_file(args.export, data_type, args.env)
            # 读取导出文件并显示摘要
            with open(args.export, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"已导出到: {args.export}")
            print(render_export_summary(data))
            return 0
        except Exception as e:
            print(f"错误: 导出失败: {e}", file=sys.stderr)
            return 2

    if args.import_file:
        importer = DataImporter(base_dir)
        try:
            result = importer.import_from_file(args.import_file, args.env)
            print(f"已从 {args.import_file} 导入数据")
            print(render_import_result(result))
            return 0
        except FileNotFoundError as e:
            print(f"错误: 文件不存在: {e}", file=sys.stderr)
            return 2
        except (json.JSONDecodeError, ValueError) as e:
            print(f"错误: 导入失败: {e}", file=sys.stderr)
            return 2

    if args.backup:
        manager = BackupManager(base_dir)
        data_type_map = {
            "all": None,  # None 表示全部
            "config": [DataType.CONFIG],
            "state": [DataType.STATE],
            "reports": [DataType.REPORTS],
        }
        data_types = data_type_map.get(args.type)
        try:
            manager.create_backup(args.backup, data_types, args.env)
            print(f"已创建备份: {args.backup}")
            return 0
        except Exception as e:
            print(f"错误: 备份失败: {e}", file=sys.stderr)
            return 2

    if args.restore:
        manager = BackupManager(base_dir)
        try:
            result = manager.restore_backup(args.restore, args.env)
            print(f"已从 {args.restore} 恢复")
            print(render_restore_result(result))
            return 0
        except FileNotFoundError as e:
            print(f"错误: 文件不存在: {e}", file=sys.stderr)
            return 2
        except ValueError as e:
            print(f"错误: 恢复失败: {e}", file=sys.stderr)
            return 2

    if args.list_backups:
        manager = BackupManager(base_dir)
        backups = manager.list_backups(args.dir)
        print(render_backup_list(backups))
        return 0

    if args.verify:
        manager = BackupManager(base_dir)
        result = manager.verify_backup(args.verify)
        print(render_verify_result(result))
        if not result.get("valid", False):
            return 1
        return 0

    # 无参数时显示帮助
    print("用法: data [选项]")
    print("")
    print("选项:")
    print("  --export FILE          导出数据到 JSON 文件")
    print("  --import FILE          从 JSON 文件导入数据")
    print("  --backup FILE          创建备份归档（tar.gz）")
    print("  --restore FILE         从备份归档恢复")
    print("  --list-backups         列出备份文件")
    print("  --verify FILE          验证备份完整性")
    print("  --type TYPE            数据类型（all/config/state/reports）")
    print("  --env ENV              环境名")
    print("  --dir DIR              备份目录")
    return 0


def cmd_instance(args: argparse.Namespace) -> int:
    """多实例管理与编排。"""
    from root.left.app.left.src.utils_main.instance_manager import (
        AgentInstance,
        InstanceManager,
        render_instance_detail,
        render_instances,
        render_operation_results,
        render_summary,
    )

    manager = InstanceManager()

    if args.list:
        print(render_instances(manager.list_instances()))
        return 0

    if args.summary:
        print(render_summary(manager))
        return 0

    if args.add:
        name = args.add[0]
        inst = AgentInstance(
            name=name,
            env=args.env_opt or "dev",
            port=args.port_opt or 8080,
            max_loops=args.max_loops_opt if args.max_loops_opt is not None else 1000,
            dry_run=args.dry_run_opt,
            description=args.desc,
        )
        manager.register(inst)
        print(f"已添加实例: {name}")
        print(render_instance_detail(inst))
        return 0

    if args.remove:
        if manager.unregister(args.remove):
            print(f"已移除实例: {args.remove}")
            return 0
        print(f"错误: 实例不存在: {args.remove}", file=sys.stderr)
        return 1

    if args.info:
        inst = manager.get(args.info)
        if inst is None:
            print(f"错误: 实例不存在: {args.info}", file=sys.stderr)
            return 1
        print(render_instance_detail(inst))
        return 0

    if args.start:
        ok, msg = manager.start(args.start)
        print(msg)
        return 0 if ok else 1

    if args.stop:
        ok, msg = manager.stop(args.stop)
        print(msg)
        return 0 if ok else 1

    if args.restart:
        ok, msg = manager.restart(args.restart)
        print(msg)
        return 0 if ok else 1

    if args.start_all:
        results = manager.start_all()
        print(render_operation_results(results))
        return 0

    if args.stop_all:
        results = manager.stop_all()
        print(render_operation_results(results))
        return 0

    if args.save:
        try:
            manager.save_to_file(args.save)
            print(f"已保存实例配置到: {args.save}")
            return 0
        except OSError as e:
            print(f"错误: 保存失败: {e}", file=sys.stderr)
            return 2

    if args.load:
        try:
            count = manager.load_from_file(args.load)
            print(f"已从 {args.load} 加载 {count} 个实例")
            return 0
        except FileNotFoundError as e:
            print(f"错误: 文件不存在: {e}", file=sys.stderr)
            return 2
        except (json.JSONDecodeError, KeyError) as e:
            print(f"错误: 加载失败: {e}", file=sys.stderr)
            return 2

    # 无参数时显示帮助
    print("用法: instance [选项]")
    print("")
    print("选项:")
    print("  --list                    列出所有实例")
    print("  --summary                 显示管理器摘要")
    print("  --add NAME                添加实例")
    print("  --remove NAME             移除实例")
    print("  --info NAME               显示实例详情")
    print("  --start NAME              启动实例")
    print("  --stop NAME               停止实例")
    print("  --restart NAME            重启实例")
    print("  --start-all               启动所有实例")
    print("  --stop-all                停止所有实例")
    print("  --save FILE               保存实例配置到文件")
    print("  --load FILE               从文件加载实例配置")
    print("")
    print("添加实例时的选项:")
    print("  --env-opt ENV             实例环境")
    print("  --port-opt PORT           实例端口")
    print("  --max-loops-opt N         最大循环数")
    print("  --dry-run-opt             试运行模式")
    print("  --desc DESC               实例说明")
    return 0


def _check_python_version() -> tuple:
    version = sys.version_info
    if version >= (3, 10):
        return True, f"{version.major}.{version.minor}.{version.micro}"
    return False, f"需要 3.10+，当前 {version.major}.{version.minor}"


def _check_config(env: str) -> tuple:
    try:
        _load_and_validate(env)
        return True, "配置加载与校验通过"
    except ConfigurationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"未知错误: {e}"


def _check_dependencies() -> tuple:
    missing: List[str] = []
    for dep in ["yaml", "psutil"]:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    if missing:
        return False, f"缺少依赖: {', '.join(missing)}"
    return True, "所有核心依赖已安装"


def _print_config_hint(env: str) -> None:
    """配置错误时打印修复建议。"""
    print(f"\n提示: 请检查配置文件 right/cfg/left/dev/{env}.yaml 是否存在且格式正确。", file=sys.stderr)
    print("可运行 'python -m root.left.app.left.src.cli config --show-defaults' 查看默认配置。", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="self-evolving-agent",
        description="自驱永续进化 Agent - 统一命令行入口",
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run
    run_parser = subparsers.add_parser("run", help="启动 Agent 运行主循环")
    run_parser.add_argument("--env", default="dev", help="环境名称 (默认 dev)")
    run_parser.add_argument("--max-loops", type=int, default=None, help="最大循环次数 (0=无限)")
    run_parser.add_argument("--loop-interval", type=float, default=None, help="循环间隔秒数")
    run_parser.add_argument("--port", type=int, default=None, help="健康检查端口")
    run_parser.add_argument("--dry-run", action="store_true", help="强制 dry-run 模式")
    run_parser.add_argument(
        "--guide",
        action="store_true",
        help="交互式向导模式，逐步询问配置（需要交互式终端）",
    )
    run_parser.set_defaults(func=cmd_run)

    # status
    status_parser = subparsers.add_parser("status", help="查询运行中 Agent 的状态")
    status_parser.add_argument("--port", type=int, default=8080, help="Agent 端口 (默认 8080)")
    status_parser.set_defaults(func=cmd_status)

    # health
    health_parser = subparsers.add_parser("health", help="检查运行中 Agent 的健康状态")
    health_parser.add_argument("--port", type=int, default=8080, help="Agent 端口 (默认 8080)")
    health_parser.set_defaults(func=cmd_health)

    # validate
    validate_parser = subparsers.add_parser("validate", help="校验配置文件")
    validate_parser.add_argument("--env", default="dev", help="环境名称 (默认 dev)")
    validate_parser.set_defaults(func=cmd_validate)

    # config
    config_parser = subparsers.add_parser("config", help="查看配置")
    config_parser.add_argument("--show-defaults", action="store_true", help="显示默认配置")
    config_parser.add_argument("--describe", action="store_true", help="显示配置项说明")
    config_parser.add_argument("--env", default="dev", help="环境名称 (默认 dev)")
    config_parser.set_defaults(func=cmd_config)

    # doctor
    doctor_parser = subparsers.add_parser("doctor", help="自诊断")
    doctor_parser.set_defaults(func=cmd_doctor)

    # diagnose
    diagnose_parser = subparsers.add_parser("diagnose", help="深度诊断 Agent 模块状态")
    diagnose_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    diagnose_parser.set_defaults(func=cmd_diagnose)

    # welcome
    welcome_parser = subparsers.add_parser("welcome", help="首次使用介绍")
    welcome_parser.set_defaults(func=cmd_welcome)

    # help
    help_parser = subparsers.add_parser("help", help="查看命令帮助")
    help_parser.add_argument(
        "command_name",
        nargs="?",
        default=None,
        help="要查看帮助的命令名（留空显示所有命令概览）",
    )
    help_parser.set_defaults(func=cmd_help)

    # examples
    examples_parser = subparsers.add_parser("examples", help="常见使用场景示例")
    examples_parser.set_defaults(func=cmd_examples)

    # init
    init_parser = subparsers.add_parser("init", help="从模板创建配置文件")
    init_parser.add_argument("--list", action="store_true", help="列出所有可用模板")
    init_parser.add_argument("--show", default=None, metavar="TEMPLATE", help="查看指定模板内容")
    init_parser.add_argument("--template", default=None, metavar="TEMPLATE", help="使用指定模板创建配置")
    init_parser.add_argument("--env", default="dev", help="目标环境名称 (默认 dev)")
    init_parser.add_argument("--force", action="store_true", help="覆盖已有配置文件")
    init_parser.set_defaults(func=cmd_init)

    # control
    control_parser = subparsers.add_parser("control", help="运行时控制 Agent（暂停/恢复/停止/重载/状态）")
    control_parser.add_argument(
        "action",
        choices=["pause", "resume", "stop", "reload", "status"],
        help="控制动作: pause(暂停) resume(恢复) stop(停止) reload(热重载) status(状态)",
    )
    control_parser.add_argument("--port", type=int, default=8080, help="Agent 端口 (默认 8080)")
    control_parser.add_argument("--env", default="dev", help="reload 时使用的环境名称 (默认 dev)")
    control_parser.set_defaults(func=cmd_control)

    # docs
    docs_parser = subparsers.add_parser("docs", help="查看用户文档")
    docs_parser.add_argument(
        "topic",
        nargs="?",
        default=None,
        help="文档主题: quickstart(快速入门) commands(命令参考) config(配置指南) "
             "troubleshooting(故障排查) faq(常见问题)",
    )
    docs_parser.set_defaults(func=cmd_docs)

    # logs
    logs_parser = subparsers.add_parser("logs", help="查看与分析日志文件")
    logs_parser.add_argument("file", help="日志文件路径")
    logs_parser.add_argument("--level", default=None, help="按级别过滤 (DEBUG/INFO/WARNING/ERROR/CRITICAL)")
    logs_parser.add_argument("--module", default=None, help="按模块过滤（子串匹配）")
    logs_parser.add_argument("--keyword", default=None, help="按消息关键字过滤（子串匹配）")
    logs_parser.add_argument("--tail", type=int, default=None, help="只显示最后 N 条")
    logs_parser.add_argument("--stats", action="store_true", help="显示日志统计而非条目")
    logs_parser.add_argument("--no-module", action="store_true", help="不显示模块名")
    logs_parser.set_defaults(func=cmd_logs)

    # report
    report_parser = subparsers.add_parser("report", help="生成运行报告")
    report_parser.add_argument("file", help="日志文件路径")
    report_parser.add_argument("--env", default="dev", help="环境名称 (默认 dev)")
    report_parser.add_argument("--loop-count", type=int, default=0, help="循环次数")
    report_parser.add_argument("--duration", type=float, default=0.0, help="运行时长（秒）")
    report_parser.add_argument("--health", default="unknown", help="健康状态")
    report_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    report_parser.add_argument("--output", default=None, help="保存报告到文件")
    report_parser.set_defaults(func=cmd_report)

    # completion
    completion_parser = subparsers.add_parser("completion", help="生成或安装 Shell 补全脚本")
    completion_parser.add_argument(
        "--shell",
        default=None,
        choices=["bash", "zsh"],
        help="目标 shell（不指定则自动检测）",
    )
    completion_parser.add_argument(
        "--install",
        action="store_true",
        help="显示安装指引而非打印脚本",
    )
    completion_parser.add_argument(
        "--command-name",
        default="agent",
        metavar="NAME",
        help="命令名（默认 agent）",
    )
    completion_parser.set_defaults(func=cmd_completion)

    # install
    install_parser = subparsers.add_parser("install", help="安装一键启动脚本")
    install_parser.add_argument(
        "--command-name",
        default="agent",
        metavar="NAME",
        help="命令名（默认 agent）",
    )
    install_parser.add_argument(
        "--install-dir",
        default=None,
        metavar="DIR",
        help="安装目录（默认 ~/.local/bin）",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="覆盖已有启动脚本",
    )
    install_parser.set_defaults(func=cmd_install)

    # diff
    diff_parser = subparsers.add_parser("diff", help="配置差异对比与变更审计")
    diff_parser.add_argument("--env", default="dev", help="环境名称 (默认 dev)")
    diff_parser.add_argument("--against", default=None, metavar="ENV", help="对比的目标环境")
    diff_parser.add_argument("--against-defaults", action="store_true", help="对比环境与默认配置")
    diff_parser.add_argument("--file", default=None, metavar="FILE", help="基准配置文件")
    diff_parser.add_argument("--file2", default=None, metavar="FILE", help="目标配置文件")
    diff_parser.add_argument("--audit", action="store_true", help="生成审计报告")
    diff_parser.add_argument("--describe", action="store_true", help="显示配置项说明")
    diff_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    diff_parser.add_argument("--output", default=None, help="保存报告到文件")
    diff_parser.set_defaults(func=cmd_diff)

    # benchmark
    benchmark_parser = subparsers.add_parser("benchmark", help="性能基准与资源占用报告")
    benchmark_parser.add_argument("--env", default="dev", help="环境名称 (默认 dev)")
    benchmark_parser.add_argument("--iterations", type=int, default=10, help="迭代次数 (默认 10)")
    benchmark_parser.add_argument("--monitor", action="store_true", help="资源监控模式（持续采样）")
    benchmark_parser.add_argument("--interval", type=float, default=1.0, help="监控采样间隔秒数 (默认 1.0)")
    benchmark_parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    benchmark_parser.add_argument("--output", default=None, help="保存报告到文件")
    benchmark_parser.set_defaults(func=cmd_benchmark)

    # repl
    repl_parser = subparsers.add_parser("repl", help="启动交互式 REPL")
    repl_parser.add_argument(
        "--history-file",
        default=None,
        metavar="FILE",
        help="命令历史文件路径（默认 ~/.agent_history）",
    )
    repl_parser.add_argument(
        "--force",
        action="store_true",
        help="在非交互式环境强制启动",
    )
    repl_parser.set_defaults(func=cmd_repl)

    # alert
    alert_parser = subparsers.add_parser("alert", help="告警系统管理")
    alert_parser.add_argument("--list-rules", action="store_true", help="列出所有告警规则")
    alert_parser.add_argument("--summary", action="store_true", help="显示告警系统摘要")
    alert_parser.add_argument("--test", action="store_true", help="用测试指标触发告警")
    alert_parser.add_argument("--evaluate", default=None, metavar="JSON", help="评估指定指标是否触发告警")
    alert_parser.set_defaults(func=cmd_alert)

    # schedule
    schedule_parser = subparsers.add_parser("schedule", help="定时任务调度")
    schedule_parser.add_argument("--list", action="store_true", help="列出所有定时任务")
    schedule_parser.add_argument("--presets", action="store_true", help="显示预设 cron 表达式")
    schedule_parser.add_argument("--summary", action="store_true", help="显示调度器摘要")
    schedule_parser.add_argument("--add", nargs=3, metavar=("NAME", "CRON", "COMMAND"), help="添加任务")
    schedule_parser.add_argument("--remove", metavar="NAME", help="移除任务")
    schedule_parser.add_argument("--enable", metavar="NAME", help="启用任务")
    schedule_parser.add_argument("--disable", metavar="NAME", help="禁用任务")
    schedule_parser.add_argument("--next", action="store_true", help="显示下次执行时间")
    schedule_parser.add_argument("--history", action="store_true", help="显示执行历史")
    schedule_parser.add_argument("--validate", metavar="CRON", help="校验 cron 表达式")
    schedule_parser.add_argument("--test", metavar="CRON", help="测试 cron 表达式下次匹配时间")
    schedule_parser.set_defaults(func=cmd_schedule)

    # data
    data_parser = subparsers.add_parser("data", help="数据导入导出与备份恢复")
    data_parser.add_argument("--export", metavar="FILE", help="导出数据到 JSON 文件")
    data_parser.add_argument("--import", metavar="FILE", dest="import_file", help="从 JSON 文件导入数据")
    data_parser.add_argument("--backup", metavar="FILE", help="创建备份归档（tar.gz）")
    data_parser.add_argument("--restore", metavar="FILE", help="从备份归档恢复")
    data_parser.add_argument("--list-backups", action="store_true", help="列出备份文件")
    data_parser.add_argument("--verify", metavar="FILE", help="验证备份完整性")
    data_parser.add_argument("--type", default="all", choices=["all", "config", "state", "reports"], help="数据类型")
    data_parser.add_argument("--env", default="dev", help="环境名")
    data_parser.add_argument("--dir", default=None, help="备份目录（用于 --list-backups）")
    data_parser.set_defaults(func=cmd_data)

    # instance
    instance_parser = subparsers.add_parser("instance", help="多实例管理与编排")
    instance_parser.add_argument("--list", action="store_true", help="列出所有实例")
    instance_parser.add_argument("--summary", action="store_true", help="显示管理器摘要")
    instance_parser.add_argument("--add", nargs="+", metavar="NAME", help="添加实例（NAME [--env ENV] [--port PORT] [--max-loops N] [--dry-run]）")
    instance_parser.add_argument("--remove", metavar="NAME", help="移除实例")
    instance_parser.add_argument("--info", metavar="NAME", help="显示实例详情")
    instance_parser.add_argument("--start", metavar="NAME", help="启动实例")
    instance_parser.add_argument("--stop", metavar="NAME", help="停止实例")
    instance_parser.add_argument("--restart", metavar="NAME", help="重启实例")
    instance_parser.add_argument("--start-all", action="store_true", help="启动所有实例")
    instance_parser.add_argument("--stop-all", action="store_true", help="停止所有实例")
    instance_parser.add_argument("--save", metavar="FILE", help="保存实例配置到文件")
    instance_parser.add_argument("--load", metavar="FILE", help="从文件加载实例配置")
    instance_parser.add_argument("--env-opt", default=None, help="实例环境（用于 --add）")
    instance_parser.add_argument("--port-opt", type=int, default=None, help="实例端口（用于 --add）")
    instance_parser.add_argument("--max-loops-opt", type=int, default=None, help="最大循环数（用于 --add）")
    instance_parser.add_argument("--dry-run-opt", action="store_true", help="试运行模式（用于 --add）")
    instance_parser.add_argument("--desc", default="", help="实例说明（用于 --add）")
    instance_parser.set_defaults(func=cmd_instance)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """CLI 主入口。"""
    parser = build_parser()

    # 拦截未知命令，提供智能建议
    if argv is None:
        argv = sys.argv[1:]

    if argv:
        first_arg = argv[0]
        # 仅对非选项参数（不以 - 开头）检查
        if not first_arg.startswith("-"):
            known_commands = set()
            for action in parser._actions:
                if isinstance(action, argparse._SubParsersAction):
                    known_commands.update(action.choices.keys())
            if first_arg not in known_commands:
                from root.left.app.left.src.utils_main.command_suggest import format_did_you_mean
                suggestion = format_did_you_mean(first_arg)
                if suggestion:
                    print(suggestion, file=sys.stderr)
                    print("", file=sys.stderr)
                    print("提示: 输入 'help' 查看所有可用命令。", file=sys.stderr)
                    return 2
                # 无建议时也返回 2，避免 argparse 的 SystemExit
                print(f"错误: 未知命令 '{first_arg}'", file=sys.stderr)
                print("提示: 输入 'help' 查看所有可用命令。", file=sys.stderr)
                return 2

    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if e.code is not None else 0

    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
