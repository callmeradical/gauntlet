# gating-workflow Specification

## Purpose
Defines the dual-gate integration in the `intake` skill and `gauntlet:epsilon` orchestrator.

## Requirements

### Requirement: Intake Gate requires eta PASS
The `intake` skill at Step 4 (Gate) SHALL require running `gauntlet:eta` with the PRD and OpenSpec change paths, passing only when `eta` issues a `PASS`. A `HOLD` from `eta` SHALL halt the intake process and return to grilling.

#### Scenario: Intake gate failure
- **WHEN** `gauntlet:eta` returns `HOLD` on a drafted change during intake
- **THEN** the gate check fails and the operator resolves the cited gap before proceeding to hand-off.

### Requirement: Epsilon pre-flight verifies eta
`gauntlet:epsilon` and the `gauntlet-loop` skill SHALL mandate verifying `gauntlet:eta` on the PRD and OpenSpec change before invoking `gauntlet:delta` or creating worktrees. If `eta` returns `HOLD`, `epsilon` SHALL abort without creating git branches or worktrees.

#### Scenario: Epsilon pre-flight abort
- **WHEN** `epsilon` runs on a change that fails `gauntlet:eta`
- **THEN** `epsilon` halts with `spec_gate_failed` and creates no slice branches or worktrees.
