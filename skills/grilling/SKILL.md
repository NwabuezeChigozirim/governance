---
name: grilling
description: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

**If you have a tool for asking the user questions, use it for every round**, and print nothing in its place. Put each frontier question in the tool with your recommended answer as the first option, marked as recommended. Where the decision has real alternatives, offer them as options, each with what it gives and what it costs; do not reduce a decision to yes or no on your own proposal when another answer is plausible. If the tool takes fewer questions than the frontier holds, send the round as consecutive calls.

With no such tool, format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Word each question so "yes", or picking the first option, accepts your recommended answer.

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, tools, etc.), dispatch a sub-agent with a fresh context window to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

**What it is built with is a branch of the tree.** When the thing being planned has no code yet (a new product, or a new part such as a first mobile app or database), the frontier is not empty until its technology stack is decided. Do not ask the user to pick one. Once what it must do is settled, load and follow the `stack` skill: it recommends a stack from those requirements, shows the alternatives, and lists what the user must set up before building.

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.
