---
name: intake
description: >
  Take a feature or change from idea to a build-ready OpenSpec change:
  historical grounding from prior PRDs and archived changes, an autonomous
  pre-grilling shootdown, structured grilling, an OpenSpec change, and a gate
  check before handing off to the gauntlet (epsilon).
---

# Intake

Turn a request into a change the gauntlet can build without guessing.

```
PRD (what, why) → grilling (no open questions) → OpenSpec (how) → gate (eta) → gauntlet
```

Run intake in the main session: grilling needs the user, and background
agents can't ask them anything.

## 1. PRD: what and why

- Ground in repository history: scan existing PRDs in `docs/prd/*.md` and
  archived changes in `openspec/changes/archive/**` to extract active
  settled decisions (`D*`), domain models, and prior rejected alternatives.
- Avoid amnesia: never silently contradict a past settled decision. If a new
  proposal intentionally departs from an earlier decision, state it explicitly
  with `Supersedes: NNN/DX` and provide the rationale.
- Use **write-a-prd** to write `docs/prd/NNN-<name>.md` (next free number):
  problem, goals and non-goals, users and scenarios, requirements, and an
  **Open questions** list.
- Product behavior only. No implementation, no file or function names.
- If a PRD already exists for this work, update it instead; note what changed.

## 2. Grilling: close every open question

- **Autonomous pre-grilling shootdown:** Before engaging the user, stress-test
  the draft PRD across four dimensions:
  1. *Failure mode and edge cases*: What corrupted inputs, concurrency races,
     or unhandled error states break this?
  2. *Blast radius and operational risks*: What existing commands, APIs, or
     workflows risk degradation or performance regression?
  3. *Migration and rollback*: How does existing data or state transition? Can
     every change be reverted safely?
  4. *Surface minimalism*: What proposed requirements are speculative or non-essential?
  Synthesize identified risks and open trade-offs into crisp decisions.
- **Structured grilling:** Use the **grilling** skill. One question at a time.
- Every question presented to the user must be structured as multiple-choice
  with concrete options and clear trade-offs, putting the recommended option
  first prefixed with `(Recommended)`. Open-ended questions are strictly
  forbidden.
- Look facts up in the code and data yourself; put only genuine trade-off
  decisions to the user.
- Ground questions in real examples (actual emails, records, screens) where
  possible.
- Record each answer where it applies: in the requirement it shapes, and as
  *Decided (date): <answer>* on the open question it closes.
- Any decision the user makes later, in any step, goes into the PRD the same
  way before work continues.
- Done when no open question is undecided and the user confirms a shared
  understanding.

## 3. OpenSpec: how

- Ground the change in repository history and PRD decisions:
  - Verify consistency with retrieved `docs/prd/*.md` settled decisions and
    `openspec/changes/archive/**` rejected alternatives to avoid known failure modes.
  - If a decision supersedes an earlier decision, ensure `Supersedes: NNN/DX` is
    documented.
- Use **prd-to-spec** (or the openspec-propose workflow) to draft the change:
  - **proposal:** why, linking the PRD and quoting the decisions it builds on;
    what changes (mark **BREAKING**); capabilities; impact.
  - **delta specs:** requirements with SHALL and at least one scenario each.
  - **design:** decisions with alternatives considered, risks, and a staged
    migration plan (expand, backfill, switch, contract, each with a rollback)
    when data, schemas, or APIs change.
  - **tasks:** grouped in build order, each stating how it is verified.
- Look facts up in the code. A new decision that surfaces while specifying
  goes back to the user (step 2), not into the spec as an assumption.
- `openspec validate <change> --strict` must pass.

## 4. Gate

Run `gauntlet:eta` with the repository root, the PRD path, and the OpenSpec
change directory. `gauntlet:eta` audits both artifacts together across four
orthogonal lenses (Comprehension, Invariant Safety, Blast Radius & Rollback,
Surface Minimization) from a fresh, zero-context state.

Check all of these; `gauntlet:epsilon` re-checks them before building:

- [ ] `gauntlet:eta` returns PASS on the PRD and OpenSpec change together.
- [ ] Active settled decisions from prior PRDs are respected; any departed
      decision explicitly cites `Supersedes: NNN/DX`.
- [ ] All failure modes and risks from pre-grilling shootdown are resolved.
- [ ] The PRD has no undecided open questions.
- [ ] The change validates with `--strict`.
- [ ] design.md has no open question that would change specs, approach, or
      tasks (deferrable ones may stay, marked as such).
- [ ] Every task states its verification.
- [ ] The PRD and the change agree (no requirement in one contradicted by the
      other).
- [ ] The user approved building it.

A failed check or a `gauntlet:eta` HOLD goes back to the step that owns it:
what or why → grilling on the PRD; how → the OpenSpec change.

## 5. Hand off

- Commit the PRD and the change on the integration branch.
- Start the gauntlet (**gauntlet-loop** skill): `gauntlet:epsilon` for a
  change with several behaviors, a single `gauntlet:alpha` ⇄ `gauntlet:beta`
  loop for one small task. Pass the PRD and change paths, the integration
  branch, the project name, a loop id, what to build now versus hold back
  (e.g. a later migration phase), and the environment constraints.
- During building, a spec gap a builder would have to guess at stops that
  slice and comes back here as a question for the user; record the answer in
  the PRD or spec, then resume.
