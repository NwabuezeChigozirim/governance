# governance

A Cursor plugin that makes coding agents prove their work. It is built on one equation:
good codebase + good environment + verification = work that does not need rechecking.

The owner approves a stage's intent and checks once. After that the agent must drive
the real app, seal the evidence, pass an independent verdict from a second checkout,
and close the stage on evidence that matches the current code.

## Install

```bash
python scripts/install.py
```

This copies the plugin into `~/.cursor/plugins/local/governance` and pins the hooks to
the Python that ran the installer, so it works where `python3` is not on PATH (common
on Windows). Run it again after pulling changes, then restart Cursor and start a task
with `/govern <what you want>`. Needs Python 3.10+ and Git.

## Adopt a project

Installing the plugin gives Cursor the skills and hooks. A project is constrained only
after its owner adopts it:

```bash
python scripts/adopt.py --repo path/to/project
```

In Cursor the owner types `/adopt` with the project open instead: it runs the same script,
installs any linter the script names, commits the result and makes the `gate` job a
required check. Agents never start it themselves.

| It adds | Effect |
|---|---|
| `tools/governance/` | `stagectl`, `verifyctl`, `rulectl`, `rulekit`, so CI and the terminal can run them |
| `.governance/config.json` | `require_stage: true`: the hook blocks an agent's file edits until a stage is frozen. `exempt` lists path globs that need no stage. It starts with the planning documents the `intent` plugin writes outside a stage: `GLOSSARY.md`, `docs/adr/`, `docs/agents/` and `.scratch/` |
| `.governance/rules.json`, `bad/R-*.*`, `baseline.json` | Starter rules, each with a bad example, and a baseline of today's violations. R-001: no comments in source files. R-002: no source file over 400 lines. Then the strict preset for the language |
| `ruff.toml` or `eslint.config.mjs` | Strict linter settings, only when the project has none |
| `AGENTS.md` | A `## Rules` table listing the starter rules |
| `.github/workflows/governance.yml` | On every pull request: the rules hold, every rule's proof fails as it must, and a stage receipt matches the exact code |
| `.gitignore` | `.verify/` |

The strict preset is borrowed judgement: the standard tools already encode what
experienced engineers reject, so the owner does not have to.

| Project | Rules added | Needs installed |
|---|---|---|
| Python | `ruff` with a wide rule set (bugs, complexity limit 10, naming, unused arguments, dead code) and `mypy --strict` | `pip install ruff mypy` |
| TypeScript or JavaScript with a `package.json` | ESLint with `typescript-eslint` strict, complexity limit 10, depth 4, 4 parameters; plus `tsc --strict --noUncheckedIndexedAccess` when there is a `tsconfig.json` | `npm install --save-dev eslint @eslint/js typescript-eslint typescript` |
| Other languages | R-001 and R-002 only | Nothing |

If a tool is missing, adoption says `NOT DONE` and names the command to run; the
baseline is recorded once the tools are there. An existing linter config is used as it
is, not replaced.

It never overwrites a file that exists, apart from refreshing `tools/governance/`.

Adopting an empty project gives it only R-001 and R-002, because there is no language
to choose a preset for. Run `adopt.py` again once the project has source files: it adds
the strict rules for the languages it now finds, their bad examples, their rows in
`AGENTS.md` and the linter install step in the workflow, and records today's findings
for those new rules only. Violations of a rule that was already there are never forgiven
by running it again.

Commit the result to the main branch directly (its own pull request has no receipt
yet), then make the `gate` job a required check. Only then is the gate a merge gate.

## Test

```bash
python -B -m unittest discover -s tests
```

CI runs this on Linux and Windows.

## What is here now

### Verification

| Piece | What it does |
|---|---|
| `skills/create-verification-skill` | Generates a project-local `verify-<app>` skill: launch, doctor, drive, evidence, cleanup, plus a feature map |
| `skills/maintain-verification-skill` | Re-reads and re-drives every mapped feature and ships proven corrections |
| `skills/principle-prove-it-works` | The rule that done means checked against the real artifact |
| `scripts/verifyctl` | Enforces the above: lints the skill and map, seals proof files by hash, and fails when evidence is missing, changed, or does not cover a feature |

