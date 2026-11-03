# 001 · Gauntlet plugin

**Status:** Proposed · **Drafted:** 2026-11-03

## Summary

The gauntlet becomes one installable plugin that conforms to the [Agent Plugins 1.0.0 specification](https://agent-plugins.org/specification) and also installs natively in Claude Code: the five agents (delta slices, alpha builds, beta reviews, gamma reports progress, epsilon orchestrates), the intake and gauntlet-loop skills, the progress-page template, and a small `gauntlet` command for worktrees and loop status. It is installed on each of the user's machines from a private repo that is also its own marketplace, and updated like any plugin.

## Problem

The gauntlet grew in one day out of loose files:

- **Five agent definitions** in `~/.claude/agents/`, copied by hand into the dotfiles at `~/.agents/agents/`.
- **Two skills** (`intake`, `gauntlet-loop`) in `~/.augy/skills/`, symlinked into `~/.claude/skills/` and `~/.opencode/skills/`.
- **A template** at `~/.agents/templates/progress.html` that agents find by an absolute path.
- **Worktrees made by improvisation.** epsilon reads naming and setup rules and types its own `git worktree` commands each run, so runs differ.
- **Project specifics baked into general instructions.** The shared `node_modules` symlink, the check commands, and the native rebuild are ControlTower's, written as if every project had them.
- **No cleanup.** Finished loops leave their worktrees and branches behind (14 for ControlTower so far).
- **No versioning.** A change to an agent applies mid-run to loops already going, and other machines (the user's other machines) only get it if someone copies the files.

## Goals

- A vendor-neutral package: the portable parts (skills, MCP servers) load in any Agent Plugins client; Claude Code additionally gets the agents.
- One install per machine; one version of the gauntlet everywhere; updates through the plugin system.
- Worktrees, shared folders, locks, and cleanup done the same way every run, by a command, not by an agent's improvisation.
- Project-specific facts (shared folders, checks, rebuild steps, integration branch) live in the project, not in the agents.
- Running loops keep the definitions they started with; installing or updating the plugin doesn't change a loop in flight.

**Non-goals**

- Changing how the gauntlet works (roles, intake, gate, loop rules). This packages what exists.
- Sharing with a team or publishing publicly.
- Non-git projects.

## Users and scenarios

- *"On a new machine, I install the gauntlet once and have every agent and skill."*
- *"I start a loop on a repo and its worktrees come out the same every time, with the right folders shared."*
- *"I ask what loops are running and see each one's worktrees, phase, and lock."*
- *"After a release, I clean up a finished loop's worktrees and branches in one step, and nothing unmerged is lost."*
- *"I improve beta's instructions and every machine picks it up with a plugin update; loops already running are unaffected."*

## Requirements

### Contents

0. The gauntlet has six agents: delta (slice), alpha (build), beta (review), gamma (progress), epsilon (orchestrate), and zeta (design advisor to alpha).
1. The plugin conforms to Agent Plugins 1.0.0: a root `plugin.json`, the skills intake and gauntlet-loop as Agent Skills, and any MCP server in `mcp.json`. The progress-page template ships inside a skill.
1a. The same repo installs as a Claude Code plugin and marketplace, adding the agents delta, alpha, beta, gamma, and epsilon, which Agent Plugins 1.0.0 doesn't cover. Skills are shared by both formats, not duplicated.
1b. Instructions refer to the agents by their installed names (for example `gauntlet:alpha`).
1c. **zeta** answers alpha's design questions (inheritance vs composition, polymorphism, public/private, imported/exported, DRY, SOLID, and the like) only when alpha asks, limited to the question, grounded first in the codebase's existing patterns (citing files), then the language's conventions, then general principles. It reads code, writes none, starts no agents, and never grades alpha's work. beta never consults zeta, and zeta never sees beta's bar.
2. Agents and skills find the template and the command inside the plugin, not by a path in the user's home folder.
2b. The plugin bundles the `tdd` skill (Matt Pocock's, MIT, `mattpocock/skills` `skills/engineering/tdd`) with its license notice and attribution, text unchanged apart from link paths. alpha's definition directs it to follow that skill rather than restating it, with one override: the seams under test are the ones the OpenSpec change defines (its spec scenarios and the interfaces in its design), carried into each slice brief by delta, not confirmed with the user. beta's bar checks that every scenario in a slice has a test at those seams.
2a. All five agent definitions, including alpha and beta, are written as task directives, without personification, and keep their current behavior.

### Worktrees and loops

3. A `gauntlet worktree new <loop> <slice>` command creates a slice's worktree and branch off the loop's integration branch, links the project's shared folders, and records it in the loop's state.
4. A `gauntlet worktree rm <loop> [<slice>]` command removes a loop's (or one slice's) worktrees and branches, refusing any branch with commits not merged into the integration branch.
5. A `gauntlet status` command lists loops with their repo, change, phase, worktrees, and any merge lock, and flags finished loops that still have worktrees.
5a. epsilon removes each slice's worktree and branch as soon as the slice is merged. The integration worktree and any unmerged slice (for example one stopped after 3 HOLD rounds) stay until the user removes them.
6. epsilon uses these commands instead of writing git worktree steps itself.
6a. The commands are tools of a portable MCP server (Agent Plugins `mcp.json`), so any Agent Plugins client and Claude Code can call them; the same program also runs from a terminal. It needs nothing installed beyond Python 3 and git.

### Project configuration

7. Each project can describe itself in a `.gauntlet.json`: the integration branch, shared folders, check commands, and any one-time setup step before a loop. Without the file, the gauntlet asks once and offers to write it.
8. ControlTower's configuration captures today's facts: shared `node_modules`, the four checks, and the Node rebuild before a loop.

### Install and update

9. The plugin installs from the private repo `callmeradical/gauntlet`, which is also its marketplace: this Mac first, then the user's other machines. The README documents each machine's setup, including GitHub access for the private repo.
10. Updating the plugin never changes a loop already running.
11. Once installed, the plugin is the single source: Claude Code's loose copies are removed, and other tools' copies are symlinks into the plugin repo. The switch happens only while no loop is running.

## Experience

After installing, the agents and skills appear as today. Starting work is unchanged: intake, then epsilon. The user can run `gauntlet status` to see loops and `gauntlet worktree rm` to clean up.

## Open questions

1. *Decided (2026-11-03):* where it lives: a private repo that is also its own marketplace, `callmeradical/gauntlet`.
1a. *Decided (2026-11-03):* the package follows the Agent Plugins 1.0.0 spec (https://agent-plugins.org/specification), with Claude Code's own manifest and agents alongside, since agents are outside that spec's core.
2. What replaces the loose copies: remove `~/.claude/agents/{alpha,beta,gamma,delta,epsilon}.md`, the dotfiles copies, and the skill symlinks once the plugin is installed, or keep any? *Decided (2026-11-03): in Claude Code, remove `~/.claude/agents/{alpha,beta,gamma,delta,epsilon}.md` and the `~/.claude/skills/{intake,gauntlet-loop}` links once the plugin is installed (they would take precedence over the plugin's). For other tools, `~/.augy/skills/{intake,gauntlet-loop}` and `~/.agents/agents/*.md` become symlinks into the plugin repo, dropped for any tool that loads Agent Plugins directly. The switch waits until no loop is running.*
3. How is the `gauntlet` command delivered: a portable MCP server (works in any Agent Plugins client and in Claude Code) or a Claude-only script on PATH? *Decided (2026-11-03): a portable MCP server declared in `mcp.json`, written as one Python file using only the standard library, which also runs as a command-line tool (`gauntlet status`).*
4. Should loop cleanup run automatically after a loop's work is released, or only when asked? *Decided (2026-11-03): epsilon removes each slice's worktree and branch as soon as the slice is merged; the integration worktree and anything unmerged stay until the user runs `gauntlet worktree rm`; `gauntlet status` flags finished loops that still have worktrees.*
5. How should agent names appear once namespaced? *Resolved by fact (2026-11-03): Claude Code namespaces plugin agents as `gauntlet:<name>`, and loose copies in `~/.claude/agents` take precedence, so instructions use the namespaced names (requirement 1b).*
6. Which machines get it first (this Mac and the user's other machines), and does a Linux machine need anything different? *Decided (2026-11-03): this Mac first; the other machines once back on the home network, each after GitHub access for `callmeradical` is set up (gh login and setup-git, or a passphrase-free SSH key). Nothing is platform-specific; the README carries a per-machine install section.*
7. Should alpha and beta, the user's original definitions, be rewritten as task directives like the others? *Decided (2026-11-03): yes; same behavior, wording reviewed against the originals.*
8. How does alpha get TDD guidance? *Decided (2026-11-03): bundle the `tdd` skill with the plugin and reference it from alpha; don't summarize it.*
9. Who agrees the seams the tdd skill tests at? *Decided (2026-11-03): the OpenSpec change does: its scenarios and design interfaces are the seams; delta carries them into each slice brief; the user isn't asked.*
10. What does zeta do? *Decided (2026-11-03): answers alpha's design questions only when asked, narrowly, grounded in the repo first; advisory only; no contact with beta or its bar.*
