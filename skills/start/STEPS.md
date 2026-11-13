# The six steps

Every piece of work goes through these, in this order. Steps 1 to 4 plan; steps 5 and 6 build. The owner needs three commands: `/start` to begin, `/next` to carry on, `/approve` to say yes.

| Step | Name | What happens | What the owner does |
|---|---|---|---|
| 1 | Describe | An interview until nothing is assumed | Answers |
| 2 | Choose the stack | A recommended stack, the alternatives, and what must be set up first | Accepts or changes it |
| 3 | Spec | What was agreed, written as an issue | Nothing |
| 4 | Tickets | The spec split into small buildable pieces, as issues | Approves the list |
| 5 | Build | One ticket: the rules are turned on if they are not yet, a contract is shown, then it is built and proven | `/approve`, once per ticket |
| 6 | Merge | A pull request with the proof | Merges, then `/next` |

## How to speak to the owner on this path

The owner is a person, not an agent, and may not be a software engineer. On every message while on this path:

1. **Open with the step line**: `Step N of 6: <Name>.` and, in steps 5 and 6, which ticket out of how many.
2. **Say what is happening in plain words**, in a sentence or two. When you start helpers or background work, say how many, what for, and that the owner need not do anything.
3. **Close with two lines**:
   - `You:` what the owner must do now, or `Nothing.`
   - `Next:` what happens next.

Do not name skills, plugins or internal steps unless the owner asks. Say "I'll compare three designs", not "running the architect arena". Never end a step by telling the owner which command comes next when you can simply do it.

When the owner must wait for something only they can do (a ticket marked for them, an approval, a merge), say exactly that and stop.
