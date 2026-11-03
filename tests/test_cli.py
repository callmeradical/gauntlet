"""gauntlet-tools / CLI: the same functions from the terminal, printing the tool's JSON."""

import json
import os
import stat
import subprocess
import tempfile
import unittest

import helpers

CONFIG = {"integration_branch": "main", "shared": ["node_modules"]}


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)
        self.repo = helpers.make_repo(self.home, "proj", config=CONFIG)

    def cli(self, *args):
        return helpers.run_cli(*args, home=self.home)

    def ok(self, *args):
        proc = self.cli(*args)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        result = json.loads(proc.stdout)
        self.assertEqual(proc.stdout, json.dumps(result, indent=2) + "\n")
        return result

    def fails(self, *args):
        proc = self.cli(*args)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertEqual(proc.stdout, "")
        return json.loads(proc.stderr)


class LoopCommandsTest(CliTestCase):
    def test_loop_start_update_end(self):
        state = self.ok("loop", "start", "pri", "--repo", self.repo, "--change", "fix-pri")
        self.assertEqual((state["loop"], state["repo"], state["change"]), ("pri", self.repo, "fix-pri"))
        self.assertEqual(state["integration_branch"], "main")

        state = self.ok(
            "loop", "update", "pri", "--phase", "build", "--slice", "tracer", "--worktree", "/w", "--branch", "b",
            "--status", "building", "--round", "2", "--commit", "abc", "--verdict", "HOLD",
        )
        self.assertEqual(state["phase"], "build")
        self.assertEqual(
            state["slices"]["tracer"],
            {"worktree": "/w", "branch": "b", "status": "building", "round": 2, "commit": "abc", "verdict": "HOLD"},
        )

        state = self.ok("loop", "end", "pri", "done")
        self.assertEqual(state["status"], "done")
        with open(os.path.join(self.home, ".local", "state", "gauntlet", "pri.json")) as f:
            self.assertEqual(json.load(f), state)

    def test_loop_start_with_integration_branch(self):
        state = self.ok(
            "loop", "start", "pri", "--repo", self.repo, "--change", "c", "--integration-branch", "feat/decision-tree"
        )
        self.assertEqual(state["integration_branch"], "feat/decision-tree")

    def test_duplicate_loop_prints_error_json_to_stderr(self):
        # Scenario: Duplicate id, from the terminal
        self.ok("loop", "start", "pri", "--repo", self.repo, "--change", "a")
        err = self.fails("loop", "start", "pri", "--repo", self.repo, "--change", "b")
        self.assertEqual((err["error"], err["running"]), ("duplicate_loop", "pri"))

    def test_missing_config_from_the_terminal(self):
        bare = helpers.make_repo(self.home, "bare")
        err = self.fails("loop", "start", "pri", "--repo", bare, "--change", "c")
        self.assertEqual(err["error"], "config_missing")
        self.assertEqual(err["ask"], ["integration_branch", "shared", "checks", "setup"])

    def test_bad_end_status_is_a_usage_error(self):
        proc = self.cli("loop", "end", "pri", "finished")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")


class ConfigCommandTest(CliTestCase):
    def test_config_prints_config_read_result(self):
        self.assertEqual(
            self.ok("config", self.repo),
            {
                "path": os.path.join(self.repo, ".gauntlet.json"),
                "config": {"integration_branch": "main", "shared": ["node_modules"], "checks": [], "setup": None},
            },
        )

    def test_config_output_equals_the_tool_result_over_mcp(self):
        with helpers.McpClient(self.home) as client:
            is_error, payload = client.call("config_read", {"repo": self.repo})
        self.assertFalse(is_error)
        self.assertEqual(self.ok("config", self.repo), payload)

    def test_invalid_config_error_equals_the_tool_error_over_mcp(self):
        bad = helpers.make_repo(self.home, "bad", config={"integration_branch": "main", "shared": "node_modules"})
        with helpers.McpClient(self.home) as client:
            is_error, payload = client.call("config_read", {"repo": bad})
        self.assertTrue(is_error)
        self.assertEqual(self.fails("config", bad), payload)


class CorruptStateTest(CliTestCase):
    def test_corrupt_state_file_is_error_json_and_exit_1(self):
        folder = os.path.join(self.home, ".local", "state", "gauntlet")
        os.makedirs(folder)
        with open(os.path.join(folder, "x.json"), "w") as f:
            f.write("{corrupt")
        err = self.fails("loop", "end", "x", "done")
        self.assertEqual(err["error"], "unknown_loop")
        self.assertTrue(err["reason"])


class PathLinkTest(CliTestCase):
    def test_cli_runs_through_a_symlink_on_path(self):
        bin_dir = tempfile.mkdtemp(dir=self.home)
        link = os.path.join(bin_dir, "gauntlet")
        os.symlink(os.path.join(helpers.PLUGIN, "server", "gauntlet.py"), link)
        env = dict(os.environ, HOME=self.home, PATH=bin_dir + os.pathsep + os.environ.get("PATH", ""))
        proc = subprocess.run(
            ["gauntlet", "config", self.repo],
            env=env,
            cwd=self.home,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=helpers.TIMEOUT,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            json.loads(proc.stdout),
            {
                "path": os.path.join(self.repo, ".gauntlet.json"),
                "config": {"integration_branch": "main", "shared": ["node_modules"], "checks": [], "setup": None},
            },
        )


class WiringTest(CliTestCase):
    def test_every_subcommand_exists(self):
        commands = [
            ("status",),
            ("worktree", "new"),
            ("worktree", "rm"),
            ("lock", "acquire"),
            ("lock", "release"),
            ("loop", "start"),
            ("loop", "update"),
            ("loop", "end"),
            ("config",),
        ]
        for command in commands:
            proc = self.cli(*command, "--help")
            self.assertEqual(proc.returncode, 0, (command, proc.stderr))
            self.assertIn("usage:", proc.stdout)

    def test_unknown_subcommand_is_a_usage_error(self):
        proc = self.cli("frobnicate")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")

    def test_server_is_an_executable_python3_script(self):
        server = os.path.join(helpers.PLUGIN, "server", "gauntlet.py")
        with open(server) as f:
            self.assertEqual(f.readline().rstrip("\n"), "#!/usr/bin/env python3")
        self.assertTrue(os.stat(server).st_mode & stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
