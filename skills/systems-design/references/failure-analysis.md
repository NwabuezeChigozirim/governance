# Failure analysis

Read the applicable rows at each durable or remote boundary. Do not require every
mechanism for every capability.

| Failure question | Required reasoning |
| --- | --- |
| Crash after accepting work but before persisting it? | Define the durable acceptance point. Return accepted only after required intent is durable; client retry must not create a second logical operation. |
| Crash while executing or after effect but before acknowledgment? | Expect redelivery where at-least-once delivery applies. Define lease/visibility timeout, renewal, recovery and completion acknowledgment. A lease can expire while a worker still runs. |
| Same operation executes concurrently? | Use atomic uniqueness/conditional transitions and a scoped operation identity. Check-then-insert is racy. Fencing/version checks may reject stale workers; a lock alone cannot undo an external effect. |
| External request times out after possibly succeeding? | Outcome is unknown, not necessarily failed. Use provider-supported idempotency, query operation status or reconcile before repeating an irreversible effect. |
| DB commits but publish fails? | Persist intent with state in one transaction and relay with retry. Monitor oldest pending intent. Marking published before sending loses messages; sending before marking can duplicate them. |
| Object write succeeds but DB update fails, or the reverse? | Track durable pending state, deterministic/versioned object names, retry-safe finalization and orphan cleanup. Do not claim a cross-store transaction. |
| Transaction succeeds but response is lost? | Stable request identity and persisted result permit a safe client retry. Specify key scope, payload conflict handling and dedup retention. |
| Consumer sees duplicates, reordering or an old event after a new one? | Define per-entity ordering/version checks and deduplication atomically with local effects. Replay must not repeat irreversible external effects. Global ordering is a separate expensive requirement. |
| Retries amplify an outage? | Retry transient failures only, with capped exponential backoff and jitter, bounded attempts AND elapsed deadline. Coordinate retry ownership across layers; honor throttling signals. |
| Permanent bad input / poison message? | Quarantine or a failed-job table may suffice instead of a separate DLQ service. Define terminal state, alert owner, inspection, retention and safe redrive. |
| Backlog exceeds deadline or storage? | Bound depth/age/payload, apply quotas and admission control; expire/cancel obsolete work if semantics allow. Monitor oldest-job age, not just depth. |
| One tenant or dependency consumes all worker slots? | Bound concurrency and consider separate pools/bulkheads only for required isolation; protect fairness and downstream limits. |
| Cancellation, restart, deployment or operator redrive occurs? | Persist checkpoints if needed, drain safely, define cancellation races and compatible payload/schema versions. Old jobs may outlive new deployments. |
| Cache or read replica is stale/unavailable? | Define allowed staleness, authoritative source, fallback load, invalidation and read-after-write behavior. Authorization-sensitive data needs particular care. |
| Region, database or credentials become unavailable? | Derive failover and restoration from availability and recovery objectives; test backups, credential rotation and dependency recovery. Avoid automatic multi-region designs. |
| Recovery leaks or resurrects deleted data? | Carry tenant authorization and retention/deletion obligations into jobs, caches, indexes, logs and replay. Store references rather than unnecessary sensitive payloads. |

## Reliability language

“At-least-once” is a scoped delivery/execution contract, not guaranteed business
success. State the acknowledgment boundary, persistence and retention assumptions,
and behavior when retry limits expire. “Exactly once” must name its transaction or
broker scope; never infer end-to-end exactly-once external effects from a broker label.

For idempotency, record operation identity (often tenant + entity + operation version),
atomic enforcement, stored outcome, retention horizon and treatment of changed input.
An entity ID alone can wrongly suppress legitimate repeat operations. A DB transaction
can atomically deduplicate local effects; it cannot make an unrelated provider call atomic.

For each material failure give detection, recovery actor, safe automatic behavior,
and escalation condition. Metrics should answer whether obligations hold: age of
pending work, retry/terminal failure rate, duplicate effects, dependency saturation,
publication lag and restore time. Trace job/operation IDs across boundaries.

## Supporting primary sources

Consulted 2026-09-15 for the reliability distinctions; verify current implementation
semantics when selecting technology.

- [AWS transactional outbox guidance](https://docs.aws.amazon.com/en_en/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html): atomic state/intent writes and duplicate-aware consumption.
- [AWS Builders' Library: safe retries with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/): operation identity and ambiguous retries.
- [AWS retry guidance](https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_limit_retries.html): limiting retries and adding jitter.
