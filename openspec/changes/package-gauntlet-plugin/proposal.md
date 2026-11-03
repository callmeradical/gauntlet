# Proposal

## Why

[001 · Gauntlet plugin](../../../docs/prd/001-gauntlet-plugin.md): the gauntlet is loose files copied by hand between `~/.claude/agents`, the dotfiles, and skill folders; epsilon improvises git worktree commands each run; project specifics (ControlTower's shared `node_modules`, checks, Node rebuild) are written into general instructions; finished loops leave worktrees behind; and nothing is versioned, so other machines and running loops see whatever the files say at the moment.

**Decided (2026-11-03, 001 grilling):** a private repo `callmeradical/gauntlet` that is also its marketplace; the package follows Agent Plugins 1.0.0, with Claude Code's manifest and agents alongside; Claude Code's loose copies are removed and other tools' copies become symlinks into the repo, switched only while no loop runs; the `gauntlet` command is a portable MCP server in one standard-library Python file that also runs from a terminal; epsilon removes each slice's worktree once merged, leaving the integration worktree and anything unmerged for the user; this Mac first, then the user's other machines.

## What Changes

- **Plugin package** in `plugins/gauntlet/`: an Agent Plugins 1.0.0 `plugin.json`, the skills `intake` and `gauntlet-loop` (with the progress template inside), and `mcp.json` declaring the gauntlet server; plus Claude Code's `.claude-plugin/plugin.json`, its MCP config, and `agents/` with delta, alpha, beta, gamma, and epsilon. The repo root holds Claude Code's `.claude-plugin/marketplace.json`.
- **gauntlet MCP server and CLI** (`plugins/gauntlet/server/gauntlet.py`): tools to start a loop, update its state, create and remove worktrees, take and release merge locks, read a project's configuration, and report status; the same file answers `gauntlet status`, `gauntlet worktree rm`, and the rest from a terminal.
- **Project configuration**: `.gauntlet.json` in a project (integration branch, shared folders, checks, setup step); ControlTower gets one capturing today's facts.
- **Agents and skills updated** to use `gauntlet:<agent>` names, the server's tools instead of git steps, `${CLAUDE_PLUGIN_ROOT}` for the template, and slice cleanup after merge.
- **Setup and cutover**: a README with per-machine install; a cutover script that, only when no loop is running, backs up and removes Claude Code's loose copies and relinks other tools' copies into the repo, with a rollback.

## Capabilities

### New Capabilities
- `plugin-package`: what the plugin contains and how it conforms to Agent Plugins 1.0.0 and installs in Claude Code.
- `gauntlet-tools`: the MCP server and CLI: loops, worktrees, locks, cleanup, status.
- `project-config`: the per-project `.gauntlet.json`.
- `setup-cutover`: installing on a machine and switching from loose copies to the plugin safely.

### Modified Capabilities

## Impact

- New repo content only, plus a `.gauntlet.json` committed to ControlTower and, at cutover, changes to `~/.claude/agents`, `~/.claude/skills`, `~/.augy/skills`, and `~/.agents/agents` (backed up first).
- Publishing: creating and pushing `callmeradical/gauntlet` happens only with the user's go-ahead.
- Dependencies: Python 3 standard library and git.
