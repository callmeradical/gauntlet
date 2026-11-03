# Slice plan: `package-gauntlet-plugin` (loop `gauntlet-plugin`, `main` at 119b7e6)

The plan has a tracer and eight slices that can run in parallel after it. It is in two parts so you can save Part 1 without the bars:

- **Part 1** (save as `slices.gauntlet-plugin.md`): findings, contracts, briefs, merge plan, integration step, questions.
- **Part 2** (critic bars): kept outside the repo for beta only.

---

# Plan and builder briefs

## Where the spec and the code disagree

I checked these against the live files.

1. **design.md's `info/exclude` approach doesn't work, and that is a design error.** I built a temp repo to test it. Git ignores `info/exclude` inside a worktree's own git dir (`.git/worktrees/<id>/info/exclude`). `git rev-parse --git-path info/exclude` points to the common dir's file, and only that file worked (`!! node_modules`). A `.gitignore` entry of `node_modules/` with a trailing slash does not match a symlink, so a test without the exclude passes only if its fixture is wrong. See Q2.
2. **The live state folder already has hand-written loop files the server must read.** The files are:
   - `~/.local/state/gauntlet/pri-fixes.json` (running)
   - `gauntlet-plugin.json` (this loop, running)
   - `wiki-ask.json` (done)

   They key the loop id as `loop` (not `id`), have no schema version, and carry extra keys (`project`, `events`, `plan`, `integration_worktree`, `baseline`...). The folder also holds non-loop files: `*.bar.*.md`, `*.brief.*.md`, `*.plan-full.md`. If status, the duplicate check, or the cutover's refusal miss these files, the cutover could run while `pri-fixes` is live.
3. **Lock file names break on branches with slashes.** `<repo>--<branch>.lock` with ControlTower's `feat/decision-tree` contains a `/`. See Q3.
4. **The caller supplies the integration worktree, and it can be shared.** ControlTower's is `~/Dev/controltower-decision-tree`, a linked worktree several loops use. No tool creates it. The spec's "remove a loop's worktrees" plus the status scenario "integration worktree remains" leave unsaid whether `worktree rm <loop>` removes it. See Q1.
5. **The third-party skills at `mattpocock/skills@4ae2317ddb22b046e26455e4f9c9b3aaaf62212d` don't match the design's layout cleanly.**
   - Each folder also has `agents/openai.yaml`, which the layout doesn't mention.
   - `tdd/SKILL.md` says "confirm [seams] with the user" and sends refactoring to a `code-review` skill that isn't bundled.
   - `DESIGN-IT-TWICE.md` starts parallel sub-agents, which zeta can't do at depth 3.
