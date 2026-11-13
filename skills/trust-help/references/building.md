# Govern help

Answer the user's question about this plugin, hand them a prompt they can send, and name the file the answer came from. For a help question, don't start the work. The user asked how, and a governed run spends real tokens, so let them send the prompt.

A message that asks for work, such as "use govern to fix this bug", is not a help question. Read [`govern`](../../govern/SKILL.md), do the work under it, and mention once that a Custom Mode keeps it on.

This file maps questions to the skills that hold the answers. Those files own the details. Read the file you route to before you quote it, and trust it when it disagrees with this map.

## Find out what they need

Infer the need from the message and the conversation. A named situation, such as "which skill reviews a PR?", goes straight to its section. If the need is still unclear, ask one multiple-choice question with these options, then answer only the section they pick:

- Get set up
- Start a task with `/govern`
- Pick a skill for a situation
- Keep the code good
- Fix a run that went wrong
- Make it my own

Check the state that changes the answer, and mention it only when it does:

- No `.governance/config.json` in the project means it is not adopted: no hook blocks edits, no rules run, no merge gate exists. The skills still work, but nothing is enforced.
- No `verify-*` skill in the project means agents have no scripted way to drive the app. Mention `/create-verification-skill` when the question is about proving a change works.
- No `~/.cursor/rules/pstack-models.mdc` means `/setup-pstack` hasn't run for this user, so every role uses its default model.
- No formal verification skill in the project means no property is checked past what tests reach. Mention `/create-formal-verification-skill` when the question is about a race, an invariant, or another case tests rarely hit.

## Get set up

1. Install: from a checkout of the plugin, the owner runs `python scripts/install.py`, then restarts Cursor.
2. Adopt each project: the owner types [`/adopt`](../../adopt/SKILL.md) with the project open. It runs the adopt script, which adds the tools under `tools/governance/`, the starter rules, the strict linter and type-checker preset for the language, and the CI merge gate; installs any linter the script names; commits the result to the main branch; and makes the `gate` job a required check. The same script can be run from a terminal: `python scripts/adopt.py --repo <project>`.
3. If the project was empty when adopted, the owner types `/adopt` again once it has source files, to add the strict rules for its language.
4. Run [`/setup-pstack`](../../setup-pstack/SKILL.md) once to pick a model for each role and a reasoning budget.
5. Start a real task with `/govern`, a goal, and a check that can pass or fail.

The plugin's `README.md` has the details and the known limits. Offer to word their first prompt with them, per [`references/prompting.md`](prompting.md).

If cost is the worry, say where the tokens go: subagents, review panels, and verification. Rerun `/setup-pstack` and pick a smaller budget or cheaper models. In the contract, `review: none` skips the independent verifier for a low-risk stage. Save `/govern` for work that needs rigor.

## Start a task with `/govern`

`/govern` matches the task to a playbook, copies the playbook's steps into the todo list, and runs the other skills as the steps need them. A good prompt states the goal and how to tell it's done. It doesn't list skills. Read [`references/prompting.md`](prompting.md) before you help word one.

Every playbook that ships a change runs inside a stage (the [`stage`](../../stage/SKILL.md) skill):

1. The agent writes a contract under `.governance/stages/`: the intent, the acceptance list, and the commands that prove it.
2. The owner reads it and types `/approve`. This is the one approval. The agent then runs the freeze; the hook lets it through once, for the contract as the owner saw it, and blocks it otherwise.
3. The agent works, runs the checks, and gets an independent verdict when the contract asks for one.
4. `stagectl close` writes a receipt naming the exact code. The CI gate passes only when a receipt matches the pull request.

Enter on `/govern` attaches the skill to one message. Option+Enter on Mac or Alt+Enter on Windows, or Use as Mode from the skill entry, makes it a Custom Mode that stays on. Mid-chat, "new task" makes the mode match a fresh playbook.

## Pick a skill

