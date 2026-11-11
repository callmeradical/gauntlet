# intake-historical-grounding Specification

## Purpose
Defines requirements for cross-session historical grounding and decision retrieval in the intake workflow.

## Requirements

### Requirement: Historical Retrieval During PRD and OpenSpec Authoring
The `intake` skill SHALL require the authoring agent to scan existing PRDs in `docs/prd/*.md` and archived OpenSpec changes in `openspec/changes/archive/**` during Step 1 (PRD authoring) and Step 3 (OpenSpec drafting) to retrieve settled decisions (`D*`), domain models, and previously rejected alternatives.

#### Scenario: Retrieval before PRD drafting
- **WHEN** an agent begins Step 1 of the intake workflow
- **THEN** it reads existing PRDs in `docs/prd/` and archived changes in `openspec/changes/archive/` to extract relevant settled decisions and rejected alternatives before drafting new requirements.

### Requirement: Explicit Superseding of Settled Decisions
The `intake` skill SHALL require that any new PRD or OpenSpec change that alters, replaces, or contradicts an existing settled decision (`D*`) must explicitly cite the superseded decision (e.g., `Supersedes: NNN/DX`) with a clear rationale. Silent contradictions are forbidden.

#### Scenario: Contradicting a prior decision without citation
- **WHEN** a draft PRD proposes a behavior that contradicts an existing settled decision without citing it
- **THEN** the proposal fails the intake grounding requirements and must be amended to either adhere or explicitly declare the superseding decision.

#### Scenario: Legitimate superseding with attribution
- **WHEN** a draft PRD intentionally changes an earlier architectural decision
- **THEN** the PRD contains an explicit section citing `Supersedes: <PRD-NUM>/<DECISION-ID>` with the rationale for superseding the prior decision.
