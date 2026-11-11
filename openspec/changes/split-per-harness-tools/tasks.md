# Tasks

## 1. Lists and generator

- [x] 1.1 Add `tests/test_harness_tools.py` (red); verify with `python3 -m unittest discover -s tests -p "test_harness_tools.py"`
- [x] 1.2 Split `tools` into Claude Code names and `pi-tools` in `plugins/gauntlet/agents/*.md`; add `scripts/build_pi_agents.py` and generate `plugins/gauntlet/pi-agents/`; verify with `python3 scripts/build_pi_agents.py --check`
- [x] 1.3 Update the tool assertions in `test_agents.py`, `test_eta.py`, `test_zeta.py`, `test_handoff.py`; verify with `python3 -m unittest discover -s tests`

## 2. Docs and check on pi

- [x] 2.1 Update docs/install.md, docs/reference.md, docs/development.md, README
- [x] 2.2 Launch the generated eta on pi from a project `.pi/agents/` and confirm no "unavailable child tools"
