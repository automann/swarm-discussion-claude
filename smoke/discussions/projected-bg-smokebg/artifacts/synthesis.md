# Synthesis — Composed round-step command vs granular transport/WAL primitives

**Mode:** lightweight · 1 round · phase: response
**Discussion:** projected-bg-smokebg

## Executive summary

The Runtime Architect (`r1-msg-001`) argues to **keep the granular transport/WAL
primitives** and ship no composed round-step as a runtime command, because a round
straddles the host-execution seam (transport-init hands a spawn-order to the host,
which performs the spawn/wait the runtime cannot), and because per-primitive
events + atomic-rename artifacts are exactly what make `events.jsonl` auditable and
`resume_plan` well-defined after a reap. The DX Skeptic (`r1-msg-002`) argues to
**ship a composed `round_step` as the default integration surface** (primitives kept
underneath), because the cross-primitive ordering contract today lives in prose and
tribal knowledge, so every adapter re-implements and drifts on the boring,
replay-diverging bugs.

Critically, **both experts independently converge on the same resolution shape**: a
composite is acceptable only as a **strictly post-collect runtime reducer**
(`collect-result.json → append-message* → finalize-round`) that **provably never
crosses the host seam** and **emits byte-identical WAL records and resume
boundaries** to the hand-rolled sequence.

## Recommendation

Do **not** ship a composed command that spans the host seam. Instead, if round-step
ergonomics are wanted, add a **post-collect runtime reducer** that consumes an
already-written `collect-result.json` and drives `append-message*` → `finalize-round`
in the runtime-owned order, while (a) never invoking host transport, (b) emitting the
same per-step events (`message_appended`, `checkpoint_written`, `round_finalized`),
and (c) exposing a resumable step cursor backed by a single on-disk marker
`resume_plan` can name. Gate it behind one runtime conformance test that pins the
order and the emitted record set. Absent that guarantee, keep the granular primitives
as the canonical surface and ship composition only as an adapter-level recipe.

## Key agreements (`r1-msg-001`, `r1-msg-002`)

- Granular primitives remain the public, supported substrate; per-step WAL records
  and per-phase resume points are non-negotiable for audit and crash recovery.
- Any composition must emit identical per-primitive records/events and expose the
  same resume boundaries as the hand-rolled sequence — auditability is a property of
  the record stream, not of which command was called.

## Strongest surviving counter

From the Skeptic (`r1-msg-002`), aimed squarely at the keep-granular default:
granularity is not free — it pushes identical cross-primitive ordering onto N adapter
authors with **no shared conformance test**, so the ordering contract is prose, not
code, and the recurring failures (WAL appended before transport confirmed; commit
skipped on a partial send) surface only when a replay diverges. The call-count win is
paid once at integration time; the ordering-bug cost is paid repeatedly across hosts.
This counter survives because it is **not refuted** — it is only conditionally
defused by the post-collect-reducer design, which still has to be built and proven to
preserve identical records/resume points.

## Active disagreement (unresolved axis first)

- **Should a composed round-step be a runtime command at all, or live in the adapter?**
  - Architect (`r1-msg-001`): adapter-level only — a runtime round-step risks crossing
    the host seam (breaking the lone host-agnostic constraint) or leaving `resume_plan`
    an unnameable intermediate state.
  - Skeptic (`r1-msg-002`): runtime command by default — centralize the ordering
    contract in one tested place instead of N drifting re-implementations.

## Open questions

1. Can a round-step be cleanly bisected at the host seam so the runtime half never
   spawns/waits?
2. What single on-disk marker would `resume_plan` read to distinguish
   "composed-step in progress" from a bare partial?
3. Does any host need to inject behavior *between* transport and WAL (which would
   forbid a single runtime-owned ordering contract)?
