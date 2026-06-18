#!/usr/bin/env python3
"""Short OpenCode gate for a single local profile.

Runs three small OpenCode tasks and applies deterministic, conservative checks.
It is meant as a fast gate after smoke/tool-use, not as a full quality benchmark.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO = Path(r"D:\repos\ik_llama.cpp")
DEFAULT_OUTPUT_DIR = REPO / "bench-opencode-local"


@dataclass(frozen=True)
class GateTask:
    id: str
    prompt: str
    agent: str | None = None


TASKS: list[GateTask] = [
    GateTask(
        "explain-bug",
        "In massimo 8 righe, spiega il bug in questo pseudo-codice e proponi una fix: "
        "function getUser(id) { if (cache[id]) return cache[id]; user = db.find(id); "
        "cache[id] = user.name; return user; }",
    ),
    GateTask(
        "write-patch",
        "Scrivi una patch TypeScript minimale per rendere questa funzione sicura quando input e null o undefined: "
        "export function slugify(input: string) { return input.trim().toLowerCase().replaceAll(' ', '-'); }",
    ),
    GateTask(
        "review",
        "Fai una code review concisa di questa funzione C++ e indica i 3 rischi principali: "
        "const char* name(std::string s) { return s.c_str(); }",
    ),
]


def extract_text_from_opencode_lines(lines: list[str]) -> dict[str, Any]:
    text_parts: list[str] = []
    tokens = None
    for line in lines:
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            text_parts.append(line)
            continue
        if event.get("type") == "text":
            part = event.get("part") or {}
            text_parts.append(str(part.get("text") or ""))
        elif event.get("type") == "step_finish":
            part = event.get("part") or {}
            tokens = part.get("tokens")
    return {"text": "".join(text_parts), "tokens": tokens}


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(needle in low for needle in needles)


def evaluate_task(task_id: str, output: str) -> dict[str, Any]:
    low = output.lower()
    if task_id == "explain-bug":
        checks = {
            "mentions_cache": "cache" in low,
            "mentions_user_name": "user.name" in low or "nome" in low,
            "mentions_store_user": "cache[id] = user" in low or "intero" in low or "object" in low or "oggetto" in low,
        }
    elif task_id == "write-patch":
        checks = {
            "mentions_nullish_type": (
                "null" in low or "undefined" in low or "input?" in low or "input?: string" in low
            ),
            "guards_input": (
                "if (!input)" in low or "input == null" in low or "input === null" in low
                or "input ??" in low or "input ||" in low
            ),
            "keeps_slug_ops": "trim()" in low and "tolowercase()" in low and "replaceall" in low,
        }
    elif task_id == "review":
        checks = {
            "mentions_cstr": "c_str" in low,
            "mentions_dangling_or_lifetime": _contains_any(low, ("dangling", "lifetime", "vita", "scade", "locale")),
            "mentions_string_copy": "std::string" in low or "string" in low,
        }
    else:
        return {"pass": False, "verdict": "FAIL_UNKNOWN_TASK", "checks": {}}

    missing = [name for name, ok in checks.items() if not ok]
    return {
        "pass": not missing,
        "verdict": "PASS" if not missing else "FAIL_CHECKS",
        "checks": checks,
        "missing": missing,
    }


def resolve_opencode_command() -> str | None:
    for candidate in ("opencode.cmd", "opencode.exe", "opencode"):
        path = shutil.which(candidate)
        if path:
            return path
    return None


def run_opencode_task(project: Path, model: str, task: GateTask, timeout: int) -> dict[str, Any]:
    command = resolve_opencode_command()
    if not command:
        return {
            "id": task.id,
            "pass": False,
            "verdict": "FAIL_MISSING_OPENCODE",
            "exit_code": None,
            "elapsed_s": 0.0,
            "output": "",
        }

    args = [command, "run", "--dir", str(project), "--model", model, "--format", "json"]
    if task.agent:
        args += ["--agent", task.agent]
    args.append(task.prompt)

    t0 = time.time()
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        elapsed_s = time.time() - t0
    except FileNotFoundError as exc:
        return {
            "id": task.id,
            "pass": False,
            "verdict": "FAIL_MISSING_OPENCODE",
            "exit_code": None,
            "elapsed_s": round(time.time() - t0, 2),
            "output": str(exc),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "id": task.id,
            "pass": False,
            "verdict": "FAIL_TIMEOUT",
            "exit_code": None,
            "elapsed_s": round(time.time() - t0, 2),
            "output": (exc.stdout or "") + (exc.stderr or ""),
        }

    lines = (proc.stdout or "").splitlines()
    if proc.stderr:
        lines += proc.stderr.splitlines()
    parsed = extract_text_from_opencode_lines(lines)
    evaluation = evaluate_task(task.id, parsed["text"])
    return {
        "id": task.id,
        "pass": proc.returncode == 0 and evaluation["pass"],
        "verdict": evaluation["verdict"] if proc.returncode == 0 else "FAIL_EXIT",
        "exit_code": proc.returncode,
        "elapsed_s": round(elapsed_s, 2),
        "tokens": parsed["tokens"],
        "output_chars": len(parsed["text"]),
        "output": parsed["text"],
        "checks": evaluation.get("checks", {}),
        "missing": evaluation.get("missing", []),
    }


def run_gate(project: Path, model: str, timeout: int) -> dict[str, Any]:
    results = [run_opencode_task(project, model, task, timeout) for task in TASKS]
    passed = sum(1 for row in results if row["pass"])
    return {
        "model": model,
        "project": str(project),
        "status": "pass" if passed == len(results) else "fail",
        "passed": passed,
        "total": len(results),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--project", type=Path, default=REPO)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run_gate(args.project, args.model, args.timeout)
    out = args.out
    if out is None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        safe_model = args.model.replace("/", "_").replace(":", "_")
        out = DEFAULT_OUTPUT_DIR / f"opencode-gate-{safe_model}-{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({
        "model": report["model"],
        "status": report["status"],
        "passed": f"{report['passed']}/{report['total']}",
        "out": str(out),
    }, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
