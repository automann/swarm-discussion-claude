# Agent Operating Contract — swarm-discussion-claude

This repository is the **Claude adapter** for the swarm-discussion family. The
governing contract is `docs/ADAPTER-SPEC.md` in the runtime repo
(`swarm-discussion-runtime`). Keep every change consistent with it.

## Principles

1. This repo holds host-specific glue only: the skill, the two agent
   definitions, the wrapper, and the vendored runtime. No protocol semantics,
   no runtime mechanics — those live in the runtime repo and are vendored.
2. The orchestrator runs as a sub-agent (nested topology). The skill stays
   thin: collect brief → spawn orchestrator → relay synthesis. Never move
   protocol execution into the skill (that re-pollutes the parent context).
3. Persona experts (`swarm-expert`) stay no-tools (`Read` only) and must never
   receive the `Agent` tool. Only `swarm-orchestrator` may spawn sub-agents.
4. Give every spawned agent a concrete, bounded, role-specific prompt. Never a
   self-replicating prompt (capable hosts refuse them).
5. The wrapper contains no discussion mechanics — only runtime discovery, the
   `doctor` readiness check (incl. host nesting probe), and gate/primitive
   delegation.

## Vendored runtime

- `vendor/swarm-runtime/` is **read-only**. To update, re-vendor from a new
  runtime SHA with the runtime repo's `scripts/vendor.py`, then run
  `scripts/vendor.py verify` and re-certify. Never hand-edit vendored files.
- After any re-vendor, run `python3 bin/swarm_runtime_wrapper.py doctor
  --smoke-fixture` and re-certify against a real discussion before release.

## Release checklist

- `doctor --smoke-fixture` passes (contract + fixture gates + nesting).
- A real Claude-driven discussion passes `conformance/certify_adapter.py`
  (from the runtime repo) with this repo's vendored bundle.
- Release notes state the pinned `runtimeSha` from `vendor-manifest.json` and
  the runtime compatibility string.

## Push Cadence

The maintainer has opted into auto-push: after any work turn that commits to
this repo, push the new commits to `origin/main` without asking first.
