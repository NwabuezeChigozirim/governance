---
name: systems-design
description: >
  Derive architectural patterns from requirements, workload, and failure modes for
  a capability or subsystem. Use to decide whether queues, caching, events, scaling,
  or other infrastructure are justified, or to review a proposed architecture for
  missing reliability mechanisms and premature complexity. Does not own full
  specifications, delivery sequencing, or infrastructure deployment.
---

# Systems Design Decision Framework

Start from requirements, workload characteristics, and failure modes — then derive
architecture. Do not start from technologies.

Requirements / workload / failure modes → architectural pressures → appropriate
pattern → implementation options.

## Scope and composition

Run this skill independently for one capability, or use its decision record inside
an existing technical design. Keep one shared reasoning procedure; load supporting
references only for the pressures that apply. Split out a specialist skill later
only if it needs a distinct workflow, evidence, or tools (for example, measured
performance diagnosis), not one skill per infrastructure product.

Cite the project's `GLOSSARY.md` terms and existing ADRs when present. Record a
decision that passes the ADR test in `domain-modeling` as an ADR; otherwise put the
reasoning in the spec's Implementation Decisions. If a proposed mechanism changes
user-visible behavior (such as immediate success becoming eventual completion),
surface that product decision rather than assume it.

## Vocabulary

- **Job:** description of work to be done, with identity and input/reference data.
- **Queue:** durable waiting/buffering mechanism for work in this framework. Verify
  actual persistence/acknowledgment settings; an in-memory queue is not durable.
- **Worker:** process that executes jobs; it can share the application's codebase.
- **Command:** “do this,” directed to an owner; it may be synchronous or asynchronous.
- **Event:** “this happened,” a fact that consumers can independently react to.

These are different responsibilities, not necessarily different deployed services.
A database jobs table and worker can implement a durable queue. Async execution alone
provides no durability. Multiple workers competing for a job are not event fan-out.

## Decision procedure

### 1. Bound the capability and evidence

Identify the desired outcome, completion semantics, current implementation, constraints,
and evidence source. Label facts as supplied requirements, measurements, assumptions,
or unknowns. Do not invent traffic, service-level objectives (SLOs), retry counts, or
team capacity. Ask only questions that materially change the decision; continue with
explicit reversible assumptions elsewhere. Missing correctness constraints can leave
that choice unresolved without blocking independent analysis.

Capture relevant dimensions, not a mandatory interview checklist:

- Immediate result or acknowledgment? End-to-end deadline, including tail latency?
- Can processing be deferred? What does the user see while pending or failed?
- Arrival rate, burst size/duration, service-time distribution, payload size, growth?
- CPU, network, database reads/writes, storage, or external-dependency bottleneck?
- Can arrival exceed processing? Must work survive restart? Can it expire or be lost?
- Atomic invariants, concurrency, duplicates, ordering scope, freshness, replay?
- Independent consumers, time triggers, independent scaling or isolation needs?
- Availability, acceptable data loss and recovery time, trust/tenant boundaries?
- Existing platform capabilities, cost ceiling, operational ownership and skills?

### 2. Establish the simplest adequate baseline

For a conventional transactional web application, consider:

`Client → Application / modular monolith → PostgreSQL`

This is a starting hypothesis, not a universal stack mandate. Preserve an adequate
existing stack. Required safety, durability, availability, or known load may justify
additional mechanisms from day one; do not demand a production incident first.

### 3. Derive pressures, then evaluate pattern gates

Read [pattern rubric](references/pattern-rubric.md) for relevant branches. This is a
set of composable gates, not a single exclusive decision tree or additive score.
A strong correctness requirement cannot be averaged away by low traffic.

For each candidate record:

1. Requirement/evidence → pressure or concrete failure being prevented.
2. Simplest alternative and why it meets or fails the requirement.
3. Pattern status: **needed now**, **conditional** (name missing evidence),
   **deferred** (give revisit trigger), or **unjustified** for this scope.
4. New consistency, operational, cost, and failure obligations introduced.

Recommend only needed patterns in the current architecture. Do not turn every row
into a component. Slow critical work is still critical when asynchronous. If the
result must be immediate but exceeds its deadline, expose infeasibility or a product
tradeoff; a queue cannot satisfy that immediate-result requirement.

### 4. Walk failure boundaries

For durable, concurrent, or external work, read
[failure analysis](references/failure-analysis.md). Trace acceptance → durable intent
→ execution → side effect → state commit → acknowledgment. At every boundary ask
what survives a crash, how recovery finds it, and what happens on repetition.

Define state transitions, concurrency control, acknowledgment, retry budget,
reconciliation, and ownership only where applicable. A key named “idempotency key”
is not an implementation. Explain its uniqueness scope, atomic enforcement, lifetime,
and how external effects and intentional re-execution are distinguished.

### 5. Choose implementation only after the pattern decision

First decide whether a queue (or another pattern) is needed. Then compare only viable
implementations against required durability, ordering, throughput, retention/replay,
latency, failure recovery, platform fit, security, cost, and maintenance burden.
Include a simple implementation on the existing platform where viable. Usually two
or three options suffice; skip vendor comparison when technology selection is out of
scope. Verify version-specific guarantees, limits, prices, and platform behavior in
current primary documentation; label unverified claims instead of inventing certainty.

Redis/BullMQ, RabbitMQ, SQS, and Kafka are not interchangeable answers to “async.”
Do not promote Kafka, microservices, Kubernetes, Redis, a gateway, or a service mesh
because of prestige, hypothetical scale, or another company's architecture.

### 6. Produce a proportional decision record and stop

Use [decision template](assets/capability-decision.md); omit inapplicable sections.
A small synchronous CRUD capability may need one short paragraph plus its invariant
and revisit trigger. Use [worked examples](references/examples.md) when a concrete
comparison helps. Do not generate a system-wide architecture inventory for a local edit.

Finish when requirements are accounted for, material failure paths have a response,
assumptions are visible, and a simpler alternative has been assessed. For uncertainty,
propose the smallest measurement or experiment that would change the decision, with
a stopping condition. Include observable verification (for example, kill a worker
after its side effect and verify recovery), not a promise that the diagram is robust.
Design analysis does not authorize provisioning, migration, or deployment.
