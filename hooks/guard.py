#!/usr/bin/env python3
"""Cursor hook guard for governed work.

pre-tool-use
  Always: an agent cannot record owner approval, and cannot touch stage state or
  write a stage receipt by hand.
  While a stage is active in this worktree: destructive or unclassified Git commands
  are blocked for owner review.
  In a project whose .governance/config.json sets require_stage: file edits are
  blocked until a stage is frozen, and the agent cannot edit that config.
  In a project with .governance/rules.json: the rule file, the linter and type-checker
  configs and the governance workflow can be edited only when the frozen contract
  lists the file in its outputs, and the baseline cannot be edited by hand.
stop
  While a stage is active and not ready to close, send the agent back once with the
  list of what is still unproven. In a require_stage project with no active stage,
  send it back once when governed files changed and no receipt covers them.

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

APPROVAL = re.compile(r"\b(stagectl|rulekit)\b.*--owner-approved|--owner-approved.*\b(stagectl|rulekit)\b", re.DOTALL)
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


def inside(root: Path, target: str) -> str | None:
    """Repository-relative form of an edit target, or None when it is outside the worktree."""
    path = Path(target)
    try:
        return (path if path.is_absolute() else root / path).resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        return None


def unproven_changes(stagectl, root: Path) -> list[str]:
    """Governed files changed against HEAD that no receipt covers."""
    settings = stagectl.config(root)
    if not settings["require_stage"]:
        return []
    listing = stagectl.git(root, "status", "--porcelain", "--untracked-files=all")
    changed = sorted({line[3:].split(" -> ")[-1].strip('"') for line in listing.splitlines() if len(line) > 3})
    changed = [name for name in changed if not stagectl.exempt(root, name, settings)]
    if not changed:
        return []
    tree = stagectl.governed_tree(root)
    return [] if any(item["tree"] == tree for item in stagectl.receipts(root)) else changed


def approved_outputs(stagectl, root: Path) -> set[str]:
    """Outputs of the frozen contract: the files the owner agreed this stage may produce."""
    try:
        outputs = stagectl.active(root)[2]["contract"]["outputs"]
    except Exception:
        return set()
    return {relative for relative in (inside(root, value) for value in outputs) if relative}


def deny(reason: str) -> dict[str, str]:
    return {"permission": "deny", "user_message": reason, "agent_message": reason}


def pre_tool_use(payload: dict) -> dict[str, str]:
    command, target = hook_policy.action(payload)
    if command and APPROVAL.search(command):
        return deny("Governance: only the owner records approval. Show the owner the contract and ask them to run "
                    "this command themselves; do not retry it.")
    if (command and STATE in command and "stagectl" not in command) or (target and STATE in Path(target).parts):
        return deny("Governance: stage records are written only by stagectl. Do not read around or edit them.")
    if not command and not target:
        return {}
    stagectl = load_stagectl()
    root = worktree(stagectl, payload)
    if root is None:
        return {}
    staged = stagectl.pointer_path(root).is_file()
    if target:
        relative = inside(root, target)
        if relative is None:
            return {}
        if relative.startswith(stagectl.RECEIPTS + "/"):
            return deny("Governance: a stage receipt is written only by `stagectl close`. Do not create or edit one.")
        settings = stagectl.config(root)
        if relative == stagectl.BASELINE and (root / stagectl.RULES).is_file():
            return deny("Governance: the baseline is written only by `rulekit baseline`, and it only shrinks. "
                        "Fix the violation instead.")
        if stagectl.protected(root, relative, settings) and relative not in approved_outputs(stagectl, root):
            return deny(f"Governance: {relative} sets how strict the checks are. Fix the code, not the check. If the "
                        "task really is to change this file, list it in the contract's outputs so the owner "
                        "sees it when freezing (or revising) the stage, then retry.")
        if not settings["require_stage"]:
            return {}
        if relative == stagectl.CONFIG:
            return deny("Governance: only the owner changes .governance/config.json. Tell them what you need changed.")
        if not staged and not stagectl.exempt(root, relative, settings):
            return deny("Governance: this project requires a stage before files change. Restate the intent, write "
                        "the contract under .governance/stages/, show it to the owner and ask them to freeze it "
                        "(the stage skill). Then retry this edit.")
        return {}
    if staged and hook_policy.command_requires_review(command):
        return deny("Governance: a stage is active in this worktree, and this Git operation can discard or rewrite "
                    "work. Ask the owner to review and run it, or use a non-destructive alternative.")
    return {}


def stop(payload: dict) -> dict[str, str]:
    if payload.get("stop_hook_active") or payload.get("status") in {"aborted", "error"}:
        return {}
    stagectl = load_stagectl()
    root = worktree(stagectl, payload)
    if root is None:
        return {}
    if not stagectl.pointer_path(root).is_file():
        changed = unproven_changes(stagectl, root)
        if not changed:
            return {}
        shown = ", ".join(changed[:8]) + (f" and {len(changed) - 8} more" if len(changed) > 8 else "")
        return {"followup_message": f"This project requires a stage, and these files changed without one: {shown}. "
                                    "If you changed them, write the contract under .governance/stages/, ask the "
                                    "owner to freeze it, and prove the change. If the owner changed them, say so "
                                    "and leave them alone."}
    report = stagectl.inspect(root)
    if report["ready"]:
        return {"followup_message": f"Stage {report['stage_id']} has current evidence for every check. "
                                    "Close it with `stagectl close`, commit the receipt it writes, "
                                    "and report it."}
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
