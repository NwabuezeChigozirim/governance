---
name: start
description: "The front door. The owner types /start with what they want to build, a new product or a new feature, and is taken through the six steps from idea to merged code. Owner-started only."
disable-model-invocation: true
---

# Start

The owner wants to build something and has typed `/start` with a description. Take them down the one path in [STEPS.md](STEPS.md). They should never have to choose a skill, know which step comes next, or run a setup command.

## 1. See where the project is

Run the `where` script (`../../scripts/where --repo .` from this file, or `tools/governance/where` in an adopted project). Read [STEPS.md](STEPS.md) for what each step is and how to speak to the owner.

- If it reports work already under way (a stage being built, an open pull request, open tickets), tell the owner in one line and ask whether this is a new piece of work or they meant to carry on. To carry on, follow the **next** skill.
- If the project is not a Git repository with a GitHub remote, say what is missing and stop.

## 2. Set up quietly

If `docs/agents/issue-tracker.md` is missing, load and follow the **setup-project** skill with its defaults (GitHub issues, the five default triage labels, one glossary) without asking its questions; tell the owner in one line what you set up. Ask only if the repo is not on GitHub.

Do not adopt the rules now. That happens at step 5, once the stack is known.

## 3. Step 1: Describe

Load and follow three skills: **grilling**, **domain-modeling** and **need-first**, with the owner's description as the idea. Interview in rounds through your question tool.

Stay in one conversation for this. Use the **wayfinder** skill only if the interview cannot finish in one sitting because research or other people's answers must come first, and say so before switching.

## 4. Steps 2 to 4, without being asked

When the owner confirms the shared understanding, carry straight on. Do not stop to tell them which command to type.

- **Step 2, Choose the stack.** For anything with no code yet, load and follow the **stack** skill.
- **Step 3, Spec.** Load and follow the **to-spec** skill.
- **Step 4, Tickets.** Load and follow the **to-tickets** skill. The owner approves the list.

## 5. Hand over to building

When the tickets are published, tell the owner: how many tickets there are, which ones are theirs to do by hand, and that each agent ticket is built in its own new chat by typing `/next`. Building in a fresh chat keeps each ticket's work clean.
