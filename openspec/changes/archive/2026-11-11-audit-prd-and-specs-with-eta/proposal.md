# Proposal

## Why

[002 · Cold spec critic (eta) and orthogonal review lenses](../../../docs/prd/002-cold-spec-critic-eta.md): The gauntlet isolates builders from grading their own work during code delivery via `gauntlet:beta`, but lacks cold-context verification during the specification phase. The agent that drafts an OpenSpec change shares the conversational context and unspoken assumptions of the intake grilling session. Without an independent critic auditing the PRD and OpenSpec change together, technical specs can omit PRD requirements (`R*`), violate settled decisions (`D*`), leak implementation details into the PRD, or leave scenarios ambiguous. Furthermore, `gauntlet:beta`'s slice reviews lack structured boundaries, risking subjective nitpicks rather than targeted architectural invariants.

**Decided (2026-11-10, 002 grilling):** Introduce `gauntlet:eta`, a read-only agent that audits the PRD and OpenSpec change together from a clean, zero-context state before slicing begins; structure all critic evaluations (`beta` and `eta`) across four non-overlapping lenses (Comprehension, Invariant Safety, Blast Radius & Rollback, Surface Minimization); invoke `eta` both in `intake` at Step 4 (Gate) and as `epsilon`'s pre-flight check before slicing.

## What Changes

- **New Agent (`gauntlet:eta`)**: `plugins/gauntlet/agents/eta.md` defining the pre-flight spec critic. Read-only tools (`Read`, `Glob`, `Grep`, `Skill`, `WebFetch`, `WebSearch`), zero access to intake conversational transcripts or reasoning, taking the repo root, PRD path, and OpenSpec change path. Returns `PASS` or `HOLD` naming the single biggest gap.
- **Updated Agent (`gauntlet:beta`)**: `plugins/gauntlet/agents/beta.md` updated to evaluate slice artifacts strictly along the four orthogonal lenses, forbidding subjective cosmetic or style nitpicks.
- **Updated Intake Skill**: `plugins/gauntlet/skills/intake/SKILL.md` updated at Step 4 (Gate) to require running `gauntlet:eta` with the PRD and change paths, passing only when `eta` issues a `PASS`.
- **Updated Orchestration & Loop Skill**: `plugins/gauntlet/agents/epsilon.md` and `plugins/gauntlet/skills/gauntlet-loop/SKILL.md` updated to verify `gauntlet:eta` before invoking `gauntlet:delta` or creating worktrees.
- **Tests**: `tests/test_agents.py` updated to include `eta` in the agent fleet checks; new unit tests in `tests/test_eta.py` verifying `eta`'s definition, dual-artifact audit instructions, tool constraints, and absence of persona/home-path violations.

## Capabilities

### New Capabilities
- `spec-critic-eta`: Defines the `gauntlet:eta` agent, inputs, checks, and verdict rules for auditing the PRD and OpenSpec change together.
- `orthogonal-review-lenses`: Defines the four non-overlapping review dimensions across `gauntlet:beta` and `gauntlet:eta`.
- `gating-workflow`: Defines the dual-gate integration in `intake` and `epsilon`.

### Modified Capabilities

## Impact

- Plugin files in `plugins/gauntlet/agents/` and `plugins/gauntlet/skills/` updated. No breaking changes to existing git worktree or CLI server tools.
