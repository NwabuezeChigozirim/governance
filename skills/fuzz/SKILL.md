---
name: fuzz
description: "Hunt for bugs nobody reported: drive the real app like an unpredictable user and test stated properties with generated inputs, then turn each confirmed bug into a failing repro and a fix stage. Use for /fuzz, after a release build, or when asked to find bugs, stress, or harden a feature."
disable-model-invocation: true
---

# Fuzz

A fuzz run finds bugs by trying inputs and sequences nobody wrote a test for. It produces findings, each with a repro that fails on demand. It ships nothing by itself: every fix goes through its own stage.

It depends on the project's `verify-<app>` skill. If there is none, run the **create-verification-skill** skill first. Fuzzing an app you cannot launch and drive reliably produces noise.

## 1. Say what must always hold

A fuzz run without properties only finds crashes. Read the feature map and write, per feature, the things that are true whatever the user does. Useful families:

- **Round trip.** Save then load gives back the same thing. Encode then decode. Undo then redo.
- **Invariant.** A total is never negative. A list never shows a deleted item. Exactly one item is selected.
- **Idempotence.** Doing it twice equals doing it once (retry, double click, replayed request).
- **Equivalence.** Every entry point the feature file lists leaves the same state.
- **Order independence.** Two independent actions give the same state in either order.
- **No crash, no hang.** No uncaught error in the console or log, and the app answers within its normal time.

Write them to `.verify/fuzz/<run>/properties.md`. If the project has a formal model (the **create-formal-verification-skill** skill), take its invariants: they are already the properties.

## 2. Property-based tests for logic

For pure logic (parsers, reducers, calculations, state machines), use the language's property-testing library: Hypothesis for Python, fast-check for TypeScript and JavaScript, proptest for Rust, `testing/quick` or rapid for Go. Generate inputs, assert the property, let the library shrink a failure to its smallest case. Keep every shrunk failing case as a named regression test.

Do not add a property-testing dependency without the owner's agreement. If there is none and they decline, generate inputs with a seeded loop in an ordinary test and print the seed on failure.

## 3. Drive the app like a hostile user

Through the `verify-<app>` driver, per feature, in this order:

1. **Boundaries.** Empty, one, many, the maximum, one past it. Very long text, text with quotes and markup, other scripts, emoji, leading and trailing spaces.
2. **Sequences.** Random walks over the feature's actions from a seeded generator. Record the seed and the action list as you go, so any failure replays.
3. **Interruptions.** Act twice quickly, navigate away mid-action, reload, go offline and back, resize, two windows or sessions on the same data.
4. **States the map marks as gotchas.** Each gotcha in a feature file is a lead.

After every action check the properties from step 1 and read the console and logs. Fan out across features with the **swarm** skill when the map is large; give each agent its own app instance and seed.

## 4. Confirm before you report

A finding counts only when it replays. For each suspected bug:

1. Replay it from a clean launch using the recorded seed or action list. No replay, no finding: note it as a flake with what you saw.
2. Shrink it to the fewest steps that still fail.
3. Check it against the intended behavior (the spec, the feature file's Expected behavior). Surprising is not the same as wrong. If intent is unclear, list it as a question for the owner, not a bug.
4. Write `.verify/fuzz/<run>/findings/<n>-<slug>.md`: the property broken, the shortest repro, expected, actual, and the evidence file.

## 5. Fix each finding in its own stage

Per confirmed finding, run the **Bug fix** playbook inside a stage (the **stage** skill): the repro lands first as a failing check, the fix lands on top, and the stage's checks include the repro. One finding per stage and per PR. Do not batch fixes, and do not fix what you could not replay.

When a finding shows a whole class of mistake, run the **correct** skill after the fix so the class is closed by a rule, not only this instance.

## 6. Report

Open with the scope and the seed. Then a table: finding, property broken, steps to replay, severity, status (PR link, question for owner, or flake). State what was not covered: features skipped, entry points unreachable, properties you could not check. A clean run says how many actions ran over which features, not "no bugs".

## Rules

- Never weaken a property to make a run clean. A property that turns out wrong is a question for the owner.
- Fuzz a local or disposable instance. Never production, never shared data, never real accounts or payment paths.
- Keep the app instance, data directory and ports private to the run, and stop them at the end.
