---
name: need-first
description: Separate what a user asked for from the job they need done, before it becomes a spec or a ticket. Use when grilling a product idea or feature request, writing user stories, or reviewing a spec or ticket list for features that have not earned their place.
---

# Need First

A stated request is evidence about a user. It is not the requirement. "I need a map" tells you the user is thinking about location. The job might be judging distance, estimating travel cost, or comparing suppliers near a site, and each job has several possible responses: a distance figure, a travel time, a sort by proximity, a radius filter, a map.

Nothing earns its place in the product because it fits the product's identity, is technically possible, already exists, looks impressive, or was imagined early. It earns its place by materially helping a user accomplish a real job in the realities of their context.

## While grilling

For each capability the user asks for, settle these before any question about how it works. Find what you can from the repo and the conversation; ask the user only for what changes the answer.

1. **Who** is the user in this context, and does another role in the same workflow need something different?
2. **The job**: what are they trying to accomplish, and what decision or action does this let them take? Derive it from context. Never copy the request into it.
3. **Information**: what must they know to do that confidently, and what do they not need?
4. **Simplest complete response**: the least complex thing that satisfies the job. A response may be a new capability, but also exposing information that already exists, removing a step, changing a default, changing wording, or deliberately doing nothing.
5. **Removal test**: if this were removed, which user outcome gets materially worse? If none, it is a preference, not a need.

Put the richer response to the user only with what it adds over the simplest one and what it costs.

"Simplest" removes unjustified complexity, not required capability. Reject an "MVP" or "first slice" that deletes behavior the primary job needs.

## Say what kind of claim it is

When you record a decision, say which of these it rests on: a verified fact, behavior you observed, a requirement stated by a named stakeholder, a constraint from the domain or the law, or an assumption, a hypothesis, a preference. Confident prose is not evidence. Name the assumptions most able to invalidate the idea and settle them first, by research or a prototype, before expensive design.

## In the spec and the tickets

- Each user story's "so that" names the job, not a restatement of the feature.
- Each ticket's "What to build" can be explained backward to a user, a context and an outcome. If it cannot, an unjustified assumption sits somewhere above it: go back and grill it.
- An existing system being rebuilt is evidence, not authority. Keep its business rules, invariants and hard-won lessons. Make its screens, navigation and architecture re-earn their place.
- A technology cannot create a requirement. A geospatial database does not imply a map; realtime infrastructure does not imply realtime behavior; an AI capability does not imply an AI interaction.

For a review pass over a finished spec or ticket list, read [REVIEW-QUESTIONS.md](REVIEW-QUESTIONS.md).
