---
name: intake
description: >
  Take a feature or change from idea to a build-ready OpenSpec change: a PRD
  for the what and why, a grilling session that closes every open question,
  an OpenSpec change for the how, and a gate check before handing off to the
  gauntlet (epsilon). Use when the user wants to start a new feature or
  change "the right way", says "intake", "PRD to OpenSpec", "get this ready
  to build", or before running the gauntlet on work that has no settled PRD
  or spec.
---

# Intake

Turn a request into a change the gauntlet can build without guessing.

```
PRD (what, why) → grilling (no open questions) → OpenSpec (how) → gate → gauntlet
```

Run intake in the main session: grilling needs the user, and background
agents can't ask them anything.

## 1. PRD: what and why

- Use **write-a-prd** to write `docs/prd/NNN-<name>.md` (next free number):
  problem, goals and non-goals, users and scenarios, requirements, and an
  **Open questions** list.
- Product behavior only. No implementation, no file or function names.
- If a PRD already exists for this work, update it instead; note what changed.

## 2. Grilling: close every open question

- Use the **grilling** skill. One question at a time, each with a
  recommended answer.
- Look facts up in the code and data yourself; put only decisions to the user.
- Ground questions in real examples (actual emails, records, screens) where
  possible.
- Record each answer where it applies: in the requirement it shapes, and as
  *Decided (date): <answer>* on the open question it closes.
- Any decision the user makes later, in any step, goes into the PRD the same
  way before work continues.
- Done when no open question is undecided and the user confirms a shared
  understanding.

## 3. OpenSpec: how

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

Check all of these; epsilon re-checks them before building:

- [ ] The PRD has no undecided open questions.
- [ ] The change validates with `--strict`.
- [ ] design.md has no open question that would change specs, approach, or
      tasks (deferrable ones may stay, marked as such).
- [ ] Every task states its verification.
- [ ] The PRD and the change agree (no requirement in one contradicted by the
      other).
- [ ] The user approved building it.

A failed check goes back to the step that owns it: what or why → grilling on
the PRD; how → the OpenSpec change.

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
