# Spec Delta

## Purpose

How a project tells the gauntlet its integration branch, shared folders, checks, and one-time setup, so agents carry no project specifics.

## ADDED Requirements

### Requirement: A project describes itself in .gauntlet.json
A project MAY contain `.gauntlet.json` at its root with: the default integration branch, shared folders to link into slice worktrees, the check commands (each with a name and a command), and an optional setup command to run once before a loop. The server SHALL read and validate it and report errors by field.

#### Scenario: Invalid field
- **WHEN** `.gauntlet.json` lists `shared` as a string instead of a list
- **THEN** reading it reports the `shared` field as invalid

### Requirement: Without a config the gauntlet asks once
When a project has no `.gauntlet.json`, starting a loop SHALL report that it's missing; epsilon SHALL ask the caller for the integration branch, shared folders, checks, and setup, and offer to write the file.

#### Scenario: New project
- **WHEN** a loop starts in a repo without `.gauntlet.json`
- **THEN** epsilon returns the questions instead of guessing

### Requirement: ControlTower is configured
ControlTower SHALL get a `.gauntlet.json` with integration branch `feat/decision-tree`, shared folder `node_modules`, the checks `npx vitest run`, `npm run build:ts`, `npm run build:app`, and `npx tsc --noEmit -p src/renderer`, and setup `npm run rebuild:node`.

#### Scenario: ControlTower slice
- **WHEN** a ControlTower loop creates a slice
- **THEN** `node_modules` is linked and the checks come from the file
