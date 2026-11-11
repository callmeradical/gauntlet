# Design

## Context

pi-subagents reads `tools` as a strict, case-sensitive allowlist and fails the run when a listed tool is not registered in the child. Its agent frontmatter (docs/agents.md in pi-subagents 0.86) has no per-harness tool key: the only tool fields are `tools` and `excludeTools`, and pi reads the same `tools` key Claude Code does. Claude Code reads `tools` and ignores frontmatter keys it does not support.

## Decisions

### Generated pi copies from one source
`plugins/gauntlet/agents/*.md` stays the Claude Code plugin's agent folder and the only file anyone edits. pi's values sit beside Claude Code's in the same frontmatter as `pi-<key>` entries (`pi-tools`, `pi-async`). `scripts/build_pi_agents.py` writes `plugins/gauntlet/pi-agents/<name>.md` with each `<key>` replaced by its `pi-<key>` value, keys set only for pi appended, `pi-*` keys dropped, and the body copied byte for byte. The copies are committed, so a clone is ready to link with no build step; `--check` (run by the tests) fails when a copy is stale.

This is the least invasive option that gives each harness only its own names: Claude Code's install is untouched, each agent still has one source file, and pi gets plain files in the documented `~/.pi/agent/agents/` location.

### pi names
- Built-ins: `Read`→`read`, `Bash`→`bash`, `Edit`→`edit`, `Write`→`write`, `Grep`→`grep`, `Glob`→`find` + `ls`.
- `Agent`→`subagent` (pi-subagents' nested launch tool); alpha starts zeta, epsilon starts every role.
- `Skill`, `WebFetch`, `WebSearch`, `SendMessage`: no entry. pi loads skills through its skill catalog; web access comes from extensions and is not part of any role's invariant; `contact_supervisor` is injected by pi-subagents.
- gauntlet MCP tools: `mcp:gauntlet/<tool>`, pi-subagents' documented direct-MCP selection, which pi-mcp-adapter registers as `gauntlet_<tool>` from the `gauntlet` server in `~/.pi/agent/mcp.json`. pi loads MCP tools only in background children, so epsilon's pi copy sets `async: true`.
- gamma and delta keep no `tools` line on either harness.

## Rejected Alternatives

- Keeping one mixed list and hiding Claude names with pi's `excludeTools`: Claude Code would still see the lowercase names, and the trick relies on undocumented ordering between exclusion and the availability check.
- pi `subagents.agentOverrides.<name>.tools` in each user's settings: per machine, outside the repo, and untested.
- A generated Claude copy instead: Claude Code's plugin layout fixes `agents/`, so the Claude files are the natural source.
- Building the copies at install time only: a clone would not be linkable without running a script, and drift would go unseen.
