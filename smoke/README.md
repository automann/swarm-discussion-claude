# Host-Native Smoke

This directory holds a real Claude-driven discussion produced by this adapter
and used to certify it (ADAPTER-SPEC deliverable 6).

## `discussions/cert-config-layout`

A lightweight discussion ("config layout for a small CLI tool", 2 personas, 1
round, 3 messages) driven end to end through the nested orchestrator topology:
a `general-purpose` sub-agent following `agents/swarm-orchestrator.md` ran the
runtime loop and spawned the two persona experts as its own sub-agents (depth
2), fanning their results back through the transport path. All 20 runtime
commands returned ok; message ids, argument graph, and synthesis are genuine
runtime output.

### Certification (re-runnable)

From a checkout of the runtime repo:

```bash
python3 <runtime-repo>/conformance/certify_adapter.py \
  --discussion <this-repo>/smoke/discussions/cert-config-layout \
  --vendored  <this-repo>/vendor/swarm-runtime \
  --runtime   <this-repo>/vendor/swarm-runtime/runtime/swarm_rt.py
```

Result on 2026-06-11 against vendored runtime `bed47da`: **CERTIFIED** — all
five gates pass (`runtime-contract`, `vendor-manifest`, `adapter-smoke`,
`validate-loop`, `validate-discussion`).

### Notes / known v1 untidiness

- The personas were spawned as `general-purpose` (the `swarm-expert` plugin
  type is not registered unless the plugin is installed). The artifact tree —
  what certification checks — is identical; this run does not exercise plugin
  packaging/registration.
- The orchestrator wrote its temp spawn-order inputs at
  `transport/r001-*-spawn-order.json` (root of `transport/`) rather than under
  `tmp/`. Harmless (certification passes), but a future orchestrator-prompt
  refinement should place transient inputs under `tmp/`.
