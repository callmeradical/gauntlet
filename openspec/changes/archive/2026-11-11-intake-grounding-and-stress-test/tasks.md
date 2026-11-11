# Tasks

## 1. Skill updates

- [x] 1.1 Update `plugins/gauntlet/skills/intake/SKILL.md`: update Step 1 (PRD) to mandate scanning `docs/prd/` and `openspec/changes/archive/` for historical decisions and rejected alternatives; verify with `python3 -m unittest discover -s tests -p "test_skills.py"`
- [x] 1.2 Update `plugins/gauntlet/skills/intake/SKILL.md`: update Step 2 (Grilling) to add autonomous pre-grilling shootdown (failure modes, operational risks, migration/rollback, minimalism) and require structured multiple-choice questions with `(Recommended)` first; verify with `python3 -m unittest discover -s tests -p "test_skills.py"`
- [x] 1.3 Update `plugins/gauntlet/skills/intake/SKILL.md`: update Step 3 (OpenSpec) and Step 4 (Gate) to enforce explicit superseding attribution (`Supersedes: NNN/DX`) and checklist verification; verify with `python3 -m unittest discover -s tests -p "test_skills.py"`

## 2. Tests and validation

- [x] 2.1 Update `tests/test_skills.py`: add tests verifying historical retrieval instructions, pre-grilling shootdown, structured multiple-choice grilling requirements, and gate checklist items in `intake`; verify with `python3 -m unittest discover -s tests -p "test_skills.py"`
- [x] 2.2 Validate OpenSpec change with `openspec validate intake-grounding-and-stress-test --strict`
- [x] 2.3 Run full test suite with `python3 -m unittest discover -s tests`
