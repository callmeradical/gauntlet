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

Bundled with the gauntlet plugin. Delegate by the names below; don't restate
their instructions inline.

| Agent | Role | Receives | Never receives |
|---|---|---|---|
| **gauntlet:delta** | Slices a spec into a tracer bullet plus vertical slices; writes a builder brief and a separate critic bar per slice | The spec and the code it touches | — |
| **gauntlet:alpha** | Builds one slice (TDD) | The goal or brief, environment constraints, or beta's HOLD gap | The critic bar, beta's identity |
| **gauntlet:beta** | Judges one slice; spawn fresh every round | The artifact location (full files, not diffs) and the bar | alpha's reasoning, conversation, or self-assessment |
| **gauntlet:gamma** | Writes the progress page after every step | Facts: commits, verdicts, test results, merges | — |
| **gauntlet:epsilon** | Orchestrates the full pipeline | The change, integration branch, loop id, environment | — |
| **gauntlet:zeta** | Answers one design question for alpha; writes no code; only alpha starts it | alpha's question and the relevant files | The critic bar, beta's verdicts |
| **gauntlet:eta** | Audits the PRD and OpenSpec change together before slicing; returns PASS or HOLD with the single biggest spec gap | The repository, PRD path, and OpenSpec change directory | Author reasoning, intake conversation |

Never use general-purpose agents for building, reviewing, or slicing.

## Intake first

Work enters the gauntlet only through the **intake** skill:

```
PRD (what, why) → grilling (no open questions) → OpenSpec (how) → gate (eta) → gauntlet
```

Intake runs in the main session (grilling needs the user) and ends with a
gate: `gauntlet:eta` passes the PRD and OpenSpec change together, no undecided
PRD questions, a strictly valid change, no spec-changing open questions in
design.md, a verification per task, PRD and change in agreement, and the user's
go-ahead. epsilon re-checks the gate (including `gauntlet:eta`) before building.

Then choose the mode:

- **Single loop** (one well-scoped task): drive alpha ⇄ beta yourself, below.
- **Full pipeline** (a change with several behaviors): start `gauntlet:epsilon`.

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

1. **`gauntlet:alpha`:** round 1 gets the goal; later rounds get beta's HOLD
   gap verbatim as the whole task ("fix exactly this, don't rebuild").
2. **Collect the real artifact:** complete current files (a diff hides missing
   sibling changes), screenshots or a running instance for UI, the full draft
   for writing. Never a builder-written summary.
3. **`gauntlet:beta`, fresh:** the bar plus the artifact location, and spec
   artifacts if any. Don't paste alpha's reasoning into its prompt.
4. **Branch:** PASS → stop and report rounds and outcome. HOLD → back to 1.
   Ceiling → stop, report the latest gap, recommend direct review.

## Full pipeline (epsilon)

Start `gauntlet:epsilon` with: the change (paths to proposal, design, specs,
tasks, and the PRD), the integration branch and its worktree, the project name,
the loop id, what to build now and what to hold back (e.g. a later migration
phase), and the environment constraints below. epsilon then runs:

1. **Slice:** register the loop with `loop_start`, then `gauntlet:delta` →
   plan saved as `openspec/changes/<change>/slices.<loop>.md` without the
   critic bars (epsilon keeps those for beta).
2. **Tracer:** the thinnest end-to-end slice carrying the shared contracts
   (schema, types, signatures). `gauntlet:alpha` ⇄ `gauntlet:beta` until PASS,
   merge, full checks.
3. **Fan out:** one worktree and branch per remaining slice from
   `worktree_new`, alphas in parallel; a fresh beta for each as it finishes;
   HOLD back to that alpha. Record each slice's worktree, branch, status,
   round, commit, and verdict with `loop_update`.
4. **Merge:** PASSed slices one at a time in delta's merge order, each under
   the merge lock (`lock_acquire` before, `lock_release` after), full checks
   after each; a merge that breaks something goes back to its alpha and needs
   a fresh PASS. Right after each merge, `worktree_rm` for that slice removes
   its worktree and branch.
5. **Integrate:** docs and tasks.md, final full run, final gamma, `loop_end`,
   report. The integration worktree and any unmerged slices stay for the user,
   who removes them with `gauntlet worktree rm <loop>` (it keeps anything
   unmerged or dirty and never deletes the integration branch).

The project describes itself in `.gauntlet.json` (integration branch,
`shared` folders, `checks`, `setup`), read with `config_read`. Without it,
`loop_start` refuses with `config_missing`, and epsilon returns the four
questions (integration branch, shared folders, checks, setup) instead of
guessing, and offers to write the file. Ask the user, then start
`gauntlet:epsilon` again with the answers. epsilon doesn't commit the file.

epsilon stops before releasing, pushing, or opening a PR; those need the user.

## Loop ids and concurrency

The loop id scopes everything a loop creates:

- state `~/.local/state/gauntlet/<loop>.json`, written only by `loop_start`,
  `loop_update` and `loop_end` (running loops: the `status` tool or
  `gauntlet status`)
- worktrees `<repo-parent>/<repo>-<loop>-<slice>`, branches
  `gauntlet/<loop>/<slice>`, created by `worktree_new` and removed by
  `worktree_rm`
- plan `openspec/changes/<change>/slices.<loop>.md`
- progress page `~/wiki/features/<project>-<loop>-progress.html`
- agent descriptions prefixed `[<loop>]`

Two loops never share an id, a change, a worktree, or a branch. Merges into a
shared integration branch hold its merge lock: `lock_acquire` before,
`lock_release` after.

## Environment rules (give every alpha and beta)

- Worktrees share the project's `shared` folders from `.gauntlet.json` by
  symlink: never install into or rebuild them, release, or commit the
  symlinks; stage files explicitly. Run the project's `setup` command once
  before the loop starts, and never while another loop uses the same shared
  folders.
- Run the project's real `checks` from `.gauntlet.json` and name any
  pre-existing failures so a slice is judged on new ones only.
- Never touch live user data; build fixtures from copies.
- Conventional commits on the slice branch; never push.

## Progress page

`gauntlet:gamma` writes `~/wiki/features/<project>-<loop>-progress.html` from
the template `references/progress.html` in this skill's folder: header with
loop id, a summary (merged/total, tests, current and next step), a slice table
with the latest verdict (HOLD gaps verbatim), a timeline, and open items. It
writes no other wiki file and never commits the wiki. In single-loop mode, run
`gauntlet:gamma` at the end, or skip it for short tasks.

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
- Agent definitions: the gauntlet plugin's
  `gauntlet:{alpha,beta,gamma,delta,epsilon,zeta,eta}`
