# Review questions

Ask these of any idea, spec or ticket list. A "yes" is a finding to put to the user, not a verdict.

- Is the product defined as a list of features rather than jobs?
- Is an "X-first" identity (map-first, AI-first, dashboard product) dictating the interaction?
- Is there a screen inventory before the jobs are understood?
- Is there architecture before the behavior it must serve?
- Is a technology looking for a use case?
- Does a map communicate more than distance or area text would?
- Is a dashboard standing where the user needs a direct task flow?
- Is visualization doing work that a sentence or a sorted list would do better?
- Is feature parity with a competitor or a legacy system standing in for evidence?
- Are all roles being treated as if they had the same needs?
- Is a rare workflow being optimised at the cost of a frequent one?
- Is essential information hidden behind an impressive interaction?
- Is an abstraction present because it is elegant rather than needed?
- Is the design shaped by a component library rather than the task?
- Has legacy behavior been carried into a rebuild without revalidation?
- Has a business desire been written down as a user need?
- Has a user request been copied into the job without investigating context?
- Is "MVP" being used to avoid solving the complete core problem?

## Order of reasoning

Let each step constrain the next:

```
user need → user job → required information → appropriate interaction
→ business or domain rule → system behavior → interface → visual treatment
```

Design an interaction only after the task and its information are understood. Different jobs deserve different tools: a table, calendar, map, wizard, feed or search is chosen because it is the best tool for that task, not because another part of the product uses it.
