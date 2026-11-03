# Install and update

Back to the [README](../README.md).

## Requirements

On every machine:

- Claude Code
- Python 3.9 or later, available as `python3` on the PATH. Claude Code starts the server with `python3`.
- git, plus `gh` if you use it for GitHub access
- The skills that `intake` calls but the plugin doesn't bundle: `write-a-prd`, `grilling` and `prd-to-spec`

## Install on a machine

Do this Mac first, then your other machines, Linux included. The steps are the same on each machine; nothing is platform-specific.

### 1. GitHub access

The repo is public, so installing and updating need no GitHub credentials. Only pushing changes does: sign in as `callmeradical` with `gh auth login`, then `gh auth setup-git`, so plain `git` over HTTPS uses gh's credentials.

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
