# trust

A Cursor plugin that takes you from an idea to merged code you can trust, along one path.

It is built on one equation: clear intent + good codebase + verification = work that does not need rechecking. You say what you want and approve what will be built. The agent plans it with you, builds each piece under enforced rules, and must prove each piece works before it can merge.

## Install

```bash
python3 scripts/install.py
```

This copies the plugin into `~/.cursor/plugins/local/trust`, removes the two plugins it replaces (`governance` and `intent`) if they are installed beside it, and pins the hooks to the Python that ran the installer. Run it again after pulling changes, then restart Cursor. Needs Python 3.10+, Git, and the GitHub CLI signed in (`gh auth login`).

## Use

Three commands:

| Type | When |
|---|---|
| `/start <what you want to build>` | To begin a new product or feature |
| `/next` | Any time, in any chat. It says where the project is and does the next step |
| `/approve` | When shown what is about to be built |

One path:

| Step | What happens | What you do |
|---|---|---|
| 1. Describe | An interview until nothing is assumed | Answer |
| 2. Choose the stack | A recommended stack, the alternatives, and what you must set up first | Accept or change it |
| 3. Spec | What was agreed, written as a GitHub issue | Nothing |
| 4. Tickets | The spec split into small buildable pieces on GitHub | Approve the list |
| 5. Build | One ticket: the rules are turned on, a contract is shown, then it is built and proven | `/approve`, once per ticket |
| 6. Merge | A pull request with the proof | Merge, then `/next` |

[docs/GUIDE.md](docs/GUIDE.md) is the one-page guide. [docs/REFERENCE.md](docs/REFERENCE.md) explains how each part works and its limits.

## Test

```bash
python3 -B -m unittest discover -s tests
```

CI runs this on Linux and Windows.

## Status

Alpha. The scripts, hooks and package structure are tested. The first trial inside Cursor ran the planning steps and adoption on a real project; building a ticket through to a merged pull request, and `/approve`, `/start` and `/next` inside Cursor, have not been seen end to end yet.

## Credit

Most skills, the playbooks, both agents and the feature-map example are taken from
[pstack](https://github.com/cursor/plugins/tree/main/pstack) by Lauren Tan (MIT, commit
`2eaf465`), with additions that wire them to `verifyctl` and `rulectl`. See
`THIRD_PARTY_LICENSE-pstack`.

The planning skills are adapted from [Matt Pocock's skills](https://github.com/mattpocock/skills) (MIT). See `THIRD_PARTY_LICENSE-mattpocock-skills`.
