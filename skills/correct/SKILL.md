---
name: correct
description: "Find the mistakes agents keep repeating in this repo and make each one impossible. Try architecture first, then types, then a lint whose error names the fix, then a test, and write docs last. Prove each check fails on a real past mistake. Repeat this each time the operator corrects you. Use for /correct."
disable-model-invocation: true
---

# Correct

The operator keeps correcting agents in this repo for the same mistakes. Change the repo so the next agent can't make them.

Assume every contributor is an agent that sees only the files it opened, copies the nearest example, and takes the shortest path that compiles. Design the repo so a change that looks right from one file is right for the whole repo.

## Find the mistake classes

First, read recent commits, reverts, review comments, agent instruction files, and comments that explain workarounds. Group the mistakes into classes. A class counts once it has happened twice.

## Fix each class at the highest level that works

1. **Eliminate it with architecture.** Give each piece of state one owner and each task one supported way. Hide internals so the wrong import fails. Replace hand-synced lists with one source of truth. Delete old ways and dead code an agent would copy.
2. **Enforce it with types so the bad state can't be written.** If bad code still compiles, add a lint or CI check whose error names the file, type, or function to use instead. If the pattern is already common, fail only when a change adds more.
3. **Test the behavior.** Fix or delete any test that still passes when the behavior it checks breaks, or that fails when only the internals change.
4. **Write docs or agent rules last, only for judgment calls.** Nothing fails when an agent skips them.

## Fix and prove

Then fix the most frequent classes now, one commit each. Prove each new check fails on a real past mistake. Run the same command locally and in CI. Exceptions go on the offending line with a reason, an expiry date, and a human's approval.

## Keep the rule table

Last, keep a table in the agent instruction file that pairs each rule with what enforces it. When the operator corrects you, fix the mistake and add the rule. If the rule was already there and nothing enforces it, that's a repeat, so fix it at the highest level in the same change. Drop a rule once its mistake can't happen.

The table sits under a `## Rules` heading in `AGENTS.md` with exactly these columns:

```markdown
| ID | Rule | Level | Enforced by | Proof | Notes |
|---|---|---|---|---|---|
| R-001 | Renderer never imports main-process code | lint | `eslint.config.js` rule no-main-import | `npx eslint rules/bad/R-001.ts` | |
| R-002 | Prefer one PR per slice | docs | | | Judgment call; no size threshold fits every change |
```

`Level` is `architecture`, `types`, `lint`, `test`, or `docs`. Above `docs`, `Enforced by` cites in backticks the repository file that does the enforcing, and `Proof` is one backticked command that runs that enforcer against a committed example of the mistake, taken from the real past mistake where you can. The proof command must fail. Keep bad examples somewhere the normal build and lint skip, such as `rules/bad/`, so they fail only when the proof targets them. A `docs` rule says in `Notes` why no higher level worked. Then run the checker, locally and in CI:

```bash
python3 ../../scripts/rulectl check --repo . --prove --max-docs <n>
```

It exits 3 when a rule cites no existing enforcer, a proof passes (the enforcer let the mistake through) or cannot run, a `docs` rule gives no reason, or the count of `docs` rules passes the limit. Set the limit to today's count and lower it as rules move up. A rule the checker rejects is not in force, whatever the table says.

**Reply:** each class with its evidence, the level you picked, and why a higher level didn't work.
