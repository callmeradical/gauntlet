"""The shared test helpers behave as the slice contract says."""

import json
import os
import tempfile
import unittest

import helpers


class FakeHomeTest(unittest.TestCase):
    def test_sets_and_restores_home(self):
        real = os.environ.get("HOME")
        with helpers.fake_home() as home:
            self.assertEqual(os.environ["HOME"], home)
            self.assertTrue(os.path.isdir(home))
            self.assertNotEqual(home, real)
            self.assertEqual(os.environ["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(os.environ.get("HOME"), real)
        self.assertFalse(os.path.exists(home))

    def test_git_identity_lets_commits_succeed(self):
        with helpers.fake_home() as home:
            repo = helpers.make_repo(home, "proj")
            author = helpers.git(repo, "log", "-1", "--format=%an <%ae>")
            self.assertTrue(author)
            self.assertEqual(author, "Gauntlet Test <test@example.invalid>")

    def test_server_state_dir_is_inside_fake_home(self):
        with helpers.fake_home() as home:
            server = helpers.load_server()
            self.assertEqual(server.state_dir(), os.path.join(home, ".local", "state", "gauntlet"))


class MakeRepoTest(unittest.TestCase):
    def test_creates_committed_repo_on_named_branch(self):
        with helpers.fake_home() as home:
            repo = helpers.make_repo(home, "proj", branch="feat/x", files={"src/a.txt": "hello\n"})
            self.assertEqual(repo, os.path.realpath(os.path.join(home, "proj")))
            self.assertEqual(helpers.git(repo, "rev-parse", "--abbrev-ref", "HEAD"), "feat/x")
            self.assertEqual(helpers.git(repo, "status", "--porcelain"), "")
            with open(os.path.join(repo, "src", "a.txt")) as f:
                self.assertEqual(f.read(), "hello\n")

    def test_writes_and_commits_config(self):
        with helpers.fake_home() as home:
            repo = helpers.make_repo(home, "proj", config={"integration_branch": "main"})
            with open(os.path.join(repo, ".gauntlet.json")) as f:
                self.assertEqual(json.load(f), {"integration_branch": "main"})
            self.assertIn(".gauntlet.json", helpers.git(repo, "ls-files"))

    def test_no_config_by_default(self):
        with helpers.fake_home() as home:
            repo = helpers.make_repo(home, "proj")
            self.assertFalse(os.path.exists(os.path.join(repo, ".gauntlet.json")))


class RunCliTest(unittest.TestCase):
    def test_runs_server_with_given_home(self):
        with helpers.fake_home() as home:
            repo = helpers.make_repo(home, "proj", config={"integration_branch": "main"})
            proc = helpers.run_cli("config", repo, home=home)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)["config"]["integration_branch"], "main")


class McpClientTest(unittest.TestCase):
    def test_request_and_call(self):
        with helpers.fake_home() as home:
            repo = helpers.make_repo(home, "proj", config={"integration_branch": "main"})
            with helpers.McpClient(home) as client:
                reply = client.request("ping")
                self.assertEqual(reply["result"], {})
                is_error, payload = client.call("config_read", {"repo": repo})
                self.assertFalse(is_error)
                self.assertEqual(payload["config"]["integration_branch"], "main")


class ReadFrontmatterTest(unittest.TestCase):
    def _write(self, text):
        fd, path = tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w") as f:
            f.write(text)
        self.addCleanup(os.remove, path)
        return path

    def test_plain_values_and_quotes(self):
        path = self._write('---\nname: alpha\ntools: Read, Write, Agent\nmodel: "opus"\n---\nbody\n')
        self.assertEqual(
            helpers.read_frontmatter(path),
            {"name": "alpha", "tools": "Read, Write, Agent", "model": "opus"},
        )

    def test_folded_block_scalar(self):
        path = self._write(
            "---\nname: x\ndescription: >\n  first line\n  second line\n\n  new paragraph\nother: y\n---\n"
        )
        fm = helpers.read_frontmatter(path)
        self.assertEqual(fm["description"], "first line second line\nnew paragraph\n")
        self.assertEqual(fm["other"], "y")

    def test_literal_block_scalar_with_strip(self):
        path = self._write("---\ndescription: |-\n  line one\n    indented\n  line three\nname: z\n---\n")
        fm = helpers.read_frontmatter(path)
        self.assertEqual(fm["description"], "line one\n  indented\nline three")
        self.assertEqual(fm["name"], "z")

    def test_missing_frontmatter_is_empty(self):
        path = self._write("# no frontmatter\n")
        self.assertEqual(helpers.read_frontmatter(path), {})


class PluginPathTest(unittest.TestCase):
    def test_plugin_points_at_plugin_dir(self):
        self.assertTrue(helpers.PLUGIN.endswith(os.path.join("plugins", "gauntlet")))
        self.assertTrue(os.path.isdir(helpers.PLUGIN))


if __name__ == "__main__":
    unittest.main()
