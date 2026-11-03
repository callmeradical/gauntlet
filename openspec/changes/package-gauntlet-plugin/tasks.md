# Tasks

## 1. Server core

- [ ] 1.1 `server/gauntlet.py` state and config: atomic loop state files, loop id validation, duplicate id/change refusal, `.gauntlet.json` reading with per-field errors; verify with `python3 -m unittest` tests using temp state dirs and temp repos
- [ ] 1.2 Worktrees and locks: `worktree_new` (path and branch naming, shared-folder links excluded via the worktree's `info/exclude`), `worktree_rm` (refuses unmerged branches, reports kept ones), `lock_acquire`/`lock_release` (O_EXCL, 30-minute staleness, holder-only release); verify with tests on temp git repos including an unmerged slice and a stale lock, and that `git status` shows the shared link as ignored
- [ ] 1.3 `status` (loops, worktrees, locks, finished loops with leftovers) and the CLI subcommands over the same functions; verify with tests comparing CLI output to tool results

## 2. MCP protocol

- [ ] 2.1 JSON-RPC stdio loop: initialize, initialized notification, tools/list with input schemas, tools/call with text content and `isError`; verify with a test that spawns the server, sends real messages, and calls every tool

## 3. Package

- [ ] 3.1 Agent Plugins files: `plugins/gauntlet/plugin.json` and `mcp.json`; Claude Code files: `.claude-plugin/marketplace.json`, `plugins/gauntlet/.claude-plugin/plugin.json`, `.mcp.json`; verify by validating the Agent Plugins files against the 1.0.0 schemas (vendored copies, standard-library check of required fields and patterns) and a test that both MCP files declare the same server
- [ ] 3.2 Skills: move intake and gauntlet-loop into `skills/` with the template under `skills/gauntlet-loop/references/`, updated for `gauntlet:` names and the server's tools; verify with a test that skill folders contain `SKILL.md` with valid frontmatter and no `~/.agents` or `~/.claude` paths
- [ ] 3.3 Agents: copy the five definitions into `agents/`, update for `gauntlet:` names, server tools, slice cleanup after merge, `config_read` checks, and the template via `${CLAUDE_PLUGIN_ROOT}`; de-personify alpha and beta; verify with a test for frontmatter names, `Agent` in epsilon's tools, and no "You are" phrasing or home-folder paths
- [ ] 3.4 Smoke test: `claude --plugin-dir plugins/gauntlet` lists the five `gauntlet:` agents, both skills, and the server's tools; verify by running it non-interactively and recording the output in the PR notes

## 4. Setup and cutover

- [ ] 4.1 `scripts/cutover.py` with `--dry-run`, refusal while loops run, backup manifest, removals, symlinks, and `--rollback`; verify with tests against a fake home directory
- [ ] 4.2 README: what the gauntlet is, per-machine install (GitHub access, marketplace add, install, PATH link, cutover), updating only between loops; verify the steps by following them on this Mac during cutover (task 5.2)
- [ ] 4.3 ControlTower `.gauntlet.json` drafted in the repo's `examples/controltower.gauntlet.json`; verify `config_read` accepts it

## 5. Release (user go-ahead required)

- [ ] 5.1 Create private `callmeradical/gauntlet`, push, add marketplace and install on this Mac *(needs the user's go-ahead)*
- [ ] 5.2 When no loop runs: cutover dry-run, cutover, and commit ControlTower's `.gauntlet.json`; verify `gauntlet:*` agents resolve and `gauntlet status` works *(needs the user's go-ahead)*
