# Worked examples

Numbers below are illustrative supplied requirements or explicit design assumptions,
not defaults to copy into production.

## Video processing

**Requirements (example):** processing takes 30–180 seconds; upload acknowledgment
must be prompt; accepted processing must survive restarts; completion can be eventual.
Input/output are large media objects. One application DB already exists.

**Execution:** asynchronous. Acknowledge accepted processing after a transaction
records the uploaded asset and durable job. Upload initiation is not proof of a
completed upload; verify the object before accepting processing.

**Patterns:** job + durable queue + worker; object storage. Start by evaluating a
DB jobs table and separately deployed worker using the existing codebase. No separate
broker is justified without workload or platform evidence. Writing the job in the
same DB transaction avoids a DB/broker dual write. If a broker is selected later,
use a transactional outbox or an equivalently justified reliable handoff.

**State:** uploaded → queued → processing → ready | failed. A transient failure can
return processing → queued; redrive failed → queued is explicit and recorded.

**Reliability:** at-least-once attempts within retention/retry policy. Claim jobs with
leases; renew during execution and recover expired claims. Acknowledge completion only
after durable finalization. Expired leases can produce concurrent processing.

**Idempotency:** `(tenant_id, video_id, processing_version)` for the logical operation,
with a unique DB constraint and conditional state/version updates. Use attempt-specific
output objects, then atomically select the winner in the DB; clean unused outputs.
Retain operation results through the allowed redrive window. `video_id` alone would
block intentional reprocessing. Fence stale attempts from replacing a newer result.

**Retry policy (assumption to confirm):** at most 3 total attempts, transient failures
only, capped exponential backoff with jitter and a 15-minute elapsed budget. Invalid
media fails immediately. Timeout selection must accommodate measured processing tails;
180 seconds is not assumed to be a proven maximum.

**Failure handling:** a failed-job table with reason, alert owner and safe redrive
suffices initially; a separate DLQ is conditional on broker/operations needs.

- Worker crashes midway: lease expires; retry or resume from a justified checkpoint.
- Same job runs twice: both may compute, but only the current fenced attempt finalizes.
- Object write succeeds, DB update fails: retry-safe finalization and reconcile orphan
  objects after a grace period that protects live attempts.
- Queue is unavailable: do not report durable acceptance unless durable intent exists.

**Checks:** crash after output upload; run duplicate/stale attempts; interrupt DB
finalization; verify one current result, eventual recovery, and eventual orphan cleanup.
Monitor oldest queued job, processing duration, failures and storage growth. Measure
arrival bursts and effective worker capacity before choosing worker count or broker.

## Small internal CRUD tool

Supplied: 20 staff, modest traffic, indexed queries meet the 300 ms target, changes
must be visible immediately. Keep synchronous application + existing PostgreSQL.
Use a transaction/constraints for related changes and lost-update protection where
concurrent edits matter. No queue, cache, replicas or gateway is currently justified.
Review query latency and capacity if the target is missed; backups follow the actual
recovery requirement regardless of traffic. Low load does not remove correctness needs.

## Immediate inventory reservation plus optional email

Inventory reservation must be confirmed now and cannot oversell. Use a synchronous
transaction with a conditional stock update/appropriate concurrency control. Do not
move reservation behind a queue simply because confirmation email is slow. Email may
be a durable job recorded in that transaction if delivery must survive restart.
Provider timeout can mean email was sent; use supported idempotency or accept/document
possible duplicates. Do not claim outbox gives exactly-once email.

## Sustained overload

Supplied: 100 jobs/s continuously; 10 effective slots; mean service time 1 second.
Nominal capacity is 10 jobs/s and backlog grows about 90 jobs/s. A queue alone cannot
stabilize this workload. Measure the limiting resource, then increase viable capacity,
reduce work or reject/defer admission with explicit semantics. A finite burst would
be a different case: calculate whether backlog can drain before its deadline.
