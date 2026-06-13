# Synthesis — Config layout for a small CLI tool

**Mode:** lightweight · **Round:** 1 · **Discussion:** cert-config-layout

## Recommendation

Use **one hand-editable config file** with a namespaced `[commands.<name>]` section per
subcommand, loaded by a single parse-then-merge-with-defaults pass (r1-msg-001).

**Main trade-off:** loader simplicity and a single source of truth — one parse, one
precedence story (defaults < file < env/flags), and additive growth from ~6 to ~12
subcommands — *versus* the hand-editing and merge-review ergonomics of one file that keeps
growing. The decision is asymmetric: one-to-many is a safe additive split later, whereas
many-to-one is the breaking direction (r1-msg-001), so single-file is the lower-regret
default under the "no breaking changes after release" constraint.

## Strongest objection to the chosen option

The load-bearing risk is **not file count but merge-with-defaults semantics** (r1-msg-002).
Once defaults live in code, the one "authoritative" file is only half the truth. Concrete
failure: a replace-style merge on a list key (e.g. `exclude`) silently drops the shipped
defaults the moment a user adds a single entry — nothing errors, and the file looks correct.
The only clean fix, switching that key to list-merge, changes the observed config of every
existing user and so itself violates "no breaking changes."

## Resolution within the single-file design (r1-msg-003)

The architect conceded the point and resolved it without abandoning single-file:

- **Freeze the per-key merge contract at v1:** defaults fill only omitted keys; any key the
  user writes wins verbatim, lists included (replace, never element-merge). Document it as a
  stability guarantee so it never has to change.
- **Ship a materialized default config** on first run (or shipped commented defaults) so every
  list is fully visible and editable — "add one entry" becomes "edit the full list,"
  eliminating the silent-drop failure without any list-merge logic.
- **Preserve unknown sections/keys** on load with a non-fatal warning, keeping growth additive.

Accepted residual cost: forward-only **upgrade drift** — new default list entries shipped in
later releases do not reach users who pinned that list. This is explicit and one-directional,
unlike the un-undoable, breaking switch that list-merge would later force.

## Agreements

- A single namespaced config file is the right default for a 6-to-12 command single-binary
  CLI; growth stays additive (architect + contrarian, resolved by argument — r1-msg-001,
  r1-msg-002, r1-msg-003).

## Open questions

- Must new default list entries shipped in later releases reach users who customized that
  list? If yes, plain replace is insufficient and versioned-default migration must be decided
  **before** v1 freezes the merge contract (r1-msg-003).
- Does "preserve unknown sections" extend to unknown keys inside a known section, and to user
  comments and key ordering on write-back (r1-msg-002)?

## Argument graph

- r1-msg-002 **counters** r1-msg-001 (merge semantics, not file count, is the hazard)
- r1-msg-003 **extends** r1-msg-001 (specifies the previously underspecified merge contract)
- r1-msg-003 **supports** r1-msg-002 (concedes and resolves the contrarian's objection)
