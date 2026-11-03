# gauntlet

A build/review loop with separated roles, packaged as one plugin. An OpenSpec change goes in; reviewed, merged code comes out. The builder never sees the reviewer's bar, and the reviewer never sees the builder's reasoning.

The plugin follows [Agent Plugins 1.0.0](https://agent-plugins.org/specification), so its skills and MCP server load in any Agent Plugins client. It also installs natively in Claude Code, which adds the agents.

## What's in it

**Six agents** (Claude Code only), installed as `gauntlet:<name>`:

| Agent | Role |
|---|---|
| `gauntlet:delta` | Slices an OpenSpec change into a tracer bullet plus vertical slices, each with a builder brief and a critic bar. |
| `gauntlet:alpha` | Builds one slice test-first in its own worktree. |
| `gauntlet:beta` | Reviews a slice with fresh context against its bar and returns PASS or HOLD. |
| `gauntlet:gamma` | Keeps the loop's progress page in the wiki. Reports facts and never judges. |
| `gauntlet:epsilon` | Orchestrates: runs delta, the alphas, the betas and gamma, then merges PASSed slices one at a time. |
| `gauntlet:zeta` | Answers alpha's design questions when alpha asks. It writes no code and never sees beta's bar. |

**Four skills** (Agent Skills format, used by both Claude Code and Agent Plugins clients):

| Skill | What it does |
|---|---|
| `intake` | Takes work from idea to a build-ready OpenSpec change: PRD, grilling, OpenSpec, gate. |
| `gauntlet-loop` | The loop itself, including the progress-page template in `references/progress.html`. |
| `tdd` | Test-driven development. Bundled from `mattpocock/skills` (see [Credits](#credits)). |
| `codebase-design` | Deep-module vocabulary for zeta. Bundled from `mattpocock/skills`. |

**The `gauntlet` server and CLI.** `plugins/gauntlet/server/gauntlet.py` is one Python file that uses only the standard library and git. Run with no arguments, it is the MCP stdio server, declared in `mcp.json` (Agent Plugins) and `.mcp.json` (Claude Code). Run with arguments, it is a terminal command that prints the same JSON the tools return. It has nine tools:

| Tool | Terminal command |
|---|---|
| `loop_start`, `loop_update`, `loop_end` | `gauntlet loop start <loop> --repo <path> --change <change>`, `gauntlet loop update <loop> ...`, `gauntlet loop end <loop> done\|stopped\|failed` |
| `worktree_new`, `worktree_rm` | `gauntlet worktree new <loop> <slice>`, `gauntlet worktree rm <loop> [<slice>]` |
| `lock_acquire`, `lock_release` | `gauntlet lock acquire <loop>`, `gauntlet lock release <loop>` |
| `config_read` | `gauntlet config <repo>` |
| `status` | `gauntlet status` |

Loop state and merge locks live in `~/.local/state/gauntlet/`, outside the plugin, so updates and every client share them.

Starting work is the same as before: run `intake`, then hand the change to `gauntlet:epsilon`.

## Layout

```
.claude-plugin/marketplace.json     Claude Code marketplace "gauntlet", source ./plugins/gauntlet
plugins/gauntlet/
  plugin.json, mcp.json             Agent Plugins 1.0.0
  .claude-plugin/plugin.json        Claude Code manifest
  .mcp.json                         Claude Code MCP config
  agents/                           the six agents
  skills/                           the four skills
  server/gauntlet.py                MCP server and CLI
scripts/cutover.py                  switches a machine from loose copies to the plugin
examples/controltower.gauntlet.json ControlTower's project config
tests/                              python3 -m unittest discover -s tests
```

## Requirements

On every machine:

- Claude Code
- Python 3.9 or later, available as `python3` on the PATH. Claude Code starts the server with `python3`.
- git, plus `gh` if you use it for GitHub access
- The skills that `intake` calls but the plugin doesn't bundle: `write-a-prd`, `grilling` and `prd-to-spec`

## Publishing (once, from this Mac)

The repo is private, at `callmeradical/gauntlet`, and is its own marketplace. Publish it only when you've decided to; nothing in this repo does it for you. From the repo at `~/Dev/gauntlet`:

```sh
cd ~/Dev/gauntlet
gh repo create callmeradical/gauntlet --private --source . --remote origin --push
```

The plugin's `license` is `UNLICENSED`, which suits a private personal repo. Change it before you share the repo with anyone.

## Install on a machine

Do this Mac first, then your other machines, Linux included. The steps are the same on each machine; nothing is platform-specific.

### 1. GitHub access to the private repo

Claude Code and git both need to read `callmeradical/gauntlet`. Choose one:

- **gh:** run `gh auth login`, then `gh auth setup-git`, so plain `git` over HTTPS uses gh's credentials.
- **SSH:** add a passphrase-free SSH key to the `callmeradical` GitHub account, then check it with `ssh -T git@github.com`. The key needs no passphrase because Claude Code clones without prompting.

### 2. A dedicated clone at `~/Dev/gauntlet`

The terminal command and the cutover's symlinks point into this clone, so keep it at this path and pull it whenever you update the plugin.

```sh
git clone https://github.com/callmeradical/gauntlet.git ~/Dev/gauntlet
# or, with SSH:
git clone git@github.com:callmeradical/gauntlet.git ~/Dev/gauntlet
```

On this Mac the repo is already at `~/Dev/gauntlet`, so skip the clone.

### 3. Add the marketplace and install the plugin in Claude Code

In Claude Code:

```
/plugin marketplace add callmeradical/gauntlet
/plugin install gauntlet@gauntlet
```

If you set up SSH access, add the marketplace with `/plugin marketplace add git@github.com:callmeradical/gauntlet.git` instead. Either way the marketplace is named `gauntlet` (from `.claude-plugin/marketplace.json`), so the plugin is `gauntlet@gauntlet`.

Restart Claude Code. `/agents` should list the six `gauntlet:` agents, and `/mcp` should show the `gauntlet` server.

### 4. Put `gauntlet` on the terminal PATH

```sh
mkdir -p ~/.local/bin
ln -s ~/Dev/gauntlet/plugins/gauntlet/server/gauntlet.py ~/.local/bin/gauntlet
gauntlet status
```

`~/.local/bin` must be on your PATH. On Linux, many distributions add it at login only if the folder already existed, so log in again after creating it. On a machine with no loops, `gauntlet status` prints:

```
{
  "loops": []
}
```

### 5. Cut over from the loose copies

Before the plugin, the gauntlet lived in loose files: agents in `~/.claude/agents/`, skills linked into `~/.claude/skills/`, and copies for other tools in `~/.augy/skills/` and `~/.agents/agents/`. The loose Claude Code copies take precedence over the plugin's, so they have to go. The cutover:

- removes `~/.claude/agents/{alpha,beta,gamma,delta,epsilon}.md` and the `~/.claude/skills/{intake,gauntlet-loop}` links
- replaces `~/.augy/skills/{intake,gauntlet-loop}` and `~/.agents/agents/{alpha,beta,gamma,delta,epsilon}.md` with symlinks into `~/Dev/gauntlet/plugins/gauntlet/`
- first backs up everything it changes to `~/.local/state/gauntlet/cutover-<timestamp>/`, with a manifest

Run it only while no loop is running. It refuses, changing nothing, while `gauntlet status` shows any loop with `"status": "running"`, and it names those loops. It also refuses if a link target is missing from the clone. It skips targets that don't exist, and a second run changes nothing.

```sh
gauntlet status                                     # confirm no loop is running
python3 ~/Dev/gauntlet/scripts/cutover.py --dry-run # print the plan; writes nothing
python3 ~/Dev/gauntlet/scripts/cutover.py           # back up, remove, relink
```

To undo it, pass the backup folder it reported:

```sh
python3 ~/Dev/gauntlet/scripts/cutover.py --rollback ~/.local/state/gauntlet/cutover-<timestamp>
```

The rollback restores every file and link from the manifest. To go back completely, also run `/plugin uninstall gauntlet@gauntlet` in Claude Code.

The cutover leaves the loose `~/.claude/skills/tdd` and `~/.claude/skills/codebase-design` links alone. The plugin bundles its own copies of both skills, and those links keep working beside them. Remove the links yourself if you want only the plugin's copies.

### Per machine

- **This Mac:** the repo is already at `~/Dev/gauntlet`, and the loose copies exist, so all five steps apply. Run the cutover only when `gauntlet status` shows no running loop.
- **A Linux machine:** steps 1 to 5. Check that `python3` is 3.9 or later and that `~/.local/bin` is on the PATH. The cutover skips any loose copies the machine doesn't have.
- **Any other machine:** steps 1 to 5, as above.

## Updating

Update only while no loop is running. A loop should end on the definitions it started with, so check first:

```sh
gauntlet status | grep '"status": "running"'   # no output means no loop is running
```

Then update the clone and the plugin together:

```sh
git -C ~/Dev/gauntlet pull --ff-only
```

In Claude Code, run `/plugin marketplace update gauntlet`, update `gauntlet@gauntlet` from the `/plugin` menu, and restart Claude Code. The clone matters too: the terminal command and the symlinks in `~/.augy` and `~/.agents` read from it.

## Releasing

Every release bumps the version, because Claude Code offers an update only when the version changes. The marketplace entry carries no version. Change all three places to the same value:

- `plugins/gauntlet/plugin.json` (`version`)
- `plugins/gauntlet/.claude-plugin/plugin.json` (`version`)
- `VERSION` in `plugins/gauntlet/server/gauntlet.py`

`tests/test_manifests.py` checks that the three agree and pins the current value, so update it with the bump. Then run the checks, commit, push, and update each machine as described in [Updating](#updating).

## Project configuration: `.gauntlet.json`

Each project describes itself in a `.gauntlet.json` at its root, so the agents carry no project specifics. ControlTower's (`examples/controltower.gauntlet.json`):

```json
{
  "integration_branch": "feat/decision-tree",
  "shared": ["node_modules"],
  "checks": [
    {"name": "test", "command": "npx vitest run"},
    {"name": "build:ts", "command": "npm run build:ts"},
    {"name": "build:app", "command": "npm run build:app"},
    {"name": "typecheck", "command": "npx tsc --noEmit -p src/renderer"}
  ],
  "setup": "npm run rebuild:node"
}
```

| Field | Type | Default | Meaning |
|---|---|---|---|
| `integration_branch` | string, required | none | The branch slices are cut from and merged into. `loop_start` can override it per loop. |
| `shared` | list of relative paths | `[]` | Folders in the integration worktree to symlink into each slice worktree, such as `node_modules`. No absolute paths and no `..`. |
| `checks` | list of `{"name", "command"}` | `[]` | The commands every slice must pass. Each entry has exactly these two non-empty strings. |
| `setup` | string or `null` | `null` | A command to run once before a loop. |

Any other key is an error. The server reports errors by field (`config_invalid` with `fields`). To check a file, run `gauntlet config <repo>`.

Shared folders are linked from the integration worktree and kept out of git through the repository's common `info/exclude` (found with `git rev-parse --git-path info/exclude`), using an anchored entry such as `/node_modules`. The project's `.gitignore` is never edited.

If a project has no `.gauntlet.json`, `loop_start` refuses with `config_missing` and lists the four fields. epsilon then asks you for them and offers to write the file. It doesn't commit the file.

## Development

The checks, all of which must pass:

```sh
python3 -m unittest discover -s tests -v
/usr/bin/python3 -m unittest discover -s tests -v   # Python 3.9
python3 -m py_compile plugins/gauntlet/server/gauntlet.py scripts/cutover.py
openspec validate package-gauntlet-plugin --strict
```

Tests use temp folders, temp git repos and a fake `HOME`, so they never touch your real `~/.claude` or `~/.local/state/gauntlet`. To try the plugin without installing it, run `claude --plugin-dir plugins/gauntlet`.

## Credits

The plugin bundles two skills from [`mattpocock/skills`](https://github.com/mattpocock/skills) by Matt Pocock, at commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`, under the MIT licence:

- `plugins/gauntlet/skills/tdd`, from `skills/engineering/tdd`
- `plugins/gauntlet/skills/codebase-design`, from `skills/engineering/codebase-design`

Each folder keeps the upstream `LICENSE`, and each `SKILL.md` ends with a source line. The text is unchanged apart from moving reference files under `references/` and rewriting links to match. The upstream `agents/openai.yaml` files are left out.
