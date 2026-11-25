# Trust from idea to wave demo

**Design for owner review · 25 November 2026 · based on Trust b97f5ca**

When you open Trust, you should be able to say what you are building, why the current wave comes now, what you will watch at its end, and what needs your attention today. Before the first ticket exists, you should be able to do that for the entire build.

## The path you see

| Step | What Trust gives you | Your part | What carries forward |
|---|---|---|---|
| 1 · Describe | The existing interview, or a reading of your FSD followed by questions about gaps | Answer until the description matches your intent | People, needs, terms, decisions and unresolved questions |
| 2 · What we’re building | Part 1 of one plan. Problem, users, numbered requirements as stories, decisions, Before Building, testing decisions and out of scope | Read and correct it | A counted scope against which you can judge the stack and the route |
| 3 · Stack | A recommendation with alternatives and trade-offs against Part 1. For existing code, Trust reads the stack of the affected component and records what it found | Accept or change a new stack. An established stack normally needs no action | Stack evidence, setup needs and the Technology stack decision record for a new stack |
| 4 · How we’ll build it | Part 2 of the same plan. First the overview, then the wave briefs, then the slice cards and coverage | Approve the whole plan once it reads clearly | One approved revision, one GitHub Project, one milestone per wave |
| 5 · Build wave by wave | At each wave’s go, its issues. For each slice, one contract, one independent verdict, one receipt and one PR. After the merges, one demo | Give the wave its go, approve slice contracts, merge proven PRs, watch the demo and sign off | Named contracts later waves can rely on and a record of what you saw |

Every new product or feature entering through `/start` gets this path. A small feature can have one wave and one slice. A bug fix can still enter through `/govern`. You are the sole human decision-maker in this version. A separate business signature or human tester workflow can be designed when a team uses Trust. The independent agent check already in Trust applies to every planned slice.

### What the plan looks like before there are issues

Illustrative payroll excerpt. These are sample wave and slice counts for the walkthrough, separate from the i4Smart register.

| Order | What you will see | Why here | What the next wave can use |
|---|---|---|---|
| 1 · Tenant access · 2 slices | Two companies sign in. Each sees only its own workers | Every later demo depends on whose data the user may see | A tenant-scoped worker lookup |
| 2 · Dated pay records · 2 slices | HR records a pay change and can retrieve both the old and new amounts by date | The calculation needs an agreed answer for mid-period changes | Pay history for a worker as of a date |
| 3 · Payroll calculation · 3 slices | A joiner’s pay run agrees with the worked example down to the kobo | A plausible-looking total can still be wrong. Prove the calculation before integrating payments | Approved calculation and payslip totals. Bank submission belongs to a later wave in the full plan |

**Open the payroll wave.** Its brief names the accepted example and dated-pay lookup as prerequisites. The demo gives you a worker, a start date, the agreed expected amount and the screen where you compare the payslip. If worked examples are missing, you see that before giving the go. The hand-off identifies the amounts and rounding rule a later payment wave can consume.

**Open one slice, “Calculate a joiner’s first period.”** For illustration, it serves PAY-03 and depends on the earlier dated-pay lookup and the period runner. A payroll clerk can run the example and see the prorated amount. Its tests cover the start date and calculation through the runner. Its acceptance evidence is the expected and actual amount for that case. Those criteria appear again, with the same IDs, when you approve the stage contract.

### What returning to the build feels like

> Step 4 of 5 · How we’ll build it. All 18 requirements have a slice. Three waves, seven slices. Read the overview and the three exit demos.
>
> You: Approve this plan with `/approve plan`, or tell me what to change.
>
> Next: I’ll create the Project and its three milestones. Wave 1 will wait for your go.

> Step 5 of 5 · Wave 3 of 3 · Payroll calculation · ticket 2 of 3. One slice merged. The joiner calculation has passed independent review and its PR is green.
>
> You: Merge “Calculate a joiner’s first period.”
>
> Next: Prove the payslip agrees with the calculation, then run the payroll demo.

> Step 5 of 5 · Wave 3 of 3 · Payroll calculation. All three slices merged with proof. The demo is ready.
>
> You: Run the worked payroll example and compare the payslip to the expected amount. If it matches, type `/approve signoff W3`.
>
> Next: Record what you saw and finish the build.

The first line links to the relevant plan section, issue, PR or demo. “Ticket 2 of 3” is its planned position inside this wave. Separate counts say how many are proven and merged. A failed demo keeps the wave open. Trust records the discrepancy and takes you through a corrective slice or plan revision before inviting sign-off again.

