---
name: gauntlet-loop
description: >
  Build/review loop with separated roles. alpha builds via TDD; beta, spawned
  fresh with no shared history, judges the artifact against a concrete bar and
  returns PASS or HOLD with the single biggest gap; HOLD becomes alpha's next
  task. Work enters only through the intake skill (PRD → grilling → OpenSpec
  → gate). For a whole OpenSpec change, epsilon orchestrates the full
  pipeline: delta slices it into a tracer bullet plus vertical slices, alphas
  build slices in parallel worktrees, a fresh beta reviews each, PASSed slices
  merge one at a time, and gamma keeps a progress page in the wiki. Loops are
  named by a loop id so several can run at once. Use when the user says
  "gauntlet loop", "run the gauntlet", "PRD to OpenSpec to build", "builder and critic", "have epsilon
  build it", "fan out with alpha and beta", or wants adversarial review where
  the reviewer never saw the builder's reasoning.
---

# Gauntlet Loop

Builder and critic stay separate: an agent that writes and reviews its own work
rationalizes its choices instead of interrogating them. beta starts from a blank
slate every round and judges only the artifact.

Lineage: an internal ADR-driven Builder/Critic/Red-Teamer/Judge pipeline, and
Matt Shumer's ["Gauntlet Loop"](https://somethingbig.ai/gauntlet-loop).

## Agents

Defined in `~/.claude/agents/` and mirrored in `~/.agents/agents/`. Delegate
by name; don't restate their instructions inline.

| Agent | Role | Receives | Never receives |
|---|---|---|---|
| **delta** | Slices a spec into a tracer bullet plus vertical slices; writes a builder brief and a separate critic bar per slice | The spec and the code it touches | — |
| **alpha** | Builds one slice (TDD) | The goal or brief, environment constraints, or beta's HOLD gap | The critic bar, beta's identity |
| **beta** | Judges one slice; spawn fresh every round | The artifact location (full files, not diffs) and the bar | alpha's reasoning, conversation, or self-assessment |
| **gamma** | Writes the progress page after every step | Facts: commits, verdicts, test results, merges | — |
| **epsilon** | Orchestrates the full pipeline | The change, integration branch, loop id, environment | — |

Never use general-purpose agents for building, reviewing, or slicing.

## Intake first

Work enters the gauntlet only through the **intake** skill:

```
PRD (what, why) → grilling (no open questions) → OpenSpec (how) → gate → gauntlet
```

Intake runs in the main session (grilling needs the user) and ends with a
gate: no undecided PRD questions, a strictly valid change, no spec-changing
open questions in design.md, a verification per task, PRD and change in
agreement, and the user's go-ahead. epsilon re-checks the gate before
building.

Then choose the mode:

- **Single loop** (one well-scoped task): drive alpha ⇄ beta yourself, below.
- **Full pipeline** (a change with several behaviors): start epsilon.

Loops build against a fixed target and never renegotiate it. A spec gap a
builder would have to guess at stops that slice and goes back through intake
as a question for the user; the answer is recorded in the PRD or spec before
the slice resumes.

## Before starting

1. **The goal, not the route.** Give alpha the destination. Prescribed steps
   turn the critic's question into "did it follow instructions", a weak bar.
2. **A concrete bar.** In order of strength: a reference to compare against
   (an existing file, product, or screenshot), a measurable target (named
   scenarios, tests, a number), conformance to the codebase's patterns. If
   none exists, have a planning pass propose one before the loop starts.
   In the full pipeline, delta writes the bar from the spec's requirements
   and scenarios.
3. **A ceiling.** Default 3 HOLD rounds on the same gap per slice, then stop
   and report. A no-ceiling run (stop on diminishing returns) is available if
   the user asks for it.
4. **A loop id** for full-pipeline runs: kebab-case, at most 24 characters
   (`pri`, `bg-ingest`); defaults to the change name.

## Single loop

Repeat until PASS or the ceiling:

