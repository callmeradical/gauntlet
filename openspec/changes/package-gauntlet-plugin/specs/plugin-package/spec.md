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
The repo root SHALL contain a Claude Code `marketplace.json` listing the plugin, and the plugin SHALL contain a Claude Code `plugin.json`, an MCP configuration declaring the same gauntlet server, and an `agents/` directory with delta, alpha, beta, gamma, epsilon, and zeta. The skills SHALL exist once and serve both formats.

#### Scenario: Local Claude Code load
- **WHEN** Claude Code is started with the plugin directory
- **THEN** the agents `gauntlet:delta`, `gauntlet:alpha`, `gauntlet:beta`, `gauntlet:gamma`, `gauntlet:epsilon`, and `gauntlet:zeta`, the skills intake, gauntlet-loop, tdd, and codebase-design, and the gauntlet server's tools are available

### Requirement: Third-party skills are bundled with their license
The plugin SHALL bundle the `tdd` skill (with `tests.md` and `mocking.md`) and the `codebase-design` skill (with `DEEPENING.md` and `DESIGN-IT-TWICE.md`) from `mattpocock/skills`, unchanged apart from link paths and reference files moved under `references/`, with the MIT license text and attribution to the source repository and path.

#### Scenario: License notice
- **WHEN** the bundled skills are inspected
- **THEN** each skill folder carries the MIT notice and names `mattpocock/skills` and its source path

### Requirement: Bundled files are found inside the plugin
The progress-page template SHALL live inside the gauntlet-loop skill's folder, and agents and skills SHALL refer to the template and the server by their location inside the installed plugin, never by a path in the user's home folder.

#### Scenario: Template location
- **WHEN** gamma writes a progress page
- **THEN** it reads the template from the installed plugin

### Requirement: alpha builds test-first at the OpenSpec seams
alpha's definition SHALL direct it to follow the bundled `tdd` skill, overriding only who agrees the seams: the seams under test are those the OpenSpec change defines (its scenarios and the interfaces in its design), carried into the slice brief by delta, never confirmed with the user. alpha SHALL refactor only when beta's HOLD or the slice brief asks for it, keeping the full suite green before and after.

#### Scenario: Refactor request
- **WHEN** beta's HOLD says two adapters duplicate their parsing
- **THEN** alpha's next round removes the duplication with the suite green before and after, and changes nothing else

### Requirement: beta checks scenario coverage
beta's definition SHALL include in every bar that each scenario in the slice has a test at its seam, and that no test is tautological or coupled to implementation details, as the `tdd` skill defines them.

#### Scenario: Missing scenario test
- **WHEN** a slice's spec has three scenarios and the artifact tests two
- **THEN** beta returns HOLD naming the untested scenario

### Requirement: zeta advises alpha on design questions
The plugin SHALL include zeta. zeta SHALL answer only questions alpha asks, limited to the question, grounded first in the codebase's existing patterns (citing files), then the language's conventions, then general principles, using the bundled `codebase-design` vocabulary. zeta SHALL read code, write none, start no agents, and never assess alpha's work. beta SHALL never consult zeta, and zeta SHALL never receive beta's bar.

#### Scenario: Composition question
- **WHEN** alpha asks zeta whether three Mail adapters should share a base class
- **THEN** zeta answers with a recommendation, the repo files showing the existing pattern, and its reasons, and writes no code

### Requirement: alpha knows when and how to consult zeta
alpha's definition SHALL say when to consult zeta (a design choice the slice brief and the codebase's patterns don't settle) and how (start `gauntlet:zeta` with one question and the relevant files), that zeta is the only agent alpha may start, and that alpha lists the design questions it asked in its hand-back.

#### Scenario: Hand-back lists questions
- **WHEN** alpha consulted zeta about exporting a helper
- **THEN** alpha's hand-back lists that question, without zeta's reasoning

### Requirement: Agents and skills use the plugin's names and tools
Agent and skill instructions SHALL name agents as `gauntlet:<agent>`, SHALL use the gauntlet server's tools for loops, worktrees, locks, and cleanup instead of spelling out git worktree steps, and SHALL remain written as task directives without personification.

#### Scenario: epsilon creates a slice
- **WHEN** epsilon starts a slice
- **THEN** it calls the server's worktree tool and spawns `gauntlet:alpha`