```bash
scripts/verifyctl lint   --skill .cursor/skills/verify-<app>
scripts/verifyctl record --skill ... --run .verify/runs/<id> --feature <id> --entry "<entry point>" --outcome verified --artifact <file>
scripts/verifyctl check  --skill ... --run .verify/runs/<id> --all
```

Exit codes: 0 valid, 2 invalid invocation, 3 validation failed. Standard library only.

`verifyctl` proves the evidence exists, is unchanged since it was recorded, and covers
the requested features through every entry point their feature files list. An entry
point that cannot be reached is recorded as `unreachable` with its reason; one with no
record fails the check. It does not judge whether a screenshot shows the right thing.

### Environment: the rule table

| Piece | What it does |
|---|---|
| `skills/correct` | Finds mistakes agents repeat and fixes each at the highest level that works: architecture, types, lint, test, docs last |
| `skills/principle-encode-lessons-in-structure` | The rule that a repeated instruction should become a check |
| `scripts/rulectl` | Reads the `## Rules` table in `AGENTS.md` and fails when a rule cites no existing enforcer, its proof does not fail, a docs-only rule gives no reason, or docs-only rules exceed a limit |

```bash
scripts/rulectl check --repo . --prove --max-docs 3
```

Each enforced rule carries a Proof: a command that runs the enforcer against a
committed example of the mistake. `--prove` runs it and rejects the rule when the
command passes or cannot run, so a rule whose enforcer catches nothing is not counted
as enforced. A failing proof shows the enforcer rejects that one example, not every
form of the mistake. `--prove` executes commands from the instruction file.

### Environment: the rule kit

