# Spec Delta

## Purpose

Defines requirements for autonomous pre-grilling stress-testing ("Shootdown") and structured multiple-choice grilling questions in the intake workflow.

## ADDED Requirements

### Requirement: Autonomous Pre-Grilling Stress-Test (Shootdown)
Before initiating interactive grilling with the human operator in Step 2, the agent SHALL autonomously stress-test the draft PRD across four dimensions: failure modes and edge cases, operational blast radius, migration and rollback hazards, and surface minimalism.

#### Scenario: Pre-grilling shootdown execution
- **WHEN** the agent completes the initial draft of the PRD in Step 1
- **THEN** it executes an autonomous shootdown analysis across the four dimensions before presenting any questions to the user.

### Requirement: Structured Multiple-Choice Grilling Questions
The `intake` skill SHALL require all grilling questions presented to the human operator in Step 2 to be structured as multiple-choice questions with distinct options, clear trade-offs, and the recommended option placed first prefixed with `(Recommended)`. Open-ended questions SHALL NOT be asked.

#### Scenario: Posing a decision to the user
- **WHEN** an architectural decision requires input from the human operator
- **THEN** the question is presented with concrete multiple-choice options, trade-offs, and `(Recommended)` on the top option.

#### Scenario: Factual inquiry resolution
- **WHEN** an agent needs factual information about the codebase, existing flags, configurations, or schemas
- **THEN** the agent inspects the code directly rather than asking the human operator.