## How Trust writes a plan worth reading

1. Count scope before sequencing it. For an interview, give each story a stable ID. For an FSD, index its own IDs and locations and keep its wording at source. Part 1 explains gaps, additions, exclusions and decisions. Record which inventory in the source defines the total. Reconcile extracted IDs to that inventory independently of the slices. For a document without parseable IDs, present a reviewed source index with section/page anchors and identify the manual check explicitly.
2. Sketch the natural phases. For each, write one scene you can actually judge. Split independent outcomes. Move work that depends on a capability you have yet to prove. Order the remaining waves by the important uncertainty each retires, subject to dependencies. Tenancy first makes sense for payroll. Another product may need to prove something else first.
3. For each hand-off, name what will freeze at sign-off, who consumes it and what has been deferred to which wave. Show a dependency graph beside the overview. A table listing predecessors conveys the same information in plain Markdown readers. Sequential owner-go is the default, including for independent waves.
4. Work backwards from each scene to vertical slices small enough for one session and one PR. Each card gives outcome, requirements served, why now, usable result, earlier dependencies, tests, acceptance criteria and evidence. An infrastructure card must name the capability and later slice it unlocks.
5. Validate scope and sequence, then read the route aloud in ordinary language. A script can detect a missing scene or unallocated ID. You judge whether the scene demonstrates the promised capability. The plan review presents both results.

## Files and ownership

Use one directory per build under `docs/agents/builds/<build-id>/`. This fits the planning-document exemption already produced by adoption and keeps completed builds addressable. A custom adopted repository that protects this location gets an explicit setup diagnostic and uses its existing owner-controlled configuration process. Planning never silently widens an exemption.

| File in that directory | Writer and purpose |
|---|---|
| `PLAN.md` | Generated owner reading copy with both parts, overview, graph, briefs, cards and traceability. Exists from Part 1 onward. Section anchors use stable IDs. |
| `plan.json` | Authoritative versioned data for the build ID, title, source inventory, requirements, Part 1 sections, setup items, stack decision or existing-stack evidence, ordered wave IDs and any named blockers. |
| `waves/<wave-id>.json` | One wave’s purpose, risk, exit scene, dependencies, deferrals, contracts, demo steps and ordered slice cards. |
| `questions.json` | Optional Wayfinder working map. Resolved decisions used by the plan are incorporated by ID. Open questions name the exact step or wave they block. |
| `history/<revision>/` | Immutable snapshot of approved plan inputs, including the source inventory, stack reference with content digest and rendered plan. An approval event names its digest and predecessor. |
| `events/` and `github.json` | Tool-written approval, go, sign-off and revision records, and bindings to external IDs. Stage progress and board status are computed. |
| `exports/` | Word or PDF when requested. Each shows revision, approval state and export date. A pre-approval copy is visibly a draft. |

New build IDs are persistent and repo-unique. Wave and slice IDs are permanent keys within a build. Display order is an array, so inserting a wave does not renumber an existing wave. The approved revision supplies denominators. Report “7 → 8 slices, revision 2” if scope changes. With several builds, reuse the current branch’s recorded build association or ask which named build to resume. A glossary on its own is insufficient evidence of an active interview.

Use strict UTF-8 JSON with a schema version and checked-in schemas. Reject duplicate keys, unknown fields, wrong types, unsafe paths and unsupported versions. Use deterministic serialization for approval digests, including canonical line endings for rendered text. Render atomically. Check that `PLAN.md` equals the rendering before showing an approval prompt. If an owner edits the Markdown, show the difference and incorporate their edit in the source before rendering again. Never silently overwrite their correction.

**Proof of coverage.** Let R be every in-scope ID from Part 1, including accepted additions and explicitly included provisional items. Let S be the union of the slices’ served IDs. Approval requires R = S. Show missing and unknown IDs, duplicate definitions, rejected IDs still cited and one-to-many assignments with their distinct contributions. Trace from requirement to slices and back. Every setup item has an owner, a needed-by wave, consuming slices and an observable completion criterion. A conditional item states the condition. Count owner setup issues separately from delivery slices.

