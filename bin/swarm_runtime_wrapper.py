#!/usr/bin/env python3
"""Thin Claude-side wrapper for the v2 swarm runtime contract.

Contains no discussion mechanics. It discovers the vendored runtime CLI, checks
the runtime contract, records host nesting support, and delegates the
integration gates and runtime primitives. The discussion protocol lives in the
vendored runtime's `protocol/` and is driven by the swarm-coordinator background session.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ENV_RUNTIME = "SWARM_DISCUSSION_RUNTIME"
COMPATIBILITY = "swarm-runtime-v2-alpha"
ADAPTER_SMOKE = "adapter-smoke"
RUNTIME_CONTRACT = "runtime-contract"
VALIDATE_LOOP = "validate-loop"
# Vendor bundle layout (produced by the runtime repo's scripts/vendor.py):
VENDOR_SUBDIR = ("vendor", "swarm-runtime")
BUNDLED_CLI = (*VENDOR_SUBDIR, "runtime", "swarm_rt.py")
FIXTURE_REL = (*VENDOR_SUBDIR, "fixtures", "e2e", "minimal-v2")
MIN_NESTING_VERSION = (2, 1, 172)
MIN_AGENT_VIEW_VERSION = (2, 1, 139)
PRIMITIVE_COMMANDS = [
    "context-build",
    "prompt-build",
    "collect-merge",
    "transport-init",
    "transport-append-batch",
    "transport-collect",
    "append-message",
    "checkpoint",
    "finalize-round",
    "resume-plan",
    "validate-round",
    "validate-discussion",
    "trace",
    "evidence",
    "validate-host-step",
    "capability-doctor",
    "init",
]


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def display_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def command_from_string(value: str) -> list[str]:
    parts = shlex.split(value)
    if not parts:
        raise ValueError("empty runtime command")
    first = Path(parts[0]).expanduser()
    if first.suffix == ".py" and first.exists():
        return [sys.executable, str(first), *parts[1:]]
    if first.exists():
        return [str(first), *parts[1:]]
    return parts


def runtime_candidates(explicit: str | None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    if explicit:
        candidates.append({"source": "--runtime", "command": command_from_string(explicit)})

    env_value = os.environ.get(ENV_RUNTIME)
    if env_value:
        candidates.append({"source": ENV_RUNTIME, "command": command_from_string(env_value)})

    bundled = plugin_root().joinpath(*BUNDLED_CLI)
    if bundled.exists():
        candidates.append({"source": "vendored", "command": [sys.executable, str(bundled)]})

    path_runtime = shutil.which("swarm-rt")
    if path_runtime:
        candidates.append({"source": "PATH", "command": [path_runtime]})

    seen: set[tuple[str, ...]] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        key = tuple(candidate["command"])
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def run(command: list[str], args: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            [*command, *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    except OSError as exc:
        return {"ok": False, "returncode": None, "stdout": "", "stderr": str(exc), "json": None}

    parsed: Any | None = None
    if completed.stdout.strip():
        try:
            parsed = json.loads(completed.stdout)
        except json.JSONDecodeError:
            parsed = None
    return {
        "ok": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "json": parsed,
    }


def contract_ok(payload: Any) -> bool:
    if not isinstance(payload, dict) or payload.get("ok") is not True:
        return False
    contract = payload.get("contract")
    if not isinstance(contract, dict):
        return False
    runtime = contract.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("compatibility") != COMPATIBILITY:
        return False
    commands = contract.get("commands")
    if not isinstance(commands, dict):
        return False
    required = {ADAPTER_SMOKE, VALIDATE_LOOP, *PRIMITIVE_COMMANDS}
    return required <= set(commands)


def contract_summary(payload: dict[str, Any]) -> dict[str, Any]:
    validation = payload.get("validation")
    if not isinstance(validation, dict):
        return {}
    summary = validation.get("summary")
    return summary if isinstance(summary, dict) else {}


def plugin_fixture_dir() -> Path:
    return plugin_root().joinpath(*FIXTURE_REL)


def host_nesting() -> dict[str, Any]:
    """Record whether this host supports nested sub-agent spawning.

    Nested spawning is a Claude Code host capability (>= 2.1.172), not a
    runtime property; the wrapper records it by reading `claude --version`.
    """
    claude = shutil.which("claude")
    if not claude:
        return {"supported": None, "version": None, "reason": "claude not on PATH", "minVersion": ".".join(map(str, MIN_NESTING_VERSION))}
    try:
        out = subprocess.run([claude, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except OSError as exc:
        return {"supported": None, "version": None, "reason": str(exc), "minVersion": ".".join(map(str, MIN_NESTING_VERSION))}
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", out.stdout)
    if not match:
        return {"supported": None, "version": out.stdout.strip() or None, "reason": "could not parse version", "minVersion": ".".join(map(str, MIN_NESTING_VERSION))}
    version = tuple(int(g) for g in match.groups())
    return {
        "supported": version >= MIN_NESTING_VERSION,
        "version": ".".join(map(str, version)),
        "minVersion": ".".join(map(str, MIN_NESTING_VERSION)),
    }


def host_background_sessions() -> dict[str, Any]:
    """Record whether this host supports background sessions (`claude --bg` / agent view).

    The v0.3.0 coordinator runs as a background session — the only Claude path that
    can spawn dynamically-projected `.claude/agents` files (they load at a fresh
    session's start). Capability is probed with `claude agents --json`, which prints
    a JSON array when agent view is available and errors / prints subagents when it
    is not. The skill stops if this is not `true` (no silent fallback; ADR 0001 D2).
    """
    min_version = ".".join(map(str, MIN_AGENT_VIEW_VERSION))
    claude = shutil.which("claude")
    if not claude:
        return {"supported": None, "probe": "claude agents --json", "reason": "claude not on PATH", "minVersion": min_version}
    try:
        out = subprocess.run([claude, "agents", "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    except OSError as exc:
        return {"supported": None, "probe": "claude agents --json", "reason": str(exc), "minVersion": min_version}
    parsed: Any | None = None
    if out.stdout.strip():
        try:
            parsed = json.loads(out.stdout)
        except json.JSONDecodeError:
            parsed = None
    supported = out.returncode == 0 and isinstance(parsed, list)
    return {
        "supported": supported,
        "probe": "claude agents --json",
        "returncode": out.returncode,
        "minVersion": min_version,
        "reason": None if supported else "claude agents --json did not return a JSON array (agent view unavailable or disabled)",
    }


def resolve_runtime(explicit: str | None) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for candidate in runtime_candidates(explicit):
        # The runtime prints a compact summary by default; --full restores the
        # contract object that contract_ok() inspects.
        result = run(candidate["command"], [RUNTIME_CONTRACT, "--full"])
        payload = result["json"]
        attempts.append(
            {
                "source": candidate["source"],
                "command": display_command(candidate["command"]),
                "returncode": result["returncode"],
                "contractOk": contract_ok(payload),
                "stderr": result["stderr"].strip(),
            }
        )
        if result["ok"] and contract_ok(payload):
            return {
                "ok": True,
                "runtime": {
                    "source": candidate["source"],
                    "command": candidate["command"],
                    "display": display_command(candidate["command"]),
                },
                "contract": payload,
                "attempts": attempts,
            }

    return {
        "ok": False,
        "errors": [
            {
                "code": "runtime_not_found",
                "message": (
                    f"Set {ENV_RUNTIME}, pass --runtime, vendor the runtime under "
                    "vendor/swarm-runtime, or install swarm-rt on PATH."
                ),
            }
        ],
        "attempts": attempts,
    }


def cmd_doctor(args: argparse.Namespace) -> int:
    resolved = resolve_runtime(args.runtime)
    ok = resolved["ok"]
    nesting = host_nesting()
    payload: dict[str, Any] = {
        "ok": ok,
        "wrapper": {
            "kind": "swarm.claude_runtime_wrapper",
            "compatibility": COMPATIBILITY,
            "path": str(Path(__file__).resolve()),
            "pluginRoot": str(plugin_root()),
            "fixtureDir": str(plugin_fixture_dir()),
        },
        "hostNesting": nesting,
        "hostBackgroundSessions": host_background_sessions(),
        "attempts": resolved["attempts"],
    }
    if resolved["ok"]:
        payload["runtime"] = {
            "source": resolved["runtime"]["source"],
            "command": resolved["runtime"]["display"],
        }
        payload["contractSummary"] = contract_summary(resolved["contract"])
        if args.smoke_fixture:
            fixture_dir = plugin_fixture_dir()
            smoke = run(resolved["runtime"]["command"], [ADAPTER_SMOKE, "--dir", str(fixture_dir)])
            smoke_json = smoke["json"] if isinstance(smoke["json"], dict) else {}
            payload["fixtureSmoke"] = {
                "ok": smoke["ok"],
                "dir": str(fixture_dir),
                "returncode": smoke["returncode"],
                "summary": smoke_json.get("summary"),
                "errors": smoke_json.get("errors"),
                "stderr": smoke["stderr"].strip(),
            }
            ok = ok and smoke["ok"]
            payload["ok"] = ok
    else:
        payload["errors"] = resolved["errors"]
    emit(payload)
    return 0 if ok else 1


def _delegate(args: argparse.Namespace, runtime_args: list[str]) -> int:
    resolved = resolve_runtime(args.runtime)
    if not resolved["ok"]:
        emit({"ok": False, "errors": resolved["errors"], "attempts": resolved["attempts"]})
        return 1
    result = run(resolved["runtime"]["command"], runtime_args)
    emit(
        {
            "ok": result["ok"],
            "wrapper": {"compatibility": COMPATIBILITY},
            "runtime": {
                "source": resolved["runtime"]["source"],
                "command": resolved["runtime"]["display"],
                "args": runtime_args,
                "returncode": result["returncode"],
            },
            "result": result["json"],
            "stderr": result["stderr"].strip(),
        }
    )
    return 0 if result["ok"] else 1


def cmd_runtime_contract(args: argparse.Namespace) -> int:
    return _delegate(args, [RUNTIME_CONTRACT])


def cmd_adapter_smoke(args: argparse.Namespace) -> int:
    runtime_args = [ADAPTER_SMOKE, "--dir", str(args.dir)]
    if args.host_step:
        runtime_args.extend(["--host-step", str(args.host_step)])
    return _delegate(args, runtime_args)


def cmd_validate_loop(args: argparse.Namespace) -> int:
    runtime_args = [VALIDATE_LOOP, str(args.dir)]
    if args.require_projection:
        runtime_args.append("--require-projection")
    if args.require_stress:
        runtime_args.append("--require-stress")
    return _delegate(args, runtime_args)


def cmd_runtime_primitive(args: argparse.Namespace) -> int:
    return _delegate(args, [args.runtime_command, *args.runtime_args])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarm-runtime-wrapper",
        description="Resolve and delegate to the vendored v2 swarm runtime CLI.",
    )
    parser.add_argument("--runtime", help=f"Runtime command override. Also supported through {ENV_RUNTIME}.")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="Check wrapper, runtime, and host nesting readiness")
    doctor.add_argument("--smoke-fixture", action="store_true", help="Run adapter-smoke against the vendored minimal fixture")
    doctor.set_defaults(func=cmd_doctor)

    contract = sub.add_parser(RUNTIME_CONTRACT, help="Emit the runtime contract through the wrapper")
    contract.set_defaults(func=cmd_runtime_contract)

    smoke = sub.add_parser(ADAPTER_SMOKE, help="Run runtime adapter-smoke through the wrapper")
    smoke.add_argument("--dir", type=Path, required=True, help="Discussion directory")
    smoke.add_argument("--host-step", type=Path, help="Optional host-step path")
    smoke.set_defaults(func=cmd_adapter_smoke)

    loop = sub.add_parser(VALIDATE_LOOP, help="Run runtime validate-loop through the wrapper")
    loop.add_argument("dir", type=Path, help="Discussion directory")
    loop.add_argument("--require-projection", action="store_true", help="Require projected custom-agent provenance (v0.3.0 release mode)")
    loop.add_argument("--require-stress", action="store_true", help="Require the declared stressPolicy be satisfied (engineered disagreement; ADR 0002)")
    loop.set_defaults(func=cmd_validate_loop)

    for command in PRIMITIVE_COMMANDS:
        primitive = sub.add_parser(command, help=f"Delegate runtime {command}")
        primitive.add_argument("runtime_args", nargs=argparse.REMAINDER)
        primitive.set_defaults(func=cmd_runtime_primitive, runtime_command=command)

    return parser


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    runtime_override: str | None = None
    index = 0
    while index < len(raw):
        item = raw[index]
        if item == "--runtime" and index + 1 < len(raw):
            runtime_override = raw[index + 1]
            index += 2
            continue
        if item.startswith("--runtime="):
            runtime_override = item.split("=", 1)[1]
            index += 1
            continue
        break

    if index < len(raw) and raw[index] in PRIMITIVE_COMMANDS:
        args = argparse.Namespace(
            runtime=runtime_override,
            runtime_command=raw[index],
            runtime_args=raw[index + 1 :],
        )
        return cmd_runtime_primitive(args)

    parser = build_parser()
    args, unknown = parser.parse_known_args(raw)
    if unknown:
        parser.error(f"unrecognized arguments: {' '.join(unknown)}")
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
