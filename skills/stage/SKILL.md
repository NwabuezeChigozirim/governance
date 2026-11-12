---
name: stage
description: "Run a bounded piece of work under a frozen contract: restate the intent, freeze it with executable checks after the owner approves, do the work, prove it, and close on current evidence. Use for /stage, or before any change that ships behavior."
disable-model-invocation: true
---

# Stage

A stage is one reviewable unit of work in one worktree. The owner approves its intent and checks once, at the start. After that nothing waits on the owner: the stage closes itself when every check has passed on the final code.

`stagectl` is at `../../scripts/stagectl` from this file. Run it as `python3 <path>/stagectl --repo . <command>`.

## 1. Restate the intent

Apply the **in-your-own-words** skill: say what the owner wants, the problem it solves, and the smallest change that meets it. If the work is larger than one reviewable unit, split it per **principle-sequence-verifiable-units** and run one stage per unit.

## 2. Write the contract

Write `stage.json` in the repository:

```json
{
  "version": 1,
  "name": "Bulk archive action",
  "intent": "Users can archive several selected notes at once from the list view.",
  "review": "independent",
  "inputs": ["docs/notes-FSD.md"],
  "outputs": ["src/notes/archive.ts"],
  "acceptance": [
    {"id": "AC-001", "description": "Selecting three notes and choosing Archive moves all three to the archive", "checks": ["CHK-001", "CHK-002"]}
  ],
  "checks": [
    {"id": "CHK-001", "argv": ["npm", "test", "--", "archive"], "timeout_seconds": 300},
    {"id": "CHK-002", "argv": ["python3", ".cursor/skills/verify-notes/verifyctl", "check", "--skill", ".cursor/skills/verify-notes", "--run", ".verify/runs/current", "--feature", "archive", "--fresh"], "timeout_seconds": 60}
  ]
}
```

- `intent` is your restatement from step 1.
- `review` is `independent` for any change that ships behavior: a second agent must verify it from its own checkout before the stage can close. Use `none` only for changes with no behavior to drive, such as docs or a rename, and say why when you ask for approval.
- Each acceptance item states an outcome a user could observe, and names the checks that prove it.
- `inputs` are the files whose change would invalidate this agreement (specs, the wave brief). `outputs` must exist and be nonempty at close. Either list may be empty.
- A check is an argv array, not a shell string. It must not edit the code it checks.
- Any stage that changes behavior a user can see needs a `verifyctl check ... --fresh` check against the project's `verify-<app>` skill. `--fresh` fails when the code changed after the evidence was recorded. If the project has no such skill, run the **create-verification-skill** skill first.

## 3. Get approval and freeze

Show the owner the intent, the acceptance list and the check commands. This is the one approval in the stage. Ask them to run this themselves:

```bash
stagectl --repo . freeze --contract stage.json --owner-approved
```

You do not run it. Only the owner records approval, and the plugin's hook blocks an agent that tries. The same holds for `revise`.

## 4. Do the work, then prove it

Make the change. Drive the real app with the `verify-<app>` skill and seal the evidence with its `verifyctl record`. Then:

```bash
stagectl --repo . run-check --all
stagectl --repo . status
```

A receipt is bound to the exact code that was tested. Any edit afterwards makes it stale, so run the checks last. Fix failures at their root cause and rerun; do not weaken a check or an acceptance item to make it pass.

## 5. Get the independent verdict

When `review` is `independent`, commit everything, then hand the stage ID and commit to a fresh agent with the **verify-stage** skill. Use a subagent or a cloud agent that has not seen this conversation. Give it the stage ID and the commit, not your reasoning.

You cannot record the verdict yourself: `stagectl verify` refuses the worktree that did the work, and requires the verifier's checkout to match your committed code exactly. If the verdict is `fail`, fix the root cause, commit, rerun the checks, and ask for a fresh verdict. Any edit after a verdict makes it stale.

## 6. Close

```bash
stagectl --repo . close
```

It succeeds only when every check's latest attempt passed on the current code, the frozen inputs are unchanged, the outputs exist, and an independent stage has a passing verdict on that same code. It needs no owner flag. Report the stage ID and the receipt path.

## When the agreement changes

- A frozen input changed, or the intent, acceptance or checks must change: update `stage.json`, get the owner's approval for the new version, then `stagectl revise --contract stage.json --owner-approved --reason "..."`. All checks start over.
- The work is abandoned: `stagectl cancel --reason "..."`. Cancellation is never completion.

Exit codes: 0 ok, 2 invalid invocation or no active stage, 3 checks failed or stale, 4 owner approval needed.