**Other checks.** Exactly one exit scene per wave, a reason and risk, at least one slice, valid test/evidence and acceptance fields, unique IDs, every dependency pointing earlier, no cycles, valid contract consumers and deferral destinations. At a wave’s go, check prerequisite sign-offs and blocking decisions. Setup that can run during the wave blocks its consuming slices. Setup essential for entry is surfaced while the wave is still gated and can be completed locally with evidence before publication at go. On sign-off, require every planned slice merged with valid proof, resolved setup and demo evidence. Validation errors identify the affected card or requirement and a repair.

## Commands and approval boundaries

| Component | Responsibility in the five-step path |
|---|---|
| `start`, `next`, `start/STEPS.md`, `trust-help`, GUIDE and README | Teach the same five steps. Keep the familiar step line and “You” and “Next” messages. Resume from evidence across chats. |
| `setup-project`, interviewing skills | Set up local conventions and persist interview completion locally. Defer GitHub labels, tracker setup writes and any research publication. Keep research local during planning. A new local plan needs no network call. |
| New `plan` skill, existing `stack` skill | Write Part 1, hand to stack, then write Part 2. Remove stack-first routing from grilling, Wayfinder and planning entry points. Stack records new choices under `docs/adr/` with the title and decision format `adopt.py` consumes. Distinguish a new component with no applicable stack from an established component in the same repo. |
| New `scripts/planctl` | `check`, `render`, `status --json`, `diff`, `export` and `migrate --preview`. Prepare and apply narrowly typed `approve-plan`, `go` and `signoff` transitions. `sync` reconciles only previously authorized GitHub changes. Install/copy via the same packaging and adoption routes as `where` and `stagectl`. |
| `to-tickets` | Internal publisher for one authorized wave. Materialize the approved cards and owner setup items, attach dependencies, milestone and Project membership. Issue body includes stable build/wave/slice key, outcome, acceptance IDs and the approved snapshot link. |
| `implement`, `stage`, `stagectl` | Verify build association, wave go and unblocked slice before freezing. Use the approved wave brief and slice card as real local immutable contract inputs. The current input hasher expects repository files. Link the GitHub URL inside a local ticket snapshot. Every card criterion becomes a contract obligation with a real check. Enforce independent review. |
| `approve`, `hooks/approval.py`, `guard.py` | Preserve existing stage and baseline commands. Add exact plan, wave-go and wave-sign-off grants. Protect tool-owned approval records and reject unauthorized direct writes. |
| `where` | Read-only dispatcher. For a new plan it reads local planning state first. After approval it combines the approved revision, local stage state, GitHub bindings, merged PR facts and repository proof. `/next` carries out the indicated action and can reconcile the board. `where` never publishes. |

The wave-go prompt names its effect explicitly, for example “Give Payroll calculation its go with `/approve go W3`. This creates three slice issues and one setup issue.” A plan revision uses `/approve plan` after showing the revision diff.

**Bind approval to what was shown.** Before asking, prepare an immutable review subject with action, build ID, revision digest, wave ID when applicable, expected prior event, and digest of relevant inputs. Store the pending subject in the existing worktree-local protected state and bind it to the conversation. For sign-off include the completed evidence set, demo result and owner’s observation. The hook uses the owner’s exact message, the same conversation and the existing 15-minute, single-use grant. Exact named verbs take precedence over the current free-form stage remark fallback. Unknown wave IDs, ambiguous subjects, a changed render, stale evidence and a different checkout fail closed. Show the new subject if anything changed. Bare `/approve` keeps its stage meaning.

**Record locally, publish resumably.** Approval records a local transition before network writes. Show “Plan approved · GitHub setup pending” if publication fails. Reconnect and resume the same transition without asking for plan approval twice. Use atomic writes and an expected prior event to reject competing transitions. Keep a canonical planning branch for each build after approval, publish only reviewed plan files and records to it, and link GitHub to the approved snapshot there. Import the slice’s approved inputs into its worktree before freeze. Give the owner the branch and snapshot link. This keeps planning records shareable across clones without introducing a planning PR into slice counts.

Authenticate and serialize remote publication through that branch: a normal fast-forward push of a unique operation claim against the last observed branch head must succeed before a publisher creates anything. Another clone reloads on rejection. After a crash, a takeover first verifies the prior writer stopped and reconciles remote objects. For a create with an uncertain outcome, wait and rediscover by the stable key. If uniqueness cannot be established, report the candidate objects and halt that operation. GitHub creation across these resources has no single transaction. Avoid promising exactly-once creation from a retry loop. An existing protected-branch policy must allow the chosen planning branch or an agreed review path for plan records.