| Piece | What it does |
|---|---|
| `scripts/rulekit` | A dependency-free linter driven by `.governance/rules.json`. Six kinds of rule: `ban-comments`, `ban-import` (one directory may not import from another), `ban-pattern` (a banned API or construct), `max-lines` (a file-length cap; a file already over it may shrink but not grow), `require-layout` (source files may live only in the listed folders), and `linter` (runs the project's own linter or type checker and holds its findings to the same baseline). Every failure prints the rule's message, which states the fix |
| `skills/rulekit` | How an agent adds a rule: config entry, committed bad example, proof command, table row |

```bash
python tools/governance/rulekit check
python tools/governance/rulekit check --rule R-002 --as src/renderer/x.ts .governance/bad/R-002.ts
python tools/governance/rulekit baseline
python tools/governance/rulekit check --no-baseline
python tools/governance/rulekit survey
```

The baseline records how many violations each file has today, so a rule can be switched
on in an old codebase and fail only when a file gets worse. It only shrinks: growing it
needs `--owner-approved`, which the hook stops an agent from passing unless the owner
typed `/approve baseline`.

Limits: `ban-comments` covers Python (exact, via the tokenizer) and C-style languages
(a scanner that skips strings, templates and most regular-expression literals; an
unusual regex can be misread). `ban-import` resolves relative imports and Python
modules, not bundler path aliases; use `forbid_specifiers` for those. It is a starter
kit, not a replacement for the project's own linter and type checker; the `linter`
kind is how those are brought under the same baseline. A `linter` rule is only as
strict as the tool's config file, so the hook protects those files: in a project with
`.governance/rules.json`, an agent can edit the rule file, `ruff.toml`, `mypy.ini`,
`eslint.config.*`, `.eslintrc*`, a root `tsconfig*.json` or the governance workflow
only when the frozen contract lists that file in `outputs`, and can never edit the
baseline by hand. `protected` in `.governance/config.json` adds more globs, for
example `pyproject.toml`. This covers the edit tools, not a file written through the
shell; the diff and the owner's review catch that. `max-lines` and
`require-layout` are blunt: they stop a file or folder from getting worse, they do
not tell you the right design.

### Merge gate: the receipt

| Piece | What it does |
|---|---|
| `stagectl close` | Also writes `.governance/receipts/<stage>.json`: intent, acceptance, checks, verdict, and the Git tree ID of the code that was proven |
| `stagectl gate` | Passes only when a committed receipt names the tree being checked. `--base` passes a change that touches no governed file. `--rerun` runs the receipt's checks again. `--markdown` writes the receipt for the pull request or the CI summary |

The tree ID leaves out Git-ignored files, receipts, contract drafts under
`.governance/stages/` and the configured exempt paths. Any other edit after close
changes it, so the gate fails until a new stage proves the new code.

Limits: without `--rerun` the gate trusts the receipt, and a receipt is a plain file
that an agent could write by hand through the shell (the hook only stops the edit
tools). With `--rerun` CI runs the listed checks itself, but it cannot tell whether
the owner approved that list. The receipt is in the diff, so a reviewer can. Runtime
evidence (screenshots, recordings) stays local under `.verify/`; the agent attaches it
to the pull request, and CI does not see it.

### Flow: the stage contract

| Piece | What it does |
|---|---|
| `skills/stage` | The working loop: restate the intent, freeze it with checks after the owner approves, do the work, prove it, close |
| `skills/in-your-own-words`, `skills/principle-sequence-verifiable-units` | Restating the goal, and splitting work into units that each end in a check |
| `scripts/stagectl` | Freezes the contract, runs its checks, and binds each receipt to the exact code tested. `close` needs no owner flag: it succeeds only when every receipt is current |

```bash
scripts/stagectl --repo . freeze --contract stage.json --owner-approved
scripts/stagectl --repo . run-check --all
scripts/stagectl --repo . close
```

### Independent verdict

| Piece | What it does |
|---|---|
| `skills/verify-stage` | A second agent checks out the exact commit in its own worktree, drives the app itself, tries to break it, and records PASS or FAIL |
| `skills/interrogate`, `skills/arena` | pstack's adversarial review: several agents try to break a change, and only findings proven by a run survive |
| `stagectl verify` | Refuses the author's worktree, requires the verifier's checkout to match the author's code exactly, and reruns every frozen check there. A contract with `"review": "independent"` cannot close without a passing verdict on the current code |

```bash
scripts/stagectl --repo ../verifier-worktree verify --stage ST-... --outcome pass --summary "..."
```

This separates checkouts, not identities: it proves the work was committed and passes
in a clean tree, and it cannot prove a different agent ran the command.

Ported from the earlier `governance-system` stage contracts, without policy versions,
approval-record files, discovery notes or impact review. The owner approves once at
freeze and again only for a revision. There is one stage per worktree, so agents in
separate worktrees run in parallel. `verifyctl check --fresh` ties recorded evidence to
the current code, so a stage cannot close on proof gathered before the last edit.

The owner approves in chat by typing `/approve`. Cursor's `beforeSubmitPrompt` hook sees
that message, which an agent cannot write, and records a grant in the stage state
directory. The grant lets the agent run one freeze or revise command, in the same
conversation, within fifteen minutes, for the newest contract under `.governance/stages/`
(or the one named, `/approve <short-name>`) exactly as it was when the owner typed it.
`/approve baseline` does the same for one `rulekit baseline --owner-approved`. Without a
grant the hook blocks these commands, and the owner can always run them in a terminal.

Limits: `--owner-approved` is an attestation, not authentication. Whether Cursor passes a
typed slash command to `beforeSubmitPrompt` unchanged is unconfirmed; if it does not, no
grant is recorded and the terminal remains the way to approve. A stage in another
worktree (as `/implement-spec` uses) is not covered by `/approve` yet. A passing check does
not prove the check covers its acceptance item. Environment, services and toolchain
versions are not part of the fingerprint. Reopening a closed stage is not implemented.
State is local to the machine (`<git-common-dir>/governance-v3/`). The three scripts
run on Linux, macOS and Windows; on Windows invoke them as `python <path>`.

### Entry point, hooks and install

| Piece | What it does |
|---|---|
| `skills/govern` | The starting command. pstack's `/poteto-mode` router and its 23 playbooks, renamed, with a Governance section that wraps every change-shipping playbook in a stage |
| `hooks/guard.py` | Blocks an agent from recording owner approval, touching stage records or writing a receipt. While a stage is active, blocks destructive or unclassified Git commands. In a project with `require_stage`, blocks file edits until a stage is frozen and blocks edits to the config. At the end of a turn, sends the agent back once if the stage is unproven, or if governed files changed with no stage and no receipt |
| `hooks/hook_policy.py` | The Git command classifier, carried over from the earlier `governance-system` |

The hooks follow the layout other Cursor plugins use (`hooks/hooks.json`,
`${CURSOR_PLUGIN_ROOT}`); pstack itself ships none. They are tested by feeding payloads
to the script, not inside a running Cursor, so the exact payload fields and the
`loop_limit` behavior are unconfirmed there, including which tool names Cursor reports
for file edits. The guard is a guardrail, not a sandbox: a command that hides
`--owner-approved` behind a script or variable is not caught, and a file written through
the shell is not blocked at the time. The end-of-turn check and the CI gate catch that
afterwards. A
cloud agent with no human at a terminal has no way to obtain the freeze approval yet.

### Gardening and cleanup

| Piece | What it does |
|---|---|
| `rulekit survey` | Facts about where the code is weakest: longest files, fullest folders, excuse comments, silenced checks, and how much of each rule's baseline is left |
| `skills/garden` | Reads the survey, recent commits and past chats, groups repeated mistakes into habits, appends them to `.governance/findings.md`, and proposes one rule per habit for the owner to approve |
| `skills/govern/playbooks/cleanup.md` | Removes one rule's old violations in reviewable batches, each in its own stage, with behavior unchanged, and shrinks the baseline |

The survey is deterministic. The garden skill and the cleanup playbook are prose:
nothing enforces that they are run. Run `/garden` every few days, or on a schedule.
Not from pstack; the idea is from Lauren Tan's talks (the gardener role, and logging
findings before fixing them).

