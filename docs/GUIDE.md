# Guide

How to build with this plugin. Written for the owner, not the agent.

## The whole thing in one minute

You type three commands. Everything else happens for you.

| Type | When |
|---|---|
| `/start <what you want to build>` | To begin a new product or feature |
| `/next` | Any time, in any chat. It tells you where you are and does the next step |
| `/approve` | When shown what is about to be built |

Every piece of work goes through six steps, always in this order:

| Step | What happens | What you do |
|---|---|---|
| 1. Describe | The agent interviews you until nothing is assumed | Answer. Picking the first option accepts its recommendation |
| 2. Choose the stack | It recommends what to build with, shows alternatives, and lists what you must set up yourself | Accept or change it |
| 3. Spec | It writes down what was agreed, as a GitHub issue | Nothing |
| 4. Tickets | It splits the spec into small pieces on GitHub, each one something you could see working | Approve the list |
| 5. Build | For one ticket: it turns on the rules if they are not on yet, shows you what it will build and how it will prove it, then builds and proves it | Read it, type `/approve` |
| 6. Merge | It opens a pull request carrying the proof | Merge it, then type `/next` |

Steps 1 to 4 happen in one chat. Each ticket in step 5 gets its own new chat: type `/next` there.

**If you are ever unsure what to do, type `/next`.**

## What you will see

Every message on the path opens with where you are, for example:

> Step 5 of 6: Build. Ticket 2 of 7.

and closes with two lines:

> You: what you need to do now, or "Nothing."
> Next: what happens next.

While it works you may see helper agents start, designs being compared, or issues appear on GitHub. That is normal, and the message will say what they are for. Unless the `You:` line asks for something, you do not need to do anything.

## One-time setup on each machine

1. Install the GitHub CLI and sign in:

```bash
gh auth login
```

2. From a checkout of this plugin:

```bash
python3 scripts/install.py
```

3. Restart Cursor.

A project needs no setup. The first `/start` sets up planning, and the first build turns on the rules.

## What only you can do

| Yours | Not yours |
|---|---|
| Answering the interview | Looking up facts in code or documentation |
| Accepting the stack | Working out which stack fits |
| Approving the ticket list | Writing the spec and the tickets |
| `/approve` for each ticket | Building, testing, reviewing, proving |
| Tickets labelled for you (accounts, keys, things only your login can do) | Everything else |
| Merging | Opening the pull request |

## Words you will meet

| Word | Meaning |
|---|---|
| Spec | One GitHub issue describing the problem, the solution and every user story |
| Ticket | One GitHub issue for one small, complete piece of the spec |
| Blocked | A ticket that cannot start until another is done |
| Contract | What the agent shows you before building a ticket: the goal, the list of things that must be true, and the commands that prove each one |
| `/approve` | Your yes to that contract. The agent cannot approve its own |
| Rule | A check on the code that runs every time: a banned pattern, a file length limit, a strict linter |
| Receipt | The record that every check passed on the exact final code |
| Gate | The check on GitHub that fails a pull request with no matching receipt |
| Glossary | `GLOSSARY.md`: the project's agreed words, so you and the agent mean the same thing |

## When something goes wrong

| What you see | What to do |
|---|---|
| You don't know where you are | Type `/next` |
| The agent starts coding during the interview | "Do not act until I confirm we have a shared understanding." |
| The agent asks questions as plain text | "Use your question tool." |
| "This project requires a stage before files change" | Working as designed. Nothing is edited until you `/approve` a contract |
| After `/approve`, the agent says the hook saw no approval | Run the command it gives you in a terminal, and report it |
| `/next` says GitHub could not be reached | Run `gh auth login` |
| The `gate` check fails on a pull request | Type `/next`. Something changed after the proof; it will prove it again |
| GitHub will not make `gate` a required check | A free private repository cannot. The gate still shows red on a bad pull request; it just cannot block the merge |
| A ticket is too big, or covers only one layer | Reject it when approving the list. Each ticket must be showable working by itself |
| You had to correct the agent | Type `/correct`. The correction becomes a rule for every later agent |

## Optional commands

You never need these. They are there when you want something off the main path.

| I want to | Type |
|---|---|
| Ask how something in the plugin works | `/trust-help <question>` |
| Do a task that has no ticket | `/govern <goal, and how to tell it is done>` |
| Fix a bug | `/govern <symptom>. repro first, then fix and verify.` |
| Build a whole spec in parallel | `/implement-spec <spec issue>` |
| Plan something too big for one sitting | `/wayfinder <idea>` |
| Get a fact researched from primary sources | `/research <question>` |
| See an idea working before committing to it | `/prototype <question>` |
| Choose or revisit the stack | `/stack` |
| Stop a mistake from happening again | `/correct` |
| Find bad habits that are spreading in the code | `/garden` |
| Have other models try to break a change | `/interrogate` |
| Understand how or why code works | `/how <thing>`, `/why <thing>` |
| Hear the last message in plain words | `/wait-what` |
| Sort incoming bug reports and requests | `/triage` |
| Move the work to another chat or person | `/handoff` |

## Known limits

- Building a ticket through to a merged pull request has not been seen end to end in Cursor yet, nor have `/start`, `/next` and `/approve`.
- `/next` reads GitHub issues. A project that keeps tickets as local files is not supported by it yet.
- A file written by a shell command bypasses the edit-time hook. The gate still catches it.
- Receipts can be forged by someone determined; the gate guards against mistakes, not an adversary.
- `/approve` covers one ticket at a time. `/implement-spec` still hands you terminal commands.