The default answer is `/govern`, which runs most of the others when its steps need them. Name a skill directly when the user wants more or less of something than the playbook gives. Read the skill before you recommend it, and give one example prompt.

| The user wants to | Skill |
|---|---|
| Do any non-trivial task with rigor | [`/govern`](../../govern/SKILL.md) |
| Agree what "done" means before code changes, and prove it after | [`/stage`](../../stage/SKILL.md) |
| Have a second agent judge a finished stage on its evidence | [`/verify-stage`](../../verify-stage/SKILL.md) |
| Check that the agent understood their goal before it starts | [`/in-your-own-words`](../../in-your-own-words/SKILL.md) |
| Get a prompt rewritten deeper before sending it | [`/sharpen`](../../sharpen/SKILL.md) |
| Know how code works now, or where new code should live | [`/how`](../../how/SKILL.md) |
| Know why code is shaped this way | [`/why`](../../why/SKILL.md) |
| Understand a change or subsystem, explained plainly | [`/teach`](../../teach/SKILL.md) |
| Catch up on their own recent work on a topic | [`/recall`](../../recall/SKILL.md) |
| Catch up on what changed in this chat since their last message | [`/ketchup`](../../ketchup/SKILL.md) |
| Know what a small diff could break outside itself | [`/blast-radius`](../../blast-radius/SKILL.md) |
| Settle types and module shape before code | [`/architect`](../../architect/SKILL.md) |
| Get several attempts at one brief, merged into the best one | [`/arena`](../../arena/SKILL.md) |
| Run parallel checks or race workers as cloud agents | [`/swarm`](../../swarm/SKILL.md) |
| Have different models review a diff and try to break it | [`/interrogate`](../../interrogate/SKILL.md) |
| Fix a bug test-first | [`/tdd`](../../tdd/SKILL.md) |
| Hunt for unreported bugs by driving the app unpredictably | [`/fuzz`](../../fuzz/SKILL.md) |
| Apply TypeScript rules to `.ts` or `.tsx` work | [`/typescript-best-practices`](../../typescript-best-practices/SKILL.md) |
| Strip comments before review | [`/no-comments`](../../no-comments/SKILL.md) |
| Clean AI tells out of prose | [`/unslop`](../../unslop/SKILL.md) |
| Write docs, a README, a PR description, or a commit message | [`/technical-writing`](../../technical-writing/SKILL.md) |
| Hear the last reply again in plain words | [`/bro`](../../bro/SKILL.md) |
| Give agents a scripted way to drive the app and prove behavior | [`/create-verification-skill`](../../create-verification-skill/SKILL.md) |
| Bring a verification skill back in line with the app | [`/maintain-verification-skill`](../../maintain-verification-skill/SKILL.md) |
| Formally verify a race or invariant | [`/create-formal-verification-skill`](../../create-formal-verification-skill/SKILL.md) |
| Bring a formal verification back in line after the code changed | [`/maintain-formal-verification-skill`](../../maintain-formal-verification-skill/SKILL.md) |
| Show what the user sees as a state chart checked by a TLA+ model | [`/statechart`](../../statechart/SKILL.md) |
| Vet a performance number before acting on it | [`/benchmark-checklist`](../../benchmark-checklist/SKILL.md) |
| Run a large or cross-cutting change | [`/figure-it-out`](../../figure-it-out/SKILL.md) |
| Keep a decision log during a run | [`/show-me-your-work`](../../show-me-your-work/SKILL.md) |
| Pick a model for each role and a reasoning budget | [`/setup-pstack`](../../setup-pstack/SKILL.md) |
| Find their way around the plugin | `/trust-help` |

If a skill directory next to this one is missing from the table, read its frontmatter and route by its description.

Not in this plugin: `/deslop`, `control-cli`, and `control-ui` ship in Cursor's `cursor-team-kit` plugin. `/loop` and `/create-skill` are Cursor built-ins.

