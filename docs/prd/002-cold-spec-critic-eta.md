# 002 · Cold spec critic (eta) and orthogonal review lenses

**Status:** Proposed · **Extends:** 001 · **Drafted:** 2026-11-10

## Summary

Adds a seventh agent to the gauntlet fleet: **`gauntlet:eta`**, a stateless, zero-context pre-flight specification critic ("the spec goldfish"). `eta` operates at the gate between intake and execution, auditing the PRD (`docs/prd/*.md`) and the OpenSpec change (`openspec/changes/*`) **together** before `delta` slices or `epsilon` orchestrates. Additionally, updates `gauntlet:beta` (the code slice critic) with four non-overlapping evaluation lenses (Comprehension, Invariant Safety, Blast Radius & Rollback, Surface Minimization) to eliminate subjective nitpicks and focus HOLD verdicts on blocking flaws.

## Problem

The gauntlet prevents builders from grading their own work during code delivery by having `beta` review code in a fresh context. However, this cold-context isolation is currently missing from the **specification phase**:

- **Context Blindness at the Gate**: The agent drafting the OpenSpec change participates in the intake conversation and grilling sessions. It shares the human's unspoken context and mental model, meaning it cannot reliably evaluate whether the written change is self-contained.
- **Divergence Between PRD and OpenSpec**: Without an independent auditor checking both documents together, technical specs can silently omit PRD requirements (`R*`), violate settled decisions (`D*`), or sneak in unapproved scope ("how" dictating "what").
- **Spec Leaks to Alpha**: When an OpenSpec change contains ambiguous requirements or implicit assumptions, `alpha` (the builder) is forced to guess during test-driven construction or abort the slice midway.
- **Unstructured Review Verdicts**: `beta`'s criteria for a HOLD on code slices lack explicit boundaries, leaving reviews vulnerable to style preferences or unfocused commentary rather than targeted architectural invariants.

## Proposal

1. **Dual-Artifact Spec Gating Agent (`gauntlet:eta`)**:
   Introduce `eta` as a dedicated read-only agent invoked during intake before hand-off, and re-verified by `epsilon` before slicing. `eta` receives zero conversation history: it is given only the repository files, the upstream PRD, and the OpenSpec change directory. It audits the PRD and OpenSpec change **together** to guarantee:
   - **Traceability & Completeness**: Every PRD requirement (`R*`) and settled decision (`D*`) is accounted for in the OpenSpec change; no unauthorized features are sneaked in.
   - **Leakage Prevention**: The PRD describes product behavior only (no code/file names); the OpenSpec change contains concrete scenarios and verifiable tasks.
   - **Zero-Guessing Testability**: An engineer with no prior conversation memory can understand every scenario and write tests without guessing.
   - **Strict Gating**: If unstated assumptions, contradictions, or missing rollback plans exist, `eta` returns a HOLD naming the single biggest gap, returning the change to intake grilling.
2. **Four Orthogonal Evaluation Lenses for Critics (`beta` & `eta`)**:
   Formalize evaluation criteria across four non-overlapping dimensions:
   - **Comprehension**: Are all requirements and scenarios unambiguous and self-sufficient without implicit knowledge?
   - **Invariant Safety**: Do interfaces, types, and behaviors preserve documented project patterns and domain models?
   - **Blast Radius & Rollback**: Are failure modes, migrations (expand/backfill/switch/contract), and operational risks handled?
   - **Surface Minimization**: Is speculative abstraction or dead weight introduced beyond the required scope?
3. **Role Separation Contract**:
   Explicitly separate **high-context synthesis roles** (PRD authoring, OpenSpec drafting, `alpha` builder, `epsilon` orchestrator) from **zero-context gating roles** (`eta` spec critic, `beta` code critic). Gating roles must never receive author scratchpads, parent conversation threads, or reasoning logs.

## Out of scope

- Changing the PRD format or the OpenSpec change schema.
- Automatic patching of specifications without human review.
- Modifying the git worktree locking or cleanup mechanisms in `gauntlet`.

## Users and scenarios

- *"I finish grilling a PRD and draft an OpenSpec change; before any worktree is spawned, `eta` audits the PRD and change together and catches that OpenSpec missed requirement R4."*
- *"Alpha never stalls on an ambiguous scenario because `eta` already proved that every scenario can be turned into an unambiguous test."*
- *"When Beta reviews an Alpha slice, it returns a concise HOLD focused on blast radius or invariant safety, rather than subjective style preferences."*

## Requirements

### Pre-flight Spec Critic (`gauntlet:eta`)

- **R1**: The gauntlet plugin provides a read-only agent named `gauntlet:eta`.
- **R2**: `eta` runs in an isolated, stateless context without access to the intake conversation transcript or author reasoning.
- **R3**: `eta` takes exactly three inputs: the project repository, the PRD path (`docs/prd/NNN-<name>.md`), and the OpenSpec change directory (`openspec/changes/<change>/`).
- **R4**: `eta` evaluates the PRD and OpenSpec change together against:
  1. *PRD/OpenSpec Agreement*: 1:1 traceability from every PRD requirement (`R*`) and settled decision (`D*`) to OpenSpec delta specs and scenarios; no orphaned requirements and no unauthorized scope additions.
  2. *Separation of Concerns*: The PRD contains product behavior only (no implementation details, function/file names); OpenSpec contains technical design and verifiable tasks.
  3. *The Four Orthogonal Lenses*: Comprehension, Invariant Safety, Blast Radius & Rollback, Surface Minimization.
- **R5**: `eta` returns either a PASS or a HOLD naming the single highest-severity gap. A HOLD halts the pipeline and returns the change to intake before any slice worktree is initialized.

### Orthogonal Review Lenses (`gauntlet:beta` & `gauntlet:eta`)

- **R6**: `gauntlet:beta` and `gauntlet:eta` evaluate artifacts strictly along four non-overlapping lenses:
  1. *Comprehension* (unambiguous, self-sufficient, testable)
  2. *Invariant Safety* (conformance to existing architecture, domain models, and system types)
  3. *Blast Radius & Rollback* (failure handling, migration safety, operational risk)
  4. *Surface Minimization* (removal of premature abstractions and unrequested complexity)
- **R7**: Review feedback from `beta` and `eta` must cite the failing lens, the exact scenario or file location, and the concrete gap. Cosmetic, styling, and personal code preferences are explicitly forbidden as reasons for a HOLD.

### Workflow & Invocation Integration

- **R8**: The `intake` skill updates Step 4 (Gate) to require a PASS from `gauntlet:eta` (run with the PRD and OpenSpec change) before declaring the change ready for `gauntlet:epsilon`.
- **R9**: `gauntlet:epsilon` re-runs `gauntlet:eta` as its very first step prior to invoking `gauntlet:delta` (slicing) or creating worktrees; if `eta` returns HOLD, `epsilon` aborts immediately with the gap and creates no branches.
- **R10**: `gauntlet status` and progress tracking (`gamma`) report `eta` spec review status alongside slice loop progress.

## Settled decisions

- **D1**: `eta` audits the PRD and the OpenSpec change together in the same cold pass, ensuring cross-document consistency, scope bounds, and scenario traceability.
- **D2**: `eta` runs both in `intake` (so the operator sees issues during gating) and as `epsilon`'s pre-flight check (enforcing that no loop ever slices an unvalidated change).
