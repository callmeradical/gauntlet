# Tasks

## 1. Server core

- [x] 1.1 `server/gauntlet.py` state and config: atomic loop state files, loop id validation, duplicate id/change refusal, `.gauntlet.json` reading with per-field errors; verify with `python3 -m unittest` tests using temp state dirs and temp repos
- [x] 1.2 Worktrees and locks: `worktree_new` (path and branch naming, shared-folder links excluded via the worktree's `info/exclude`), `worktree_rm` (refuses unmerged branches, reports kept ones), `lock_acquire`/`lock_release` (O_EXCL, 30-minute staleness, holder-only release); verify with tests on temp git repos including an unmerged slice and a stale lock, and that `git status` shows the shared link as ignored
- [x] 1.3 `status` (loops, worktrees, locks, finished loops with leftovers) and the CLI subcommands over the same functions; verify with tests comparing CLI output to tool results

## 2. MCP protocol

- [x] 2.1 JSON-RPC stdio loop: initialize, initialized notification, tools/list with input schemas, tools/call with text content and `isError`; verify with a test that spawns the server, sends real messages, and calls every tool

## 3. Package

- [x] 3.1 Agent Plugins files: `plugins/gauntlet/plugin.json` and `mcp.json`; Claude Code files: `.claude-plugin/marketplace.json`, `plugins/gauntlet/.claude-plugin/plugin.json`, `.mcp.json`; verify by validating the Agent Plugins files against the 1.0.0 schemas (vendored copies, standard-library check of required fields and patterns) and a test that both MCP files declare the same server
- [x] 3.2 Skills: move intake and gauntlet-loop into `skills/` with the template under `skills/gauntlet-loop/references/`, updated for `gauntlet:` names and the server's tools; verify with a test that skill folders contain `SKILL.md` with valid frontmatter and no `~/.agents` or `~/.claude` paths
- [x] 3.3 Agents: copy the five definitions into `agents/`, update for `gauntlet:` names, server tools, slice cleanup after merge, `config_read` checks, and the template via `${CLAUDE_PLUGIN_ROOT}`; de-personify alpha and beta; alpha follows `tdd` with the OpenSpec-seam and refactor-on-feedback overrides and knows when and how to consult zeta; beta's bar includes scenario coverage and the tdd anti-patterns; verify with a test for frontmatter names, `Agent` in epsilon's and alpha's tools and not in beta's or zeta's, the zeta and tdd references, and no "You are" phrasing or home-folder paths
- [ ] 3.3a zeta: write `agents/zeta.md` (answer-only, repo-first grounding with file citations, `codebase-design` vocabulary, no writes, no spawning, no contact with beta); verify with the same definition test and a manual round where alpha asks one composition question in a scratch repo
- [x] 3.3b Bundle `tdd` and `codebase-design` from `mattpocock/skills` at a recorded commit (reference files under `references/`, links rewritten, MIT `LICENSE`, source attribution); verify with a test that links resolve inside the plugin and each folder has the license
- [x] 3.4 Smoke test: `claude --plugin-dir plugins/gauntlet` lists the six `gauntlet:` agents, the four skills, and the server's tools; verify by running it non-interactively and recording the output in the PR notes *(2026-11-03, main session: `claude plugin validate` passes for plugin and marketplace; `claude -p --plugin-dir plugins/gauntlet` lists gauntlet:alpha, beta, delta, epsilon, gamma, zeta; skills gauntlet:intake, gauntlet-loop, tdd, codebase-design; nine tools mcp__plugin_gauntlet_gauntlet__{config_read,lock_acquire,lock_release,loop_end,loop_start,loop_update,status,worktree_new,worktree_rm}, each once)*

## 4. Setup and cutover

- [x] 4.1 `scripts/cutover.py` with `--dry-run`, refusal while loops run, backup manifest, removals, symlinks, and `--rollback`; verify with tests against a fake home directory
- [x] 4.2 README: what the gauntlet is, per-machine install (GitHub access, marketplace add, install, PATH link, cutover), updating only between loops; verify the steps by following them on this Mac during cutover (task 5.2; written and tested in the repo, follow-through pending 5.2)
- [x] 4.3 ControlTower `.gauntlet.json` drafted in the repo's `examples/controltower.gauntlet.json`; verify `config_read` accepts it

## 5. Release (user go-ahead required)

- [ ] 5.1 Create public `callmeradical/gauntlet` (MIT), push, add marketplace and install on this Mac *(needs the user's go-ahead)*
- [ ] 5.2 When no loop runs: cutover dry-run, cutover, and commit ControlTower's `.gauntlet.json`; verify `gauntlet:*` agents resolve and `gauntlet status` works *(needs the user's go-ahead)*
