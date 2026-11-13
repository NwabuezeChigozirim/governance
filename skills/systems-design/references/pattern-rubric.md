# Pattern gates

Use only relevant rows. “Candidate” means evaluate the gate and simpler alternative,
not install it. Patterns compose across execution, consistency, storage and operations.

| Requirement or evidence | Candidate and gate | Simpler alternative / obligation |
| --- | --- | --- |
| Result is needed within the request deadline | Synchronous request path if total work fits | Bound dependency calls; moving work to a queue changes completion semantics. |
| Work can finish later, is slow, CPU-heavy, network-heavy, or should be isolated | Job + worker | Best-effort in-process execution is acceptable only if loss is explicitly acceptable. A worker can share the monolith repository. |
| Accepted work must survive crashes, retry later, or absorb finite bursts | Durable queue with recovery | A transactional jobs table may suffice. A broker is a separate decision. Bound backlog, retention, and admission. |
| Time triggers work | Scheduler, optionally enqueueing jobs | Short bounded work may execute directly. Define timezone, daylight-saving behavior, missed-run catch-up, overlap and duplicate-run identity. |
| Several independent consumers react to the same fact | Event + pub/sub when independent delivery/lifecycle matters | In-process handlers may suffice when coupled execution is acceptable. Durable subscriptions, replay and ordering require explicit contracts. |
| Several changes in one database must obey an invariant | Transaction plus appropriate constraints/isolation | A transaction alone does not prevent every concurrent race. Use uniqueness, conditional updates, locking or serializable execution as needed. |
| DB state and intent to publish must not diverge | Transactional outbox: write state + intent in the same transaction, relay later | A job row in the same transaction may already solve the need. Publication is eventual; relay duplicates and backlog remain possible. |
| Multi-step work spans independent transactional resources | Persisted workflow / saga if local transaction cannot cover it | First consider keeping the invariant in one owner/database. Compensation is a business action, not guaranteed rollback; irreversible steps need reconciliation. |
| Repeated expensive reads/computation cause material cost or latency | Cache if useful reuse exists and freshness permits | Optimize query/index/batching first; consider request-local reuse. Define invalidation, TTL, tenant-safe keys, stampede control and cache-loss behavior. |
| Read pressure persists after query/index/connection tuning | Read replicas if eligible reads tolerate lag | Size primary first where viable. Route read-after-write needs appropriately; replicas are not backups or automatic full HA. |
| Large binary/media data needs independent transfer, retention or delivery | Object storage | Small bounded blobs may fit an existing store. Define access control, upload limits, lifecycle and orphan reconciliation. |
| Repeated geographically distributed content delivery dominates latency/bandwidth | CDN / edge caching | Ordinary origin delivery may suffice; define purge/freshness and private-content handling. |
| Full-text, fuzzy, relevance or faceted search exceeds native DB capabilities | Dedicated search index | Evaluate DB search first. Index is derived state: define lag, rebuild, deletion and authorization behavior. |
| One app instance cannot meet proven load or availability requirements | Horizontal instances + load balancing | Compare vertical sizing/optimization. Externalize necessary session/job state; eliminate dependency single points of failure and test failover. |
| Clients face material routing, authentication or aggregation complexity across services | Gateway or backend-for-frontend when shared policy or client adaptation justifies it | Existing ingress/router or one application endpoint may suffice. More services alone do not justify a gateway. |
| Overload, abuse, quotas or tenant interference threaten deadlines | Admission control, rate limits, bounded concurrency, backpressure | A queue delays overload; it does not create capacity. Set rejection/degradation behavior and protect downstream capacity. |
| Unavailable/slow dependency exhausts local resources | Deadlines + isolation; circuit breaker if repeated calls worsen failure | First bound calls/concurrency. Define fail-open/closed or stale fallback from requirements; never invent success. |
| Write contention or dataset size exceeds a tuned single DB | Partitioning/sharding only after identifying the actual limit | Consider batching, schema/index changes, archival and larger capacity. Define routing, cross-partition invariants, skew and rebalancing. |
| Independent deployment, ownership, trust or failure isolation is a demonstrated need | Service boundary / microservice where benefit exceeds distributed cost | Modules or separate worker deployments often suffice. Kubernetes and service mesh require their own operational justification. |
| Data loss/recovery objectives require restoration | Backups + tested restore; redundancy/failover as required | Replication can copy corruption/deletion. Specify recovery point/time objectives, restore drills and dependency recovery. |

## Capacity reasoning

Use measurements or explicitly labeled estimates with units. For arrival rate λ jobs/s,
mean service time S seconds/job and c effective parallel slots, nominal capacity is
c/S jobs/s; utilization is λS/c. This is a first approximation, not a sizing guarantee:
account for tail latency, CPU limits, downstream quotas and headroom.

For a finite burst, estimate backlog from excess arrivals over service capacity.
Drain time is roughly backlog / (capacity − continuing arrivals), only if that
denominator is positive. Sustained arrival above capacity needs more capacity,
less work, admission control or changed expectations, not an unbounded queue.

Determine whether the measured limit is reads, writes, CPU, network, storage,
connections, contention or an external quota before selecting a scaling pattern.

## Technology comparison contract

State the chosen pattern and required semantics first. For each implementation show
fit, known gaps, operating burden, cost drivers and reversibility. Treat managed and
self-hosted options fairly given the team's constraints. A replayable event log is
not simply a more powerful job queue. An existing DB queue still requires safe
claiming/leases, indexes, cleanup and capacity analysis. No universal traffic threshold
selects a vendor or demands microservices.
