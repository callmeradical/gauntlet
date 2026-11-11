# Proposal

## Why

[005 · Per-harness tool lists](../../../docs/prd/005-per-harness-tool-lists.md): each agent's `tools` line mixes Claude Code and pi names, so pi-subagents fails every launch with "requested unavailable child tools", and Claude Code sees names it does not know.

## What Changes

- `plugins/gauntlet/agents/*.md` (Claude Code, the source): `tools` holds only Claude Code names; a new `pi-tools` key holds pi's list, and `pi-async` sets pi-only options. Claude Code ignores keys it does not support.
- New `scripts/build_pi_agents.py` generates `plugins/gauntlet/pi-agents/*.md`, replacing each `<key>` with its `pi-<key>` value and copying the body unchanged; `--check` reports stale copies.
- epsilon on pi: `mcp:gauntlet/<tool>` for every server tool, `subagent`, and `async: true`. alpha on pi: `subagent`.
- Tests: `tests/test_harness_tools.py`; the tool assertions in `test_agents.py`, `test_eta.py`, `test_zeta.py` and `test_handoff.py` follow the split.
- Docs: install (pi links `pi-agents/`), reference, development, README.

## Capabilities

### New Capabilities
- `per-harness-agent-tools`: per-harness tool lists, the generated pi copies, and their freshness check.

### Modified Capabilities

The `add-context-handoff` requirement "Agents launch on pi" now applies to the generated pi copies, which replace 003 D3's mixed list.

## Impact

pi users must relink `~/.pi/agent/agents/*.md` from `plugins/gauntlet/agents/` to `plugins/gauntlet/pi-agents/`. Claude Code behaviour is unchanged apart from dropping the lowercase names.
