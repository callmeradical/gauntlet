# 003 · Context handoffs

**Status:** Proposed · **Extends:** 001 · **Drafted:** 2026-11-11

## Summary

Long-running gauntlet roles run out of context mid-task. Each role hands its work to a fresh agent of the same role, through a written handoff document, before its context fills, so no work is lost and no verdict is issued from a half-remembered session.

## Problem

- A role near the end of its context forgets earlier evidence and decisions, and its later work degrades.
- Without a durable written record, a successor has to ask the operator to re-explain the setup, or guesses.
- A critic that runs out of context mid-review can issue a verdict from partial evidence.
- The plugin's agents fail to launch under pi-subagents, whose tool allowlist uses lowercase names.

## Requirements

- **R1**: The plugin bundles a `handoff` skill that writes a handoff document to a durable per-user location outside the workspace and temp folders, naming the loop, slice or queue item, branch, worktree and exact head commit.
- **R2**: A handoff gives done and proven work with evidence, an ordered checklist of what is left, open decisions and owners, promises made, running subagents and jobs, and environment rules; it references artifacts instead of copying them, redacts secrets, marks unverified claims "unverified", and ends with suggested skills.
- **R3**: Every role and the loop skill hand off at a configurable share of context (default 65%): stop at a clean point, write a handoff, and pass to a successor of the same role started with "Continue from handoff <path>".
- **R4**: Builders and critics report the handoff to the orchestrator, which starts the successor; the orchestrator starts its own successor; the loop state records each handoff.
- **R5**: A critic about to hand off reports "incomplete" and the handoff, never a verdict; its successor redoes every bar item without recorded evidence.
- **R6**: Handoffs are announced in the coordination channel, if any.
- **R7**: The threshold is set per project and an invalid value is reported.
- **R8**: Every agent with a tool list launches under pi as well as Claude Code; read-only agents stay read-only.

## Settled decisions

- **D1**: Handoffs live in `~/.local/state/gauntlet/handoffs/`, beside the loop state.
- **D2**: The successor prompt is only "Continue from handoff <path>"; a handoff is never pasted into a shell command.
- **D3**: Agents list pi's lowercase built-in tool names beside the Claude Code names, instead of granting eta or zeta a shell.
