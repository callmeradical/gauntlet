# 004 · Intake grounding and pre-grilling stress test

**Status:** Proposed · **Extends:** 001 · **Drafted:** 2026-11-11

## Summary

Complements Gauntlet's cold-context specification critic (`gauntlet:eta`) with cross-session architectural grounding and autonomous pre-grilling stress-testing in the `intake` workflow. Before grilling the human operator or authoring changes, `intake` retrieves settled architectural decisions and rejected alternatives across all past PRDs and archived OpenSpec changes. Furthermore, before interactive grilling begins, the drafting agent autonomously stress-tests the draft PRD against failure modes, migration risks, and blast radius to formulate high-leverage multiple-choice trade-offs with recommended answers, replacing open-ended questioning and eliminating amnesia.

## Problem

- **Cross-Session Amnesia**: When initiating a new feature or change, agents operate primarily on the immediate prompt. Past settled decisions (`D*`), hard-won architectural patterns, and rejected alternatives recorded in earlier PRDs (`docs/prd/`) or archived changes (`openspec/changes/archive/`) are forgotten or ignored.
- **Silent Invariant Invalidation**: A new PRD can contradict earlier foundational architectural decisions without acknowledging or explaining the deviation, creating conflicting requirements across the repository.
- **High Human Grilling Burden**: During interactive grilling, agents frequently ask broad, open-ended questions (e.g. "How should we handle failure?", "What database should we use?"). This offloads the entire synthesis burden onto the human operator instead of having the agent research facts and offer structured multiple-choice options with reasoned recommendations.
- **Premature Grilling with Unidentified Edge Cases**: Grilling often begins before the draft PRD has been stress-tested for edge cases, operational blast radius, or rollback risks, causing obvious structural flaws to surface late in the cycle (or during the `gauntlet:eta` gate).

## Proposal

1. **Historical Memory & Decision Grounding**:
   - In Step 1 (PRD authoring) and Step 3 (OpenSpec drafting), `intake` mandates scanning existing repository PRDs (`docs/prd/*.md`) and archived OpenSpec changes (`openspec/changes/archive/**`).
   - The agent extracts settled decisions (`D*`), previously rejected alternatives, and established domain invariants.
   - Any proposal touching an area governed by a prior decision must explicitly adhere to it or formally declare a superseding decision (`Supersedes: NNN/DX`) with explicit rationale.
2. **Autonomous Pre-Grilling Stress-Testing ("Shootdown")**:
   - Before grilling the human operator (Step 2), the drafting agent executes an autonomous stress test ("Shootdown") against the draft PRD across four dimensions: failure modes & edge cases, operational blast radius, migration/rollback hazards, and scope minimalism.
   - The agent uses the findings of the shootdown to formulate crisp, structured multiple-choice questions for the remaining architectural decisions.
   - Every question posed to the user must provide distinct numbered options, put the recommended option first (prefixed with `(Recommended)`), and state the trade-offs of each choice. Open-ended questions are strictly disallowed.
3. **Traceability Gate Integration**:
   - `gauntlet:eta` and the Step 4 Gate verify that the draft PRD does not contradict active prior settled decisions (`D*`) unless an explicit superseding rationale is documented.

## Out of scope

- Modifying the OpenSpec change directory format or core CLI tooling.
- Changing `gauntlet:alpha` or `gauntlet:beta` slice-execution behaviors.
- Automatic interactive prompts outside the CLI / terminal session.

## Users and scenarios

- *"When I ask to add a new storage mechanism, `intake` detects that PRD 001 already decided on SQLite with a specific schema migration strategy, and either aligns with it or asks if we intend to supersede decision 001/D2."*
- *"When intake moves to grilling, instead of asking 'How should error handling work?', it presents 3 concrete options with the recommended failure-mode strategy, explaining the trade-offs so I can answer with a single number."*
- *"Eta catches if a new PRD silently reverts a settled decision from an earlier archived change without stating why."*

## Requirements

- **R1**: Step 1 (PRD Authoring) of `intake` mandates reading all active repository PRDs (`docs/prd/*.md`) and archived changes (`openspec/changes/archive/**`) to retrieve settled decisions (`D*`) and prior rejected alternatives.
- **R2**: If a new PRD touches an invariant or area governed by an existing settled decision, it must either uphold the decision or explicitly cite it in a dedicated "Superseded decisions" section with clear rationale.
- **R3**: Prior to interactive grilling (Step 2), the agent performs an autonomous multi-perspective stress test ("Shootdown") against the draft PRD, evaluating failure modes, operational risks, migration/rollback hazards, and surface minimalism.
- **R4**: Grilling questions must be presented as structured multiple-choice options with a recommended answer listed first (`(Recommended)`), complete with pros/cons. Open-ended grilling questions are forbidden; factual lookups must be performed autonomously by the agent in repository code and docs.
- **R5**: Step 3 (OpenSpec Drafting) verifies consistency with retrieved historical decisions and rejected alternatives, ensuring known failure modes documented in past changes are avoided.
- **R6**: The Step 4 Gate verifies that historical decisions have not been silently violated and all grilling questions were resolved as recorded `D*` decisions.

## Settled decisions

- **D1**: Historical context is derived directly from repository artifacts (`docs/prd/` and `openspec/changes/archive/`) without requiring an external database or indexing service.
- **D2**: Grilling questions must always offer multiple-choice selections with the recommended option first; the human operator should never be asked an open-ended question during intake.
- **D3**: Superseding a prior settled decision requires explicit attribution (`Supersedes: <PRD-NUM>/<DECISION-ID>`) in the PRD; silent overrides are rejected at the intake gate.
