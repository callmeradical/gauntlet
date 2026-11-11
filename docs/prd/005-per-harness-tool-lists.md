# 005 · Per-harness tool lists

**Status:** Proposed · **Extends:** 003 · **Drafted:** 2026-11-11

## Summary

Each harness that loads the gauntlet agents gets only the tool names it knows: Claude Code gets Claude Code names, pi-subagents gets pi names. Agents launch cleanly on both, with the same roles and the same read-only limits.

## Problem

- Each agent's single `tools` line mixes Claude Code names (`Read`, `Glob`, `Skill`, ...) with pi names (`read`, `grep`, ...), per 003 D3.
- pi-subagents treats `tools` as a strict allowlist: every launch of eta (and the others) ends "requested unavailable child tools: Read, Glob, Grep, Skill, WebFetch, WebSearch" and the run is marked failed, even when the work completes.
- Claude Code sees lowercase names it does not know.
- epsilon's pi list has no gauntlet MCP tools, and alpha's and epsilon's have no way to start agents.

## Requirements

- **R1**: Every agent's Claude Code tool list holds only Claude Code tool names; every agent's pi tool list holds only pi tool names.
- **R2**: eta and zeta are read-only on both harnesses: on pi only `read`, `grep`, `find`, `ls`.
- **R3**: epsilon gets every gauntlet server tool on both harnesses, under each harness's own name.
- **R4**: Each agent keeps one source definition; the per-harness lists cannot drift from it unnoticed.
- **R5**: The install docs say where pi loads the agents from.

## Settled decisions

- **D1**: Supersedes 003 D3: no mixed list.
- **D2**: pi-subagents has no per-harness frontmatter key, so pi reads generated copies of the agents (see the OpenSpec change `split-per-harness-tools`).
