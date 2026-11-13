---
name: approve
description: "The owner's approval, given in chat. The owner types /approve after reading a stage contract (or /approve baseline to let the baseline grow), and the agent then runs the one approval command the hook has unlocked. Owner-started only."
disable-model-invocation: true
---

# Approve


When this runs as part of the owner's path from idea to merged code, follow [STEPS.md](../start/STEPS.md): open each message with the step line, say what is happening in plain words, and close with what the owner must do and what comes next.

The owner typed `/approve`. That message is the approval: the plugin's hook saw it come from the owner and unlocked one approval command for this conversation, for about fifteen minutes. Nothing you write can create that unlock, so never tell the owner it is done until the command below has actually succeeded.

`stagectl` and `rulekit` are at `../../scripts/` from this file, and at `tools/governance/` in an adopted project.

## What was approved

- `/approve`, or `/approve` followed by a remark: the stage contract you most recently wrote or changed under `.governance/stages/`.
- `/approve <short-name>`: the contract `.governance/stages/<short-name>.json`.
- `/approve baseline`: letting the rule baseline grow once.

If you have not shown the owner what they are approving in this conversation (the intent, the acceptance list and the check commands; or for the baseline, which rules and files would grow and why), show it now and ask them to type `/approve` again. Do not run anything on an approval of something they have not seen.

## Run the one command

Run exactly one of these, by itself: no `cd`, no `&&`, no pipe, no redirect, no variables. The hook refuses anything else and the unlock is single-use.

```bash
python3 <path>/stagectl --repo . freeze --contract .governance/stages/<short-name>.json --owner-approved
```

```bash
python3 <path>/stagectl --repo . revise --contract .governance/stages/<short-name>.json --owner-approved --reason "<what changed>"
```

```bash
python3 <path>/rulekit --repo . baseline --owner-approved
```

Use `revise` when this worktree already has an active stage and the contract changed; otherwise `freeze`.

## If the hook refuses

It says why. Act on the reason; do not try another form of the command.

| Reason | What to do |
|---|---|
| The contract changed after the owner approved it | Show the owner the contract as it is now and ask them to type `/approve` again. Do not edit a contract between their approval and the freeze. |
| The owner approved a different contract | Ask them to type `/approve <short-name>` for the one you mean. |
| The approval expired, or was given in a different conversation | Ask them to type `/approve` again here. |
| The owner has not approved anything | The hook did not see the message. Tell the owner, and give them the command to run in a terminal themselves; that path always works. |

## Then carry on

After a freeze or revise succeeds, continue the stage (the **stage** skill, step 4) without waiting for anything else.
