# Agent Operating Contract — swarm-discussion-claude

This repository is the **Claude adapter** for the swarm-discussion family. The
governing contract is `docs/ADAPTER-SPEC.md` in the runtime repo
(`swarm-discussion-runtime`). Keep every change consistent with it.

## Principles

1. This repo holds host-specific glue only: the skill, the two agent
   definitions, the wrapper, and the vendored runtime. No protocol semantics,
   no runtime mechanics — those live in the runtime repo and are vendored.
2. The discussion runs in a `swarm-coordinator` BACKGROUND session (`claude --bg`),
   not the parent thread. The skill stays thin: collect brief → project per-topic
   expert agents → dispatch the coordinator session → relay synthesis → tear down.
   Never run protocol execution in the skill/parent (that re-pollutes the parent
   context). A background session is required because dynamically-projected
   `.claude/agents` files load only at a fresh session's start (ADR 0001 D2).
3. Persona experts stay no-tools (`Read` only) and must never receive the `Agent`
   tool. Only `swarm-coordinator` may spawn sub-agents.
4. Give every spawned agent a concrete, bounded, role-specific prompt. Never a
   self-replicating prompt (capable hosts refuse them).
5. The wrapper contains no discussion mechanics — only runtime discovery, the
   `doctor` readiness check (host nesting + background-session probes), and
   gate/primitive delegation. v0.3.0 depends on background sessions (research
   preview); the skill stops if `doctor` reports they are unsupported.
6. Run-scoped projection: the parent projects `.claude/agents/swarm-<runId>-<role>.md`
   and deletes only the files it created (zero residue) on every exit path; the
   coordinator writes the `projection-manifest.json` body. Never touch user or
   plugin agents.

## Vendored runtime

- `vendor/swarm-runtime/` is **read-only**. To update, re-vendor from a new
  runtime SHA with the runtime repo's `scripts/vendor.py`, then run
  `scripts/vendor.py verify` and re-certify. Never hand-edit vendored files.
- After any re-vendor, run `python3 bin/swarm_runtime_wrapper.py doctor
  --smoke-fixture` and re-certify against a real discussion before release.

## Release checklist

- `doctor --smoke-fixture` passes (contract + fixture gates + nesting).
- A real Claude-driven PROJECTED discussion passes `conformance/certify_adapter.py
  --require-projection` (from the runtime repo) with this repo's vendored bundle,
  AND a zero-residue check shows no run-scoped `.claude/agents/swarm-<runId>-*`
  file survived.
- Release notes state the pinned `runtimeSha` from `vendor-manifest.json` and
  the runtime compatibility string.

## Push Cadence

The maintainer has opted into auto-push: after any work turn that commits to
this repo, push the new commits to `origin/main` without asking first.
