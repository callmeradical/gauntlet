---
name: handoff
description: >
  Write a handoff document so a fresh agent of the same role can continue the
  work cold. Use when context use reaches the handoff threshold (about 65%,
  `handoff.context_threshold` in .gauntlet.json), when the user says "handoff"
  or "/handoff", or when forking a side task to another agent.
argument-hint: "What will the next session be used for?"
---

# Handoff

Adapted from [mattpocock/skills](https://github.com/mattpocock/skills)
`productivity/handoff` (MIT).

Write a handoff document that sums up the current session so a fresh agent
can continue the work without anyone re-explaining the setup.

## Where

Save it to
`~/.local/state/gauntlet/handoffs/<loop-or-pane>-<role>-<YYYYmmdd-HHMM>.md`,
not the workspace and not `/tmp`. Successors may start hours later, temp
folders get cleared, and a file in the workspace ends up in a commit. Use the
loop id when there is one, else the pane or session name. Print the path when
done.

## What to include

1. **Purpose of the next session.** If an argument was passed, treat it as
   that purpose and keep the reasoning that bears on it.
2. **Where the work is:** the loop, the slice or queue item, the branch, the
   worktree and the exact head commit (`git rev-parse HEAD`, not a branch
   name).
3. **Done and proven**, each item with its evidence: the command run and its
   result, the commit, the verdict.
4. **What is left**, as an ordered checklist, with the step in flight first.
5. **Open decisions and their owners** (the operator, the orchestrator, another
   agent), and decisions made with their reasons.
6. **Promises made** to the operator or other agents.
7. **Running subagents and background jobs**: their ids and how to check them.
8. **Environment rules in force**: target folders, ports, labels, things never
   to touch.

## What not to include

- **Artifacts.** PRDs, specs, slice briefs, critic bars, diffs, logs and
  subagent reports already exist: reference them by path (or URL) and never
  copy them into the handoff.
- **Secrets.** Redact API keys, passwords, tokens and personal data.

## Verified vs believed

The successor trusts this document and won't re-check it. Mark every claim
not verified in this session as "unverified" (for example "tests green,
unverified: not re-run after the rebase"). Never write an assumption as a
fact.

## Handing it over

The successor starts with a prompt that says only
"Continue from handoff <path>". Never paste a handoff into a shell command:
backticks and `$(...)` get mangled silently.

The handoff works if it is a small fraction of the session, reads cold, and
lets the successor start without asking anyone to re-explain the setup.

## Suggested skills

End every handoff with a "Suggested skills" section naming the skills the
successor should load (for example `gauntlet-loop`, `tdd`, `intake`).