## Keep the code good

The user does not need to know what good code is. Three things carry it:

| The user wants to | Use |
|---|---|
| Approve a stage contract the agent just showed, or a larger baseline | [`/approve`](../../approve/SKILL.md), or `/approve baseline` |
| Stop a mistake they just corrected from happening again | [`/correct`](../../correct/SKILL.md) |
| Add one enforced rule fast: ban comments, an import, a pattern, cap file length, fix the folder layout | [`/rulekit`](../../rulekit/SKILL.md) |
| Find the bad habits that are spreading, before being asked | [`/garden`](../../garden/SKILL.md) |
| Remove old violations a rule still tolerates | `/govern clean up the baseline for <rule ID>` (the Cleanup playbook) |
| Turn what a finished task taught into skill edits | [`/reflect`](../../reflect/SKILL.md) |

A rule's failure message states the fix. The agent fixes the code, never the rule. The hook blocks an agent from editing the rule file, the linter and type-checker configs, or the baseline unless the frozen contract lists that file in its `outputs`, so the owner sees it before approving.

## Playbooks and principles

Playbooks are step lists inside `/govern`, not skills, so they have no slash command. Describing the task picks one. These phrases name one directly:

- "babysit this pr" or "check on pr 123" runs Babysit. It doesn't merge unless the user asks.
- "land the stack" runs Shipping.
- "take over this branch" runs Session pickup.
- "pause safely" runs Pause safely.
- "full autopilot on this queue" runs Autopilot-full. "autopilot, don't merge" runs Autopilot-stack.
- "fuzz this" runs Fuzz. "clean up the baseline" runs Cleanup.

The Playbooks section of [`govern`](../../govern/SKILL.md) lists every playbook and when it applies.

Principles are one-rule skills that `/govern` reads and cites. The user steers with the names, as in "apply prove it works. show me the real output." Typing `/principle-<name>` loads one on demand.

## Fix a run that went wrong

| Symptom | Fix |
|---|---|
| "This project requires a stage before files change" | Working as designed. The agent writes the contract and the owner freezes it. For files that should never need a stage, the owner adds a glob to `exempt` in `.governance/config.json`. |
| The agent asks the owner to type `/approve` | Working as designed. Read the contract it shows, then type it. |
| The agent says the hook saw no approval after `/approve` | Cursor did not pass the message to the hook. Run the `--owner-approved` command it gives you in a terminal, and report it as a plugin bug. |
| "sets how strict the checks are" | The agent tried to edit a linter config or the rule file. If that really is the task, the contract must list the file in `outputs`. |
| `rulekit check` exits 127 | A linter is not installed. Install the tool the message names. Do not remove the rule. |
| The CI `gate` job fails | No receipt matches the pull request's code. Something changed after `stagectl close`. Rerun the checks, close again, commit the new receipt. |
| The mode stopped applying after a few turns | It was started with Enter. Start it as a Custom Mode, or start each task with `/govern`. |
| A new model choice had no effect | The rule from `/setup-pstack` applies to new chats. Start one. |
| Parallel agents overwrote each other | Give each agent its own worktree. A stage belongs to one worktree. |
| The reply claims success from a green build | Ask for the real command, flow, stored value, or profile. That's the prove-it-works principle. |

For a run that drifts, [`references/prompting.md`](prompting.md) has one-line steers.

## Make it my own

- [`/automate-me`](../../automate-me/SKILL.md) drafts a personal mode skill from the user's own chat history, to use alongside `/govern`.
- [`/reflect`](../../reflect/SKILL.md) after a session turns its lessons into skill edits the user approves.
- `/govern write a skill for <workflow>` runs the authoring playbook.

## Reply

Lead with the answer. Give at most one example prompt in a code block, adapted from [`references/recipes.md`](building-recipes.md) when one fits, then the file it came from. Keep it short unless the user asked for the whole map.