1. **alpha:** round 1 gets the goal; later rounds get beta's HOLD gap verbatim
   as the whole task ("fix exactly this, don't rebuild").
2. **Collect the real artifact:** complete current files (a diff hides missing
   sibling changes), screenshots or a running instance for UI, the full draft
   for writing. Never a builder-written summary.
3. **beta, fresh:** the bar plus the artifact location, and spec artifacts if
   any. Don't paste alpha's reasoning into its prompt.
4. **Branch:** PASS → stop and report rounds and outcome. HOLD → back to 1.
   Ceiling → stop, report the latest gap, recommend direct review.

## Full pipeline (epsilon)

Start epsilon with: the change (paths to proposal, design, specs, tasks, and
the PRD), the integration branch and its worktree, the project name, the loop
id, what to build now and what to hold back (e.g. a later migration phase),
and the environment constraints below. epsilon then runs:

1. **Slice:** delta → plan saved as `openspec/changes/<change>/slices.<loop>.md`
   without the critic bars (epsilon keeps those for beta).
2. **Tracer:** the thinnest end-to-end slice carrying the shared contracts
   (schema, types, signatures). alpha ⇄ beta until PASS, merge, full checks.
3. **Fan out:** one worktree and branch per remaining slice, alphas in
   parallel; a fresh beta for each as it finishes; HOLD back to that alpha.
4. **Merge:** PASSed slices one at a time in delta's merge order, full checks
   after each; a merge that breaks something goes back to its alpha and needs
   a fresh PASS.
5. **Integrate:** docs and tasks.md, final full run, final gamma, report.

epsilon stops before releasing, pushing, or opening a PR; those need the user.

## Loop ids and concurrency

The loop id scopes everything a loop creates:

- state `~/.local/state/gauntlet/<loop>.json` (list the folder for running loops)
- worktrees `<repo-parent>/<repo>-<loop>-<slice>`, branches `gauntlet/<loop>/<slice>`
- plan `openspec/changes/<change>/slices.<loop>.md`
- progress page `~/wiki/features/<project>-<loop>-progress.html`
- agent descriptions prefixed `[<loop>]`

Two loops never share an id, a change, a worktree, or a branch. Merges into a
shared integration branch take `~/.local/state/gauntlet/<repo>--<branch>.lock`.

## Environment rules (give every alpha and beta)

- Worktrees may share `node_modules` by symlink: never install, rebuild native
  modules, release, or commit the symlink; stage files explicitly. Do any
  one-time native rebuild before the loop starts, and none while another loop
  uses the same `node_modules`.
- Run the project's real checks (tests, builds, typecheck) and name any
  pre-existing failures so a slice is judged on new ones only.
- Never touch live user data; build fixtures from copies.
- Conventional commits on the slice branch; never push.

## Progress page

gamma writes `~/wiki/features/<project>-<loop>-progress.html` from the
template `~/.agents/templates/progress.html`: header with loop id, a summary
(merged/total, tests, current and next step), a slice table with the latest
verdict (HOLD gaps verbatim), a timeline, and open items. It writes no other
wiki file and never commits the wiki. In single-loop mode, run gamma at the
end, or skip it for short tasks.

## After the loop

- Report: what merged, rounds per slice, test and build results, beta's
  unfixed minor notes, and in-app checks left to the user.
- An optional smoothing pass (one fresh agent) can reconcile independently
  built slices; its job is coherence, not another quality gate.

## Extending

More roles layer on the same mechanism: a red-teamer spawned blind to beta's
feedback, a judge on a stronger model for final sign-off, a shared task board.
Add one at a time, only after the base loop converges.

## See also

- [The Gauntlet Loop (Matt Shumer)](https://somethingbig.ai/gauntlet-loop)
- **intake** skill: PRD → grilling → OpenSpec → gate
- Agent definitions: `~/.claude/agents/{alpha,beta,gamma,delta,epsilon}.md`
