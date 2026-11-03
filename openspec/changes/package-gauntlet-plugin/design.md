# Design

## Context

Today's sources: agents in `~/.claude/agents/{alpha,beta,gamma,delta,epsilon}.md` (mirrored to `~/.agents/agents/`); skills in `~/.augy/skills/{intake,gauntlet-loop}` linked from `~/.claude/skills/` and `~/.opencode/skills/`; template at `~/.agents/templates/progress.html`; loop state in `~/.local/state/gauntlet/<loop>.json` written by epsilon by hand. Claude Code plugin facts (code.claude.com plugin docs): `.claude-plugin/plugin.json` (only `name` required) and `.claude-plugin/marketplace.json` (`name`, `owner`, `plugins[{name, source}]`); the documented same-repo layout is `plugins/<name>/` with `"source": "./plugins/<name>"`; plugin agents are namespaced `<plugin>:<name>` and lose to `~/.claude/agents` copies; `${CLAUDE_PLUGIN_ROOT}` is substituted in agent/skill markdown and MCP args but is not in the Bash environment; plugin agents may spawn subagents (default depth 3) if `Agent` is in their tools; `plugin.json` `frontmatter` fields `permissionMode`, `hooks`, `mcpServers`, `initialPrompt` are ignored for plugin agents; with a `version` set, users get updates only when it changes. Agent Plugins 1.0.0 facts: root `plugin.json` with `$schema` and `name` (closed schema: `additionalProperties: false`, so unknown fields fail validation), `skills/<name>/SKILL.md` discovered one level deep, `mcp.json` with `$schema` and `mcpServers` (`type: stdio`, `command`, `args`, `env`, `cwd`), `${PLUGIN_ROOT}` expanded only in stdio `args`, `env` values, and `cwd`.

## Goals / Non-Goals

**Goals:**
- One plugin directory valid for both formats, with skills written once.
- Deterministic loop mechanics in code; agents only orchestrate.

**Non-Goals:**
- Changing gauntlet behavior (roles, intake, gate, verdict rules).
- Hooks, commands, or MCP resources; a team or public release.

## Decisions

- **Layout.**
  ```
  .claude-plugin/marketplace.json          # Claude Code marketplace, source ./plugins/gauntlet
  plugins/gauntlet/
    plugin.json                            # Agent Plugins 1.0.0
    mcp.json                               # Agent Plugins MCP: python3 ${PLUGIN_ROOT}/server/gauntlet.py
    .claude-plugin/plugin.json             # Claude Code manifest (name, version, description, mcpServers → ./.mcp.json)
    .mcp.json                              # Claude Code MCP: python3 ${CLAUDE_PLUGIN_ROOT}/server/gauntlet.py
    agents/{alpha,beta,gamma,delta,epsilon,zeta}.md
    skills/intake/SKILL.md
    skills/gauntlet-loop/SKILL.md
    skills/gauntlet-loop/references/progress.html
    skills/tdd/{SKILL.md,LICENSE,references/{tests,mocking}.md}
    skills/codebase-design/{SKILL.md,LICENSE,references/{DEEPENING,DESIGN-IT-TWICE}.md}
    server/gauntlet.py
  docs/prd/, openspec/, README.md, scripts/cutover.py, tests/
  ```
  Two MCP files because each format expands a different root variable; a test asserts they declare the same server and arguments. Alternative considered: plugin at the repo root. Rejected: the docs only confirm the `plugins/<name>/` same-repo layout, and it keeps repo docs and tests out of the installed plugin.
