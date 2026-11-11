# Proposal

## Why

[003 · Context handoffs](../../../docs/prd/003-context-handoff.md): gauntlet roles run out of context mid-task, a critic can then judge from partial evidence, and agents with Claude-only tool names do not launch on pi.

## What Changes

- New skill `plugins/gauntlet/skills/handoff/SKILL.md`, adapted from mattpocock/skills `productivity/handoff`.
- A "Context handoffs" section in all seven agents and in the `gauntlet-loop` skill.
- `.gauntlet.json` gains `handoff.context_threshold` (default 0.65), validated by `config_read`.
- `loop_update` gains `handoff` (a path), appended to the loop state's `handoffs` list.
- Agents with a `tools` line also list pi's lowercase built-ins.
- Docs: README, reference, install, configuration.

## Capabilities

### New Capabilities
- `context-handoff`: the handoff skill, the per-role rule, the threshold, and recording handoffs in loop state.

### Modified Capabilities

## Impact

Additive: a new optional config key and a new optional `loop_update` argument. `config_read` output gains `handoff`. No migration.