6. **The Agent Plugins `plugin.schema.json` is closed.** It has `additionalProperties: false` and requires only `$schema` and `name`; `author` is an object. design.md says "unknown fields ignored", but the schema rejects them. The spec separately requires version, description, author, repository and license.
7. **Loose `~/.claude/skills/tdd` and `~/.claude/skills/codebase-design` links exist.** The cutover spec doesn't cover them. See Q12.
8. **`/usr/bin/python3` is 3.9.6** (Homebrew's is 3.14.7), so 3.9 is the realistic minimum.
9. **Today alpha, beta and epsilon have no `tools:` line, so they inherit every tool.** The design's "Agent in tools" means writing explicit lists, which takes tools away (Skill, MCP tools). See Q8.
10. **Task 3.3's "no home-folder paths" clashes with legitimate paths.** gamma writes `~/wiki/features/...`, and the state folder is `~/.local/state/gauntlet`. See Q9.
11. **Task 3.3a's "manual round" needs the plugin loaded,** which is task 3.4 and outside slice scope. It moves to the main session.

## Shared environment (part of every brief)

- **Worktree:** `~/Dev/gauntlet-gauntlet-plugin-<slice>` on branch `gauntlet/gauntlet-plugin/<slice>`, branched off `main` after the tracer merges. Commit only there; never push, publish, install, or run the cutover against the real home.
- **Runtime:** Python 3 standard library and git only, and it must run on Python 3.9: no `match`, no runtime `X | Y` types, no `tomllib`.
- **Checks, all of which must pass:**
  - `python3 -m unittest discover -s tests -v`, and the same with `/usr/bin/python3`
  - `python3 -m py_compile` on every script
  - `openspec validate package-gauntlet-plugin --strict`
- **Test isolation:** tests use temp dirs, temp git repos and a fake `HOME` from `tests/helpers.py`.
  - Never touch the real `~/.claude`, `~/.augy`, `~/.agents`, `~/wiki` or `~/.local/state/gauntlet`. Two live loops are writing there now.
  - No network in tests.
- **Read-only sources:** `~/.claude/agents/*.md`, `~/.augy/skills/{intake,gauntlet-loop}/SKILL.md`, `~/.agents/templates/progress.html`, and `mattpocock/skills` via `gh api` at `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`.
- **File ownership:** edit only the files your slice lists. `tests/helpers.py` belongs to the tracer; put any extra helpers in your own test file.
- **Style:** agent definitions are task directives with no persona ("You are...").
- **Commits:** conventional commits ending with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **No shared folders:** no symlinked folders and no `node_modules` here.
- **Seams under test:** the OpenSpec scenarios each slice lists, plus the interfaces in the contract below. Don't confirm seams with anyone.
- **Spec gaps:** if a question below is still open when you reach it, stop and report it rather than guessing.

## Shared contracts (the tracer lays these down; everything else is briefed against them)

**Plugin identity.** Name `gauntlet`, version `0.1.0` (Q13), marketplace name `gauntlet`. The server constant `VERSION` equals the version in both manifests.

**Server module `plugins/gauntlet/server/gauntlet.py`** (executable, `#!/usr/bin/env python3`, one file):

- **Calling.** Public functions have the same names as the tools, with keyword arguments matching each tool's input schema. They return plain dicts and raise `GauntletError(code, message, **details)`.
- **Public helpers:**
  - `state_dir()`: `$HOME/.local/state/gauntlet`, read on every call
  - `load_loop(loop)`
  - `save_loop(state)`: atomic, temp file in the same dir then `os.replace`
  - `list_loops()`: every `*.json` in the state dir that has a `loop` key, legacy files included; skips directories, `.lock` files and `.md` files
  - `running_loops()`
  - `main_worktree(path)`: absolute path of the repo's main worktree, found from `--git-common-dir`
- **Modes.** With no arguments it runs as the MCP stdio server. With arguments it runs as the argparse CLI. The CLI prints the tool's result as indented JSON to stdout (Q7), or the error JSON to stderr with exit code 1.
- **File layout.** The file is split into banner-delimited sections in this order:
  1. `core` (tracer)
  2. `worktrees` (owned by the worktrees slice)
  3. `locks` (owned by locks-status)
  4. `status` (owned by locks-status)
  5. `registry + MCP + CLI` (tracer)

  The tracer registers all nine tools with their final input schemas and wires every CLI subcommand. Tools not built yet are stubs that raise `GauntletError("not_implemented")`.

**State file** `<state_dir>/<loop>.json` keeps the legacy key names and preserves unknown keys on every update:

```
{"schema": 1, "loop", "repo" (abs path of integration worktree), "change", "integration_branch",
 "integration_worktree", "phase", "status": "running|done|stopped|failed",
 "started", "updated", "ended", "slices": {name: {worktree, branch, status, round, commit, verdict}}}
```

A file without `schema` is legacy and still counts.

**Loop ids** match `^[a-z0-9]+(-[a-z0-9]+)*$` and are at most 24 characters. Slice names use the same rule.

**`.gauntlet.json`** (Q6):

```
{"integration_branch": str (required), "shared": [relative paths, no "..", default []],
 "checks": [{"name": str, "command": str}] default [], "setup": str|null default null}
```

**Tool inputs and results:**

| Tool | Input | Result |
|---|---|---|
| `loop_start` | `{loop, repo, change, integration_branch?}` | state |
| `loop_update` | `{loop, phase?, slice?, worktree?, branch?, status?, round?, commit?, verdict?}` | state |
| `loop_end` | `{loop, status: done\|stopped\|failed}` | state |
| `worktree_new` | `{loop, slice}` | `{loop, slice, worktree, branch, base, shared:[...]}` |
| `worktree_rm` | `{loop, slice?}` | `{removed:[{slice, worktree, branch}], kept:[{slice, worktree, branch, reason, commits:[...]}]}` |
| `lock_acquire` | `{loop}` | `{lock, loop, repo, branch, acquired}` |
| `lock_release` | `{loop}` | `{released: true, lock}` |
| `config_read` | `{repo}` | `{path, config}` |
| `status` | `{}` | `{loops:[{loop, repo, change, phase, status, finished, leftover, worktrees:[{name, path, branch}], lock}]}` |

`lock_acquire` and `lock_release` take the repo and branch from the loop's state.

**Errors.** The error object is `{"error": code, "message", ...details}`. The codes are:

- `invalid_id`
- `duplicate_loop` (details name the running loop)
- `unknown_loop`
- `config_missing` (with `path`, `ask: [integration_branch, shared, checks, setup]`)
- `config_invalid` (with `fields: {name: message}`)
- `exists`
- `lock_held` (with `holder`, `acquired`)
- `not_holder`
- `git_failed`
- `not_implemented`

**MCP behaviour:**

- One JSON-RPC 2.0 message per line.
- `initialize` echoes the client's `protocolVersion` and returns `capabilities.tools` and `serverInfo`.
- Notifications get no reply; `ping` returns `{}`; an unknown method returns `-32601`; unparseable input returns `-32700`.
- `tools/call` returns `content:[{type:"text", text:<json>}]` and `isError`.
- stdout carries only protocol messages.

**`tests/helpers.py`** provides:

- `fake_home()`: context manager that sets `HOME`, the git identity env vars, and `GIT_CONFIG_NOSYSTEM`
- `make_repo(parent, name, branch="main", config=None, files=None)`
- `git(cwd, *args)`
- `load_server()`
- `run_cli(*args, home)`: uses `sys.executable`
- `McpClient(home)`: has `.request`, `.notify` and `.call(tool, args) -> (is_error, payload)`
- `read_frontmatter(path)`: handles `key: value` plus folded (`>`) and literal (`|`) block scalars
- `PLUGIN = <repo>/plugins/gauntlet`

---

## Tracer: `tracer`

**Behaviour delivered.** A plugin whose `mcp.json` starts the gauntlet server. The server answers MCP and registers, updates and ends loops, and reads `.gauntlet.json`, both over MCP and from the terminal.

**Spec coverage.**

- **Tasks:** 1.1, 2.1, 3.1
- **Requirements:**
  - "A loop is registered before it runs" (scenario *Duplicate id*)
  - "A project describes itself in .gauntlet.json" (scenario *Invalid field*)
  - "The plugin conforms to Agent Plugins 1.0.0" (scenario *Schema validation*)
  - The manifest half of "The same package installs as a Claude Code plugin and marketplace". The *Local Claude Code load* scenario is task 3.4, run by the main session.
  - The server half of "Without a config the gauntlet asks once" (`loop_start` reports `config_missing`)

**Files created.**

- `.claude-plugin/marketplace.json`
- `plugins/gauntlet/plugin.json`
- `plugins/gauntlet/mcp.json`: stdio, `python3`, `["${PLUGIN_ROOT}/server/gauntlet.py"]`
- `plugins/gauntlet/.claude-plugin/plugin.json`: name, version, description, author, `mcpServers: "./.mcp.json"`
- `plugins/gauntlet/.mcp.json`: `${CLAUDE_PLUGIN_ROOT}` form, without `$schema` or `type`
- `plugins/gauntlet/server/gauntlet.py`: core, registry, MCP and CLI, plus stubs for the five later tools
- `tests/helpers.py`
- `tests/jsonschema_subset.py`: a standard-library validator for the keywords both schemas use
- `tests/schemas/plugin.schema.json`, `tests/schemas/mcp.schema.json`, and `tests/schemas/SOURCE`: URLs, fetch date and sha256
- `tests/test_manifests.py`, `tests/test_state.py`, `tests/test_config.py`, `tests/test_mcp.py`, `tests/test_cli.py`, `tests/test_helpers.py`
- `.gitignore`: `__pycache__/`

**Depends on:** nothing.

**Builder brief.** Make the contract above real and lock it down with tests, so eight builders can work in parallel against it without reading each other's code.

- **Server.**
  - Build the core section (state, ids, config) and the registry, MCP and CLI sections.
  - Register all nine tools with their final input schemas and wire every CLI subcommand: `status`, `worktree new|rm`, `lock acquire|release`, `loop start|update|end`, `config`.
  - Leave the worktree, lock and status bodies as stubs. Don't write tests that pin stub behaviour.
- **Manifests.** Vendor the two Agent Plugins schemas into `tests/schemas/` and validate both files against them with your standard-library validator, including failing cases. Add a test that the two MCP files declare the same server, command and arguments.
- **End-to-end test.** Read `mcp.json`, substitute `${PLUGIN_ROOT}`, spawn that command, and drive `initialize`, `tools/list` and `tools/call` for `loop_start`, `loop_update`, `loop_end` and `config_read`.
- **Duplicate checks.** Duplicate-id and same-change checks must count legacy-format running files; copy the key shapes from the live files described above into test fixtures.
- **Missing config.** `loop_start` without a `.gauntlet.json` follows Q5.
- **Verified by:**
  - the full suite under both Pythons
  - `py_compile`
  - `openspec validate --strict`
  - a manual `printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}\n' | HOME=$(mktemp -d) python3 plugins/gauntlet/server/gauntlet.py`

---

## Slice: `worktrees`

**Behaviour delivered.**

- `worktree_new` creates a slice worktree and branch with the standard naming, links the shared folders, keeps those links ignored by git, and records them in state.
- `worktree_rm` removes merged slices and keeps unmerged or dirty ones, reporting them.

**Spec coverage.**

- **Task:** 1.2 (worktree half)
- **Requirements:**
  - "Worktrees are created the same way every time" (scenario *Shared folder*)
  - "Removal never loses unmerged work" (scenario *Unmerged slice*, plus removing a single merged slice without the user)

**Files.**

- Edit `plugins/gauntlet/server/gauntlet.py`, **`worktrees` section only.** Leave banners, the registry, the CLI and other sections alone. Put new helpers inside your section, not at its edges.
- Create `tests/test_worktrees.py`.

**Depends on:** tracer.

**Builder brief.** Implement `worktree_new` and `worktree_rm` behind the registered tools and CLI.

- **Naming.** The worktree goes at `<parent of main worktree>/<main worktree basename>-<loop>-<slice>` on branch `gauntlet/<loop>/<slice>`, created from the loop's integration branch. This holds even when the loop's `repo` is a linked integration worktree with a different directory name.
- **Shared folders.** Each entry under `shared` in the config is symlinked to the integration worktree's copy and must show as ignored in `git status --porcelain --ignored`. Fact: only the common `info/exclude` works, found via `git rev-parse --git-path info/exclude` (Q2). Never edit the project's `.gitignore`.
- **Removal.** Remove a slice only when `git rev-list <integration>..<branch>` is empty. Never force-remove a dirty worktree. Never remove the main checkout, and never delete the integration branch. Handle the integration worktree per Q1.
- **State and errors.** Record creation and removal in the loop's state. Refuse unknown loops, existing paths or branches, and missing shared sources (Q15), leaving nothing half-made behind.
- **Tests.** Use real temp repos: no mocking of git or subprocess.
- **Verified by:** the *Shared folder* and *Unmerged slice* tests, plus a stdio call for each tool.

---

## Slice: `locks-status`

**Behaviour delivered.** Merge locks are taken and released per repo and integration branch. Status lists loops, their worktrees and locks, and flags finished loops that still have worktrees, with the same output over MCP and from `gauntlet status`.

**Spec coverage.**

- **Tasks:** 1.2 (lock half), 1.3
- **Requirements:**
  - "Merges into a shared integration branch are serialized" (scenario *Concurrent merge*)
  - "Status shows loops, worktrees, and leftovers" (scenario *Finished loop with leftovers*)
  - "The same program serves MCP and the terminal" (scenario *Terminal status*)

**Files.**

- Edit `plugins/gauntlet/server/gauntlet.py`, **`locks` and `status` sections only.**
- Create `tests/test_locks.py` and `tests/test_status.py`.

**Depends on:** tracer.

**Builder brief.** Implement `lock_acquire`, `lock_release` and `status`.

- **Lock file.** Create it with `O_CREAT|O_EXCL` at `<state_dir>/<main worktree basename>--<encoded branch>.lock`, using Q3's encoding. It holds JSON `{loop, repo, branch, acquired}` with an ISO time including the UTC offset.
- **Acquire.** Refuse while another loop holds a lock younger than 30 minutes, naming the holder and when it took the lock. Take over stale locks. Re-acquiring by the holder follows Q16.
- **Release.** Only the holder can release.
- **Status contents.** List every loop from `list_loops()`, legacy files included. Show only worktrees that exist on disk (slice worktrees from state, plus the integration worktree per Q1) and any lock the loop holds. Set `finished` and `leftover`.
- **Status safety.** Status never writes, and non-loop files in the state folder must not break it.
- **Seeding test state.** Tests may seed state through `loop_start`/`loop_update` and create worktrees with plain git, because the worktree tool is built in parallel. Stale locks may be written as literal lock files in the contract format.
- **Verified by:** the scenario tests, a test that CLI `status` output equals the status tool's stdio result for the same `HOME`, and stdio calls for all three tools.

---

## Slice: `skills`

**Behaviour delivered.** The intake and gauntlet-loop skills, with the template, live inside the plugin and use `gauntlet:` agent names and the server's tools.

**Spec coverage.**

- **Task:** 3.2
- **Requirements:**
  - The skills half of "Agents and skills use the plugin's names and tools"
  - The placement half of "Bundled files are found inside the plugin". The *Template location* scenario is judged in `agents`.
  - PRD requirement 1: the skills are written once and serve both formats

**Files created.**

- `plugins/gauntlet/skills/intake/SKILL.md`
- `plugins/gauntlet/skills/gauntlet-loop/SKILL.md`
- `plugins/gauntlet/skills/gauntlet-loop/references/progress.html`
- `tests/test_skills.py`

**Depends on:** tracer.

**Builder brief.** Copy the two skills and the template from their read-only sources, then change only what packaging requires:

- **Agent names.** Name agents as `gauntlet:<agent>`, and add zeta to the agent table. zeta receives alpha's question and the relevant files, and never receives beta's bar.
- **Remove old locations.** Drop the "defined in `~/.claude/agents`" text.
- **Use the server's tools.** Replace "list the folder" with `gauntlet status` / the `status` tool. Replace hand-written state, worktree and lock steps with `loop_start`, `loop_update`, `loop_end`, `worktree_new`, `worktree_rm`, `lock_acquire`, `lock_release` and `config_read`.
- **Cleanup after merge.** Each merged slice's worktree is removed after its merge. The integration worktree and unmerged slices stay for the user.
- **Generalise project specifics.** Turn the ControlTower-specific `node_modules`/rebuild rules into shared folders, checks and setup read from `.gauntlet.json`.
- **Template reference.** Refer to the template relative to the skill folder (`references/progress.html`); skills are portable, so no `${CLAUDE_PLUGIN_ROOT}`.
- **Format.** Keep Agent Skills format: `name` equals the folder name, and `description` is at most 1024 characters (gauntlet-loop's is 895 today).
- **Unchanged otherwise.** Change nothing else about how the loop works.
- **Tests.**
  - Both folders have valid frontmatter.
  - There are no `~/.agents`, `~/.claude`, `~/.augy` or `/Users/` paths in either folder.
  - The template is present.
  - A plugin-wide reference test scans every `plugins/gauntlet/**/*.md` for `${CLAUDE_PLUGIN_ROOT}/...` and relative `references/...` paths and asserts each one exists. It finds nothing to check until `agents` merges; that is expected.

---

## Slice: `agents`

**Behaviour delivered.** The five existing agents are packaged in directive style, using `gauntlet:` names and the server's tools, with alpha's tdd, seam, refactor and zeta rules and beta's scenario-coverage bar.

**Spec coverage.**

- **Task:** 3.3
- **Requirements and scenarios:**
  - "alpha builds test-first at the OpenSpec seams" (*Refactor request*)
  - "beta checks scenario coverage" (*Missing scenario test*)
  - "alpha knows when and how to consult zeta" (*Hand-back lists questions*)
  - The agents half of "Agents and skills use the plugin's names and tools" (*epsilon creates a slice*)
  - "Bundled files are found inside the plugin" (*Template location*, through gamma)
  - The epsilon half of "Without a config the gauntlet asks once" (*New project*)
  - PRD requirements 1b, 1e, 2a and 5a for these five agents

**Files created.**

- `plugins/gauntlet/agents/alpha.md`, `beta.md`, `gamma.md`, `delta.md`, `epsilon.md`
- `tests/test_agents.py`

**Depends on:** tracer.

**Builder brief.** Copy the five definitions from `~/.claude/agents/` (read-only), keep each agent's behaviour, and apply:

- **All five:** `gauntlet:<agent>` names; no `~/.claude`, `~/.agents` or `~/.augy` paths.
- **alpha and beta:** rewrite as task directives with no persona, preserving every original rule.
- **alpha:**
  - One directive to follow the bundled `tdd` skill, with no summary of it.
  - Seam override: the seams are the OpenSpec scenarios and design interfaces in the slice brief, never confirmed with the user.
  - Refactor only when beta's HOLD or the brief asks, with the full suite green before and after.
  - When and how to start `gauntlet:zeta` (one question plus the relevant files). zeta is the only agent alpha may start, alpha decides, and the hand-back lists the questions it asked without zeta's reasoning.
  - Frontmatter `tools` includes `Agent` (Q8).
- **beta:**
  - Every bar checks that each scenario has a test at its seam and that no test is tautological or coupled to implementation details, as `tdd` defines them.
  - HOLD names the untested scenario.
  - Never consults zeta; `tools` without `Agent`.
- **epsilon:**
  - Server tools for loops, worktrees, locks and cleanup.
  - `worktree_rm` per slice right after its merge.
  - Checks and setup from `config_read`. A missing config means returning the four questions and offering to write `.gauntlet.json`, never guessing.
  - Intake-gate preconditions and loop rules kept.
  - `node_modules` rules generalised to shared folders.
  - `tools` includes `Agent` and the server tools (Q8).
- **gamma:** reads the template at `${CLAUDE_PLUGIN_ROOT}/skills/gauntlet-loop/references/progress.html`; output path per Q9.
- **delta:** builder briefs carry the seams under test (the scenarios and design interfaces), and bars include scenario coverage.
- **Tests:**
  - Parse frontmatter with `helpers.read_frontmatter`. Check names, and check that `Agent` is in the parsed `tools` of alpha and epsilon and absent from beta's.
  - alpha refers to `gauntlet:zeta` and `tdd`.
  - No "You are" phrasing, and no forbidden paths.
  - The behavioural scenarios are agent behaviour; the main session exercises them after 3.4.

---

## Slice: `zeta`

**Behaviour delivered.** A design advisor that answers alpha's design questions, grounded in the repo, and never writes code, starts agents, or grades work.

**Spec coverage.**

- **Task:** 3.3a, the definition and its test. The manual round goes to the main session.
- **Requirement:** "zeta advises alpha on design questions" (scenario *Composition question*), plus PRD requirements 1c and 2a for zeta.

**Files created.**

- `plugins/gauntlet/agents/zeta.md`
- `tests/test_zeta.py`

**Depends on:** tracer.

**Builder brief.** Write `zeta.md` in directive style, matching delta, gamma and epsilon.

- **Scope.** Answer only the question alpha asks, limited to that question.
- **Grounding order.** First the repo's existing patterns, citing files; then the language's conventions; then general principles.
- **Vocabulary.** Use the bundled `codebase-design` skill for vocabulary only. Never run its DESIGN-IT-TWICE sub-agent pattern: zeta sits at depth 3 and must not spawn.
- **Answer shape.** A recommendation, the files that show the existing pattern, and the reasons.
- **Limits.**
  - Reads code and writes none (Q18 on snippets).
  - Never assesses alpha's work.
  - Declines if given a bar or asked to review.
  - Frontmatter `tools` excludes `Agent`, `Write`, `Edit` and `NotebookEdit` (Q8).
- **Test.** Uses the same frontmatter and phrasing checks as `agents`.

---

## Slice: `vendor-skills`

**Behaviour delivered.** The plugin bundles `tdd` and `codebase-design` unchanged, with their MIT licence and attribution.

**Spec coverage.**

- **Task:** 3.3b
- **Requirement:** "Third-party skills are bundled with their license" (scenario *License notice*), plus PRD requirements 2b and 2c (bundling).

**Files created.**

- `plugins/gauntlet/skills/tdd/SKILL.md`, `LICENSE`, `references/tests.md`, `references/mocking.md`
- `plugins/gauntlet/skills/codebase-design/SKILL.md`, `LICENSE`, `references/DEEPENING.md`, `references/DESIGN-IT-TWICE.md`
- `tests/test_vendored_skills.py`

**Depends on:** tracer.

**Builder brief.**

- **Fetch.** Get the files read-only with `gh api repos/mattpocock/skills/contents/<path>?ref=4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`, using the repo-root `LICENSE` for both folders.
- **Edits allowed.** Move the reference files under `references/`. Rewrite links so they resolve (for example `references/tests.md`, and `../SKILL.md` from inside `references/`). Add the attribution naming `mattpocock/skills`, the source path and the commit, per Q10. Nothing else changes; leave `agents/openai.yaml` out per Q10.
- **Tests.**
  - Each folder has a `LICENSE` containing the MIT text.
  - Attribution names the repo and path.
  - Every relative markdown link resolves inside the skill folder.
  - Frontmatter `name` equals the folder name.

---

## Slice: `cutover`

**Behaviour delivered.** `scripts/cutover.py` switches a machine from loose copies to the plugin, only when no loop runs. It has a dry run, a backup manifest, and a rollback.

**Spec coverage.**

- **Task:** 4.1
- **Requirements:**
  - "Cutover runs only when no loop is running" (scenario *Loop running*)
  - "Cutover can be rolled back" (scenario *Rollback*)

**Files created.**

- `scripts/cutover.py`
- `tests/test_cutover.py`

**Depends on:** tracer, for `running_loops()` and the state-folder layout.

**Builder brief.** `python3 scripts/cutover.py [--dry-run] [--rollback <backup dir>]`.

- **Refusal.** Refuse, changing nothing, while any loop is running. Use the server's `running_loops()` so legacy files count, and name the running loops.
- **Otherwise:**
  1. Back up every target to `~/.local/state/gauntlet/cutover-<timestamp>/` with a manifest recording each path's type, link target, content and mode.
  2. Remove `~/.claude/agents/{alpha,beta,gamma,delta,epsilon}.md` and the `~/.claude/skills/{intake,gauntlet-loop}` links. Unlink links; never follow them.
  3. Replace `~/.augy/skills/{intake,gauntlet-loop}` and `~/.agents/agents/{alpha,beta,gamma,delta,epsilon}.md` with absolute symlinks to `<repo>/plugins/gauntlet/skills/<name>` and `<repo>/plugins/gauntlet/agents/<name>.md`, where `<repo>` is the script's checkout.
- **Dry run.** `--dry-run` prints the plan and writes nothing.
- **Rollback.** `--rollback` restores everything from the manifest.
- **Edge cases.** Targets that don't exist are skipped. Missing link targets in the repo, and re-runs, follow Q12.
- **Testability.** Make the home and repo-root paths injectable at function level, so tests can use a fake home and a fake plugin tree; the skills and agents files don't exist on this branch.
- **Verified by:** tests for refusal (server-written and legacy running files), dry run, cutover and rollback, each comparing a full snapshot of the fake home.

---

## Slice: `readme-config`

**Behaviour delivered.** A README that takes a machine from nothing to a working plugin, and ControlTower's drafted `.gauntlet.json` accepted by `config_read`.

**Spec coverage.**

- **Tasks:** 4.2, 4.3
- **Requirements:**
  - "Each machine has documented setup" (the *New machine* scenario is proven at task 5.2 by the user)
  - "Updates never change a running loop" (the README rule; the version fields come from the tracer)
  - "ControlTower is configured" (*ControlTower slice*: the checks come from the file; linking is proven generically by `worktrees`)

**Files created.**

- `README.md`
- `examples/controltower.gauntlet.json`
- `tests/test_examples.py`

**Depends on:** tracer, for the `config_read` format and the marketplace name.

**Builder brief.**

- **README covers:**
  - What the gauntlet is: six agents, four skills, the server and CLI.
  - Per machine (this Mac first, then the other machines, Linux included): GitHub access (`gh auth login` plus `gh auth setup-git`, or a passphrase-free SSH key), the repo checkout location (Q11), adding the marketplace `callmeradical/gauntlet`, installing `gauntlet@<marketplace name>`, linking `~/.local/bin/gauntlet` to `plugins/gauntlet/server/gauntlet.py`, and the cutover (`--dry-run`, run, `--rollback`).
  - Update only while `gauntlet status` shows no running loop, and bump the version in both manifests and the server each release.
  - The `.gauntlet.json` format.
  - Credit for the bundled skills.
- **Example config.** Integration branch `feat/decision-tree`, shared `node_modules`, the four checks (`npx vitest run`, `npm run build:ts`, `npm run build:app`, `npx tsc --noEmit -p src/renderer`), named per Q6, and setup `npm run rebuild:node`.
- **Tests.**
  - `config_read` returns those values, asserted as literals.
  - The README contains the marketplace name read from `marketplace.json`, `--dry-run`, `--rollback` and `gauntlet status`.
- **Limits.** The README describes publishing; it never does it.

---

## Parallel plan

- **Phase 1:** `tracer` alone. It merges into `main`.
- **Phase 2:** all eight slices at once: `worktrees`, `locks-status`, `skills`, `agents`, `zeta`, `vendor-skills`, `cutover`, `readme-config`.

**File overlap.** Only one file is shared.

| | gauntlet.py | other files |
|---|---|---|
| worktrees | `worktrees` section | tests/test_worktrees.py |
| locks-status | `locks` and `status` sections | tests/test_locks.py, tests/test_status.py |
| skills | none | skills/intake, skills/gauntlet-loop, tests/test_skills.py |
| agents | none | agents/{alpha,beta,gamma,delta,epsilon}.md, tests/test_agents.py |
| zeta | none | agents/zeta.md, tests/test_zeta.py |
| vendor-skills | none | skills/tdd, skills/codebase-design, tests/test_vendored_skills.py |
| cutover | none | scripts/cutover.py, tests/test_cutover.py |
| readme-config | none | README.md, examples/, tests/test_examples.py |

The only expected conflict is between `worktrees` and `locks-status` in `gauntlet.py`. The tracer's banner sections keep their changes apart: sections separated by unchanged banner lines merge cleanly. If they still conflict, the second slice to merge resolves it by keeping both sections; no logic is shared.

**Merge order:** by risk; any order is valid.

1. `worktrees`
2. `locks-status`
3. `cutover`
4. `vendor-skills`
5. `skills`
6. `agents`
7. `zeta`
8. `readme-config`

Run the full suite after each merge. After `agents` merges, the reference test from `skills` starts checking gamma's template path.

## Integration step (after all merges; no new code)

1. **Full run on `main`:**
   - the suite under `python3` and `/usr/bin/python3`
   - `py_compile` on `plugins/gauntlet/server/gauntlet.py` and `scripts/cutover.py`
   - `openspec validate package-gauntlet-plugin --strict`
2. **Cross-slice checks:**
   - `agents/` holds exactly six definitions.
   - `skills/` holds exactly four skills.
   - `grep -rnE '~/\.(claude|agents|augy)|/Users/' plugins/` finds nothing.
   - Every server tool named in epsilon's `tools` and in the skills exists in the server's `tools/list`.
   - The three version strings (both manifests and the server) agree.
3. **`tasks.md`:** tick 1.1, 1.2, 1.3, 2.1, 3.1, 3.2, 3.3, 3.3b, 4.1, 4.2 and 4.3. Leave 3.3a unticked until the main session's manual zeta round. Leave 3.4, 5.1 and 5.2 for the main session or the user.
4. **Docs:** none beyond the README. If Q2 is decided, fix design.md's `info/exclude` wording, then run `openspec validate` again.
5. **Hand to the main session:**
   - **3.4:** run `claude --plugin-dir plugins/gauntlet`. Check that it lists six `gauntlet:` agents, four skills and nine tools, and that the server is registered once.
   - The 3.3a manual zeta round.
   - Optionally, a read-only `gauntlet status` against the real state folder, to confirm the legacy files list without errors and nothing is written.

## Product questions (with recommended defaults if you want to decide without asking)

- **Q1 (worktrees and status).** Does `worktree rm <loop>` remove the integration worktree?
  - *Recommend:* only when it is a linked worktree (never the main checkout), clean, and not the `repo` of any other running loop. Never delete the integration branch.
  - Status counts the integration worktree as a leftover only under the same rule.
- **Q2.** Shared links must go in the common `info/exclude`, which affects every worktree of the repo, because the per-worktree file doesn't work.
  - *Recommend:* accept it, with an anchored `/node_modules` entry added only if missing.
  - The alternative, `extensions.worktreeConfig` plus `core.excludesFile`, rewrites the repo's config.
- **Q3.** Lock name for branches with `/`. *Recommend:* encode `/` as `%2F`, giving `controltower--feat%2Fdecision-tree.lock`.
- **Q4.** Legacy state files. *Recommend:* always read them, and preserve unknown keys when updating.
- **Q5.** `loop_start` with no `.gauntlet.json`. *Recommend:* refuse with `config_missing` listing the four fields; epsilon asks, writes the file, and retries. Whether epsilon commits that file is also open; recommend no.
- **Q6.** `.gauntlet.json` strictness. *Recommend:* `integration_branch` required, unknown keys reported as invalid. ControlTower's check names: `test`, `build:ts`, `build:app`, `typecheck`.
- **Q7.** Terminal output. *Recommend:* the CLI prints the same JSON as the tool. The alternative is a readable table.
- **Q8.** Explicit `tools` lists, which take tools away compared with today. *Recommend:*

  | Agent | `tools` |
  |---|---|
  | alpha | `Read, Write, Edit, Bash, Glob, Grep, Skill, Agent` |
  | beta | `Read, Bash, Glob, Grep, Skill` |
  | zeta | `Read, Glob, Grep, Skill` |
  | epsilon | `Read, Write, Edit, Bash, Glob, Grep, Skill, Agent`, plus `mcp__plugin_gauntlet_gauntlet__<tool>` for each of the nine tools |
  | gamma, delta | no `tools` line (unchanged) |

  Confirm the MCP tool naming in 3.4.
- **Q9.** Which home paths are allowed in agent and skill text? *Recommend:* forbid `~/.claude`, `~/.agents`, `~/.augy` and absolute `/Users/`; allow gamma's `~/wiki/features/...` and `~/.local/state/gauntlet`.
- **Q10.** Third-party skills. *Recommend:* leave out `agents/openai.yaml`. Put the attribution as a footer line at the end of each `SKILL.md` body ("Source: github.com/mattpocock/skills, skills/engineering/<name> at <sha>. MIT, see LICENSE"), leaving the description untouched. Leave tdd's `code-review` mention as is.
- **Q11.** Which checkout do the terminal link and the cutover's symlinks point to on each machine? *Recommend:* a dedicated clone (`~/Dev/gauntlet`), pulled together with each plugin update. The alternative is Claude Code's marketplace clone.
- **Q12.** Cutover extras. *Recommend:*
  - refuse if a link target is missing in the repo
  - a re-run is a no-op
  - leave `~/.claude/skills/{tdd,codebase-design}` alone, but have the README mention them
- **Q13.** Initial version. *Recommend:* `0.1.0`; marketplace name `gauntlet` (so `gauntlet@gauntlet`); no version in the marketplace entry.
- **Q14.** Reusing an id from a finished loop. *Recommend:* allowed (it overwrites the old state). "Same repo" in the duplicate-change check means the same main repository, not the same path.
- **Q15.** A shared folder is missing in the integration worktree. *Recommend:* refuse before creating anything.
- **Q16.** Lock re-acquired by its holder. *Recommend:* succeeds and refreshes the time.
- **Q17.** Python minimum. *Recommend:* 3.9.
- **Q18.** May zeta include short illustrative snippets? *Recommend:* yes, but no edits and no full implementations.

**Risks that are not questions:**

- Claude Code may register the server twice (the default `.mcp.json` plus `mcpServers`); 3.4 will show it.
- Several scenarios describe agent behaviour that unit tests can't prove: *Refactor request*, *Missing scenario test*, *Hand-back*, *Composition question*, *Template location*, *epsilon creates a slice*, *New project*. Tests only check the definitions.
- *Update during a loop* can't be tested in the repo.
- This loop's own worktrees must be made the old way; don't point the new server at the live state folder.
- intake depends on the `write-a-prd`, `grilling` and `prd-to-spec` skills, which aren't bundled. Other machines need them.

---

---

## Decisions recorded by the loop (2026-11-03)

These settle delta's questions. Each one is either answered by the PRD/spec or is an implementation call within it. Per the user's standing rule for OpenSpec changes, they were made without asking and will be reported. Builders follow them as written.

- **Q1** (PRD 4, 5a): when the user runs `worktree rm <loop>` with no slice, it also removes the loop's integration worktree, but only if that worktree is linked (never the main checkout), clean, has no commits missing from the integration branch, and isn't the `repo` of another running loop. The integration branch is never deleted. epsilon removes only slices. Status counts the integration worktree as a leftover under the same rule.
- **Q2** (design.md fact correction): shared-folder links are excluded via the common `info/exclude`, found with `git rev-parse --git-path info/exclude`, using an anchored `/<folder>` entry added only if missing. The project's `.gitignore` is never edited. design.md's wording is corrected in the integration step.
- **Q3:** in lock file names, `/` in a branch is encoded as `%2F`, for example `controltower--feat%2Fdecision-tree.lock`.
- **Q4:** legacy state files (`loop` key, no `schema`) are always read. Updates preserve unknown keys.
- **Q5** (spec "asks once"): `loop_start` without `.gauntlet.json` refuses with `config_missing`, and `ask` lists the four fields. epsilon returns the questions, offers to write the file, and does not commit it.
- **Q6:** `integration_branch` is required. Unknown keys are reported as invalid, by field. ControlTower's check names are `test`, `build:ts`, `build:app`, `typecheck`.
- **Q7:** the CLI prints the same JSON as the tool, indented.
- **Q8** (design.md: Agent in alpha's and epsilon's tools, not in beta's or zeta's): explicit `tools` lists, keeping today's capabilities where the role needs them. epsilon needs `SendMessage` to send a HOLD back to the same alpha. The MCP tool naming is confirmed at 3.4.

  | Agent | `tools` |
  |---|---|
  | alpha | `Read, Write, Edit, Bash, Glob, Grep, Skill, WebFetch, WebSearch, Agent` |
  | beta | `Read, Bash, Glob, Grep, Skill, WebFetch, WebSearch` |
  | zeta | `Read, Glob, Grep, Skill` |
  | epsilon | `Read, Write, Edit, Bash, Glob, Grep, Skill, Agent, SendMessage`, plus `mcp__plugin_gauntlet_gauntlet__<tool>` for each of the nine tools |
  | gamma, delta | `tools` lines unchanged from the source definitions |
- **Q9** (spec: the template and server are located inside the plugin): agent and skill text forbids `~/.claude`, `~/.agents`, `~/.augy` and absolute `/Users/` paths. Runtime data paths (`~/wiki/features/...` and `~/.local/state/gauntlet`) are allowed.
- **Q10** (spec: the listed files only): leave out `agents/openai.yaml`. The attribution is one footer line at the end of each `SKILL.md` body: `Source: github.com/mattpocock/skills, skills/engineering/<name> at <sha>. MIT, see LICENSE.` Descriptions stay untouched, and tdd's `code-review` mention stays as is.
- **Q11:** the README tells each machine to keep a dedicated clone at `~/Dev/gauntlet`, pulled together with each plugin update. The PATH link and the cutover's symlinks point into that clone.
- **Q12** (spec target list): the cutover refuses if a link target is missing in the repo, and a re-run is a no-op. It leaves `~/.claude/skills/{tdd,codebase-design}` alone; the README mentions them.
- **Q13:** version `0.1.0`, marketplace name `gauntlet` (installed as `gauntlet@gauntlet`), no version in the marketplace entry.
- **Q14:** reusing the id of a finished loop is allowed and replaces its state. "Same repo" in the duplicate-change check means the same main repository.
- **Q15:** if a shared folder is missing in the integration worktree, refuse before creating anything.
- **Q16:** when the holder re-acquires its own lock, the call succeeds and refreshes the time.
- **Q17:** Python 3.9 minimum.
- **Q18** (spec: "writes no code"): zeta may quote existing repo code with file citations, but writes no new code, not even illustrative snippets.
- **Task 3.3a's manual zeta round** and **task 3.4** belong to the main session after the loop.
- **Licence** (left open by the spec): `plugin.json` `license` is `UNLICENSED`, for a private personal repo; bundled third-party skills keep their own MIT licence. This is easy to change before publishing (5.1).
- **Q4a** (contract amendment after the tracer review; live `pri-contract.json` keys its id as `loop_id`): a loop file is any top-level `<name>.json` in the state folder whose content is a JSON object with a `loop` key, a `loop_id` key, or a `status` key. Its id is `loop`, else `loop_id`, else `<name>`. A running loop is one with `status: "running"`. Unreadable or non-object `*.json` files are skipped by `list_loops()` without crashing. `load_loop` raises `GauntletError` (`unknown_loop`, with a reason) for a corrupt or non-object file, never a traceback. Status, the duplicate checks, and the cutover refusal all use this rule.
