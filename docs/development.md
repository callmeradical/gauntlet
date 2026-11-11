# Development

Back to the [README](../README.md).

## Checks

The checks, all of which must pass:

```sh
python3 -m unittest discover -s tests -v
/usr/bin/python3 -m unittest discover -s tests -v   # Python 3.9
python3 -m py_compile plugins/gauntlet/server/gauntlet.py scripts/cutover.py scripts/build_pi_agents.py
python3 scripts/build_pi_agents.py --check   # pi-agents/ matches agents/
openspec validate package-gauntlet-plugin --strict
```

Tests use temp folders, temp git repos and a fake `HOME`, so they never touch your real `~/.claude` or `~/.local/state/gauntlet`. To try the plugin without installing it, run `claude --plugin-dir plugins/gauntlet`.

After editing an agent in `plugins/gauntlet/agents/`, run `python3 scripts/build_pi_agents.py` to regenerate `plugins/gauntlet/pi-agents/`.

## Releasing

Every release bumps the version, because Claude Code offers an update only when the version changes. The marketplace entry carries no version. Change all three places to the same value:

- `plugins/gauntlet/plugin.json` (`version`)
- `plugins/gauntlet/.claude-plugin/plugin.json` (`version`)
- `VERSION` in `plugins/gauntlet/server/gauntlet.py`

`tests/test_manifests.py` checks that the three agree and pins the current value, so update it with the bump. Then run the checks, commit, push, and update each machine as described in [Updating](install.md#updating).

## Publishing

The repo is public, at `callmeradical/gauntlet`, and is its own marketplace. It was created and first pushed from `~/Dev/gauntlet` with:

```sh
cd ~/Dev/gauntlet
gh repo create callmeradical/gauntlet --public --source . --remote origin --push
```

The repo is MIT-licensed (`LICENSE`). The bundled `tdd` and `codebase-design` skills keep their own MIT notices from `mattpocock/skills`.
