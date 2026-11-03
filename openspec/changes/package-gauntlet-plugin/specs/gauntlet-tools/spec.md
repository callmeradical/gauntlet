# Spec Delta

## Purpose

The gauntlet MCP server and command line: starting and tracking loops, creating and removing worktrees, merge locks, cleanup, and status, the same way every run.

## ADDED Requirements

### Requirement: A loop is registered before it runs
Starting a loop SHALL record its id, repo, change, and integration branch in the state folder (`~/.local/state/gauntlet/`), and SHALL refuse when a running loop already has the same id or works on the same change in the same repo. Loop ids SHALL be kebab-case, at most 24 characters. Updates SHALL record the phase and each slice's worktree, branch, status, round, latest commit, and verdict; ending a loop SHALL record `done`, `stopped`, or `failed`.

#### Scenario: Duplicate id
- **WHEN** a loop `pri` is running and another loop asks to start as `pri`
- **THEN** the start is refused, naming the running loop

### Requirement: Worktrees are created the same way every time
Creating a slice's worktree SHALL add a worktree at `<repo-parent>/<repo>-<loop>-<slice>` on branch `gauntlet/<loop>/<slice>` from the loop's integration branch, link each shared folder from the project configuration into it, keep those links out of git, and record the worktree in the loop's state.

#### Scenario: Shared folder
- **WHEN** a ControlTower slice worktree is created
- **THEN** its `node_modules` links to the integration worktree's and `git status` in the new worktree shows it as ignored, not untracked

### Requirement: Removal never loses unmerged work
Removing a loop's or slice's worktrees SHALL delete each worktree and its branch only when the branch has no commits missing from the loop's integration branch; otherwise it SHALL keep that worktree and report it. Removing a slice after its merge SHALL succeed without the user.

#### Scenario: Unmerged slice
- **WHEN** removal is asked for a loop whose stopped slice has two unmerged commits
- **THEN** the merged slices are removed and the stopped slice is kept and reported

### Requirement: Merges into a shared integration branch are serialized
Taking the merge lock for a repo and integration branch SHALL succeed only when no other loop holds it or the holder's lock is older than 30 minutes, and SHALL record the holder; releasing SHALL succeed only for the holder.

#### Scenario: Concurrent merge
- **WHEN** loop `a` holds the lock and loop `b` asks for it
- **THEN** `b` is refused with `a`'s id and when it took the lock

### Requirement: Status shows loops, worktrees, and leftovers
Status SHALL list each loop with its repo, change, phase, worktrees, and any lock it holds, and SHALL flag finished loops that still have worktrees.

#### Scenario: Finished loop with leftovers
- **WHEN** a loop is `done` and its integration worktree remains
- **THEN** status lists it as finished with one worktree left

### Requirement: The same program serves MCP and the terminal
The server SHALL run over MCP stdio (initialize, list tools, call tools) and SHALL also run from a terminal with subcommands matching its tools (`status`, `worktree new`, `worktree rm`, `lock`, `loop`), using only Python 3's standard library and git, on macOS and Linux.

#### Scenario: Terminal status
- **WHEN** the user runs `gauntlet status`
- **THEN** the same information as the status tool is printed
