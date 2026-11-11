# Reference

Back to the [README](../README.md).

## Contents

**Seven agents** (Claude Code only), installed as `gauntlet:<name>`:

| Agent | Role |
|---|---|
| `gauntlet:eta` | Audits the PRD and OpenSpec change together before slicing; returns PASS or HOLD with the single biggest gap. |
| `gauntlet:delta` | Slices an OpenSpec change into a tracer bullet plus vertical slices, each with a builder brief and a critic bar. |
| `gauntlet:alpha` | Builds one slice test-first in its own worktree. |
| `gauntlet:beta` | Reviews a slice with fresh context against its bar and returns PASS or HOLD. |
| `gauntlet:gamma` | Keeps the loop's progress page in the wiki. Reports facts and never judges. |
| `gauntlet:epsilon` | Orchestrates: runs delta, the alphas, the betas and gamma, then merges PASSed slices one at a time. |
| `gauntlet:zeta` | Answers alpha's design questions when alpha asks. It writes no code and never sees beta's bar. |

**Five skills** (Agent Skills format, used by both Claude Code and Agent Plugins clients):

| Skill | What it does |
|---|---|
| `intake` | Takes work from idea to a build-ready OpenSpec change: PRD, grilling, OpenSpec, gate. |
| `gauntlet-loop` | The loop itself, including the progress-page template in `references/progress.html`. |
| `handoff` | Writes a handoff document to `~/.local/state/gauntlet/handoffs/` so a fresh agent of the same role can continue. Adapted from `mattpocock/skills` `productivity/handoff`. |
| `tdd` | Test-driven development. Bundled from `mattpocock/skills` (see [Credits](../README.md#credits)). |
| `codebase-design` | Deep-module vocabulary for zeta. Bundled from `mattpocock/skills`. |

**The `gauntlet` server and CLI.** `plugins/gauntlet/server/gauntlet.py` is one Python file that uses only the standard library and git. Run with no arguments, it is the MCP stdio server, declared in `mcp.json` (Agent Plugins) and `.mcp.json` (Claude Code). Run with arguments, it is a terminal command that prints the same JSON the tools return. It has nine tools:

| Tool | Terminal command |
|---|---|
| `loop_start`, `loop_update`, `loop_end` | `gauntlet loop start <loop> --repo <path> --change <change>`, `gauntlet loop update <loop> ...`, `gauntlet loop end <loop> done\|stopped\|failed` |
| `worktree_new`, `worktree_rm` | `gauntlet worktree new <loop> <slice>`, `gauntlet worktree rm <loop> [<slice>]` |
| `lock_acquire`, `lock_release` | `gauntlet lock acquire <loop>`, `gauntlet lock release <loop>` |
| `config_read` | `gauntlet config <repo>` |
| `status` | `gauntlet status` |

`loop_update` also takes `handoff` (`--handoff <path>`): it appends `{path, at, slice?}` to the loop's `handoffs` list, so the loop state records every context handoff.

**Context handoffs.** Every agent definition and the `gauntlet-loop` skill carry a "Context handoffs" rule. At `handoff.context_threshold` (default 0.65) of its context, a role stops at a clean point (finishes or reverts the step, restores temporary mutations, kills its own hung processes), writes a handoff with the `handoff` skill, and hands over to a successor of the same role, prompted only with "Continue from handoff <path>". Builders, critics, delta, gamma and zeta report the path to epsilon, which launches the successor and records it with `loop_update`; epsilon starts its own successor and records its handoff the same way. A critic about to hand off reports "incomplete" plus the path, never a verdict from partial evidence, and its successor redoes every bar item whose evidence is not recorded. Each handoff is announced in the coordination channel, if any.

**Tool names.** Agents with a `tools` line list both the Claude Code names (`Read`, `Bash`, ...) and pi's lowercase built-ins (`read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`), so they launch under pi-subagents too; read-only agents (eta, zeta) get only pi's read-only tools.

Loop state and merge locks live in `~/.local/state/gauntlet/`, outside the plugin, so updates and every client share them.


## Layout

```
.claude-plugin/marketplace.json     Claude Code marketplace "gauntlet", source ./plugins/gauntlet
plugins/gauntlet/
  plugin.json, mcp.json             Agent Plugins 1.0.0
  .claude-plugin/plugin.json        Claude Code manifest
  .mcp.json                         Claude Code MCP config
  agents/                           the seven agents
  skills/                           the five skills
  server/gauntlet.py                MCP server and CLI
scripts/cutover.py                  switches a machine from loose copies to the plugin
examples/controltower.gauntlet.json ControlTower's project config
tests/                              python3 -m unittest discover -s tests
```
