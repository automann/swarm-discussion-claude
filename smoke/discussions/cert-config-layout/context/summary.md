# Context Summary

## Topic

Config layout for a small CLI tool

## Objective

Decide whether a small CLI tool should keep all configuration in one file or split it across per-command files.

## Operating Mode

lightweight

## Discussion ID

cert-config-layout

## Parent Context

A single-binary CLI with ~6 subcommands is adding user configuration. The team is split between one config file and per-command files. The decision is needed before the config loader is written.

## Constraints

- No breaking changes after release
- Config must be hand-editable
- Keep the loader simple

## Known Facts

- ~6 subcommands today
- expected to grow to ~12 within a year

## Success Criteria

- A clear recommendation naming the main trade-off
- The strongest objection to the chosen option

## Alignment Rule

Keep every contribution anchored to the topic, objective, constraints, known facts, and success criteria above.
