# Synthesis — Expert lifecycle for swarm-discussion (v0.4)

**Discussion:** `stress-bg-smoke`  ·  **Mode:** deep  ·  **Stress policy:** required (stress pass ran)
**Round 1:** 7 messages, 14 reference edges (7 counter/questions), 2 position shifts, contrarian stress test triggered.

## Decision

**Hybrid, but ephemeral-by-default.** Keep v0.3's project-then-delete model and its zero-residue
certification gate unchanged as the default. Permit cross-run expert reuse **only** as an explicit,
machine-gated exception — never as the standing default.

### The one rule that settles it

> An expert may be reused across runs **only** when bound to a **run-context fingerprint**
> `H(definition/persona digest + input-slice ids + dependency digests + model id)` that the runtime
> attests and that **fails closed** on any mismatch. Otherwise, project fresh and delete.
> Reuse is a machine-enforced exception, not the default.

### Top risk of the chosen path

**Semantic staleness the residue/digest gates cannot see.** A byte-identical, validly-signed definition
can silently drift when dependencies or the underlying model change (`r1-msg-005`): the content hash is
unchanged, the promotion "reviewable diff" is **empty**, and the zero-residue gate passes — yet behavior
has moved. Secondary risks: fail-closed fingerprinting can cause re-projection storms / cold-start cost,
and a clean fingerprint still does not bound nondeterministic model-sampling drift.

## How the discussion got here (auditable)

- **Blind declarations diverged.** Advocate opened on a hybrid registry (`r1-msg-001`); skeptic on pure
  ephemeral (`r1-msg-002`).
- **Arguments engineered the split.** Advocate separated durable **definitions** from disposable
  **instances** (`r1-msg-003`); skeptic countered that any persisted definition is mutable cross-run state
  the run-scoped gate cannot see, and that a digest-pinned source + immutable cache already buys most
  warm-start (`r1-msg-004`).
- **Contrarian stress on the consensus.** Both had quietly agreed that *content-addressing + signed opt-in
  makes reuse safe/certifiable*. The contrarian attacked exactly that (`r1-msg-005`): a hash certifies
  **bytes, not semantics**; the promotion diff is empty for the most dangerous (stale-but-unchanged) reuse;
  "off by default" is an erodable human gate.
- **Both shifted (minor), converging by argument.** Advocate folded reuse into a machine-enforced
  run-context fingerprint and dropped the human opt-in (`r1-msg-006`, trigger `r1-msg-005`,`r1-msg-004`).
  Skeptic narrowed the honest certified claim to "zero **byte** residue + run-scoped provenance" and
  re-keyed reuse on the same fail-closed fingerprint (`r1-msg-007`, trigger `r1-msg-005`).

## Agreements (post-stress)

- Run-scoped provenance + zero cross-run contamination by default are non-negotiable; the v0.3
  instance-deletion gate stays.
- Certify only what the runtime can attest: the honest claim is *zero byte residue + run-scoped
  provenance*, **not** *zero semantic contamination*.
- Any reuse must be content-addressed **and** bound to a fail-closed run-context fingerprint; a machine
  gate replaces the human "off by default" opt-in.

## Strongest surviving counter / Minority report

**Skeptic (un-refuted by argument):** stay **ephemeral-by-default** — reuse must be OFF by default and only
ever a machine-gated fingerprinted exception, and **certification-gated runs should project fresh**. Even a
fail-closed fingerprint cannot bound nondeterministic model-sampling drift, and any default-on reuse path
erodes under deadline pressure. The advocate conceded fingerprinting is *necessary* but never showed
certified-run reuse is ever *safe*. Recorded as a live dissent, not resolved by majority.

## Open questions

1. Which dependency digests are behavior-relevant enough to gate the fingerprint without causing needless
   cold re-projection?
2. How is nondeterministic model-sampling drift bounded when the fingerprint is unchanged?
3. What cold-start latency budget justifies a warm-start (reuse) exception over fresh projection?
