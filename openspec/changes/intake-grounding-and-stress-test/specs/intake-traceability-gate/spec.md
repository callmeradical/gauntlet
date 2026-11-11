# Spec Delta

## Purpose

Defines requirements for verifying historical decision consistency and question resolution at the intake gate.

## ADDED Requirements

### Requirement: Historical Consistency Check at Gate
Step 4 (Gate) of the `intake` skill SHALL verify that the PRD and OpenSpec change do not silently contradict any prior active settled decisions (`D*`) and that any superseded decisions are explicitly documented.

#### Scenario: Verification of historical consistency
- **WHEN** the agent evaluates the Step 4 gate checklist
- **THEN** it checks that no prior settled decision has been silently violated without an explicit superseding citation.

### Requirement: Complete Question Resolution Verification
Step 4 (Gate) of the `intake` skill SHALL verify that all questions identified during pre-grilling shootdown and grilling have been resolved and recorded as settled decisions (`D*`).

#### Scenario: Undecided shootdown risk at gate
- **WHEN** an identified failure mode or architectural trade-off from grilling remains undecided
- **THEN** the gate check fails and returns the proposal to Step 2 (Grilling) for resolution.