Stage records remain authoritative for a slice. Reuse `stagectl` predicates for the receipt, governed tree, independent verdict and any required base-trusted SSH signature. Reprove after a qualifying rebase follows Trust’s existing checks. Plan approval cannot freeze a slice contract, approve a baseline increase, authorize a merge or supply a wave go. A direct call to the ticket publisher checks recorded authority just as the guided path does. On an adopted project, protect approval history before the generic planning-doc exemption. Validate history and approved snapshot digests from the canonical branch when deciding eligibility. The Cursor hook attests an owner prompt in its own environment. Repo write access still carries trust, as it does today.

## GitHub after approval

Use the repository owner’s Projects v2 space and link the new Project to the repository. On first approval explain the additional permission. The owner can refresh their existing CLI login with `gh auth refresh -s project`. Check effective Project and repository permissions, including organization restrictions, before provisioning. Never print tokens. A missing scope leaves the approved local plan intact. [GitHub CLI Projects](https://cli.github.com/manual/gh_project) · [GitHub Projects API](https://docs.github.com/en/issues/planning-and-tracking-with-projects/automating-your-project/using-the-api-to-manage-projects)

**The whole build on day one.** Put the approved overview in the Project README: every wave, planned count, exit scene, gate state and milestone link, plus a link to the full plan. Each milestone description shows its wave key, risk, contract hand-off, demo and planned slice count, including when it contains zero issues. This avoids maintaining placeholder issues for future slices. The board’s rows begin arriving when the first wave gets its go.

**The board during delivery.** Each slice row is its issue. Use a Trust-managed single-select *Slice status*, a *Wave* field, a *Kind* field (slice or owner setup) and a stable slice identifier. Recommend a board grouped by Slice status and a table grouped by Wave. Fields and values are provisioned programmatically. If a saved view needs UI configuration on the owner’s GitHub, the Project README and populated fields must already make the build readable. Show setup rows separately. An issue closed by hand, a dragged card or GitHub’s automatic Done column cannot supply proof.

| Slice status | Evidence Trust reads |
|---|---|
| Planned | In the approved revision, with no bound issue. Included in the overview and denominator. |
| Ticket open | The issue is bound to this exact slice. Its stage has yet to start. |
| Stage in progress | Its approved contract is frozen in an active worktree. Publish a stage reference at freeze so another clone can locate the work. Local check progress may only be known on the builder’s machine. |
| Proven | Current checks and required independent review satisfy the existing readiness predicate. Ready to close the stage. |
| Verified | A committed receipt and matching passing independent verdict cover the candidate code, with the configured signature policy and successful proof gate. |
| Merged | Verified evidence at the accepted PR head and GitHub’s merged PR into the intended base. Keep that head, receipt and verdict as historical evidence after later slices land. |

Report blockers, stale proof and unknown/offline evidence explicitly. A changed PR head triggers reevaluation. A merged PR missing proof is an exception that blocks sign-off. A failed or missing network query cannot advance a slice. Recompute after freeze, checks, close, reprove, merge, wave transitions and on `/next`; the board shows the last successful sync time. External merges may appear on the next sync. Immediate background synchronization would require separate credentials and is unnecessary for the sole-owner version.

Use Project node IDs, repository identity, milestone number, issue node ID and PR number in bindings. Persist field and option IDs. Embed discoverable build keys at creation, including a unique build key in the initial Project title and a stable key in milestone and issue descriptions. Read all pages. Preserve user notes outside Trust’s managed sections. Rediscover moved/renamed resources by ID. Never silently adopt a same-title milestone, recreate a deleted resource, move unrelated issues, or close a wave merely because GitHub reports 100%.

## Changes after approval

Write proposed edits in a draft revision. The current approval remains historical and operative for unchanged work. The review shows the reason, scope and coverage delta, moved dependencies, changed wave scenes and contracts, affected open tickets, frozen stages and merged PRs. Pause affected work; if the impact cannot be bounded, hold new starts. Recheck Part 1 against the source inventory and every slice when Part 1 or the FSD changes. A changed stack also reopens dependent design decisions. Every material plan revision requires your approval. Rendering and board repairs from identical approved data do not.

| What the revision affects | What happens on re-approval |
|---|---|
| Future wave | Keep milestone identity on rename or reorder. Add a milestone for a new wave. Mark a retired wave superseded with a link. Preserve its history. |
| Wave with issued, unfrozen slices | Update managed issue sections and blockers in place. Keep issue IDs. Mark removed slices superseded with the reason. Show moves explicitly. New tickets in a changed wave wait for an explicit go on its revised scope. |
| Frozen or verified slice | Retain its original snapshot and contract. An acceptance change needs an explicit stage revision and fresh proof, or a new follow-up slice. A different wave go or plan approval cannot invalidate history or silently loosen an obligation. |
| Merged slice or signed-off wave | Preserve its receipt, PR, demo, milestone and signed revision. Schedule a new slice for changed behaviour and a new wave if a published hand-off has to change. Name affected consumers and the decision superseding the old contract. |

For example, if W3’s signed plan had three slices and you add a fourth for a new rounding rule after two PRs merged, the review shows “2 merged of 3 → 2 merged of 4,” the requirement, affected consumers and new demo expectation. Approval records revision 2. Giving revised W3 its go publishes only the additional issue. Earlier PRs retain their original acceptance and proof.

## Wayfinder in plain words

Today Wayfinder is a place to leave a difficult question and come back to it next session. You name the decision you are trying to reach. The map shows what is settled, what remains unclear and which question can be answered next. For example, payroll planning can continue while someone finds the agreed rounding examples, but the calculation demo depends on that answer. Today the tracker stores the map and its child decision tickets, commonly as GitHub issues.

Keep that job and make the map local. The interview or plan can open a named question with its destination, dependencies, source, suggested next action, answer and affected part of the build. Show the first answerable question by name on resumption. Use one map per build, with a short list of decisions reached and links to supporting local research. Put a settled product decision in Part 1, a technology choice in its ADR, or a scheduling decision in the wave brief. Preserve the question ID as provenance. End the detour when the blocked planning step can proceed. A multi-session question can remain open if it explicitly blocks a later wave and enough is known to plan coverage. No map or decision issue is published, even at plan approval. Existing map issues remain available to legacy builds.

## Markdown, Word and PDF

The Cursor skill invokes the same repo-relative Python script from the plugin or an adopted project. `render` emits both parts into one Markdown file using only the standard library. Use the same ordered document sections and rows for every format. Each export starts with title, revision and approval record, then the overview, wave briefs, slice register and requirement-to-slice index. Include a readable predecessor table wherever a graphical rendering is unavailable. Keep current delivery counts in a dated status snapshot so an old copy is understandable.

For on-demand team documents, propose Pandoc with a bundled reference DOCX for styles, headings, repeating table headers and page breaks. Convert that DOCX to PDF with an available LibreOffice headless executable. Discover executables on Linux and Windows, including standard installation paths, use argv and a unique temp directory/profile, validate output and atomically publish to the requested destination. Keep generated files project-local unless sharing is requested. When a converter is missing, identify which format can be produced and which dependency is needed. Core planning and approval always work with Markdown. The document records the actual owner approval or draft state. Signature lines on exported paper do not operate Trust gates.

## Existing projects and command compatibility

*New build.* `/start` starts a local plan explicitly. A new build in a repo that has historical issues should not inherit their scope. `/next` selects an active local build first. If there is no plan, discover existing legacy work read-only and name it. On ambiguous repos ask once which effort to resume. The old issue-body heuristic belongs only in legacy discovery. Offline, say when existing remote work could not be checked.

*In-flight six-step build.* Offer “continue this build as it is” or “preview moving it into a plan.” Preserve the existing dispatcher for the former. A migration preview reads the selected parent issue, its actual linked tickets, blockers, map answers, stage contracts, evidence and PRs. Local Markdown projects read their configured `.scratch/` records. Present a proposed Part 1, stable requirement mapping, waves, exit scenes, setup items, unmapped issues and uncertain links. The owner resolves ambiguities and reviews the whole plan locally. Never infer merged or verified from an issue being closed. A historical delivery that lacks proof is labeled as such and needs a separately agreed verification slice before it can count toward a signed wave.

*After migration approval.* Create the Project and milestones. Retain issue numbers, links, branches and frozen contracts. Existing future-wave issues are a visible legacy exception to just-in-time creation. Bind existing issues by reviewed mapping, preserve their history and list them as awaiting wave go; at go attach them to the milestone and board and create only missing issues. An active stage can finish on its original contract. Require a reviewed one-to-one PR mapping for credit on the new path. Shared integration PRs can finish under legacy rules before cutover. A migration collision pauses just that binding. Retry resumes. Until cutover succeeds, legacy remains resumable. After cutover keep the old parent as a historical link. Show cleanup proposals separately.

*`to-spec` and `implement-spec`.* Keep their direct legacy meanings for existing efforts. On a five-step build, `to-spec` routes to local Part 1 and `implement-spec` routes to the current authorized wave and next eligible slice. Its previous integration-branch strategy cannot satisfy the one-PR-per-slice rule. Update skill descriptions, examples and tracker templates to distinguish the paths. `to-tickets` on the new path requires an approved revision and a matching wave go. Local Markdown remains supported for legacy tracking and migration input. New plans work entirely locally through review. A GitHub repository and the requisite permissions are needed to publish the approved build. If missing, preserve “approved · publication pending” and the local files.

## Implementation sequence and acceptance tests

| Deliverable | Demonstration required before extending it |
|---|---|
| 1. Read a whole plan | From an interview and from a supplied FSD, render Part 1, resolve stack, render Part 2, validate, and resume in a fresh chat. Include one-wave and multi-wave examples. Trap every GitHub mutation in steps 1–4, including labels and Wayfinder. Verify an existing repo’s stack and empty-project language adoption from the ADR. |
| 2. Approve and publish exactly the authorized work | Test before adoption and after adoption. Bind owner grants to subject, revision, checkout, verb, wave and conversation. Reject expired, reused, edited and crossed grants, direct history edits, and invalid transitions. Approve then simulate an outage and simultaneous publishers. Recover after each individual create/add/update and a lost response. Assert one Project, one milestone per wave, zero new issues until go and no duplicated resources on the second sync. |
| 3. Build and return to the wave demo | Drive a real temporary Git repo through freeze, checks, independent verification, close and gate. Use a fake GitHub transport for remote facts. Change code, rebase/reprove, remove a verdict, supply a wrong signer, close an issue without a merge, merge a different PR and open an unrelated PR. Check stale evidence and per-slice counts. All valid merges offer the demo, only owner sign-off completes the wave, and the next still waits for go. |
| 4. Change course and carry existing work across | Cover renamed, reordered and superseded milestones, edited Part 1, stale FSD, deleted IDs, open/frozen/merged slices, split legacy tickets, mixed builds and missing historical proof. Dry-run and retry migration without mutating before approval or duplicating existing issues. Check direct legacy entry points. |
| 5. Read and share at all three levels | Compare rendered coverage with an independently declared requirement inventory. Exercise a 13-wave/55-slice synthetic fixture and adversarial variants modeled on i4Smart’s plan checker: uncovered, invented or rejected IDs, forward dependencies, ambiguous exit scenes flagged for human review, missing evidence, unjustified infrastructure and premature sign-off. Inspect DOCX headings/table contents and PDF text/pagination with converters present, plus missing-converter behaviour. Verify screenshots or saved output for the owner walkthrough on both platforms. |

**Regression contract.** Keep the existing stage, guard, adoption, installer, packaging and verifier suites. Today some path tests literally require “Step 1 of 6” on an empty repo and a six-step table in the main STEPS file. Those assertions conflict with the requested front door. Preserve their legacy expectations against an explicit legacy dispatcher and guide, and add equivalent tests against the five-step default. Keep independent tests for unchanged behaviour. A green suite obtained by deleting the old scenarios would miss a migration regression.

Use Windows-safe subprocess argv, pathlib, native line endings in checkout fixtures, and a Python fake GitHub transport on both OSes. Exercise spaces and non-ASCII paths, pagination, permission denial, partial responses and offline status. Keep the existing Ubuntu 24.04 and Windows matrix with Python 3.10 and 3.12. Run Linux tests under a bounded systemd scope on this VPS. Before releasing, do an authorized trial on a disposable GitHub Project with an actual owner login and a real Cursor session. Confirm the empty-board overview, go, one PR per slice, approval hook, resume after interruption and demo sign-off. Unit tests alone cannot establish those integrations.

## Approval requested

Approve the **five-step experience and ownership model** described here: one readable plan before tickets, the whole route visible on approval, publication one wave at a time, and progress backed by Trust’s existing proof. The proposed implementation choices are strict JSON with one generated Markdown reading copy, stable GitHub bindings, owner-only human gates, and on-demand document conversion. Team sign-off is deferred. Design approval authorizes the agreed direction. Shipping code, enabling workflows in a project, or refreshing an installed copy are separate actions.
