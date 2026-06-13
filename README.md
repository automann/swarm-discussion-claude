# swarm-discussion-claude

The **Claude Code adapter** for the `swarm-discussion` plugin family. It is a
thin host shell around the host-agnostic runtime in
[`swarm-discussion-runtime`](https://github.com/automann/swarm-discussion-runtime),
which is vendored here at a pinned SHA. This repo carries no protocol or runtime
mechanics — only the Claude-specific glue.

## What it does

A parent agent invokes the `swarm-discussion` skill when it hits a hard, open
question. The skill spawns ONE `swarm-orchestrator` sub-agent that runs the
entire multi-expert discussion in its own context and returns only the
synthesis:

```text
parent agent (root)                     holds only the brief + final synthesis
  └─ skill: brief → spawn orchestrator → relay synthesis
       swarm-orchestrator (sub-agent)   owns the whole loop in its own context
         context-build · prompt-build · transport · WAL · rounds · synthesis
         └─ swarm-expert personas       one-shot structured contributions
```

This keeps discussion mechanics out of the parent's context window — the
founding goal of the v2 redesign. It relies on Claude Code's nested sub-agent
spawning (verified ≥ 2.1.172; the orchestrator spawns personas in the
foreground, so depth is unbounded for this shape).

## Layout

```text
.claude-plugin/plugin.json   plugin manifest
agents/swarm-orchestrator.md  orchestrator sub-agent (Agent + Bash + Read + Write)
agents/swarm-expert.md        persona expert (Read only — cannot spawn)
skills/swarm-discussion/      thin parent-facing skill (spawns the orchestrator)
bin/swarm_runtime_wrapper.py  runtime discovery + doctor + gate delegation (no mechanics)
vendor/swarm-runtime/         vendored runtime bundle + vendor-manifest.json (read-only)
```

## Install

Develop / test locally — loads the plugin for one session; its agent types
appear namespaced as `swarm-discussion:swarm-orchestrator` and
`swarm-discussion:swarm-expert`, and the `swarm-discussion` skill registers:

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
python3 <runtime-repo>/conformance/certify_adapter.py \
  --discussion <a real discussion dir produced by this adapter> \
  --vendored <this-repo>/vendor/swarm-runtime \
  --runtime  <this-repo>/vendor/swarm-runtime/runtime/swarm_rt.py
```

The bundled fixture proves the runtime; certification proves the adapter.
Re-certify on every re-vendor and before every release.
