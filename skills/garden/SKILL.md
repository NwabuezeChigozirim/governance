---
name: garden
description: "Find the bad habits that are spreading through this codebase before agents copy them further: long files, excuses in comments, silenced checks, repeated workarounds, and the corrections the owner keeps making in past chats. Log them in .governance/findings.md and propose one enforced rule per repeated habit. Use for /garden, 'what is wrong with this codebase', 'find anti-patterns', 'what should we ban next', or on a schedule."
disable-model-invocation: true
---

# Garden

Agents copy what they see. One workaround becomes the house style within weeks. Your job is to find what is spreading, write it down, and propose the rule that stops it. You do not fix anything in this skill.

In an adopted project the tools are at `tools/governance/`. If there is no `.governance/rules.json`, ask the owner to run the plugin's `scripts/adopt.py --repo <project>` first.

## 1. Collect facts, not impressions

```bash
python tools/governance/rulekit survey
python tools/governance/rulekit check --no-baseline --json
```

`survey` reports the longest files, the fullest folders, lines that carry an excuse (`TODO`, `HACK`, "for now", "workaround"), silenced checks (`eslint-disable`, `@ts-ignore`, `as any`, `type: ignore`, `noqa`), and how much of each rule's baseline is left. `check --no-baseline` lists every old violation the baseline still tolerates.

Then read, in this order, stopping when you have enough:

1. The ten longest files and the three fullest folders. Note every job each one does.
2. Every excuse sample and silenced check. Note what the code was avoiding.
3. The last 30 commits and any reverts (`git log --oneline -30`, `git log --grep=Revert`).
4. Past chats for this project, with the **recall** skill's transcript search. Look only for the owner correcting an agent: "no", "not like that", "I told you", "again", "why did you".

## 2. Group into habits

A habit is the same mistake in two or more places, or one the owner corrected twice. A single odd file is not a habit; leave it out.

Look for these first, because they are the ones that spread:

| Habit | What you see |
|---|---|
| Excuse instead of fix | A comment that explains why the real fix was skipped |
| Silenced check | A suppression directive, a cast to `any`, a skipped test |
| Second way to do one thing | Two helpers, two fetch wrappers, two state stores for the same job |
| File that does everything | A file near or over the length limit that keeps growing |
| Code in the wrong place | Imports that reach across folders that should not know each other |
| Copy and paste | The same block in three or more files |
| Timer or retry as a patch | `setTimeout`, `sleep`, retry loops that hide an ordering bug |
| Test that cannot fail | A test that asserts what it just set up |

## 3. Append to the findings log

Append to `.governance/findings.md`; never rewrite earlier entries. One block per habit:

```markdown
## 2026-11-12: Second fetch wrapper
- Seen in: `src/api/http.ts:14`, `src/features/cart/request.ts:3`, `src/features/user/load.ts:22`
- Count: 3 places, 1 owner correction (chat 4f2a…)
- Why it spreads: each new feature copies the nearest wrapper
- Proposed rule: ban-import, `src/features/**` may not import `axios`; message "Call `request` from `src/api/http.ts`."
- Level: lint (architecture would be better: export one client and delete the others)
- Status: proposed
```

If the habit is already in the log, add today's count under it. A count that rose since the last entry is the strongest signal you have.

## 4. Propose rules, strongest level first

For each habit, use the **correct** skill's ladder: make it impossible with architecture, then types, then a lint, then a test. For the lint level, the **rulekit** skill has six kinds: `ban-comments`, `ban-import`, `ban-pattern`, `max-lines`, `require-layout`, `linter`. Write the exact rule entry and its message. The message names what to use instead.

Show the owner the three habits with the highest counts and ask which to enforce. Do not add a rule they did not pick. Each approved rule is its own stage through the **rulekit** skill; old cases go to the baseline and are removed later with the Cleanup playbook.

## Limits

- You propose; the owner decides. Never edit `.governance/rules.json` in this skill.
- Never recommend a rule you cannot state as something a machine can see. Log it with `Level: docs` and say why.
- No taste calls. Every finding cites files and lines.

**Reply:** the facts from `survey` in three lines, the habits table with counts, the top three proposed rules with their exact entries, and what you did not look at.
