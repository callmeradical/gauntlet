# Design

## Decisions

### Handoff skill
`skills/handoff/SKILL.md` writes `~/.local/state/gauntlet/handoffs/<loop-or-pane>-<role>-<YYYYmmdd-HHMM>.md` and ends with a "Suggested skills" section.

### Threshold
`.gauntlet.json` `handoff` is an object with only `context_threshold`, a number strictly between 0 and 1 (booleans rejected). `config_read` always returns `handoff` with the default `0.65` filled in; problems are reported as `handoff` or `handoff.<key>` in `config_invalid.fields`.

### Recording
`loop_update(loop, ..., handoff=<path>)` appends `{"path", "at"[, "slice"]}` to the state's `handoffs` list. CLI: `gauntlet loop update <loop> --handoff <path> [--slice <s>]`. The path is not checked for existence: the file lives on the agent's machine and the server only records it.

### pi tool names
pi-subagents treats `tools` as a strict allowlist of pi tool names (`read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`). Each agent with a `tools` line also lists the pi equivalent of its Claude Code tools (`Glob` maps to `find` and `ls`). eta and zeta get only read-only pi tools.

## Rejected Alternatives

- Giving eta `Bash` as beta has: it breaks eta's read-only contract.
- A separate per-slice handoff field: one list on the loop, tagged with the slice, is enough for `status` and gamma.
