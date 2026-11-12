### Fuzz

**You own this task. Plan, review, verify.** The deliverable is a list of replayable findings, then one fix per finding. Fan the hunt out to subagents and stay in the lead.

1. Run the **fuzz** skill, steps 1 to 4: write the properties, test the logic with generated inputs, drive the app through the project's `verify-<app>` skill, and confirm each finding by replaying it from a clean launch.
2. Report the findings table before fixing anything, unless the operator granted full autonomy for the run. Findings whose intended behavior is unclear go to the operator as questions.
3. For each confirmed finding, run the **Bug fix** playbook in its own worktree and its own stage. The repro is the stage's first check. Prepare every contract up front so the owner freezes the batch in one sitting.
4. After the fixes, run the **correct** skill over the findings as a set: a mistake that appeared more than once becomes a rule.
5. Each fix runs **Opening a PR**. One finding per PR.

**Reply:** scope and seed, the findings table with status, what was not covered.
