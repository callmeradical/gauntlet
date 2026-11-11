# Proposal

## Why

[004 · Intake grounding and pre-grilling stress test](../../../docs/prd/004-intake-grounding-and-stress-test.md): The gauntlet provides cold-context verification via `gauntlet:eta` and `gauntlet:beta`, ensuring specifications and code slices are evaluated without author rationalization. However, the intake workflow (`intake` skill) currently suffers from cross-session amnesia and unstructured human grilling. When an agent begins drafting a PRD or OpenSpec change, it operates primarily on immediate prompt context, forgetting settled architectural decisions (`D*`), rejected alternatives, and domain invariants recorded in past PRDs (`docs/prd/`) and archived changes (`openspec/changes/archive/`). Furthermore, agents frequently ask open-ended grilling questions that transfer the design burden to the human operator before the proposal has been stress-tested for edge cases, operational blast radius, and migration hazards.

**Decided (2026-11-11, 004 grilling):** Require `intake` to ground new proposals in historical repository decisions before drafting; mandate an autonomous multi-perspective stress test ("Shootdown") of the draft PRD before interactive grilling; forbid open-ended grilling questions by requiring multiple-choice options with a recommended answer listed first; and enforce traceability at the gate so prior settled decisions cannot be silently overturned.

## What Changes

- **Historical Retrieval in Intake**: `plugins/gauntlet/skills/intake/SKILL.md` Step 1 (PRD) and Step 3 (OpenSpec) updated to mandate scanning existing PRDs (`docs/prd/*.md`) and archived changes (`openspec/changes/archive/**`) for settled decisions (`D*`), domain models, and rejected alternatives.
- **Autonomous Pre-Grilling Stress-Testing ("Shootdown")**: `plugins/gauntlet/skills/intake/SKILL.md` Step 2 (Grilling) updated with an autonomous pre-grilling shootdown evaluating failure modes, operational risks, migration/rollback hazards, and surface minimalism.
- **Structured Multiple-Choice Grilling**: `plugins/gauntlet/skills/intake/SKILL.md` Step 2 updated to mandate that all grilling questions provide multiple-choice options with trade-offs and put the recommended option first (`(Recommended)`). Open-ended questions are strictly forbidden.
- **Explicit Superseding Traceability**: `plugins/gauntlet/skills/intake/SKILL.md` Step 1, Step 3, and Step 4 (Gate) require that any deviation from a prior settled decision cite `Supersedes: NNN/DX` with clear rationale.
- **Tests**: `tests/test_skills.py` updated to verify historical retrieval instructions, pre-grilling shootdown requirements, structured multiple-choice grilling rules, and gate checks in `intake`.

## Capabilities

### New Capabilities
- `intake-historical-grounding`: Mandates scanning past PRDs and archived OpenSpec changes, extracting settled decisions (`D*`), and requiring explicit citation when superseding.
- `intake-pre-grilling-stress-test`: Mandates autonomous multi-perspective shootdown before grilling and framing all questions as structured multiple-choice selections with a recommended option first.
- `intake-traceability-gate`: Gate checks ensuring no silent deviations from settled decisions and all grilling questions resolved.

### Modified Capabilities

## Impact

- Updates `plugins/gauntlet/skills/intake/SKILL.md`. No breaking changes to existing git worktree or CLI server tools.
