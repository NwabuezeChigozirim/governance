---
name: adopt
description: "Put the current project under governance: run the adopt script, install the linters it needs, commit the result and make the merge gate required. Owner-started only, for /adopt."
disable-model-invocation: true
---

# Adopt


When this runs as part of the owner's path from idea to merged code, follow [STEPS.md](../start/STEPS.md): open each message with the step line, say what is happening in plain words, and close with what the owner must do and what comes next.

Adoption is the owner's decision to constrain a project. Run this because the owner typed `/adopt`, or because the owner typed `/next` or `/start` and the path has reached building in a project that is not adopted or lacks the strict rules for its language. Never start it for any other reason, and never suggest running the script as a way past a blocked edit.

The script is at `../../scripts/adopt.py` from this file. It only adds: it never overwrites the owner's config, rules or linter settings, and running it again never forgives a violation of a rule that was already there.

## 1. Check the ground

- The project must be a Git repository. If it is not, stop and say so.
- Run `git status --short`. If files unrelated to governance are uncommitted, tell the owner and ask whether to continue; you will commit only the adoption files, never theirs.
- Note whether `.governance/config.json` exists. If it does, this is a re-run: it refreshes `tools/governance/` and adds the strict rules for any language the project has gained.

## 2. Run the script

```bash
python3 <path>/adopt.py --repo .
```

Keep its full output for the report.

## 3. Finish what it could not

If the output contains `NOT DONE`, it names what is missing. Install exactly that (for Python `pip install ruff mypy`; for Node the `npm install --save-dev ...` line it prints), then run the baseline command the output gives, word for word. If an install fails, stop and report the error; do not edit a rule, a linter config or the baseline to get past it.

Then confirm the project passes its own rules:

```bash
python3 tools/governance/rulekit check
python3 tools/governance/rulectl check --repo . --prove
```

Both must exit 0. If either fails, report the output and stop before committing.

## 4. Commit and push

Stage only what adoption wrote: `tools/governance/`, `.governance/`, `.github/workflows/governance.yml`, `AGENTS.md`, `.gitignore`, and `ruff.toml` or `eslint.config.mjs` if the script created one (plus `package.json` and the lockfile if you installed Node linters). Commit to the default branch with the message `Adopt governance` and push. This commit goes straight to the default branch because its own pull request could have no receipt yet.

If the push is rejected because the branch is protected, stop and tell the owner; they push or merge it themselves.

## 5. Make the gate required

Find the repository and default branch with `gh repo view --json nameWithOwner,defaultBranchRef`. Read the branch's protection:

```bash
gh api repos/<owner>/<repo>/branches/<branch>/protection
```

- **404, no protection yet:** require the `gate` check and nothing else:

```bash
gh api -X PUT repos/<owner>/<repo>/branches/<branch>/protection --input - <<'JSON'
{"required_status_checks": {"strict": false, "contexts": ["gate"]},
 "enforce_admins": false, "required_pull_request_reviews": null, "restrictions": null}
JSON
```

- **Protection exists and already requires `gate`:** nothing to do.
- **Protection exists without `gate`:** do not replace it. Tell the owner to add `gate` to the required checks in the repository settings.
- **403, or a message about upgrading the plan:** GitHub does not offer branch protection for this repository on the owner's plan. Say so plainly: the gate still runs and shows red on a bad pull request, but GitHub will not block the merge.

## 6. Report

Tell the owner, in a short list:

- what the script created, kept and updated
- which rules are now enforced, by ID
- whether the baseline was recorded, and how many old violations it tolerates
- whether `gate` is now a required check, or what the owner must do to make it one
- that agent edits now need a frozen stage, except the planning documents listed in `exempt`
