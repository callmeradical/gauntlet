# Design

## Context

The gauntlet uses separated roles to avoid rationalization in specification and code construction (`eta` audits specs cold, `alpha` builds test-first, `beta` reviews blind). However, during intake (`PRD → grilling → OpenSpec → gate`), the agent drafting the PRD or technical spec often starts from scratch, forgetting earlier architectural commitments made in prior iterations of the codebase. When it does grill the user, it often asks open-ended questions that force the human to formulate technical solutions from scratch.

This design introduces architectural memory retrieval and autonomous pre-grilling stress-testing ("Shootdown") to `intake`, ensuring every proposal is grounded in repository history and thoroughly vetted before engaging the human operator.

## Decisions

### 1. In-Repository Grounding without External Indexers
Historical grounding is performed directly against repository artifacts:
- Active PRDs: `docs/prd/*.md`
- Archived OpenSpec changes: `openspec/changes/archive/**`
- Domain models and project decisions (`D*`)

No external vector database, sidecar, or indexing daemon is required. Repository files are read directly via glob and file reading tools.

### 2. Autonomous Pre-Grilling Shootdown
Before presenting questions to the user in Step 2, the drafting agent runs an autonomous stress test across four specific failure categories:
1. **Edge Cases & Failure Modes**: What inputs, network partitions, concurrency conditions, or corrupted states break this?
2. **Blast Radius & Operational Risk**: What existing commands, workflows, or sub-systems could be broken or slowed down?
3. **Migration & Rollback**: How does existing state transition to the new format? Is the change backward-compatible, and can it be reverted cleanly?
4. **Surface Minimalism**: What proposed elements are speculative or unnecessary for the immediate requirement?

The agent converts identified risks and trade-offs into crisp, structured multiple-choice questions for the human.

### 3. Structured Multiple-Choice Grilling Contract
Interactive grilling is restricted to architectural and business decisions:
- Factual queries (code structures, existing flags, schemas) must be looked up autonomously in the codebase by the agent.
- Every question presented to the user must be multiple-choice, include trade-offs, and place the recommended choice first prefixed with `(Recommended)`.
- Open-ended questions (e.g. "What should we do about X?") are explicitly forbidden.

### 4. Non-Regression and Explicit Superseding
Settled decisions (`D*`) are binding invariants.
- If a new PRD conforms to prior decisions, it cites them as grounding.
- If a new PRD deliberately departs from a prior decision, it must include an explicit `Superseded decisions` entry naming the PRD number and decision ID (e.g., `Supersedes: 001/D2`) with a stated rationale.
- The Step 4 Gate checks that no prior decision is silently contradicted.

## Rejected Alternatives

- **External Knowledge Base / Daemon**: Storing decisions in a separate vector database or local daemon was rejected because it introduces an external runtime dependency and risks divergence from git state. Repository-local markdown files (`docs/prd/`, `openspec/changes/archive/`) are canonical and travel with git history.
- **Separate Autonomous Agent for Shootdown**: Creating an eighth Greek agent solely for shootdown was rejected to avoid unnecessary agent-spawning overhead in intake. The intake agent can perform the shootdown analysis autonomously in its main session before prompting the user.

## Risks and Mitigation

- **Risk**: Reading all archived changes slows down intake in repositories with hundreds of past changes.
  - **Mitigation**: Agents scan PRDs and archived change proposals/designs rather than every individual test file, focusing on `proposal.md`, `design.md`, and PRD `Settled decisions` sections.
