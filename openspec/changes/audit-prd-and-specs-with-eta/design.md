# Design

## Context

The gauntlet uses separated roles to avoid rationalization in code construction (`alpha` builds test-first, `beta` reviews blind). However, during intake (`PRD → grilling → OpenSpec → gate`), the agent writing the OpenSpec change retains the accumulated context of the entire grilling conversation. It assumes knowledge that exists in the chat history but was never codified in the spec.

This design introduces `gauntlet:eta` to audit specifications cold before any code worktree is spawned, and aligns critic criteria across both `beta` and `eta` using four orthogonal lenses adapted from the Elephant-Goldfish Model (EGM).

## Decisions

### 1. Seventh Greek Agent: `gauntlet:eta`
`eta` is added to `plugins/gauntlet/agents/eta.md`.
- **Tools**: Read-only: `Read`, `Glob`, `Grep`, `Skill`, `WebFetch`, `WebSearch`. No `Write`, `Edit`, `Bash`, or `Agent` tools.
- **Inputs**: The project repository root, the PRD path (`docs/prd/NNN-<name>.md`), and the OpenSpec change directory (`openspec/changes/<change>/`).
- **Verdict**: Exactly `PASS` or `HOLD`. A `HOLD` names the single biggest remaining gap across either document or their agreement.

### 2. Dual-Artifact Audit (PRD + OpenSpec)
Instead of reviewing the OpenSpec change in isolation, `eta` is instructed to inspect both the PRD and the OpenSpec change together:
- Verifies 1:1 traceability from every PRD requirement (`R*`) and settled decision (`D*`) to an OpenSpec scenario.
- Verifies that no unauthorized product behavior is introduced in the technical spec that was not in the PRD.
- Verifies clean separation of concerns: PRD holds product *what & why* only; OpenSpec holds technical *how* and verifiable tasks.

### 3. Four Orthogonal Evaluation Lenses
Both `gauntlet:eta` (spec critic) and `gauntlet:beta` (code critic) evaluate artifacts strictly against four non-overlapping lenses:
1. **Comprehension**: Are requirements, scenarios, or code unambiguous and self-sufficient without implicit knowledge?
2. **Invariant Safety**: Do interfaces, types, and behaviors preserve documented project patterns and domain models?
3. **Blast Radius & Rollback**: Are failure modes, migrations (expand/backfill/switch/contract), and operational risks handled?
4. **Surface Minimization**: Is speculative abstraction or dead weight introduced beyond the required scope?

Critics must state the failing lens in their `HOLD` and cannot reject on subjective styling or personal preference.

### 4. Dual-Gate Invocation
- **Intake Gate (Step 4)**: The operator dispatches `gauntlet:eta` in the main session before hand-off to `epsilon`. If `eta` returns `HOLD`, the operator resolves the issue in grilling immediately.
- **Orchestrator Pre-flight (`epsilon`)**: When started, `epsilon` verifies that `eta` returns `PASS` on the PRD and change before invoking `gauntlet:delta` to slice. If `eta` returns `HOLD`, `epsilon` aborts immediately with `spec_gate_failed`, preventing branch or worktree creation.

## Rejected Alternatives

- **Auditing OpenSpec only without the PRD**: Rejected because an agent reviewing only the OpenSpec change cannot detect whether critical PRD requirements (`R*`) or settled human decisions (`D*`) were dropped by the architect.
- **Making `eta` a step inside `delta`**: Rejected because `delta`'s job is planning vertical slices, not objective quality gating. Slicing an ambiguous spec produces flawed slices.
- **Adopting EGM persona files directly**: Rejected because EGM's 8 persona files introduce external file dependencies and verbose prompt boilerplate. Embedding the four lenses directly into `beta.md` and `eta.md` maintains Gauntlet's minimal, task-directive architecture.

## Risks and Mitigation

- **Risk**: `eta` becomes an overly pedantic blocker on minor phrasing.
  - **Mitigation**: `eta`'s instructions explicitly forbid stylistic commentary and require citing the single highest-severity blocking gap among the four lenses.
- **Risk**: Long specs exceed context or slow down gate checks.
  - **Mitigation**: `eta` runs read-only with direct file reads and focuses strictly on delta specs, scenarios, and PRD requirement lists.
