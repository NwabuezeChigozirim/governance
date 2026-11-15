# Reference: how the parts work

The detail behind the six steps: what adoption adds, the scripts, the hooks, the receipts, and each piece's limits. The owner does not need this to use the plugin; see [GUIDE.md](GUIDE.md).

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
| `tools/governance/` | `stagectl`, `verifyctl`, `rulectl`, `rulekit`, `where`, so CI and the terminal can run them |
| `.governance/config.json` | `require_stage: true`: the hook blocks an agent's file edits until a stage is frozen. `exempt` lists path globs that need no stage. It starts with the planning documents the planning skills write outside a stage: `GLOSSARY.md`, `docs/adr/`, `docs/agents/` and `.scratch/` |
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

Adopting an empty project gives it only R-001 and R-002. When a Technology stack decision
is recorded under `docs/adr/`, those two cover the language it chose; otherwise they
cover Python. Run `adopt.py` again once the project has source files: it adds
the strict rules for the languages it now finds, their bad examples, their rows in
`AGENTS.md` and the linter install step in the workflow, and records today's findings
for those new rules only. Violations of a rule that was already there are never forgiven
by running it again.

Commit the result to the main branch directly (its own pull request has no receipt
yet), then make the `gate` job a required check. Only then is the gate a merge gate.

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
| `stagectl gate` | Passes only when a committed receipt names the tree being checked. When that receipt's review is `independent`, a committed verdict must name the same tree. `--base` passes a change that touches no governed file. `--rerun` runs the receipt's checks again. `--markdown` writes the receipt for the pull request or the CI summary |

The tree ID leaves out Git-ignored files, receipts, verdicts, the trusted-signers
file, contract drafts under `.governance/stages/` and the configured exempt paths.
Any other edit after close changes it, so the gate fails until a new stage proves
the new code.

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
| `skills/verify-stage` | A second agent checks out the exact commit, drives the app itself, tries to break it, and records PASS or FAIL |
| `skills/interrogate`, `skills/arena` | pstack's adversarial review: several agents try to break a change, and only findings proven by a run survive |
| `stagectl verify` | Refuses the author's worktree. On the same clone, a linked worktree must match the author's code exactly, and the verdict stays in local stage state. On another clone, which has no stage state, `--contract` reruns the frozen checks and writes a committed verdict |

Same clone, linked worktree:

```bash
scripts/stagectl --repo ../verifier-worktree verify --stage ST-... --outcome pass --summary "..."
```

Another machine, its own clone of the commit under judgment. Commit the file it writes and push it back; the author pulls, reruns `stagectl run-check --all` (the new commit moved HEAD), then `stagectl close`.

```bash
scripts/stagectl --repo . verify --stage ST-... --contract .governance/stages/<short-name>.json \
  --outcome pass --summary "Drove the totals form and saw thirty" \
  --checker "other-vm" --control verify-<app> --live totals=1=verified
```

`--live` repeats once per feature-map entry, as `feature=entry=verified|failed|unreachable`. `--control` names the control skill or other driver used on the live app. Both may be omitted; the summary is required either way. Screenshots and recordings stay under the git-ignored `.verify/` directory.

The committed record is `.governance/verdicts/<record_sha256>.json`. It names who checked (`checker`), which head (`head.commit` and the governed `head.tree`), which checks ran and how they finished (`checked`), and what was seen (`evidence`). `report` is `PASS`, `FAIL`, or `INVALID`. `record_sha256` is the hash of the other fields, and the file name is that hash.

`stagectl gate` recomputes the governed tree and reads the contract file the verdict names. It rejects a missing verdict, a verdict whose hash does not match its contents, a verdict for a different tree, a verdict whose commit does not contain that tree, a verdict whose contract file changed, a verdict that is missing a required field, and a re-proof whose `supersedes` link does not match the predecessor it names. The hash binds those fields together. It proves what the record says was checked.

Signing is opt-in. Set `require_verdict_signature` to `true` in `.governance/config.json` once the owner has published `.governance/verdict-signers` on the base branch. Until then, a verdict is unsigned and the gate does not ask for a signature. Existing verdicts keep working. The owner holds the trusted list: an agent cannot edit that file, and the owner changes it by committing it on the base. A key added in the pull request under review is not trusted for that pull request. The gate reads the list from the merge-base of `--base`. It also stays required when the pull request turns the flag off, if the base still has it on. Pass `--base` whenever the flag is on; without it the gate stops rather than trust this branch's list.

The checker creates a key outside the repository and sends the owner only the public line:

