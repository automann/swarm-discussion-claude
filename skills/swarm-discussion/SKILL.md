---
name: swarm-discussion
description: |
  Summon a group of experts to debate a hard, open question OUTSIDE your context window, then act on
  their synthesis. Use when the user faces a complex decision, design trade-off, architecture choice, or
  review that benefits from multiple expert perspectives with designed tension and a quality gate. The
  discussion runs inside a spawned orchestrator sub-agent; you receive only the final synthesis and
  artifact paths — not the discussion mechanics.
---

# swarm-discussion

This skill is deliberately THIN. You (the parent agent) do NOT run the discussion protocol. You collect a
brief, spawn ONE `swarm-orchestrator` sub-agent that runs the entire discussion in its own context, wait,
and relay its synthesis. All protocol mechanics live in the orchestrator and the vendored runtime.

## 1. Resolve the plugin root

Find the installed plugin directory (it contains `bin/swarm_runtime_wrapper.py`, `agents/`, and
`vendor/swarm-runtime/`). This SKILL.md lives at `<pluginRoot>/skills/swarm-discussion/SKILL.md`, so:

```bash
# Prefer the known install layout; fall back to a search.
PLUGIN_ROOT="${SWARM_DISCUSSION_PLUGIN_ROOT:-}"
if [ -z "$PLUGIN_ROOT" ]; then
  PLUGIN_ROOT="$(find "$HOME/.claude" -type f -path '*swarm-discussion*/bin/swarm_runtime_wrapper.py' 2>/dev/null | sort -V | tail -1 | sed 's#/bin/swarm_runtime_wrapper.py$##')"
fi
echo "$PLUGIN_ROOT"
```

`echo "$PLUGIN_ROOT"` must print a directory containing `bin/swarm_runtime_wrapper.py`. If it is empty,
stop and tell the user the plugin is not installed correctly.

## 2. Preflight

```bash
python3 "$PLUGIN_ROOT/bin/swarm_runtime_wrapper.py" doctor --smoke-fixture
```

Stop if this fails — it proves the vendored runtime contract and runs the bundled fixture through the
gates without touching the user's workspace. Read `hostNesting.supported` from the output:

- `true` → use the nested path below (the normal case on Claude Code ≥ 2.1.172).
- `false` / `null` → the host caps sub-agent nesting; tell the user the orchestrator-as-sub-agent shape
  is unavailable on this host and stop (do NOT silently run the whole protocol inline in this thread —
  that re-pollutes the parent context the skill exists to protect).

## 3. Assemble the brief

From the user's request, build a compact brief JSON (do not dump the whole conversation):

```json
{
  "topic": "<short title>",
  "objective": "<the single decision the user needs>",
  "mode": "lightweight | standard | deep",
  "parentContext": "<background an expert needs to avoid intent drift: origin, who is affected, what was tried>",
  "constraints": ["<hard boundaries>"],
  "knownFacts": ["<verified data points>"],
  "successCriteria": ["<what a useful synthesis must answer>"]
}
```

Pick a `discussionId` (slug) and set `discussionDir` to `./.swarm/discussions/<discussionId>` in the
user's workspace. Pick `mode` from the question's weight (quick call → lightweight).

## 4. Spawn the orchestrator and wait

Use the Agent tool with `subagent_type: swarm-orchestrator`. Pass it, in the prompt: `pluginRoot`,
`discussionDir`, `discussionId`, `mode`, and the brief JSON. Then wait for it to return.

You hold ONLY the brief and, after it returns, the synthesis — never the rounds, prompts, or fan-in.

## 5. Relay the result

Present the orchestrator's `recommendation`, `strongestCounter`, and `openQuestions` to the user, and
point to the artifacts (`synthesis`, `trace`, `evidence`) under `discussionDir`. The user (with you) then
makes the actual decision or next step — the runtime never makes the product decision.

If the orchestrator returns `{"ok": false, ...}`, relay the reason and the `discussionDir` so the user can
inspect artifacts or retry. Optionally self-check a completed discussion:

```bash
python3 "$PLUGIN_ROOT/bin/swarm_runtime_wrapper.py" adapter-smoke --dir "<discussionDir>"
```
