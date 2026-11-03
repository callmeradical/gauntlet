# Spec Delta

## Purpose

What the gauntlet plugin contains and how one package serves both Agent Plugins clients and Claude Code.

## ADDED Requirements

### Requirement: The plugin conforms to Agent Plugins 1.0.0
The plugin directory SHALL contain a `plugin.json` valid against the Agent Plugins 1.0.0 plugin schema (name `gauntlet`, a version, description, author, repository, license), a `skills/` directory whose immediate subdirectories `intake` and `gauntlet-loop` each contain a `SKILL.md` in Agent Skills format, and an `mcp.json` valid against the Agent Plugins 1.0.0 MCP schema declaring the gauntlet server as a stdio server. Plugin-relative paths SHALL start with `./` and stay inside the plugin.

#### Scenario: Schema validation
- **WHEN** `plugin.json` and `mcp.json` are validated against the published 1.0.0 schemas
- **THEN** both validate without errors

### Requirement: The same package installs as a Claude Code plugin and marketplace
The repo root SHALL contain a Claude Code `marketplace.json` listing the plugin, and the plugin SHALL contain a Claude Code `plugin.json`, an MCP configuration declaring the same gauntlet server, and an `agents/` directory with delta, alpha, beta, gamma, and epsilon. The skills SHALL exist once and serve both formats.

#### Scenario: Local Claude Code load
- **WHEN** Claude Code is started with the plugin directory
- **THEN** the agents `gauntlet:delta`, `gauntlet:alpha`, `gauntlet:beta`, `gauntlet:gamma`, and `gauntlet:epsilon`, the two skills, and the gauntlet server's tools are available

### Requirement: Bundled files are found inside the plugin
The progress-page template SHALL live inside the gauntlet-loop skill's folder, and agents and skills SHALL refer to the template and the server by their location inside the installed plugin, never by a path in the user's home folder.

#### Scenario: Template location
- **WHEN** gamma writes a progress page
- **THEN** it reads the template from the installed plugin

### Requirement: Agents and skills use the plugin's names and tools
Agent and skill instructions SHALL name agents as `gauntlet:<agent>`, SHALL use the gauntlet server's tools for loops, worktrees, locks, and cleanup instead of spelling out git worktree steps, and SHALL remain written as task directives without personification.

#### Scenario: epsilon creates a slice
- **WHEN** epsilon starts a slice
- **THEN** it calls the server's worktree tool and spawns `gauntlet:alpha`
