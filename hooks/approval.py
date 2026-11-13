#!/usr/bin/env python3
"""Owner approval given in chat.

The owner types `/approve` (or `/approve baseline`) as their own message. Cursor's
beforeSubmitPrompt hook sees that message, which an agent cannot write, and records a
grant in the stage state directory, which an agent cannot touch. The grant lets the
agent run exactly one approval command, in the same conversation, within WINDOW
seconds. A stage grant names one contract file and its hash: if the file changes
after the owner approved it, the grant no longer matches.
"""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shlex
import time
from typing import Any

WINDOW = 900
PROMPT = re.compile(r"\s*/approve\b(.*)", re.DOTALL)
STAGES = ".governance/stages"
HERE = Path(__file__).resolve().parent


class Refused(Exception):
    pass


def grant_path(stagectl, root: Path) -> Path:
    return stagectl.pointer_path(root).with_name(stagectl.pointer_path(root).stem + ".approval.json")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(stagectl, root: Path, payload: dict[str, Any]) -> bool:
    """Record a grant when the owner's own message is /approve. Returns whether one was recorded."""
    match = PROMPT.match(str(payload.get("prompt") or ""))
    conversation = payload.get("conversation_id")
    if not match or not conversation:
        return False
    words = match.group(1).split()
    grant: dict[str, Any] = {"conversation_id": conversation, "created": time.time()}
    if words[:1] == ["baseline"]:
        grant["kind"] = "baseline"
    else:
        drafts = sorted((root / STAGES).glob("*.json"), key=lambda path: path.stat().st_mtime)
        named = [path for path in drafts if words and path.stem == words[0]]
        if not drafts:
            return False
        chosen = (named or drafts)[-1]
        grant.update(kind="stage", contract=chosen.relative_to(root).as_posix(), sha256=sha256(chosen))
    stagectl.write_json(grant_path(stagectl, root), grant)
    return True


def tokens(command: str) -> list[str]:
    if any(mark in command for mark in ("`", "$", "\n", "\r")):
        raise Refused("run the approval command on its own, with no substitution")
    if os.name == "nt":
        command = command.replace("\\", "/")
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        words = list(lexer)
    except ValueError as exc:
        raise Refused("the command could not be read") from exc
    if any(word and set(word) <= set("();<>|&") for word in words):
        raise Refused("run the approval command on its own, not chained or redirected")
    return words


def parse(words: list[str], cwd: Path, root: Path) -> argparse.Namespace:
    if words and re.fullmatch(r"python[0-9.]*(\.exe)?|py", Path(words[0]).name):
        words = words[1:]
        while words and words[0].startswith("-"):
            words = words[1:]
    if not words:
        raise Refused("no command found")
    script = (cwd / words[0]).resolve()
    name = script.name
    trusted = {(HERE.parent / "scripts" / name).resolve(), (root / "tools" / "governance" / name).resolve()}
    if name not in ("stagectl", "rulekit") or script not in trusted:
        raise Refused("only the plugin's own stagectl and rulekit record approval")
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true")
    commands = parser.add_subparsers(dest="command", required=True)
    for verb in (("freeze", "revise") if name == "stagectl" else ("baseline",)):
        sub = commands.add_parser(verb, add_help=False)
        sub.add_argument("--owner-approved", action="store_true")
        if name == "stagectl":
            sub.add_argument("--contract", required=True)
        if verb == "revise":
            sub.add_argument("--reason", required=True)
    try:
        args = parser.parse_args(words[1:])
    except SystemExit as exc:
        raise Refused("this is not a freeze, revise or baseline command the owner can approve") from exc
    if (cwd / args.repo).resolve() != root.resolve():
        raise Refused("the command targets a different project than the one the owner approved in")
    return args


def permit(stagectl, root: Path, payload: dict[str, Any], command: str) -> None:
    """Consume the grant for this command, or raise Refused with the reason."""
    path = grant_path(stagectl, root)
    grant = stagectl.read_json(path)
    if not isinstance(grant, dict):
        raise Refused("the owner has not approved anything")
    if time.time() - float(grant.get("created", 0)) > WINDOW:
        path.unlink(missing_ok=True)
        raise Refused("the owner's approval has expired")
    if not payload.get("conversation_id") or payload.get("conversation_id") != grant.get("conversation_id"):
        raise Refused("the owner approved in a different conversation")
    nested = payload.get("tool_input") if isinstance(payload.get("tool_input"), dict) else {}
    cwd = Path(nested.get("working_directory") or payload.get("cwd") or root)
    args = parse(tokens(command), cwd if cwd.is_absolute() else root / cwd, root)
    if args.command == "baseline":
        if grant.get("kind") != "baseline":
            raise Refused("the owner approved a stage contract, not a larger baseline")
    else:
        if grant.get("kind") != "stage":
            raise Refused("the owner approved a larger baseline, not a stage contract")
        contract = (root / args.contract).resolve()
        if contract != (root / str(grant.get("contract"))).resolve():
            raise Refused(f"the owner approved {grant.get('contract')}, not {args.contract}")
        if not contract.is_file() or sha256(contract) != grant.get("sha256"):
            path.unlink(missing_ok=True)
            raise Refused("the contract changed after the owner approved it; show it again")
    path.unlink(missing_ok=True)