- **Server: one standard-library Python file.** JSON-RPC 2.0 over stdio with newline-delimited messages: `initialize` (protocol version echoed from the client, `capabilities.tools`), `notifications/initialized`, `tools/list`, `tools/call` returning `content: [{type: "text", text: <json>}]` and `isError` on failure. Tools: `loop_start`, `loop_update`, `loop_end`, `worktree_new`, `worktree_rm`, `lock_acquire`, `lock_release`, `config_read`, `status`. The same functions back an `argparse` CLI when run with arguments (`status`, `worktree new|rm`, `lock acquire|release`, `loop start|update|end`, `config`). Alternative considered: the MCP Python SDK. Rejected: a dependency the plugin can't install everywhere.
- **State.** `~/.local/state/gauntlet/<loop>.json` (schema version, id, repo, change, integration branch, integration worktree, phase, status, slices{name: {worktree, branch, status, round, commit, verdict}}, timestamps), written atomically (temp file + rename). Locks are `~/.local/state/gauntlet/<repo>--<branch>.lock` created with `O_EXCL`, holding loop id and time; stale after 30 minutes. Kept outside the plugin so updates and other clients share it.
- **Worktrees.** `git -C <integration worktree> worktree add -b gauntlet/<loop>/<slice> <path> <integration-branch>`; shared folders are symlinked and added as anchored `/<folder>` entries to the repo's common `info/exclude` (found with `git rev-parse --git-path info/exclude`; git ignores a per-worktree `info/exclude`) so they're ignored without touching the project's `.gitignore`. Removal checks `git rev-list <integration>..<branch>` is empty, then `git worktree remove` and `git branch -d`.
- **Agents.** Copied from today's definitions, then edited: `gauntlet:` names; epsilon calls the server's tools for loop/worktree/lock/cleanup, removes each slice's worktree after merge, reads checks and setup from `config_read`, and keeps the intake-gate preconditions; gamma reads the template at `${CLAUDE_PLUGIN_ROOT}/skills/gauntlet-loop/references/progress.html`; epsilon's frontmatter lists `Agent` among its tools. alpha and beta are de-personified to match the directive style (the user's rule for agent definitions).
- **zeta and nesting depth.** alpha's frontmatter gains `Agent` in its tools, and its directive limits it to starting `gauntlet:zeta`; zeta's frontmatter omits `Agent`. The chain main → epsilon → alpha → zeta is three levels, Claude Code's default maximum, so zeta must never spawn. beta's tools omit `Agent`. Alternative considered: zeta as a skill alpha reads. Rejected: the user asked for an agent alpha can talk to, and a separate context keeps design advice from crowding alpha's build context.
- **Third-party skills.** `tdd` and `codebase-design` are copied from `mattpocock/skills` at a recorded commit, with reference files moved to `references/` (Agent Skills layout) and links rewritten; each folder gets the MIT `LICENSE` and a source line at the end of the `SKILL.md` body (the frontmatter description is unchanged). alpha's TDD text is one directive pointing at `tdd` plus the seam and refactor overrides; no summary.
- **Cutover script** (`scripts/cutover.py`, standard library): refuses if `status` shows a running loop; backs up targets to `~/.local/state/gauntlet/cutover-<timestamp>/` with a manifest; removes the Claude Code loose copies; replaces other tools' copies with symlinks into the repo checkout; `--rollback <dir>` restores from the manifest. `--dry-run` prints the plan.
- **PATH for the terminal.** README tells the user to link `~/.local/bin/gauntlet` to the repo's `server/gauntlet.py` (executable, `#!/usr/bin/env python3`).

## Risks / Trade-offs

- [Claude Code may not accept a stdio entry with Agent Plugins' extra `type` field] → Claude Code uses its own `.mcp.json`; only the Agent Plugins file carries `$schema`/`type`.
- [Hand-rolled MCP drifts from the protocol] → Tests drive the server over stdio with real JSON-RPC messages, and a smoke test loads the plugin in Claude Code with `--plugin-dir`.
- [Cutover touches the user's live setup] → Refuses while loops run, dry-run first, full backup and rollback.
- [Agents de-personified changes alpha/beta wording] → Behavior unchanged; reviewed by beta against today's definitions.

## Migration Plan

1. Build and test in the repo; load with `claude --plugin-dir plugins/gauntlet` and smoke-test.
2. With the user's go-ahead: create private `callmeradical/gauntlet` and push.
3. On this Mac: add the marketplace, install, link `~/.local/bin/gauntlet`.
4. When `gauntlet status` shows no running loop: `scripts/cutover.py --dry-run`, then run it. Rollback: `--rollback <backup dir>` and uninstall the plugin.
5. Commit ControlTower's `.gauntlet.json` (after its running loop ends).
6. Later: the other machines per the README.
