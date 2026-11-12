### Cleanup

**You own this task. Plan, review, verify.** The deliverable is a smaller baseline for one rule, with behavior unchanged. Old violations are what the next agent copies; this playbook removes them.

1. Pick one rule. Run `python tools/governance/rulekit survey` and read `baseline_left`. Unless the operator named a rule, take the one with the most violations left. Never mix two rules in one change.
2. List the work: `python tools/governance/rulekit check --rule <ID> --no-baseline --json`. Group the files into batches a reviewer can read in one sitting, about 10 files or 300 changed lines each. Files that change together go in one batch.
3. Each batch is its own stage and its own worktree. The contract's checks are the project's full test suite, `rulekit check`, and `rulekit check --rule <ID> --no-baseline <the batch's files>`, which must pass with zero violations for those files. Prepare every contract up front so the owner freezes the batch list in one sitting.
4. Fix the cause, never the symptom. A comment is deleted only after its reason is carried by a name, a type or a test. A type error is fixed with the real type, never `any`, a cast or a suppression. A long file is split by responsibility, never by line count. If the fix needs a behavior change, stop and report it; that is a different task.
5. Behavior must not change. Run the tests before and after. Where the touched code has no test, write a characterization test first (the **tdd** skill) and commit it before the fix.
6. After the fix, run `python tools/governance/rulekit baseline`. It only shrinks, so it refuses if anything got worse. Commit the smaller baseline in the same change.
7. Each batch runs **Opening a PR**. Fan batches out to subagents when they do not touch the same files.
8. When a rule's baseline reaches zero, say so. The owner can then tighten it, for example a lower `max` for `max-lines`.

**Reply:** the rule, violations before and after, batches opened, and anything skipped because it needed a behavior change.