### Fuzzing

| Piece | What it does |
|---|---|
| `skills/fuzz`, `skills/govern/playbooks/fuzz.md` | Write the properties that must always hold, test logic with generated inputs, drive the app unpredictably through the `verify-<app>` skill, keep only findings that replay, and fix each in its own stage |

This is prose: nothing enforces that a fuzz run was thorough. Not from pstack.

### Brought in from pstack as-is

| Group | Skills |
|---|---|
| Code quality | The 24 `principle-*` skills, `tdd`, `blast-radius`, `no-comments` (with the `comment-sicko` agent), `reflect`, `benchmark-checklist`, `typescript-best-practices` |
| Context | `how`, `why`, `recall`, `architect`, `teach`, `sharpen` |
| Scale | `swarm`, `arena`, `figure-it-out`, `show-me-your-work`, `ketchup`, `bro`, and the autonomous-run, orchestrate, autopilot, babysit and shipping playbooks |
| Formal verification | `create-formal-verification-skill`, `maintain-formal-verification-skill`, `statechart` |
| Support | `setup-pstack` (model routing; still writes `pstack-models.mdc`), `unslop`, `technical-writing`, `automate-me`, the `govern-agent` delegate |

These are copied unchanged apart from renaming `poteto-mode` to `govern` and
`poteto-agent` to `govern-agent`. `tests/test_package.py` fails if any skill names a
skill the plugin does not ship. Some steps still name skills from Cursor's own
`cursor-team-kit` plugin (`deslop`, `control-ui`, `control-cli`); the Governance section
tells the agent what to do in their place. The copied TypeScript helpers
were run once here on Linux: `govern/scripts` with `bun test` (61 pass) and its
type check, `statechart/scripts` with `npm test` under Node 22 (267 pass, 67 skipped
because they need `TLA2TOOLS` pointing at `tla2tools.jar`). They are not part of
this repository's CI. `govern-help` is `poteto-help` rewritten for this plugin: the
routing table and prompt references are kept, the setup, stage and rule sections
are new, and links to pstack's guide pages are gone.
Not brought in: `make-bot-ui`, `ketchup-video` and the Benny automation pack.

## Planned, in order

1. Trial inside Cursor on a real project, including `adopt.py` and the CI gate
2. Owner approval for cloud agents with no human at a terminal
3. Claude Code adapter

## Credit

Most skills, the playbooks, both agents and the feature-map example are taken from
[pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT, commit
`2eaf465`), with additions that wire them to `verifyctl` and `rulectl`. See
`THIRD_PARTY_LICENSE-pstack`.
