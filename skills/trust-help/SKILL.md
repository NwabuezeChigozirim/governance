---
name: trust-help
description: Answers questions about how to use this plugin. Explains the six steps, what to type, and which skill fits a situation outside the main path. Type /trust-help with a question.
disable-model-invocation: true
---

# Help

Answer the owner's question about using this plugin, in plain words. Do not start the work; point them to it.

## The short answer, which covers most questions

There is one path with six steps: Describe, Choose the stack, Spec, Tickets, Build, Merge. Read [STEPS.md](../start/STEPS.md) for the table.

The owner needs three commands:

| Type | When |
|---|---|
| `/start <what you want>` | To begin a new product or feature |
| `/next` | Any time, in any chat: it says where the project is and does the next step |
| `/approve` | When shown what is about to be built |

If the question is "what do I do now", "where am I" or "what comes next", the answer is to type `/next`. Run the `where` script (`../../scripts/where --repo .`) and tell them what it reports.

## Questions past the main path

Everything else in the plugin is optional. Read the reference that matches the question, then answer from it:

- **Planning**: interviews, glossary, research, prototypes, large multi-session efforts, sorting incoming issues. Read [references/planning.md](references/planning.md).
- **Building and checking**: stages, contracts, checks, receipts, rules, the merge gate, bug fixing, reviews. Read [references/building.md](references/building.md).

Read the skill you are about to recommend before recommending it, and give one example prompt.

## Reply

Lead with the answer. One command the owner can type, when there is one. Name where it came from only if they ask.
