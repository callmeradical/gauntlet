# Tasks

## 1. Skill and rule

- [x] 1.1 Add `plugins/gauntlet/skills/handoff/SKILL.md`; verify with `python3 -m unittest discover -s tests -p "test_handoff.py"`
- [x] 1.2 Add "Context handoffs" to all agents and `gauntlet-loop`; verify with `python3 -m unittest discover -s tests -p "test_handoff.py"`

## 2. Server

- [x] 2.1 Validate `handoff.context_threshold` in `config_read`; verify with `python3 -m unittest discover -s tests -p "test_config.py"`
- [x] 2.2 Add `handoff` to `loop_update`, its schema and CLI; verify with `python3 -m unittest discover -s tests -p "test_state.py"` and `-p "test_mcp.py"`

## 3. pi tools and docs

- [x] 3.1 Add pi tool names to agent `tools`; verify with `python3 -m unittest discover -s tests -p "test_handoff.py"`
- [x] 3.2 Update README, docs/reference.md, docs/install.md, docs/configuration.md
