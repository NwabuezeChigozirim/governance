"""Bounded, non-executing classification for the governance pre-action guard.

This is not a shell sandbox: aliases, scripts, generated commands and arbitrary
interpreters are not resolved. Unknown literal Git subcommands require review.
"""

from __future__ import annotations

from pathlib import Path
import re
import shlex
from typing import Any


MAX_PAYLOAD = 1024 * 1024
SAFE_GIT = {"status", "diff", "show", "log", "reflog", "rev-parse", "ls-files", "ls-tree",
            "describe", "shortlog", "blame", "grep", "help", "version", "add", "commit",
            "fetch", "push", "branch", "tag", "checkout", "switch", "worktree", "stash",
            "config", "remote", "init", "clone", "check-ignore", "check-attr", "cat-file",
            "for-each-ref", "merge-base", "diff-files", "diff-index", "diff-tree", "ls-remote"}
GLOBAL_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix"}
GLOBAL_FLAGS = {"--no-pager", "--paginate", "-P", "-p", "--bare", "--no-replace-objects",
                "--literal-pathspecs", "--glob-pathspecs", "--noglob-pathspecs", "--icase-pathspecs",
                "--no-optional-locks", "--no-lazy-fetch"}
READ_TOOLS = {"read", "readfile", "read_file", "glob", "grep", "ls"}


def validate_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Hook payload must be an object")
    if "tool_input" in value and not isinstance(value["tool_input"], dict):
        raise ValueError("Hook tool_input must be an object")
    for item in (value, value.get("tool_input", {})):
        for key in ("command", "path", "file_path", "notebook_path", "cwd", "tool_name"):
            if key in item and (not isinstance(item[key], str) or "\0" in item[key]):
                raise ValueError("Hook action fields must be strings without NUL bytes")
    for key in ("stop_hook_active",):
        if key in value and type(value[key]) is not bool:
            raise ValueError("Hook loop flags must be booleans")
    commands = {item["command"] for item in (value, value.get("tool_input", {})) if item.get("command")}
    targets = {item[key] for item in (value, value.get("tool_input", {}))
               for key in ("path", "file_path", "notebook_path") if item.get(key)}
    if len(commands) > 1 or len(targets) > 1:
        raise ValueError("Conflicting hook action fields")
    tool = value.get("tool_name", "").lower()
    if tool in {"shell", "bash"} and not commands:
        raise ValueError("Shell action is missing its command")
    if tool in {"write", "edit", "multiedit", "notebookedit"} and not targets:
        raise ValueError("Edit action is missing its target")
    return value


def git_review(words: list[str]) -> bool:
    """Classify argv after a literal Git executable; never invoke Git here."""
    index = 0
    while index < len(words):
        word = words[index]
        if word in {"--version", "--help"}:
            return False
        if word in GLOBAL_FLAGS:
            index += 1
        elif word in GLOBAL_VALUE:
            if index + 1 == len(words):
                return True
            index += 2
        elif any(word.startswith(flag + "=") for flag in GLOBAL_VALUE if flag.startswith("--")):
            index += 1
        elif word.startswith(("-C", "-c")) and len(word) > 2:
            index += 1
        elif word.startswith("-"):
            # Unknown global semantics (including dynamic config/exec paths) cannot
            # be mistaken for a safe subcommand or skipped with guessed arity.
            return True
        else:
            break
    if index == len(words):
        return True
    command, args = words[index], words[index + 1:]
    if command not in SAFE_GIT:
        return True
    short = {letter for word in args if word.startswith("-") and not word.startswith("--") for letter in word[1:]}
    options = {word.split("=", 1)[0] for word in args if word.startswith("--")}
    if command == "push":
        return bool(short & {"f", "d"} or options & {"--force", "--force-with-lease", "--force-if-includes", "--mirror", "--delete", "--prune"}
                    or any(word.startswith(("+", ":")) for word in args))
    if command == "checkout":
        # A single operand can be a branch or a tracked path. Do not query/execute
        # it to guess; unambiguous non-forced branch creation is the exception.
        return not ("b" in short and not short & {"f", "B"} and not options & {"--force", "--overwrite-ignore"})
    if command == "switch":
        return bool(short & {"f", "C"} or options & {"--force", "--discard-changes", "--force-create"})
    if command in {"branch", "tag"}:
        return bool(short & {"d", "D", "f", "M"} or options & {"--delete", "--force", "--move"})
    if command == "worktree":
        return not args or args[0] not in {"list", "add", "lock", "unlock"} or "--force" in options or "f" in short
    if command == "stash":
        return bool(args and args[0] in {"drop", "clear", "pop"})
    return False


def command_requires_review(command: str, depth: int = 0) -> bool:
    if len(command) > MAX_PAYLOAD or depth > 3:
        return True
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        words = list(lexer)
    except ValueError:
        return True
    # Expansion changes executable meaning. This scanner cannot certify it; quoted
    # examples can be overclassified, but are never executed to find out.
    if re.search(r"\bgit\b", command) and ("$(" in command or "`" in command):
        return True
    for index, word in enumerate(words):
        executable = Path(word).name
        if executable in {"git", "git.exe"}:
            end = next((i for i in range(index + 1, len(words)) if set(words[i]) <= set(";&|()\n")), len(words))
            if git_review(words[index + 1:end]):
                return True
        if executable in {"sh", "bash", "zsh", "dash", "ksh"}:
            for offset in range(index + 1, min(index + 5, len(words) - 1)):
                if words[offset].startswith("-") and "c" in words[offset][1:]:
                    if command_requires_review(words[offset + 1], depth + 1):
                        return True
                    break
        if word == "eval" and command_requires_review(" ".join(words[index + 1:]), depth + 1):
            return True
    return False


def action(value: dict[str, Any]) -> tuple[str, str | None]:
    payload = validate_payload(value)
    nested = payload.get("tool_input", {})
    command = payload.get("command") or nested.get("command") or ""
    tool = payload.get("tool_name", "").lower()
    target = None if tool in READ_TOOLS else next((item[key] for item in (payload, nested)
        for key in ("path", "file_path", "notebook_path") if item.get(key)), None)
    return command, target
