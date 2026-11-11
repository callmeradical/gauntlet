# gauntlet

A build/review loop with separated roles, packaged as one plugin. An OpenSpec change goes in; reviewed, merged code comes out. The builder never sees the reviewer's bar, and the reviewer never sees the builder's reasoning.

It follows [Agent Plugins 1.0.0](https://agent-plugins.org/specification), so its skills and MCP server load in any Agent Plugins client, and installs natively in Claude Code, which adds the agents.

## Install

You need Claude Code, `python3` 3.9 or later, and git. `intake` also calls three skills the plugin doesn't bundle: `write-a-prd`, `grilling`, and `prd-to-spec`. In Claude Code:

```
/plugin marketplace add callmeradical/gauntlet
/plugin install gauntlet@gauntlet
```

Restart Claude Code. `/agents` lists seven `gauntlet:` agents and `/mcp` shows the `gauntlet` server. For the terminal command, moving off older loose copies, other machines, and updating, see [docs/install.md](docs/install.md).

## How it works

| Agent | Role |
|---|---|
| `gauntlet:eta` | Audits the PRD and OpenSpec change together before slicing |
| `gauntlet:delta` | Slices an OpenSpec change into a tracer bullet plus vertical slices |
| `gauntlet:alpha` | Builds one slice test-first in its own worktree |
| `gauntlet:beta` | Reviews a slice with fresh context and returns PASS or HOLD |
| `gauntlet:zeta` | Answers alpha's design questions when asked; never sees beta's bar |
| `gauntlet:gamma` | Keeps the loop's progress page; reports facts only |
| `gauntlet:epsilon` | Runs all of the above and merges PASSed slices one at a time |

A HOLD names the single biggest gap and becomes alpha's next task. A slice that holds three times on the same gap stops and comes back to you. Nothing is pushed or released without you.

## Using it

### 1. Describe the project once

Add a `.gauntlet.json` at the repo root with the integration branch, folders to share between worktrees, the checks every slice must pass, and any one-time setup:

```json
{
  "integration_branch": "main",
  "shared": [],
  "checks": [{"name": "test", "command": "npm test"}],
  "setup": null
}
```

If it's missing, epsilon asks for these and offers to write it. Fields and rules: [docs/configuration.md](docs/configuration.md).

### 2. Take the work through intake

```
/gauntlet:intake <what you want to build>
```

Intake writes a PRD (what and why), grills you one question at a time until no open question is left, writes an OpenSpec change (how), and checks a gate: no undecided questions, a strictly valid change, a verification for every task, PRD and change in agreement, and your go-ahead. Intake runs in your session because grilling needs you.

### 3. Hand the change to epsilon

Ask Claude to have `gauntlet:epsilon` build it, naming the change, the integration branch, and a loop id:

```
Have gauntlet:epsilon build openspec change add-export as loop export, integrating into main.
```

epsilon re-checks the gate, runs delta, builds the tracer slice first, then fans the remaining slices out to parallel alphas in their own worktrees. Each slice gets a fresh beta; PASSed slices merge one at a time with the full checks after each, and each merged slice's worktree is removed. It stops before any release or push and reports what merged, test results, beta's unfixed notes, and checks left for you.

A question a builder would have to guess at stops that slice and comes back to you; the answer goes into the PRD or spec before the slice resumes.

### 4. Watch it

```sh
gauntlet status
```

lists every loop with its phase, worktrees, and merge locks, and flags finished loops that still have worktrees. gamma keeps a progress page per loop at `~/wiki/features/<project>-<loop>-progress.html`.

### 5. Clean up

```sh
gauntlet worktree rm <loop>
```

removes a finished loop's integration worktree and any slice worktrees, and refuses to remove a branch with unmerged commits.

### One small task

For a single, well-scoped task, skip epsilon and use the loop directly:

```
/gauntlet:gauntlet-loop <the task and the bar it must meet>
```

alpha builds, a fresh beta judges against the bar, and HOLD feedback goes back to alpha until PASS.

### Context handoffs

Every role hands off to a fresh agent of the same role when its context reaches `handoff.context_threshold` in `.gauntlet.json` (default 0.65). It stops at a clean point, writes a handoff document with the bundled `handoff` skill to `~/.local/state/gauntlet/handoffs/`, and the successor starts with "Continue from handoff <path>". Builders and critics report the path to epsilon, which launches the successor; epsilon starts its own successor and records each handoff in the loop state (`gauntlet loop update <loop> --handoff <path>`). A critic that hands off reports "incomplete", never a verdict from partial evidence.

### Several loops at once

Give each loop its own id. Loops never share an id, a change, a worktree, or a branch; merges into a shared integration branch take a lock, and `gauntlet status` shows who holds it. Update the plugin only while no loop is running.

## More

- [docs/install.md](docs/install.md): requirements, per-machine setup, the terminal command, cutover from loose copies, updating
- [docs/configuration.md](docs/configuration.md): `.gauntlet.json` reference
- [docs/reference.md](docs/reference.md): agents, skills, server tools and CLI, state and locks, layout
- [docs/development.md](docs/development.md): checks, releasing, publishing

## Credits

The plugin bundles two skills from [`mattpocock/skills`](https://github.com/mattpocock/skills) by Matt Pocock, at commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`, under the MIT licence:

- `plugins/gauntlet/skills/tdd`, from `skills/engineering/tdd`
- `plugins/gauntlet/skills/codebase-design`, from `skills/engineering/codebase-design`

Each folder keeps the upstream `LICENSE`, and each `SKILL.md` ends with a source line. The text is unchanged apart from moving reference files under `references/` and rewriting links to match. The upstream `agents/openai.yaml` files are left out.
