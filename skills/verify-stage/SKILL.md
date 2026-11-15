---
name: verify-stage
description: "Give an independent verdict on another agent's stage: check out its exact commit in a separate worktree, drive the real app yourself, try to break it, and record PASS or FAIL with stagectl. Use for /verify-stage, or when a stage reports review-missing."
disable-model-invocation: true
---

# Verify a stage

Only a verdict from an agent that did not write the code counts, because an author checks what it meant to build. You are that agent. You get the stage ID and the commit, not the author's reasoning.

`stagectl` is at `../../scripts/stagectl` from this file.

## 1. Get the exact code

On the author's clone, use your own worktree. It shares the author's stage state.

```bash
git worktree add --detach ../verify-<stage-id> <commit>
```

On another machine, clone that commit. A clone has its own git common dir, so it does not have the author's stage state. That is expected. Check out the commit the author named and do not edit tracked files.

```bash
git clone <repo-url> verify-<stage-id>
git -C verify-<stage-id> checkout <commit>
```

Work only there. Anything you create (repro scripts, evidence) goes under the Git-ignored `.verify/` directory. A dirty governed file makes the verdict refuse, because it would no longer be about the author's commit.

## 2. Read the contract, not the diff first

Read the stage's contract under `.governance/stages/`: the intent, each acceptance item, the checks. Restate the intent with the **in-your-own-words** skill. Judge the change against that intent, not against what the code happens to do.

## 3. Prove it yourself

Drive the real app with the project's `verify-<app>` skill, through every entry point the feature map lists for the features this stage touches. Seal your own evidence with `verifyctl record` into `.verify/runs/current`. The author's evidence does not exist in your worktree, by design.

## 4. Try to break it

Apply the **interrogate** skill's brief to yourself:

> Break this change. Prove each finding with a run against the real code, such as a failing test, a repro script, or command output that shows the wrong behavior. Report each finding with a title, the exact command, the output it printed, and the output the intent requires. Leave out anything you did not run. That covers style, naming, structure, and risks that need a future change to matter. No findings is a valid result.

For a high-stakes stage, run the full **interrogate** skill so several adversaries attack it in parallel.

## 5. Record the verdict

From the linked worktree on the author's clone:

```bash
stagectl --repo . verify --stage <stage-id> --outcome pass --summary "<what you drove and what you observed>"
stagectl --repo . verify --stage <stage-id> --outcome fail --summary "<the finding, its command and its output>"
```

From a separate clone, name the committed contract and who you are. Repeat `--live` once for each feature-map entry you drove. `--control` is the control skill or other driver you used on the live app.

```bash
stagectl --repo . verify --stage <stage-id> --contract .governance/stages/<short-name>.json \
  --outcome pass --summary "<what you drove and what you observed>" \
  --checker "<your name>" --control verify-<app> --live <feature>=<entry>=verified
stagectl --repo . verify --stage <stage-id> --contract .governance/stages/<short-name>.json \
  --outcome fail --summary "<the finding, its command and its output>" --checker "<your name>"
```

Then commit the file it writes and push it. The path is `.governance/verdicts/<record_sha256>.json`.

When the repo's `.governance/config.json` sets `require_verdict_signature` to true, pass the private key that the owner enrolled for your checker identity. The key stays outside the repository.

```bash
stagectl --repo . verify --stage <stage-id> --contract .governance/stages/<short-name>.json \
  --outcome pass --summary "<what you drove and what you observed>" \
  --checker "<your name>" --key ~/.config/governance/verdict-key
```

The command also writes `.governance/verdicts/<record_sha256>.sig`. Commit that file with the verdict. Use the same `--key` on `stagectl reprove`. Your `--checker` name must be the principal on your line in `.governance/verdict-signers`.

```bash
git add .governance/verdicts
git commit -m "Record the independent verdict"
git push
```

The command reruns every frozen check in your checkout. The verdict passes only when you declare `pass` and every rerun passes. A check that passed for the author and fails for you is a finding: the work depended on something that was never committed. A `--live` entry of `failed` fails the verdict too.

Declare `fail` when any proven finding breaks the intent. Do not fix the code; the author fixes it, commits, and asks for a fresh verdict. A verdict covers one exact tree. Any governed change makes it stale. The file names the commit, the governed tree, the checks and their results, who recorded it, and the live entries you drove. Its hash binds those fields. It does not prove your identity.

Screenshots and recordings stay under `.verify/`. Do not commit them.

## 6. After a rebase

A rebase onto a moved base changes the tree the verdict is bound to. The old verdict is then stale, and you do not edit it. When the author has rebased, CI is green on the new head, and `git patch-id --stable` of the branch against the new base matches the patch the old verdict covered, re-run on that new commit:

```bash
stagectl --repo . reprove --stage <stage-id> --supersedes <record_sha256> \
  --base origin/main --contract .governance/stages/<short-name>.json \
  --outcome pass --summary "<what you drove on the rebased tree and what you observed>" \
  --checker "<your name>"
```

`--supersedes` is the record hash in the name of the verdict you are replacing. `--base` is the ref the branch was rebased onto. The command runs the frozen checks again. It writes a new file under `.governance/verdicts/` whose `supersedes` names the old record, the old commit, and the old tree. Commit that file and push it. Do not delete the old file.

If the patch changed, the command writes nothing. Stop and record a new verdict with `stagectl verify` instead. If a check fails, the command writes a failing verdict; leave that failure for the author. This step does not ask the owner to approve again.

On a repository whose default branch has the Reprove workflow, and whose owner has merged the signer pull request from Signer setup, that workflow runs this step after Verify is green. You do not run it yourself for that rebase, you do not hold that key, and you do not edit `.governance/verdict-signers`. A changed patch still waits for you.

**Reply:** the intent as you restated it, the verdict, each finding with its command and output, and the entry points you could not reach with the reason.
