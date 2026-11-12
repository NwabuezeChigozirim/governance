#!/usr/bin/env python3
"""Cursor hook guard for governed work.

pre-tool-use
  Always: an agent cannot record owner approval, and cannot touch stage state.
  While a stage is active in this worktree: destructive or unclassified Git commands
  are blocked for owner review.
stop
  While a stage is active and not ready to close, send the agent back once with the
  list of what is still unproven.

Cursor's generic preToolUse does not enforce "ask", so a review request is a visible
deny. No objection prints {} and leaves Cursor's own permission checks in place.
"""

from __future__ import annotations

from importlib.machinery import SourceFileLoader
import importlib.util
import json
import os
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hook_policy  # noqa: E402

APPROVAL = re.compile(r"\bstagectl\b.*--owner-approved|--owner-approved.*\bstagectl\b", re.DOTALL)
STATE = "governance-v3"


def load_stagectl():
    path = HERE.parent / "scripts" / "stagectl"
    loader = SourceFileLoader("stagectl", str(path))
    module = importlib.util.module_from_spec(importlib.util.spec_from_loader("stagectl", loader))
    loader.exec_module(module)
    return module


def worktree(stagectl, payload: dict) -> Path | None:
    for candidate in (os.environ.get("CURSOR_PROJECT_DIR"), payload.get("cwd"), os.getcwd()):
        if candidate:
            try:
                return stagectl.worktree_root(candidate)
            except Exception:
                continue
    return None


def deny(reason: str) -> dict[str, str]:
    return {"permission": "deny", "user_message": reason, "agent_message": reason}


def pre_tool_use(payload: dict) -> dict[str, str]:
    command, target = hook_policy.action(payload)
    if command and APPROVAL.search(command):
        return deny("Governance: only the owner records approval. Show the owner the contract and ask them to run "
                    "this stagectl command themselves; do not retry it.")
    if (command and STATE in command and "stagectl" not in command) or (target and STATE in Path(target).parts):
        return deny("Governance: stage records are written only by stagectl. Do not read around or edit them.")
    if not command:
        return {}
    stagectl = load_stagectl()
    root = worktree(stagectl, payload)
    if root is None or not stagectl.pointer_path(root).is_file():
        return {}
    if hook_policy.command_requires_review(command):
        return deny("Governance: a stage is active in this worktree, and this Git operation can discard or rewrite "
                    "work. Ask the owner to review and run it, or use a non-destructive alternative.")
    return {}


def stop(payload: dict) -> dict[str, str]:
    if payload.get("stop_hook_active") or payload.get("status") in {"aborted", "error"}:
        return {}
    stagectl = load_stagectl()
    root = worktree(stagectl, payload)
    if root is None or not stagectl.pointer_path(root).is_file():
        return {}
    report = stagectl.inspect(root)
    if report["ready"]:
        return {"followup_message": f"Stage {report['stage_id']} has current evidence for every check. "
                                    "Close it with `stagectl close` and report the receipt."}
    problems = "; ".join(problem["message"] for problem in report["problems"][:8])
    return {"followup_message": f"Stage {report['stage_id']} ({report['name']}) is not proven yet: {problems}. "
                                "Finish proving it, or state plainly what blocks you. Do not claim it is done."}


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    raw = sys.stdin.buffer.read(hook_policy.MAX_PAYLOAD + 1)
    try:
        payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        result = pre_tool_use(payload) if event == "pre-tool-use" else stop(payload) if event == "stop" else {}
    except Exception:
        # A broken guard must not silently let an approval through, and must not
        # block every tool in every project either.
        risky = event == "pre-tool-use" and (b"owner-approved" in raw or STATE.encode() in raw)
        result = deny("Governance: the guard could not evaluate this action; repair the plugin and retry.") if risky else {}
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
