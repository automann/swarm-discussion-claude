---
name: swarm-discussion
description: |
  Summon a group of experts to debate a hard, open question OUTSIDE your context window, then act on
  their synthesis. Use when the user faces a complex decision, design trade-off, architecture choice, or
  review that benefits from multiple expert perspectives with designed tension and a quality gate. The
  discussion runs inside a dedicated coordinator BACKGROUND session that spawns per-topic expert agents;
  you receive only the final synthesis and artifact paths — not the discussion mechanics.
---

# swarm-discussion

This skill is deliberately THIN. You (the parent agent) do NOT run the discussion protocol. You project
per-topic expert agents, dispatch ONE `swarm-coordinator` **background session** that runs the entire
discussion in its own context and spawns those experts, wait for its terminal index, relay the synthesis,
then tear everything down. All protocol mechanics live in the coordinator and the vendored runtime.

Why a background session: dynamically-projected `.claude/agents` files load only at a session's *start*, so
a fresh detached session is the only way to spawn them while your thread stays thin (ADR 0001 D2).

## 1. Resolve the plugin root

```bash
PLUGIN_ROOT="${SWARM_DISCUSSION_PLUGIN_ROOT:-}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT="$(find "$HOME/.claude" -type f -path '*swarm-discussion*/bin/swarm_runtime_wrapper.py' 2>/dev/null | sort -V | tail -1 | sed 's#/bin/swarm_runtime_wrapper.py$##')"
fi
echo "$PLUGIN_ROOT"   # must print a dir containing bin/swarm_runtime_wrapper.py; if empty, stop and tell the user.
```

## 2. Preflight

```bash
python3 "$PLUGIN_ROOT/bin/swarm_runtime_wrapper.py" doctor --smoke-fixture
```

Stop if it fails. Then read two capabilities from the output and **stop if either is not `true`** (v0.3.0
has no inline fallback — running the protocol in this thread would re-pollute your context):

- `hostBackgroundSessions.supported` — the coordinator runs via `claude --bg`.
- `hostNesting.supported` — the coordinator (a session) spawns expert sub-agents.

If unsupported, tell the user this host can't run the v0.3.0 topology and stop.

## 3. Assemble the brief and ids

Build a compact brief JSON (do not dump the conversation): `topic`, `objective`, `mode`
(`lightweight|standard|deep`), `parentContext`, `constraints`, `knownFacts`, `successCriteria`. Pick a
`discussionId` slug, a collision-safe `runId` (e.g. `discussionId` + a short timestamp/random suffix), and
set `discussionDir="$(pwd)/.swarm/discussions/<discussionId>"`.

## 4. Plan personas and PROJECT the expert agents

Plan the expert roster for this `mode` and topic following
`$PLUGIN_ROOT/vendor/swarm-runtime/protocol/templates/persona-generator.md` (lightweight → fewer experts;
deeper → more, with designed tension). For EACH expert write a run-scoped project agent, derived from the
template `$PLUGIN_ROOT/agents/swarm-expert.md`, to `.claude/agents/swarm-<runId>-<role>.md`:

```markdown
---
name: swarm-<runId>-<role>
description: swarm-discussion <role> expert for run <runId> (ephemeral; deleted after the run).
tools: Read
model: inherit
---
You are the <role> expert in a structured swarm-discussion: <persona stance / bias / blind spots>.
Your phase task, the slice you may cite, and your exact output JSON schema are ALL in the prompt the
coordinator gives you (produced by the runtime). Embody the persona; steel-man before countering; cite
only IDs in the slice; return ONLY the requested JSON object — no prose, no fences. You are a no-tools
leaf: do not spawn agents, coordinate, or mutate state.
```

The `name` MUST embed `<runId>` (the runtime gate rejects non-run-scoped projected agents). Then build the
`roster` JSON and capture each file's sha256:

```bash
sha256() { python3 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$1"; }
# for each expert: roster entry = {role, persona, projectedName, projectedPath, projectedSha256}
```

`projectedPath` is the path you wrote (e.g. `.claude/agents/swarm-<runId>-architect.md`); `projectedSha256`
is `sha256` of that file. Keep the roster; you'll pass it to the coordinator and reuse the paths at cleanup.

## 5. Dispatch the coordinator background session

```bash
claude --bg --agent swarm-discussion:swarm-coordinator --name "swarm-<runId>" "<packet>"
```

The `<packet>` is a prompt that gives the coordinator: `pluginRoot`, `discussionDir`, `discussionId`,
`runId`, `mode`, the `brief` JSON, and the `roster` JSON (it spawns exactly those `projectedName`s). Capture
the short session id printed as `backgrounded · <id> · swarm-<runId>`.

You hold ONLY the brief + roster, and later the synthesis — never the rounds, prompts, or fan-in.

## 6. Wait for the terminal index

Poll until the session reaches a terminal state, then read the coordinator's index file:

```bash
claude agents --json | python3 -c "import json,sys; rows=json.load(sys.stdin); print(next((r['state'] for r in rows if r.get('id')=='<id>'),'gone'))"
# when state is done/failed/stopped:
cat "<discussionDir>/coordinator-index.json"
```

Read the result from `<discussionDir>/coordinator-index.json` (deterministic). If the session ends without
that file, fall back to `claude logs <id>` and report what is known — do not invent a synthesis.

## 7. Relay the result

Present the coordinator's `recommendation`, `strongestCounter`, and `openQuestions`, and point to the
artifacts (`synthesis`, `trace`, `evidence`) under `discussionDir`. The user (with you) makes the actual
decision — the runtime never makes the product decision. On `{"ok": false, …}`, relay the reason and
`discussionDir` so the user can inspect or retry.

## 8. Tear down (always — success, failure, or abandonment)

Clean up only the run-scoped files YOU created, then finalize the projection manifest and stop the session.
Defer cleanup only while the coordinator may still be running (timeout); do it once the state is terminal.

```bash
# delete only this run's projected agents (never user/plugin agents):
rm -f .claude/agents/swarm-<runId>-*.md
# finalize deletionStatus in the manifest the coordinator wrote:
python3 - "$discussionDir/projection-manifest.json" <<'PY'
import json,sys,glob,os
p=sys.argv[1]; m=json.load(open(p))
remaining=[c["path"] for c in m.get("createdPaths",[]) if os.path.exists(c["path"])]
m["removedPaths"]=[c["path"] for c in m.get("createdPaths",[]) if not os.path.exists(c["path"])]
m["remainingPaths"]=remaining
m["deletionStatus"]="clean" if not remaining else "partial"
json.dump(m,open(p,"w"),indent=2,sort_keys=True); open(p,"a").write("\n")
PY
claude stop "<id>" 2>/dev/null || true
claude rm "<id>" 2>/dev/null || true
```

A completed run must leave NO `.claude/agents/swarm-<runId>-*` file behind and the manifest
`deletionStatus` must be `clean` (the release/certification gate checks this).

## Optional self-check

```bash
python3 "$PLUGIN_ROOT/bin/swarm_runtime_wrapper.py" validate-loop "<discussionDir>" --require-projection
```