```bash
ssh-keygen -t ed25519 -f ~/.config/governance/verdict-key -N "" -C "<checker identity>"
```

The owner adds `<checker.identity> namespaces="governance-verdict"` plus the key type and the public key to `.governance/verdict-signers`, and commits that on the base branch before any pull request relies on it. The checker then passes the private key with `--key` or `GOVERNANCE_VERDICT_KEY`. `ssh-keygen -Y sign` writes `.governance/verdicts/<record_sha256>.sig` beside the verdict. The signed bytes are `governance-verdict-v1 <record_sha256>`. That hash covers every field, including `supersedes`, so a re-proof is signed too. The verdict JSON is unchanged, and its file name stays the record hash. The trusted line is `<checker.identity> namespaces="governance-verdict" <key type> <public key>`. The principal has to be the verdict's `checker.identity`. The gate rejects a missing signature, a signature that does not match the hash, a key that is not in the base list, and a key that is listed under a different name.

A rebase onto new commits changes the tree even when the patch is the same, so the old verdict stops matching and the gate rejects it. That rejection stays. Carrying the old file forward is not allowed. After the rebase, and after CI is green on the new head, the checker runs `stagectl reprove` on a clone that does not hold the stage. Re-proof runs the frozen checks again on the new tree and writes a new verdict. It does not copy the old one.

An unchanged `git patch-id --stable` is required before that re-proof runs with no new approval. The id is the diff from the merge-base with `--base` to the commit, ignoring `.governance/verdicts` and `.governance/receipts`, because those files are the proof rather than the change. The same id is computed for the superseded commit. If the two ids differ, reprove writes nothing: the patch changed, and that needs a new `stagectl verify`. If the ids match and a check fails, reprove writes a failing verdict and the gate rejects it. The new file's `supersedes` names the old record hash, the old commit, and the old tree. `patch_id` and `patch_base` name the new side. `head` is the new commit and the new tree.

```bash
scripts/stagectl --repo . reprove --stage ST-... --supersedes <record_sha256> --base origin/main \
  --contract .governance/stages/<short-name>.json --outcome pass \
  --summary "Re-ran the totals form on the rebased tree and saw thirty" --checker "<your name>"
```

The author then pulls that commit and runs `stagectl resume`, `stagectl run-check --all`, and `stagectl close`. Resume reopens the same stage with no new approval, and only when that passing re-proof already covers the current tree. Close writes a receipt for the new tree and leaves the receipt for the old tree in place.

This separates checkouts, not identities. On one machine it proves the work was committed and passes in a clean worktree. Across machines it proves a clean checkout of that commit passed the frozen checks, and it records the live drive the checker claims. It still cannot prove a different agent ran the command.

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
Stage state is local to the machine (`<git-common-dir>/governance-v3/`), which is why a verdict used to be invisible to another clone. The receipt and the independent verdict are the records that are committed. The three scripts
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
this repository's CI. `trust-help`'s building reference is `poteto-help` rewritten for this plugin.
Not brought in: `make-bot-ui`, `ketchup-video` and the Benny automation pack.

### Planning skills

| Piece | What it does |
|---|---|
| `skills/start`, `skills/next`, `scripts/where` | The front door. `where` reads the repository, the stage state and GitHub and reports which of the six steps the project is on; `/next` does that step |
| `skills/grilling`, `grill-with-docs`, `grill-me`, `need-first`, `domain-modeling` | The interview: rounds of questions with recommended answers, each feature tested against the job behind it, agreed words kept in `GLOSSARY.md`, hard decisions under `docs/adr/` |
| `skills/stack` | Recommends the technology stack from the settled requirements, shows alternatives, lists what the owner must set up first, and records the choice |
| `skills/to-spec`, `to-tickets` | The spec as one issue with numbered stories; tickets as vertical slices with provable criteria, blocking links, and every story accounted for |
| `skills/implement`, `implement-spec` | Build one ticket as one stage, or a whole spec in parallel |
| `skills/wayfinder`, `research`, `prototype`, `triage`, `to-questionnaire`, `handoff`, `wizard`, `systems-design`, `codebase-design`, `improve-codebase-architecture`, `writing-for-agents`, `wait-what` | Optional: large multi-session planning, background research, throwaway prototypes, sorting incoming issues, and design help |

These are prose: nothing enforces that an agent follows them, apart from the stage that building always runs inside. Most are adapted from Matt Pocock's skills; `need-first` and `systems-design` come from an earlier suite; `start`, `next`, `stack`, `adopt` and `approve` are new.
