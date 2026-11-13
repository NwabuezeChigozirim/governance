# Intent help

Answer the user's question about this plugin, hand them a prompt they can send, and name the file the answer came from. For a help question, don't start the work: the user asked how, so let them send the prompt.

A message that asks for work, such as "grill me on this feature", is not a help question. Load and follow the skill it names.

This file maps questions to the skills that hold the answers. Those files own the details. Read the file you route to before you quote it, and trust it when it disagrees with this map.

## Find out what they need

Infer the need from the message and the conversation. A named situation, such as "how do I split this into tickets?", goes straight to its section. If the need is still unclear, ask one multiple-choice question with these options, then answer only the section they pick:

- Get set up
- Take an idea to tickets
- Build a ticket
- Plan something too big for one session
- Pick a skill for a situation
- Fix a session that went wrong

Check the state that changes the answer, and mention it only when it does:

- No `docs/agents/issue-tracker.md` in the project means `/setup-project` has not run, so `/to-spec`, `/to-tickets`, `/triage` and `/wayfinder` do not know where issues live.
- No `GLOSSARY.md` means no shared vocabulary exists yet. `/grill-with-docs` creates it when the first term is settled.
- No `.governance/config.json` means the project has not been adopted: `/next` and `/implement` adopt it before building.

## Get set up

1. Install `governance` first, then this plugin: from a checkout, the owner runs `python scripts/install.py`, then restarts Cursor.
2. For the GitHub tracker, the owner installs the `gh` command and runs `gh auth login` once on the machine.
3. In each project, run [`/setup-project`](../../setup-project/SKILL.md) once and accept the defaults: GitHub issues, the five triage labels, one `GLOSSARY.md` at the root.
4. Start a real idea with `/grill-with-docs`.

## Take an idea to tickets

Keep these three in one chat, without clearing, so each builds on the last:

1. [`/grill-with-docs`](../../grill-with-docs/SKILL.md): the agent asks every open question in rounds, each with a recommended answer worded so "yes" accepts it. It looks up facts itself and asks the user only for decisions. It writes settled terms to `GLOSSARY.md` and applies [`need-first`](../../need-first/SKILL.md).
2. For something with no code yet, the interview ends by loading [`stack`](../../stack/SKILL.md): a recommended technology stack with reasons and alternatives, and the list of what the user must set up before building. `/to-spec` stops without it.
3. [`/to-spec`](../../to-spec/SKILL.md): no more questions; it writes the spec from the conversation and publishes it as an issue.
4. [`/to-tickets`](../../to-tickets/SKILL.md): splits the spec into vertical slices with blocking links. The user approves the breakdown before anything is published.

A question paper cannot settle (does this state model feel right, what should this screen look like) takes a detour through [`prototype`](../../prototype/SKILL.md). A fact that needs reading goes to [`research`](../../research/SKILL.md) in the background.

[`references/flows.md`](flows.md) has the full flow and its branches.

## Build a ticket

- [`/implement <ticket>`](../../implement/SKILL.md) in a fresh chat: the ticket becomes one `/govern` stage. Its acceptance criteria become the stage's frozen checks, the owner types `/approve` once, and the stage closes when every check passes on the final code.
- [`/implement-spec`](../../implement-spec/SKILL.md) works the whole ticket graph with parallel subagents on one integration branch. The owner still freezes each stage; the skill batches the freeze commands per round.

Questions about stages, checks, receipts or rules: read [building.md](building.md).

## Plan something too big for one session

[`/wayfinder`](../../wayfinder/SKILL.md) is for work whose decisions will not fit one conversation, or whose route is not visible yet. Size and fog decide this, not the word the user chose: a new product one person will use, with a handful of open decisions, is still a `/grill-with-docs` session. Recommend `/wayfinder` only when the user expects many sessions, several people must answer, or research has to finish before most questions can be asked. When unsure, start with `/grill-with-docs`; it can hand over to `/wayfinder` if the interview outgrows the session. The first session charts a map issue and its decision tickets. Each later session resolves one ticket. It produces decisions, not code. When no tickets remain, go to `/to-spec`.

