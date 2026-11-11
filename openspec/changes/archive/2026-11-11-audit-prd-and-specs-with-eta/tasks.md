# Tasks

## 1. Agent definitions

- [x] 1.1 Create `plugins/gauntlet/agents/eta.md`: read-only tools (`Read`, `Glob`, `Grep`, `Skill`, `WebFetch`, `WebSearch`), dual PRD + OpenSpec audit instructions, 4 orthogonal lenses, PASS/HOLD rules, no persona or home-path phrasing; verify with `python3 -m unittest discover -s tests -p "test_eta.py"`
- [x] 1.2 Update `plugins/gauntlet/agents/beta.md`: incorporate the 4 orthogonal lenses (Comprehension, Invariant Safety, Blast Radius & Rollback, Surface Minimization) and explicitly forbid non-blocking cosmetic/style nitpicks; verify with `python3 -m unittest discover -s tests -p "test_agents.py"`

## 2. Skills and orchestration

- [x] 2.1 Update `plugins/gauntlet/skills/intake/SKILL.md`: add `gauntlet:eta` dispatch to Step 4 (Gate), requiring PASS on both PRD and OpenSpec change before hand-off; verify with `python3 -m unittest discover -s tests -p "test_skills.py"`
- [x] 2.2 Update `plugins/gauntlet/skills/gauntlet-loop/SKILL.md` and `plugins/gauntlet/agents/epsilon.md`: specify `gauntlet:eta` pre-flight verification before `epsilon` invokes `gauntlet:delta` or creates slice worktrees; verify with `python3 -m unittest discover -s tests -p "test_agents.py"`

## 3. Verification and validation

- [x] 3.1 Update `tests/test_agents.py` to include `eta` in the agent fleet checks and verify `EXPECTED_TOOLS`; add comprehensive `tests/test_eta.py`; verify with `python3 -m unittest discover -s tests`
- [x] 3.2 Validate the OpenSpec change: `openspec validate audit-prd-and-specs-with-eta --strict`
