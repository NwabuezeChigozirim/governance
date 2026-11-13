# Capability decision

Use applicable fields; replace prompts with evidence or explicit unknowns. This is a
reasoning record, not a requirement to fill every field or provision every pattern.

- **Capability / scope:**
- **Requirements and evidence:** Sources/IDs; facts versus assumptions; deadline,
  load, completion semantics, consistency, availability and operating constraints.
- **Architectural pressures:** Requirement → pressure / failure to prevent.
- **Execution model and why:**
- **Pattern decisions:** Needed now / conditional / deferred / unjustified; evidence,
  simplest alternative, obligations introduced, revisit trigger.
- **Implementation:** Only after pattern selection; fit and tradeoffs or not yet selected.
- **Storage / source of truth:**
- **State model:** Include acceptance and terminal states, transitions and owner.
- **Reliability:** Durable acceptance, delivery scope, acknowledgment and recovery.
- **Idempotency / concurrency:** Identity, atomic enforcement, retention, external effects.
- **Retry policy:** Error classification, attempt and time budget, jitter, retry owner.
- **Failure handling:** Crash boundaries, ambiguous outcomes, quarantine/redrive,
  reconciliation and responsible operator.
- **Verification and operations:** Observable load/failure checks and meaningful metrics.
- **Open decisions / assumptions:** Consequence, evidence needed and stopping condition.
- **Revisit / removal trigger:** Measurement or requirement that changes the decision.
