# Spec Delta

## Purpose

Installing the plugin on a machine and switching from the loose agent and skill copies to the plugin without changing a running loop.

## ADDED Requirements

### Requirement: Each machine has documented setup
The README SHALL document, per machine: GitHub access for the private repo (gh login and setup-git, or a passphrase-free SSH key), adding the marketplace and installing the plugin in Claude Code, putting `gauntlet` on the terminal PATH, and running the cutover.

#### Scenario: New machine
- **WHEN** the user follows the README on a machine with Claude Code, Python 3, and git
- **THEN** the plugin's agents, skills, and tools are available and `gauntlet status` runs

### Requirement: Cutover runs only when no loop is running
The cutover SHALL refuse while any loop is running. Otherwise it SHALL back up the files it changes, remove `~/.claude/agents/{alpha,beta,gamma,delta,epsilon}.md` and the `~/.claude/skills/{intake,gauntlet-loop}` links, and replace `~/.augy/skills/{intake,gauntlet-loop}` and `~/.agents/agents/{alpha,beta,gamma,delta,epsilon}.md` with symlinks into the repo.

#### Scenario: Loop running
- **WHEN** the cutover is run while loop `pri-fixes` is running
- **THEN** it changes nothing and names the running loop

### Requirement: Cutover can be rolled back
The cutover SHALL record what it changed, and a rollback SHALL restore every changed file from the backup.

#### Scenario: Rollback
- **WHEN** the user rolls back after a cutover
- **THEN** every file and link is as it was before

### Requirement: Updates never change a running loop
Plugin versions SHALL be bumped for each release, and the README SHALL say to update only while no loop is running.

#### Scenario: Update during a loop
- **WHEN** a new version is published while a loop runs
- **THEN** the loop keeps the definitions it started with until it ends
