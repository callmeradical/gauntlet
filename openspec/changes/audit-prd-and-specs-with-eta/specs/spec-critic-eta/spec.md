# Spec Delta

## Purpose

Defines the `gauntlet:eta` agent: its role, inputs, tools, and dual-artifact verification rules.

## ADDED Requirements

### Requirement: gauntlet:eta agent definition
The plugin SHALL provide a read-only agent definition in `plugins/gauntlet/agents/eta.md` named `eta`, with tools `Read, Glob, Grep, Skill, WebFetch, WebSearch`. It SHALL NOT possess write, edit, bash execution, or agent spawning tools.

#### Scenario: Eta definition tools and frontmatter
- **WHEN** `eta.md` is inspected
- **THEN** its frontmatter `name` is `eta`, `tools` matches exactly `Read, Glob, Grep, Skill, WebFetch, WebSearch`, and its body contains no persona phrasing ("You are") or home folder paths.

### Requirement: eta audits PRD and OpenSpec change together
`eta` SHALL take three explicit inputs: the repository root, the PRD path, and the OpenSpec change directory. `eta` SHALL audit both documents together for 1:1 requirement traceability, absence of implementation details in the PRD, and unambiguous scenario definitions in the OpenSpec change.

#### Scenario: Missing PRD requirement in OpenSpec
- **WHEN** the PRD contains requirement `R3` and the OpenSpec change contains no scenario or spec delta covering `R3`
- **THEN** `eta` issues a `HOLD` citing the missing requirement `R3` under the Comprehension lens.

### Requirement: eta verdict format
`eta` SHALL return exactly one of two verdicts: `PASS` when the PRD and OpenSpec change satisfy all checks, or `HOLD` naming the single biggest remaining specification gap, the failing lens, and the exact section or scenario.

#### Scenario: Unambiguous pass
- **WHEN** every PRD requirement maps to an OpenSpec scenario, no open questions remain, and every scenario is testable without guessing
- **THEN** `eta` returns a concise `PASS`.