Do not use it for a well-scoped feature: it is slower than `/grill-with-docs`.

## Pick a skill

Read the skill before you recommend it, and give one example prompt.

| The user wants to | Skill |
|---|---|
| Be interviewed about an idea, in a repo | [`/grill-with-docs`](../../grill-with-docs/SKILL.md) |
| Be interviewed about anything, with nothing saved | [`/grill-me`](../../grill-me/SKILL.md) |
| Check a feature request against the job behind it | [`/need-first`](../../need-first/SKILL.md) |
| Fix a fuzzy or overloaded term, or record a hard-to-reverse decision | [`/domain-modeling`](../../domain-modeling/SKILL.md) |
| Turn the conversation into a spec | [`/to-spec`](../../to-spec/SKILL.md) |
| Split a spec or plan into tickets | [`/to-tickets`](../../to-tickets/SKILL.md) |
| Build one ticket | [`/implement`](../../implement/SKILL.md) |
| Build a whole spec in parallel | [`/implement-spec`](../../implement-spec/SKILL.md) |
| Plan a large, unclear effort across sessions | [`/wayfinder`](../../wayfinder/SKILL.md) |
| Sort incoming bug reports and requests | [`/triage`](../../triage/SKILL.md) |
| Choose what to build a new product with, and learn what to set up first | [`/stack`](../../stack/SKILL.md) |
| Decide whether a queue, cache or event system is justified | [`/systems-design`](../../systems-design/SKILL.md) |
| Find modules worth restructuring | [`/improve-codebase-architecture`](../../improve-codebase-architecture/SKILL.md) |
| Design a module's interface | [`/codebase-design`](../../codebase-design/SKILL.md) |
| Answer a design question with throwaway code | [`/prototype`](../../prototype/SKILL.md) |
| Get docs or API facts read and cited in the background | [`/research`](../../research/SKILL.md) |
| Ask someone else for the answers | [`/to-questionnaire`](../../to-questionnaire/SKILL.md) |
| Be walked through setup only a human can do | [`/wizard`](../../wizard/SKILL.md) |
| Move the work to another chat, folder or person | [`/handoff`](../../handoff/SKILL.md) |
| Hear the last message again in plain words | [`/wait-what`](../../wait-what/SKILL.md) |
| Write a skill or an agent-facing doc | [`/writing-for-agents`](../../writing-for-agents/SKILL.md) |
| Configure a project for these skills | [`/setup-project`](../../setup-project/SKILL.md) |

If a skill directory next to this one is missing from the table, read its frontmatter and route by its description.

Not in this plugin: building, testing, reviewing, bug fixing, pull requests and enforced rules. Those are `/govern` and its skills.

## Fix a session that went wrong

| Symptom | Fix |
|---|---|
| The agent asks one question at a time, or asks for facts it could look up | Say "ask the whole frontier in one round, and look facts up yourself". That is the `grilling` skill. |
| The agent starts building during the interview | Say "do not act until I confirm we have a shared understanding". |
| The spec restates the request as the requirement | Run `/need-first` over it, with its review questions. |
| A ticket is one layer (only the database, only the UI) | Reject the breakdown in `/to-tickets`: each ticket is a thin path through every layer that can be shown working. |
| `/implement` stops on a criterion it cannot check | The criterion is not provable. Rewrite it on the ticket as something a command or a driven run can prove. |
| The skills say the tracker was not provided | Run `/setup-project`. |
| The chat is getting long before `/to-tickets` | Compact at the nearest boundary, not mid-interview. See [`references/PHASE-BOUNDARIES.md`](PHASE-BOUNDARIES.md). |
| "This project requires a stage before files change" while writing the glossary, a decision record or `docs/agents/` | The project's `exempt` list predates this plugin. The owner adds the planning globs listed in [`/setup-project`](../../setup-project/SKILL.md) step 4 to `.governance/config.json`. |
| `gh` commands fail | The owner runs `gh auth login` on that machine. |

## Reply

Lead with the answer. Give at most one example prompt in a code block, adapted from [`references/recipes.md`](planning-recipes.md) when one fits, then the file it came from. Keep it short unless the user asked for the whole map.
