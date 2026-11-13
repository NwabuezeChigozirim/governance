---
name: next
description: "Carry on. The owner types /next in any chat, at any time: it works out where the project is on the six steps from its real state, says so in one line, and does the next step. Owner-started only."
disable-model-invocation: true
---

# Next

The owner typed `/next`. They want to know where things stand and for the work to move forward. Do not ask them what to do; find out.

## 1. Read the state

Run the `where` script with `--json` (`../../scripts/where --repo . --json` from this file, or `tools/governance/where` in an adopted project). It reads the repository, the stage state, and the issues and pull requests on GitHub. Trust it over your memory of the conversation.

Read [STEPS.md](../start/STEPS.md) and follow its rules for speaking to the owner. Open with the step line the script gives.

## 2. Do what it says

| The script reports | Do this |
|---|---|
| Step 1, nothing planned | Ask the owner what they want to build, then follow the **start** skill |
| Step 1, an interview or a map is under way | Continue it: the **grilling** skill, or the **wayfinder** skill with the map it names |
| Step 2 | Load and follow the **stack** skill |
| Step 3 | Load and follow the **to-spec** skill |
| Step 4 | Load and follow the **to-tickets** skill with the spec it names |
| Step 5, a ticket is ready to build | First deal with the rules (below). Then load and follow the **implement** skill with that ticket |
| Step 5, a stage is being built | Continue it: the **stage** skill from its current step |
| Step 5, a stage is proven | Close it and open the pull request, as the **stage** skill says |
| Step 5, everything waits on the owner | Tell them which tickets are theirs, offer the **wizard** skill for any with many steps, and stop |
| Step 6, a pull request is open | Check its checks. If green, ask the owner to merge it. If red, find out why and fix it under the stage |
| Step 6, every ticket closed | Close the spec, tell the owner what was built, and suggest they try it |
| GitHub issues could not be read | Read the error it quotes. If it is on your side (a missing remote, a command that failed), fix it and run the script again. If only the owner can fix it (signing in), tell them exactly what to do and stop |

### The rules, before building

- **Not adopted yet** (`adopted` is false): tell the owner in one line that you are turning on the rules that keep the code honest, then load and follow the **adopt** skill. The owner started this by typing `/next`; that is their say.
- **Strict rules missing** (`strict_rules_missing` lists a language): the project gained a language after it was adopted. Follow the **adopt** skill again; it adds the strict rules for that language.

If a ticket marked for the owner is also unblocked, mention it once so they can do it while you build.

## 3. One step, then report

Do the one step the state calls for. Steps 1 to 4 flow into each other in the same chat. A ticket (step 5) is one chat: when it has a pull request open, stop, and tell the owner to merge it and type `/next` in a new chat for the next ticket.

End with the `You:` and `Next:` lines.
