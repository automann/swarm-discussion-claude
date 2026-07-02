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

## Usage

Once installed through the [aggregator marketplace](https://github.com/automann/swarm-discussion), just ask
in plain language — or run the skill directly:

```text
Use swarm-discussion to decide: should the orders service adopt event sourcing?
```

```text
/swarm-discussion
```

Bring the questions where a lone model would just nod along — architecture & design trade-offs, one-way-door
calls, adversarial reviews, open questions where easy consensus would be suspicious. **What comes back** is a
**recommendation**, the **strongest surviving counter-argument**, the **open questions**, and pointers to the
traceable artifacts (cited argument graph, synthesis, trace/evidence). The debate runs inside the
`swarm-coordinator` background session, so your main thread never fills with transcript.

**Two knobs, set together.** `mode` controls *breadth & cost* (how many experts, how many rounds);
`stressPolicy` controls *how hard they must disagree* (whether a mandatory anti-consensus stress pass
runs before synthesis). They're orthogonal — combine them freely:

```text
/swarm-discussion [--mode lightweight|standard|deep] [--stressPolicy auto|required|off] <your question>
```

`stressPolicy` **defaults from `mode`** (`lightweight → off`, `standard → auto`, `deep → required`), so
usually you set neither — pick a mode by stakes, or just describe the problem (*"go **deep** and don't let
them agree too fast"* ≈ `--mode deep --stressPolicy required`). Pass `--stressPolicy` only to override that
default:

| Invocation | What runs |
|---|---|
| `/swarm-discussion Should we adopt event sourcing?` | inferred mode + its default stress policy |
| `/swarm-discussion --mode standard --stressPolicy auto <topic>` | 2–3 experts; stress pass *only if* they converge with no real disagreement |
| `/swarm-discussion --mode deep <topic>` | full panel + a `required` stress pass (deep's default) |
| `/swarm-discussion --mode lightweight --stressPolicy required <topic>` | cheap 2-expert panel, but still force one stress pass |

Both knobs are detailed below; it defaults to **standard** when you say nothing.

## Modes

Pick a tier by stakes and budget (default **Standard**):

| Mode | Panel | Rounds | Calls/round | Use when |
|------|-------|--------|-------------|----------|
| `lightweight` | 2 dynamic experts + Moderator & Contrarian | 1–2 | 3–5 | quick sanity check, idea validation |
| `standard` *(default)* | 2–3 dynamic experts + 4 fixed roles | 2–3 | 5–8 | typical design decision, trade-off analysis |
| `deep` | 3–4 dynamic experts + 4 fixed roles | 3–5 | 8–12 | unprecedented problems, high-stakes calls |

> **Quality over quantity:** two rounds of *genuine* disagreement beat five rounds of polite agreement.

### Stress policy — engineering the disagreement

Orthogonal to `mode`, **`stressPolicy`** controls whether the panel must run an anti-consensus
**stress pass** (the Contrarian attacks the *strongest* agreement; the challenged experts answer
and may shift position) before it synthesizes:

| `stressPolicy` | Behavior | Default for |
|---|---|---|
| `required` | always run the stress pass, however smooth the round looks | `deep` |
| `auto` | run it only if the round reached consensus with no real disagreement | `standard` |
| `off` | no stress pass — fast convergence | `lightweight` |

You rarely set it (it defaults from the `mode`), but you can ask in plain language:
*"stress-test this"* / *"don't converge too fast"* → `required`. The runtime **certifies** that a
`required`/`auto` discussion actually engineered disagreement (a stress pass answered by a cited
response, or a recorded decision that none was needed) — a checked contract, not a suggestion.

Every panel runs **dynamic experts** generated per topic — each with explicit *stakes* and *blind spots* —
plus **fixed roles** that keep the debate honest:

| Role | Keeps the debate honest by… |
|------|------------------------------|
| 🧭 **Moderator** | framing the real fault lines and running the quality gate — *prevents premature consensus* |
| 🥊 **Contrarian** | stress-testing the *strongest* point of agreement — *prevents echo chambers* |
| 🔭 **Cross-Domain** *(standard / deep)* | bringing analogies from other fields — *prevents domain-locked thinking* |
| 📜 **Historian** *(standard / deep)* | building the cited argument graph and synthesis — *keeps it traceable* |

The full mode / role / round protocol lives in the runtime's
[`protocol/PROTOCOL.md`](https://github.com/automann/swarm-discussion-runtime/blob/main/protocol/PROTOCOL.md).

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

Verified 2026-06-22: `claude plugin validate` passes; `--plugin-dir` registers
`swarm-discussion:swarm-coordinator` and the `swarm-discussion` skill; a fresh
`claude -p --agent` session loads a just-written run-scoped `.claude/agents`
project agent (the projected-expert mechanism); and a real coordinator-driven
projected discussion certifies `certify_adapter.py --require-projection` (5/5).

## Release

- **v0.4.1** (2026-06-24) — honor explicit `--mode` / `--stressPolicy` invocation flags
  (over inference; live-verified) and document the combined `mode` × `stressPolicy` usage
  guide + the `stressPolicy` Modes table. Docs + skill polish over v0.4.0; same vendored
  runtime `c843931`.
- **v0.4.0** (2026-06-24) — `mode` × `stressPolicy` debate-depth orchestration (ADR
  0002): the coordinator runs the bounded loop (position → argument → stress-check →
  contrarian stress → response → synthesis); the runtime owns and certifies the
  engineered-disagreement contract. Vendored runtime SHA **`c843931`** (60 files).
  Certified against a real `claude --bg` coordinator-driven `deep`+`required`
  discussion (`smoke/discussions/stress-bg-smoke`) with
  `certify_adapter.py --require-projection --require-stress` (5/5) + zero-residue.
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

Check readiness (runtime contract, bundled-fixture gates, host nesting +
background-session support):

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

The v0.4.x release gate is `--require-projection --require-stress` (the discussion must
declare projected custom agents AND satisfy the declared `stressPolicy`) plus a
zero-residue check that no run-scoped `.claude/agents/swarm-<runId>-*` file survived.

The bundled fixture proves the runtime; certification proves the adapter.
Re-certify on every re-vendor and before every release.
