# swarm-discussion-claude

The **Claude Code adapter** for the `swarm-discussion` plugin family. It is a
thin host shell around the host-agnostic runtime in
[`swarm-discussion-runtime`](https://github.com/automann/swarm-discussion-runtime),
which is vendored here at a pinned SHA. This repo carries no protocol or runtime
mechanics — only the Claude-specific glue.

## What it does

A parent agent invokes the `swarm-discussion` skill when it hits a hard, open
question. The skill projects per-topic expert agents, dispatches ONE
`swarm-coordinator` BACKGROUND session that runs the entire multi-expert
discussion in its own context and spawns those experts, and returns only the
synthesis:

```text
parent agent (root)                        holds only the brief + final synthesis
  └─ skill: brief → project .claude/agents/swarm-<runId>-<role>.md
            → dispatch coordinator (claude --bg) → relay synthesis → tear down
       swarm-coordinator (background session)   owns the whole loop in its own context
         context-build · prompt-build · transport · WAL · rounds · synthesis
         └─ projected swarm-<runId>-<role> experts   one-shot structured contributions
```

This keeps discussion mechanics out of the parent's context window — the founding
goal of the v2 redesign. v0.3.0 uses dynamic, per-topic projected custom agents;
because project agents load only at a session's start, the coordinator runs as a
fresh background session. Requires Claude Code background sessions (research
preview, ≥ 2.1.139) plus nested spawning (≥ 2.1.172); see the runtime's
`docs/adr/0001-v0.3.0-dynamic-custom-agent-topology.md`.

## Layout

```text
.claude-plugin/plugin.json    plugin manifest
.claude/settings.json         worktree.bgIsolation none (coordinator bg session writes to the checkout)
agents/swarm-coordinator.md   coordinator background-session agent (Agent + Bash + Read + Write)
agents/swarm-expert.md        no-tools expert TEMPLATE (parent specializes per run, Read only)
skills/swarm-discussion/      thin parent skill (project agents → dispatch coordinator → tear down)
bin/swarm_runtime_wrapper.py  runtime discovery + doctor + gate delegation (no mechanics)
vendor/swarm-runtime/         vendored runtime bundle + vendor-manifest.json (read-only)
```

## Install

Develop / test locally — loads the plugin for one session; its agent types
appear namespaced as `swarm-discussion:swarm-coordinator` (per-run experts are
projected under `.claude/agents/` at runtime), and the `swarm-discussion` skill registers:

```bash
claude --plugin-dir /path/to/swarm-discussion-claude
# after editing plugin files in-session:
/reload-plugins
```

Validate the manifest at any time:

```bash
claude plugin validate /path/to/swarm-discussion-claude
```

End users install through the `swarm-discussion` aggregator marketplace; this
adapter repo intentionally ships no `marketplace.json` (distribution is the
aggregator's responsibility per the runtime repo's `docs/ADAPTER-SPEC.md`).

Verified 2026-06-11 on Claude Code 2.1.177: `claude plugin validate` passes,
`--plugin-dir` registers both agent types and the skill, and the real
`swarm-discussion:swarm-expert` type spawns and returns as a Read-only leaf.

## Release

- **v0.3.0** (2026-06-21) — dynamic custom-agent topology: the parent projects
  per-topic experts, a `swarm-coordinator` background session runs the loop and
  spawns them, with runtime-owned projection provenance. Vendored runtime SHA
  **`04f4974`**, compatibility **`swarm-runtime-v2-alpha`**. Minimum Claude Code:
  background sessions (≥ 2.1.139) + nested spawning (≥ 2.1.172). Certified against
  a real coordinator-driven projected discussion
  (`smoke/discussions/projected-bg-smokebg`) with
  `certify_adapter.py --require-projection` (5/5) and a zero-residue cleanup
  check. Note: background sessions are a research-preview Claude Code feature; the
  skill stops if `doctor` reports them unsupported (no inline fallback).
- **v0.2.1** — orchestrator-as-sub-agent topology over runtime `93e99d1`.

## Pinned runtime

The vendored runtime SHA and per-file hashes are recorded in
`vendor/swarm-runtime/vendor-manifest.json` (runtime compatibility:
`swarm-runtime-v2-alpha`). The vendored tree is **read-only** — never edit it.

## Re-vendor and certify

From a checkout of the runtime repo, re-vendor and verify:

```bash
python3 <runtime-repo>/scripts/vendor.py vendor --dest <this-repo>/vendor/swarm-runtime
python3 <runtime-repo>/scripts/vendor.py verify --dest <this-repo>/vendor/swarm-runtime
```

Check readiness (runtime contract, bundled-fixture gates, host nesting support):

```bash
python3 bin/swarm_runtime_wrapper.py doctor --smoke-fixture
```

Certify the adapter against a REAL Claude-driven discussion (from the runtime
repo, per `docs/ADAPTER-SPEC.md`):

```bash
python3 <runtime-repo>/conformance/certify_adapter.py --require-projection \
  --discussion <a real projected discussion dir produced by this adapter> \
  --vendored <this-repo>/vendor/swarm-runtime \
  --runtime  <this-repo>/vendor/swarm-runtime/runtime/swarm_rt.py
```

For v0.3.0 the release gate is `--require-projection` (the discussion must declare
projected custom agents) plus a zero-residue check that no run-scoped
`.claude/agents/swarm-<runId>-*` file survived.

The bundled fixture proves the runtime; certification proves the adapter.
Re-certify on every re-vendor and before every release.
