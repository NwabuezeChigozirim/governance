---
name: stack
description: Recommend the technology stack for a new product or a new part of one, from the requirements already settled, with the reason for each choice, the alternatives and what they cost, and the list of things the owner must set up before building. Use at the end of an interview or a wayfinder map for anything with no code yet, before a spec is written, or when the user asks what to build something with.
---

# Stack


When this runs as part of the owner's path from idea to merged code, follow [STEPS.md](../start/STEPS.md): open each message with the step line, say what is happening in plain words, and close with what the owner must do and what comes next.

Choose what the product is built with, after what it must do is settled and before a spec is written. The owner understands systems but may not have the background to pick a stack unaided: your job is a recommendation they can judge, not a menu they must choose from.

A technology still cannot create a requirement (the `need-first` skill). This skill runs the other way: the requirements choose the technology.

## When this applies

- The repo has no application code, or the work adds a part with no code yet (a first mobile app, a first background worker, a first database).
- Not for a feature inside an existing stack. There the stack is already chosen: read it from the repo and follow it.

If a decision record for the stack already exists under `docs/adr/`, read it and stop, unless the user is asking to change it.

## 1. Collect what constrains the choice

Find these yourself from the conversation, the glossary, the map or spec, and the machine. Ask the owner only for what you cannot find.

- **What it must do**: the settled behaviour, especially anything that narrows the field (a file format to produce, a protocol to speak, work that runs on a schedule with no device on, offline use, realtime).
- **Who uses it and how much**: one person or thousands; the data it keeps and for how long.
- **Where it runs**: the owner's server, a phone, a browser, a managed platform. What is already installed and paid for.
- **Who builds and maintains it**: which agents write the code, and what the owner can read well enough to notice something wrong.
- **What can be enforced**: which languages get this plugin's strict linter and type-check rules. A stack the rules cover is checked on every edit; one they do not cover is checked by tests alone. Read the governance README's adoption table for the current list.
- **Outside services** the behaviour depends on, and what each allows on the owner's plan.

## 2. Recommend one stack

Cover every part the product needs and no more: language, application framework, data store, how each special job is done (documents, scheduling, messaging, payments), how it is run and deployed, and how it is tested. Leave a part out when the product does not need it; say so in one line so the owner knows it was considered.

For each part give:

- **The choice.**
- **Why, from this product's requirements.** One or two sentences that would stop being true if the requirements changed. "Popular" and "modern" are not reasons.
- **What it costs**: money, a new thing to learn or run, a limit it brings.

Prefer, in this order: what the requirements force; what the owner's agents write reliably and the rules can enforce; what the owner already runs; the simplest thing that is complete. Prefer one language across the product unless a requirement forces a second. Prefer boring, widely used tools over new ones: agents write them better and the owner can find help.

If a part depends on a fact you have not verified (a library can do X, a service allows Y on this plan), verify it with the `research` skill or a `prototype` before recommending it, or mark it as unproven and say what would prove it.

## 3. Show the alternatives

Give two whole alternative stacks that a sensible engineer might pick, each with what it would give that the recommendation does not and what it would cost. If one alternative is close, say what fact about the owner's situation would tip the choice to it.

## 4. List what the owner must set up before building

Everything that has to exist before the first ticket can be built or proven, that only the owner can do: accounts to open, keys and tokens to create, a server, domain or certificate, settings in an outside service, access to request, something to buy. For each: what it is, where to do it, roughly how long, what it costs, and which part of the product is blocked without it.

Say where each secret will live (an environment file on the server, never the repository). Offer the `wizard` skill for any item with more than a few steps.

## 5. Get the decision

Put the recommendation to the owner through your question tool if you have one: the recommended stack as the first option, each alternative as its own option with its trade-off. The owner may accept, pick an alternative, or change one part.

## 6. Record it

Write a decision record under `docs/adr/` following the `domain-modeling` skill's ADR format, titled **Technology stack**. It holds: the stack, the reason for each part, the alternatives turned down and why, anything still unproven, and the set-up list. A later change to the stack is a new record that supersedes this one.

Then tell the owner what happens next: `/to-spec` carries the stack into its implementation decisions and the set-up list into a "Before building" section, and `/to-tickets` turns each set-up item into a ticket labelled for the owner.
