---
name: implement
description: "Implement a piece of work based on a spec or set of tickets."
disable-model-invocation: true
---

When this runs as part of the owner's path from idea to merged code, follow [STEPS.md](../start/STEPS.md): open each message with the step line, say what is happening in plain words, and close with what the owner must do and what comes next.

Implement the work described by the user in the spec or tickets.

If the user passes a ticket reference, fetch it from the issue tracker and state its title before starting. If the reference is ambiguous, ask.

Build it as one stage: load and follow the `govern` skill, with the ticket as the task. One ticket is one stage.

If the project has no `.governance/config.json`, it has not been adopted and nothing would be enforced. Tell the owner in one line and load and follow the `adopt` skill first.

- The ticket's "What to build" is the stage's intent.
- Each acceptance criterion on the ticket becomes one acceptance item in the stage contract, with at least one check command that proves it. A criterion you cannot attach a check to is not ready: say so on the ticket and stop, rather than inventing a weaker criterion.
- Name the ticket in the contract's `inputs` by its URL or file path.

The owner freezes the contract; `govern` then builds, proves and closes the stage. Do not review or commit outside that flow.

When the stage closes, resolve the ticket the way the issue tracker closes work, linking the receipt or the pull request.

Never build a ticket outside a stage. If a stage cannot be frozen, say why and stop.
