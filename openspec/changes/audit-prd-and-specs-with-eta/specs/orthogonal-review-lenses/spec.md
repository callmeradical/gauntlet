# Spec Delta

## Purpose

Defines the four orthogonal evaluation lenses across critic agents (`gauntlet:beta` and `gauntlet:eta`).

## ADDED Requirements

### Requirement: Four non-overlapping critic lenses
`gauntlet:beta` and `gauntlet:eta` SHALL structure all reviews around four non-overlapping evaluation lenses:
1. Comprehension (unambiguous, self-sufficient, testable)
2. Invariant Safety (conformance to existing patterns, domain models, and contracts)
3. Blast Radius & Rollback (failure handling, migration staging, operational safety)
4. Surface Minimization (removal of speculative abstractions and unrequested code/spec weight)

#### Scenario: Critic structure
- **WHEN** `beta.md` or `eta.md` is inspected
- **THEN** each definition explicitly names and requires evaluation across Comprehension, Invariant Safety, Blast Radius & Rollback, and Surface Minimization.

### Requirement: Style and cosmetic nitpicks forbidden
`gauntlet:beta` and `gauntlet:eta` SHALL NOT issue a `HOLD` based on cosmetic, formatting, or personal stylistic preferences. A `HOLD` must identify a concrete violation of one of the four lenses.

#### Scenario: Non-blocking cosmetic comment
- **WHEN** an artifact differs only in whitespace, variable naming style, or comment formatting that does not violate documented project invariants
- **THEN** the critic does not issue a `HOLD` on that basis.
