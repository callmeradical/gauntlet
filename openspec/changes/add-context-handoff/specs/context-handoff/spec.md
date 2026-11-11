# Spec Delta

## Purpose

Defines context handoffs across gauntlet roles.

## ADDED Requirements

### Requirement: Handoff skill
The plugin SHALL bundle a `handoff` skill that writes a handoff document to `~/.local/state/gauntlet/handoffs/`, naming the loop, slice or queue item, branch, worktree and exact head commit, with done work and evidence, an ordered checklist, open decisions and owners, promises, running subagents and jobs, and environment rules, ending with "Suggested skills".

#### Scenario: Skill contents
- **WHEN** `skills/handoff/SKILL.md` is inspected
- **THEN** it names the durable location, the required contents, references by path, redaction, "unverified", the "Continue from handoff <path>" prompt, and its last section is "Suggested skills".

### Requirement: Handoff rule in every role
Every agent and the `gauntlet-loop` skill SHALL contain a "Context handoffs" section: at `handoff.context_threshold` stop at a clean point, write a handoff with the `handoff` skill, hand over to a successor of the same role, and announce it in the coordination channel, if any.

#### Scenario: Worker hands off
- **WHEN** alpha, beta, gamma, delta, zeta or eta reaches the threshold
- **THEN** it reports the handoff path to the orchestrator, which starts the successor.

#### Scenario: Orchestrator hands off
- **WHEN** epsilon reaches the threshold
- **THEN** it starts its own successor and records the handoff with `loop_update` `handoff`.

#### Scenario: Critic hands off mid-review
- **WHEN** beta or eta must hand off before finishing
- **THEN** it reports "incomplete" and the handoff path, not PASS or HOLD, and the successor redoes every bar item whose evidence is not recorded.

### Requirement: Configurable threshold
`config_read` SHALL return `handoff.context_threshold` (default 0.65) and SHALL report `config_invalid` for a non-object `handoff`, an unknown key, or a threshold that is not a number strictly between 0 and 1.

#### Scenario: Invalid threshold
- **WHEN** `.gauntlet.json` has `"handoff": {"context_threshold": 1.5}`
- **THEN** `config_read` fails with `config_invalid` and field `handoff.context_threshold`.

### Requirement: Handoffs in loop state
`loop_update` SHALL accept `handoff` and append `{path, at[, slice]}` to the loop's `handoffs`.

#### Scenario: Recorded handoff
- **WHEN** `loop_update(loop, slice="tracer", handoff=p)` is called
- **THEN** the state's `handoffs` ends with `{path: p, at: <time>, slice: "tracer"}`.

### Requirement: Agents launch on pi
Every agent with a `tools` line SHALL include at least one pi built-in tool name, and eta and zeta SHALL include no pi write tools.

#### Scenario: eta on pi
- **WHEN** eta's tools are inspected
- **THEN** they include `read`, `grep`, `find`, `ls` and none of `bash`, `edit`, `write`.
