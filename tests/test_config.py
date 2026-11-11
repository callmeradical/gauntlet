"""project-config: reading and validating .gauntlet.json (config_read)."""

import os
import unittest

import helpers

ASK = ["integration_branch", "shared", "checks", "setup"]


class ConfigReadTest(unittest.TestCase):
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)
        self.server = helpers.load_server()

    def write_config(self, text):
        repo = helpers.make_repo(self.home, "proj")
        with open(os.path.join(repo, ".gauntlet.json"), "w") as f:
            f.write(text)
        return repo

    def read_error(self, repo):
        with self.assertRaises(self.server.GauntletError) as ctx:
            self.server.config_read(repo=repo)
        return ctx.exception.to_dict()

    def test_full_config_is_returned_with_its_path(self):
        repo = helpers.make_repo(
            self.home,
            "proj",
            config={
                "integration_branch": "feat/decision-tree",
                "shared": ["node_modules"],
                "checks": [{"name": "test", "command": "npx vitest run"}],
                "setup": "npm run rebuild:node",
            },
        )
        self.assertEqual(
            self.server.config_read(repo=repo),
            {
                "path": os.path.join(repo, ".gauntlet.json"),
                "config": {
                    "integration_branch": "feat/decision-tree",
                    "shared": ["node_modules"],
                    "checks": [{"name": "test", "command": "npx vitest run"}],
                    "setup": "npm run rebuild:node",
                    "handoff": {"context_threshold": 0.65},
                },
            },
        )

    def test_optional_fields_take_defaults(self):
        repo = helpers.make_repo(self.home, "proj", config={"integration_branch": "main"})
        self.assertEqual(
            self.server.config_read(repo=repo)["config"],
            {
                "integration_branch": "main",
                "shared": [],
                "checks": [],
                "setup": None,
                "handoff": {"context_threshold": 0.65},
            },
        )

    def test_shared_entries_are_normalised(self):
        repo = helpers.make_repo(
            self.home, "proj", config={"integration_branch": "main", "shared": ["node_modules/", "a/./b"]}
        )
        self.assertEqual(self.server.config_read(repo=repo)["config"]["shared"], ["node_modules", "a/b"])

    def test_invalid_field_shared_as_string(self):
        # Scenario: Invalid field
        repo = helpers.make_repo(
            self.home, "proj", config={"integration_branch": "main", "shared": "node_modules"}
        )
        err = self.read_error(repo)
        self.assertEqual(err["error"], "config_invalid")
        self.assertEqual(list(err["fields"]), ["shared"])
        self.assertEqual(err["path"], os.path.join(repo, ".gauntlet.json"))

    def test_integration_branch_is_required(self):
        repo = helpers.make_repo(self.home, "proj", config={"shared": []})
        self.assertEqual(list(self.read_error(repo)["fields"]), ["integration_branch"])

    def test_integration_branch_must_be_a_nonempty_string(self):
        for bad in ("", 3, None):
            repo = helpers.make_repo(self.home, "proj-%r" % (bad,), config={"integration_branch": bad})
            self.assertEqual(list(self.read_error(repo)["fields"]), ["integration_branch"], bad)

    def test_unknown_keys_are_reported_by_field(self):
        repo = helpers.make_repo(self.home, "proj", config={"integration_branch": "main", "checkz": []})
        err = self.read_error(repo)
        self.assertEqual(list(err["fields"]), ["checkz"])

    def test_shared_paths_must_stay_relative(self):
        for bad in (["../elsewhere"], ["/abs/path"], ["a/../../b"], ["."], [""], [3]):
            repo = helpers.make_repo(
                self.home, "proj%d" % len(os.listdir(self.home)), config={"integration_branch": "main", "shared": bad}
            )
            self.assertEqual(list(self.read_error(repo)["fields"]), ["shared"], bad)

    def test_checks_need_name_and_command_strings(self):
        bads = (
            "npm test",
            [{"name": "test"}],
            [{"command": "npm test"}],
            [{"name": "", "command": "npm test"}],
            [{"name": "test", "command": 5}],
            [{"name": "test", "command": "npm test", "cwd": "x"}],
            ["npm test"],
        )
        for i, bad in enumerate(bads):
            repo = helpers.make_repo(self.home, "proj%d" % i, config={"integration_branch": "main", "checks": bad})
            self.assertEqual(list(self.read_error(repo)["fields"]), ["checks"], bad)

    def test_setup_is_string_or_null(self):
        repo = helpers.make_repo(self.home, "ok", config={"integration_branch": "main", "setup": None})
        self.assertIsNone(self.server.config_read(repo=repo)["config"]["setup"])
        repo = helpers.make_repo(self.home, "bad", config={"integration_branch": "main", "setup": ["npm ci"]})
        self.assertEqual(list(self.read_error(repo)["fields"]), ["setup"])

    def test_handoff_threshold_is_read(self):
        repo = helpers.make_repo(
            self.home, "proj", config={"integration_branch": "main", "handoff": {"context_threshold": 0.5}}
        )
        self.assertEqual(self.server.config_read(repo=repo)["config"]["handoff"], {"context_threshold": 0.5})

    def test_handoff_without_threshold_takes_the_default(self):
        repo = helpers.make_repo(self.home, "proj", config={"integration_branch": "main", "handoff": {}})
        self.assertEqual(self.server.config_read(repo=repo)["config"]["handoff"], {"context_threshold": 0.65})

    def test_handoff_threshold_must_be_a_fraction(self):
        for bad in (0, 1.5, -0.1, "0.6", True, None):
            with self.subTest(value=bad):
                repo = helpers.make_repo(
                    self.home, f"p{abs(hash(repr(bad)))}", config={"integration_branch": "main", "handoff": {"context_threshold": bad}}
                )
                err = self.read_error(repo)
                self.assertEqual(err["error"], "config_invalid")
                self.assertIn("handoff.context_threshold", err["fields"])

    def test_handoff_must_be_an_object_with_known_keys(self):
        for bad, field in (("x", "handoff"), ({"threshold": 0.5}, "handoff.threshold")):
            with self.subTest(value=bad):
                repo = helpers.make_repo(
                    self.home, f"p{abs(hash(repr(bad)))}", config={"integration_branch": "main", "handoff": bad}
                )
                self.assertIn(field, self.read_error(repo)["fields"])

    def test_all_bad_fields_are_reported_together(self):
        repo = helpers.make_repo(self.home, "proj", config={"shared": "x", "checks": "y", "extra": 1})
        self.assertEqual(
            sorted(self.read_error(repo)["fields"]), ["checks", "extra", "integration_branch", "shared"]
        )

    def test_unparseable_file_is_invalid(self):
        repo = self.write_config("{not json")
        err = self.read_error(repo)
        self.assertEqual(err["error"], "config_invalid")
        self.assertEqual(list(err["fields"]), ["$"])

    def test_non_object_file_is_invalid(self):
        repo = self.write_config('["integration_branch"]')
        self.assertEqual(list(self.read_error(repo)["fields"]), ["$"])

    def test_missing_file_asks_for_the_four_fields(self):
        repo = helpers.make_repo(self.home, "proj")
        err = self.read_error(repo)
        self.assertEqual(err["error"], "config_missing")
        self.assertEqual(err["path"], os.path.join(repo, ".gauntlet.json"))
        self.assertEqual(err["ask"], ASK)
        self.assertTrue(err["message"])


if __name__ == "__main__":
    unittest.main()
