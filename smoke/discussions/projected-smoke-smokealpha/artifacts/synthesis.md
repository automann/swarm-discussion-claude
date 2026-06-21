# Synthesis

**Topic:** Should swarm-discussion-runtime ship a composed round-step command, or keep granular transport/WAL primitives?

**Recommendation:** Keep granular transport/WAL primitives; a composed round-step is sugar an adapter can add without the runtime losing auditability.

**Architect:** Keep granular transport/WAL primitives as the shipped surface and express round-step as an optional host-side composition, since fused commands erode the explicit, auditable command boundary that a host-agnostic runtime depends on.

**Skeptic:** Keep granular transport/WAL primitives and do not ship a composed round-step command, since composition belongs in host code and a bundled command risks hiding boilerplate behind a leaky, host-coupling abstraction that conflicts with the host-agnostic constraint.
