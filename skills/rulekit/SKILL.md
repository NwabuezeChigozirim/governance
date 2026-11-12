---
name: rulekit
description: "Turn a correction into an enforced rule in minutes with the built-in enforcers: ban comments, ban imports across a directory boundary, ban a pattern or API. Use when the correct skill reaches the lint level and the project has no linter rule for the mistake, or to add or tighten a rule in .governance/rules.json."
---

# Rulekit

`rulekit` is a small linter that needs no dependencies and works on any language. Use it when the **correct** skill reaches the lint level and the project's own linter cannot express the rule quickly. A rule in the project's real linter or type system is still better when it exists; cite that instead.

In an adopted project the tools are at `tools/governance/`. Run them as `python tools/governance/rulekit <command>`. If the project has no `.governance/rules.json`, ask the owner to run the plugin's `scripts/adopt.py --repo <project>` first.

## Add a rule

1. **State the mistake as something a machine can see.** One of three kinds:

   | Kind | Catches | Needs |
   |---|---|---|
   | `ban-comments` | Any comment in the matched files | `allow`: patterns for tool directives worth keeping |
   | `ban-import` | A file under `include` importing from a directory in `forbid`, or a specifier matching `forbid_specifiers` | The two directories of the boundary |
   | `ban-pattern` | A line matching `pattern` in the matched files | A pattern narrow enough not to hit correct code |

   If the mistake fits none of these, go back to the **correct** skill's ladder: a type, a test, or the project's linter.

2. **Add it to `.governance/rules.json`** with the next free ID:

   ```json
   {"id": "R-002", "kind": "ban-import", "include": ["src/renderer/**"], "forbid": ["src/main"],
    "message": "Renderer code reaches main only through the IPC client in src/shared/ipc. Import that instead."}
   ```

   The message is the fix, not the complaint. Name the file, function or type to use instead. An agent that hits the rule reads only this line.

3. **Commit a bad example** taken from the real mistake at `.governance/bad/R-002.<ext>`. Files under `.governance/` are never scanned unless named, so the example does not fail the build.

4. **Prove the rule bites.** This must exit 3:

   ```bash
   python tools/governance/rulekit check --rule R-002 --as src/renderer/example.ts .governance/bad/R-002.ts
   ```

   `--as` is needed only for `ban-import`, where the file's location is part of the rule.

5. **Add the row to the `## Rules` table in `AGENTS.md`**, with that command as its Proof and `.governance/rules.json` as Enforced by. Then both of these must pass:

   ```bash
   python tools/governance/rulekit check
   python tools/governance/rulectl check --repo . --prove
   ```

6. **If old code already breaks the rule,** run `python tools/governance/rulekit baseline`. It records today's count per file, so the rule fails only when a file gets worse. Then clean the old cases up in their own change and run `baseline` again to lock the lower count in.

## Limits you must respect

- The baseline only shrinks. If `baseline` refuses because a count would grow, fix the new violation. Growing it takes the owner running `rulekit baseline --owner-approved`; the hook blocks you from running that.
- Never widen `allow`, narrow `include`, add to `exclude`, or loosen a `pattern` to make a failure go away. A rule change is its own stage, with the owner approving the contract.
- `ban-comments` understands Python and C-style languages. `ban-import` resolves relative imports and Python modules; path aliases need `forbid_specifiers`. Say so when a rule depends on something it cannot see.
