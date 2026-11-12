---
name: verify-stage
description: "Give an independent verdict on another agent's stage: check out its exact commit in a separate worktree, drive the real app yourself, try to break it, and record PASS or FAIL with stagectl. Use for /verify-stage, or when a stage reports review-missing."
disable-model-invocation: true
---

# Verify a stage

Only a verdict from an agent that did not write the code counts, because an author checks what it meant to build. You are that agent. You get the stage ID and the commit, not the author's reasoning.

`stagectl` is at `../../scripts/stagectl` from this file.

## 1. Get the exact code, in your own worktree

```bash
git worktree add --detach ../verify-<stage-id> <commit>
```

Work only there. Do not edit tracked files. Anything you create (repro scripts, evidence) goes under the Git-ignored `.verify/` directory, or the verdict is refused because your checkout no longer matches the author's.

## 2. Read the contract, not the diff first

Read `stage.json`: the intent, each acceptance item, the checks. Restate the intent with the **in-your-own-words** skill. Judge the change against that intent, not against what the code happens to do.

## 3. Prove it yourself

Drive the real app with the project's `verify-<app>` skill, through every entry point the feature map lists for the features this stage touches. Seal your own evidence with `verifyctl record` into `.verify/runs/current`. The author's evidence does not exist in your worktree, by design.

## 4. Try to break it

Apply the **interrogate** skill's brief to yourself:

> Break this change. Prove each finding with a run against the real code, such as a failing test, a repro script, or command output that shows the wrong behavior. Report each finding with a title, the exact command, the output it printed, and the output the intent requires. Leave out anything you did not run. That covers style, naming, structure, and risks that need a future change to matter. No findings is a valid result.

For a high-stakes stage, run the full **interrogate** skill so several adversaries attack it in parallel.

## 5. Record the verdict

```bash
stagectl --repo . verify --stage <stage-id> --outcome pass --summary "<what you drove and what you observed>"
stagectl --repo . verify --stage <stage-id> --outcome fail --summary "<the finding, its command and its output>"
```

The command reruns every frozen check in your worktree. The verdict passes only when you declare `pass` and every rerun passes. A check that passed for the author and fails for you is a finding: the work depended on something that was never committed.

Declare `fail` when any proven finding breaks the intent. Do not fix the code; the author fixes it, commits, and asks for a fresh verdict. A verdict covers one exact state of the code and goes stale on any change.

**Reply:** the intent as you restated it, the verdict, each finding with its command and output, and the entry points you could not reach with the reason.
