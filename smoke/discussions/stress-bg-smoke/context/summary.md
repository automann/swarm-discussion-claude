# Context Summary

## Topic

Should swarm-discussion experts be ephemeral per-run or a persistent registry?

## Objective

Decide the v0.4 expert-lifecycle model and the one rule that settles it.

## Operating Mode

deep

## Parent Context

v0.3 projects run-scoped experts and deletes them (zero-residue). A persistent registry has been proposed for warm-start + accumulated context.

## Constraints

- Keep run-scoped provenance certifiable.
- No cross-run contamination by default.

## Known Facts

- v0.3 cleanup is a certification gate (zero residue).
- Custom agents load only at session start.

## Success Criteria

- Pick ephemeral vs registry vs hybrid.
- Give the one decision rule.
- Name the top risk of the chosen path.

## Alignment Rule

Keep every contribution anchored to the topic, objective, constraints, known facts, and success criteria above.
