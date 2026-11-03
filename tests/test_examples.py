"""setup-cutover and project-config: the README and ControlTower's example .gauntlet.json."""

import json
import os
import re
import unittest

import helpers

EXAMPLE = os.path.join(helpers.REPO_ROOT, "examples", "controltower.gauntlet.json")
README = os.path.join(helpers.REPO_ROOT, "README.md")
MARKETPLACE = os.path.join(helpers.REPO_ROOT, ".claude-plugin", "marketplace.json")
PLUGIN_JSON = os.path.join(helpers.PLUGIN, "plugin.json")
VENDORED_COMMIT = "4ae2317ddb22b046e26455e4f9c9b3aaaf62212d"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


class ConfigReadMixin:
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)
        self.server = helpers.load_server()

    def config_read_text(self, text, name="proj"):
        """Put `text` in a temp repo as .gauntlet.json and return config_read's config."""
        repo = helpers.make_repo(self.home, name, files={".gauntlet.json": text})
        return self.server.config_read(repo=repo)["config"]


class ControlTowerExampleTest(ConfigReadMixin, unittest.TestCase):
    def test_config_read_returns_controltower_facts(self):
        self.assertEqual(
            self.config_read_text(read(EXAMPLE)),
            {
                "integration_branch": "feat/decision-tree",
                "shared": ["node_modules"],
                "checks": [
                    {"name": "test", "command": "npx vitest run"},
                    {"name": "build:ts", "command": "npm run build:ts"},
                    {"name": "build:app", "command": "npm run build:app"},
                    {"name": "typecheck", "command": "npx tsc --noEmit -p src/renderer"},
                ],
                "setup": "npm run rebuild:node",
            },
        )

    def test_terminal_config_command_accepts_it(self):
        repo = helpers.make_repo(self.home, "controltower", files={".gauntlet.json": read(EXAMPLE)})
        proc = helpers.run_cli("config", repo, home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["config"]["integration_branch"], "feat/decision-tree")


class ReadmeConfigBlocksTest(ConfigReadMixin, unittest.TestCase):
    def test_every_gauntlet_json_block_in_the_readme_is_accepted(self):
        blocks = [b for b in re.findall(r"```json\n(.*?)```", read(README), re.S) if "integration_branch" in b]
        self.assertTrue(blocks, "README shows no .gauntlet.json example")
        for i, block in enumerate(blocks):
            with self.subTest(block=i):
                self.config_read_text(block, name="proj%d" % i)


class ReadmeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.readme = read(README)

    def test_install_uses_the_marketplace_and_plugin_names(self):
        marketplace = json.loads(read(MARKETPLACE))
        plugin = marketplace["plugins"][0]["name"]
        self.assertIn("%s@%s" % (plugin, marketplace["name"]), self.readme)

    def test_marketplace_is_added_from_the_plugin_repository(self):
        repository = json.loads(read(PLUGIN_JSON))["repository"]
        owner_repo = repository.split("github.com/", 1)[1]
        self.assertIn("/plugin marketplace add %s" % owner_repo, self.readme)

    def test_public_repo_needs_no_credentials_to_install(self):
        self.assertIn("The repo is public", self.readme)
        for text in ("gh auth login", "gh auth setup-git"):
            self.assertIn(text, self.readme)

    def test_dedicated_clone_and_terminal_link(self):
        self.assertIn("~/Dev/gauntlet", self.readme)
        self.assertIn("ln -s", self.readme)
        self.assertIn("~/.local/bin/gauntlet", self.readme)
        self.assertIn("plugins/gauntlet/server/gauntlet.py", self.readme)

    def test_cutover_dry_run_run_and_rollback(self):
        self.assertIn("scripts/cutover.py --dry-run", self.readme)
        self.assertIn("scripts/cutover.py --rollback", self.readme)

    def test_updates_only_while_status_shows_no_running_loop(self):
        self.assertIn("gauntlet status", self.readme)
        self.assertRegex(self.readme, r"(?i)no (loop is|running loop)")

    def test_release_bumps_every_version_location(self):
        for path in ("plugins/gauntlet/plugin.json", "plugins/gauntlet/.claude-plugin/plugin.json", "VERSION"):
            self.assertIn(path, self.readme)

    def test_names_every_machine(self):
        for text in ("A Linux machine", "Any other machine"):
            self.assertIn(text, self.readme)

    def test_credits_the_bundled_skills(self):
        for text in ("mattpocock/skills", VENDORED_COMMIT, "MIT", "skills/engineering/tdd", "skills/engineering/codebase-design"):
            self.assertIn(text, self.readme)

    def test_mentions_the_loose_skill_links_the_cutover_leaves(self):
        self.assertIn("~/.claude/skills/tdd", self.readme)
        self.assertIn("~/.claude/skills/codebase-design", self.readme)


if __name__ == "__main__":
    unittest.main()
