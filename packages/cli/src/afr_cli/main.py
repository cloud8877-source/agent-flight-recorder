from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import httpx
import yaml

from afr_cli.client import AFRClient


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _resolve_run_id(client: AFRClient, spec: dict, root: Path) -> str:
    fixture = spec.get("fixture") or {}
    script = fixture.get("script")
    if script:
        script_path = (root / script).resolve()
        if not script_path.exists():
            raise FileNotFoundError(f"fixture script not found: {script_path}")
        env = {**os.environ, "AFR_ENDPOINT": client.endpoint}
        subprocess.run([sys.executable, str(script_path)], check=True, env=env)
        runs = client.list_runs(limit=1)
        if not runs:
            raise RuntimeError("fixture script did not produce any runs")
        return runs[0]["id"]

    source_run_id = spec.get("source_run_id")
    if source_run_id:
        client.get_run(source_run_id)
        return source_run_id

    raise ValueError("regression test requires fixture.script or source_run_id")


def cmd_replay(args: argparse.Namespace) -> int:
    client = AFRClient(args.endpoint)
    mode = "model" if args.model else args.mode
    result = client.create_replay(args.run_id, mode=mode, model=args.model)
    print(f"replay {result['id']} ({result['mode']}) status={result['status']}")
    if result.get("result", {}).get("changes"):
        for change in result["result"]["changes"]:
            print(f"  {change['span']}: {change['field']} {change['from']} -> {change['to']}")
    return 0


def cmd_eval_run(args: argparse.Namespace) -> int:
    client = AFRClient(args.endpoint)
    spec_path = Path(args.yaml_file)
    spec = _load_yaml(spec_path)
    root = Path.cwd()

    run_id = args.run_id
    if not run_id:
        if spec.get("type") == "regression":
            run_id = _resolve_run_id(client, spec, root)
        else:
            run_id = spec.get("source_run_id")
    if not run_id:
        raise SystemExit("run id required: pass --run-id or include source_run_id/fixture in YAML")

    result = client.run_eval(run_id, eval_yaml=spec_path.read_text(encoding="utf-8"))

    print(f"eval {result.get('evaluator_name')} score={result.get('score')} passed={result.get('passed')}")
    if not result.get("passed"):
        for failure in result.get("failures") or []:
            print(f"  - {failure}")
        return 1
    return 0


def cmd_test(args: argparse.Namespace) -> int:
    client = AFRClient(args.endpoint)
    test_dir = Path(args.directory)
    if not test_dir.is_dir():
        raise SystemExit(f"not a directory: {test_dir}")

    root = Path.cwd()
    files = sorted(test_dir.glob("*.yml")) + sorted(test_dir.glob("*.yaml"))
    if not files:
        raise SystemExit(f"no YAML tests found in {test_dir}")

    failures: list[str] = []
    for path in files:
        spec = _load_yaml(path)
        if spec.get("type") != "regression":
            print(f"skip {path.name}: only regression suites supported in afr test")
            continue

        try:
            run_id = _resolve_run_id(client, spec, root)
            result = client.run_eval(run_id, eval_yaml=path.read_text(encoding="utf-8"))
            status = "PASS" if result.get("passed") else "FAIL"
            print(f"{status} {path.name} score={result.get('score')} run={run_id}")
            if not result.get("passed"):
                failures.append(path.name)
                for failure in result.get("failures") or []:
                    print(f"  - {failure}")
        except Exception as exc:
            failures.append(path.name)
            print(f"FAIL {path.name}: {exc}")

    if failures:
        print(f"\n{len(failures)} regression test(s) failed")
        return 1

    print(f"\nAll {len(files)} regression test(s) passed")
    return 0


def cmd_policy_list(args: argparse.Namespace) -> int:
    client = AFRClient(args.endpoint)
    policies = client.list_policies()
    for policy in policies:
        print(f"{policy['name']}\t{policy.get('description') or ''}")
    print(f"{len(policies)} policies")
    return 0


def cmd_policy_load(args: argparse.Namespace) -> int:
    client = AFRClient(args.endpoint)
    content = Path(args.yaml_file).read_text(encoding="utf-8")
    result = client.load_policy(content)
    print(f"loaded {result['name']} ({result['id']})")
    return 0


def cmd_policy_check(args: argparse.Namespace) -> int:
    client = AFRClient(args.endpoint)
    result = client.policy_check(args.run_id)
    print(f"violations={result.get('violation_count', 0)}")
    for violation in result.get("violations") or []:
        print(f"  [{violation['severity']}] {violation['action']}: {violation['message']}")
    return 1 if result.get("violation_count") else 0


def cmd_export_regression(args: argparse.Namespace) -> int:
    client = AFRClient(args.endpoint)
    content = client.regression_yaml(args.run_id)
    out = Path(args.output) if args.output else Path(f"{args.run_id}-regression.yml")
    out.write_text(content, encoding="utf-8")
    print(f"wrote {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="afr", description="Agent Flight Recorder CLI")
    parser.add_argument(
        "--endpoint",
        default=os.environ.get("AFR_ENDPOINT", "http://127.0.0.1:4318"),
        help="Collector API base URL",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    replay = sub.add_parser("replay", help="Replay a stored agent run")
    replay.add_argument("run_id", help="agent_run id")
    replay.add_argument("--mode", choices=["exact", "model"], default="exact")
    replay.add_argument("--model", help="override model for model replay")
    replay.set_defaults(func=cmd_replay)

    eval_cmd = sub.add_parser("eval", help="Run evaluators")
    eval_sub = eval_cmd.add_subparsers(dest="eval_command", required=True)
    eval_run = eval_sub.add_parser("run", help="Run a single eval or regression YAML")
    eval_run.add_argument("yaml_file", help="path to eval YAML")
    eval_run.add_argument("--run-id", help="agent_run id (optional if YAML includes fixture/source_run_id)")
    eval_run.set_defaults(func=cmd_eval_run)

    test = sub.add_parser("test", help="Run regression test suite directory (CI)")
    test.add_argument("directory", help="directory containing regression YAML files")
    test.set_defaults(func=cmd_test)

    export = sub.add_parser("export", help="Export artifacts from stored runs")
    export_sub = export.add_subparsers(dest="export_command", required=True)
    export_regression = export_sub.add_parser("regression", help="Export regression YAML for a run")
    export_regression.add_argument("run_id", help="agent_run id")
    export_regression.add_argument("-o", "--output", help="output file path")
    export_regression.set_defaults(func=cmd_export_regression)

    policy = sub.add_parser("policy", help="Policy management and checks")
    policy_sub = policy.add_subparsers(dest="policy_command", required=True)
    policy_list = policy_sub.add_parser("list", help="List loaded policies")
    policy_list.set_defaults(func=cmd_policy_list)
    policy_load = policy_sub.add_parser("load", help="Load or update a policy YAML")
    policy_load.add_argument("yaml_file", help="path to policy YAML")
    policy_load.set_defaults(func=cmd_policy_load)
    policy_check = policy_sub.add_parser("check", help="Re-run policy checks for a run")
    policy_check.add_argument("run_id", help="agent_run id")
    policy_check.set_defaults(func=cmd_policy_check)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = args.func(args)
    except httpx.HTTPStatusError as exc:  # type: ignore[name-defined]
        print(f"API error: {exc.response.status_code} {exc.response.text}", file=sys.stderr)
        code = 1
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        code = 1
    raise SystemExit(code)


if __name__ == "__main__":
    main()