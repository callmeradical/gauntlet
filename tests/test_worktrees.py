"""gauntlet-tools: worktree_new and worktree_rm against real temp git repos.

Scenarios: "Worktrees are created the same way every time" (Shared folder) and
"Removal never loses unmerged work" (Unmerged slice, single merged slice without the user).
"""

import json
import os
import unittest

import helpers

CONFIG = {"integration_branch": "main", "shared": ["node_modules"]}


class WorktreeTestCase(unittest.TestCase):
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)
        self.server = helpers.load_server()
        self.repo = helpers.make_repo(self.home, "proj", config=CONFIG)
        self.add_node_modules(self.repo)

    # -- fixtures ----------------------------------------------------------

    def add_node_modules(self, worktree):
        """An untracked node_modules folder in `worktree`, like an installed project's."""
        folder = os.path.join(worktree, "node_modules", "left-pad")
        os.makedirs(folder)
        with open(os.path.join(folder, "index.js"), "w") as f:
            f.write("module.exports = 1;\n")

    def linked_integration(self, name="proj-integration", branch="feat/x"):
        """A linked integration worktree on its own branch, one commit ahead of main."""
        path = os.path.join(self.home, name)
        helpers.git(self.repo, "worktree", "add", "-q", "-b", branch, path)
        self.commit(path, "integration.txt", "integration\n")
        self.add_node_modules(path)
        return os.path.realpath(path)

    def commit(self, worktree, name, text):
        with open(os.path.join(worktree, name), "w") as f:
            f.write(text)
        helpers.git(worktree, "add", name)
        helpers.git(worktree, "commit", "-q", "-m", "add " + name)
        return helpers.git(worktree, "rev-parse", "HEAD")

    def merge(self, slice_branch, into=None):
        helpers.git(into or self.repo, "merge", "-q", "--no-ff", "-m", "merge " + slice_branch, slice_branch)

    def start(self, loop="pri", repo=None, change="fix-pri"):
        return self.server.loop_start(loop=loop, repo=repo or self.repo, change=change)

    def state_path(self, loop):
        return os.path.join(self.home, ".local", "state", "gauntlet", loop + ".json")

    def read_state(self, loop):
        with open(self.state_path(loop)) as f:
            return json.load(f)

    def write_state(self, loop, state):
        os.makedirs(os.path.dirname(self.state_path(loop)), exist_ok=True)
        with open(self.state_path(loop), "w") as f:
            json.dump(state, f)

    def error_of(self, func, **kwargs):
        with self.assertRaises(self.server.GauntletError) as ctx:
            func(**kwargs)
        return ctx.exception.to_dict()

    def branches(self):
        return helpers.git(self.repo, "branch", "--format=%(refname:short)").split("\n")

    def worktree_paths(self):
        lines = helpers.git(self.repo, "worktree", "list", "--porcelain").split("\n")
        return [os.path.realpath(line[len("worktree ") :]) for line in lines if line.startswith("worktree ")]

    def exclude_lines(self):
        with open(os.path.join(self.repo, ".git", "info", "exclude")) as f:
            return f.read().split("\n")

    def new(self, slice, loop="pri"):
        return self.server.worktree_new(loop=loop, slice=slice)


class WorktreeNewTest(WorktreeTestCase):
    def test_creates_worktree_and_branch_with_the_standard_names(self):
        self.start()
        main_tip = helpers.git(self.repo, "rev-parse", "main")
        result = self.new("api")
        path = os.path.join(self.home, "proj-pri-api")
        self.assertEqual(
            result,
            {
                "loop": "pri",
                "slice": "api",
                "worktree": path,
                "branch": "gauntlet/pri/api",
                "base": main_tip,
                "shared": ["node_modules"],
            },
        )
        self.assertIn(path, self.worktree_paths())
        self.assertEqual(helpers.git(path, "rev-parse", "--abbrev-ref", "HEAD"), "gauntlet/pri/api")
        self.assertEqual(helpers.git(path, "rev-parse", "HEAD"), main_tip)

    def test_linked_integration_worktree_names_after_the_main_checkout_and_branches_from_integration(self):
        integration = self.linked_integration()
        self.server.loop_start(loop="pri", repo=integration, change="fix-pri", integration_branch="feat/x")
        result = self.new("api")
        path = os.path.join(self.home, "proj-pri-api")
        self.assertEqual(result["worktree"], path)
        self.assertEqual(result["base"], helpers.git(self.repo, "rev-parse", "feat/x"))
        self.assertTrue(os.path.isfile(os.path.join(path, "integration.txt")))
        self.assertFalse(os.path.exists(os.path.join(self.home, "proj-integration-pri-api")))

    def test_shared_folder_links_to_the_integration_worktree_and_shows_as_ignored(self):
        # Scenario: Shared folder
        integration = self.linked_integration()
        self.server.loop_start(loop="pri", repo=integration, change="fix-pri", integration_branch="feat/x")
        path = self.new("api")["worktree"]
        link = os.path.join(path, "node_modules")
        self.assertTrue(os.path.islink(link))
        self.assertEqual(os.readlink(link), os.path.join(integration, "node_modules"))
        self.assertTrue(os.path.isfile(os.path.join(link, "left-pad", "index.js")))
        porcelain = helpers.git(path, "status", "--porcelain", "--ignored").split("\n")
        self.assertIn("!! node_modules", porcelain)
        self.assertNotIn("?? node_modules", porcelain)
        self.assertEqual(helpers.git(path, "status", "--porcelain"), "")

    def test_shared_links_never_touch_the_project_gitignore(self):
        self.start()
        path = self.new("api")["worktree"]
        self.assertFalse(os.path.exists(os.path.join(path, ".gitignore")))
        self.assertFalse(os.path.exists(os.path.join(self.repo, ".gitignore")))

    def test_exclude_entry_is_anchored_and_added_once(self):
        self.start()
        self.new("api")
        self.new("ui")
        self.assertEqual(self.exclude_lines().count("/node_modules"), 1)

    def test_nested_shared_folder_is_linked_and_ignored(self):
        repo = helpers.make_repo(
            self.home,
            "mono",
            config={"integration_branch": "main", "shared": ["packages/app/node_modules"]},
            files={"packages/app/index.js": "1\n"},
        )
        self.add_node_modules(os.path.join(repo, "packages", "app"))
        self.start(repo=repo)
        path = self.new("api")["worktree"]
        self.assertEqual(path, os.path.join(self.home, "mono-pri-api"))
        link = os.path.join(path, "packages", "app", "node_modules")
        self.assertEqual(os.readlink(link), os.path.join(repo, "packages", "app", "node_modules"))
        self.assertIn("!! packages/app/node_modules", helpers.git(path, "status", "--porcelain", "--ignored"))
        self.assertEqual(helpers.git(path, "status", "--porcelain"), "")

    def test_records_the_worktree_in_state_preserving_unknown_keys(self):
        self.write_state(
            "pri",
            {
                "loop": "pri",
                "repo": self.repo,
                "change": "fix-pri",
                "integration_branch": "main",
                "status": "running",
                "baseline": "0d22149",
                "slices": {"tracer": {"status": "merged", "verdict": "PASS"}},
            },
        )
        result = self.new("api")
        state = self.read_state("pri")
        self.assertEqual(state["slices"]["api"]["worktree"], result["worktree"])
        self.assertEqual(state["slices"]["api"]["branch"], "gauntlet/pri/api")
        self.assertEqual(state["slices"]["tracer"], {"status": "merged", "verdict": "PASS"})
        self.assertEqual(state["baseline"], "0d22149")

    def test_unknown_loop_is_refused(self):
        self.assertEqual(self.error_of(self.server.worktree_new, loop="nope", slice="api")["error"], "unknown_loop")

    def test_invalid_slice_is_refused(self):
        self.start()
        self.assertEqual(self.error_of(self.server.worktree_new, loop="pri", slice="Bad_Name")["error"], "invalid_id")
        self.assertEqual(self.read_state("pri")["slices"], {})

    def test_existing_path_is_refused_leaving_nothing_behind(self):
        self.start()
        os.makedirs(os.path.join(self.home, "proj-pri-api"))
        err = self.error_of(self.server.worktree_new, loop="pri", slice="api")
        self.assertEqual(err["error"], "exists")
        self.assertNotIn("gauntlet/pri/api", self.branches())
        self.assertEqual(os.listdir(os.path.join(self.home, "proj-pri-api")), [])
        self.assertEqual(self.read_state("pri")["slices"], {})

    def test_existing_branch_is_refused_leaving_nothing_behind(self):
        self.start()
        helpers.git(self.repo, "branch", "gauntlet/pri/api")
        err = self.error_of(self.server.worktree_new, loop="pri", slice="api")
        self.assertEqual(err["error"], "exists")
        self.assertFalse(os.path.exists(os.path.join(self.home, "proj-pri-api")))
        self.assertEqual(self.read_state("pri")["slices"], {})

    def test_missing_shared_source_is_refused_before_creating_anything(self):
        # Q15
        repo = helpers.make_repo(self.home, "bare", config=CONFIG)
        self.start(repo=repo)
        err = self.error_of(self.server.worktree_new, loop="pri", slice="api")
        self.assertEqual(err["error"], "config_invalid")
        self.assertIn("shared", err["fields"])
        self.assertIn("node_modules", err["fields"]["shared"])
        self.assertFalse(os.path.exists(os.path.join(self.home, "bare-pri-api")))
        self.assertNotIn("gauntlet/pri/api", helpers.git(repo, "branch", "--format=%(refname:short)"))
        exclude = os.path.join(repo, ".git", "info", "exclude")
        if os.path.exists(exclude):
            with open(exclude) as f:
                self.assertNotIn("/node_modules", f.read().split("\n"))
        self.assertEqual(self.read_state("pri")["slices"], {})

    def test_failure_after_checkout_rolls_back_worktree_and_branch(self):
        # node_modules is tracked here, so the checkout already has one where the link must go.
        repo = helpers.make_repo(self.home, "tracked", config=CONFIG, files={"node_modules/x.js": "1\n"})
        self.start(repo=repo)
        err = self.error_of(self.server.worktree_new, loop="pri", slice="api")
        self.assertEqual(err["error"], "exists")
        self.assertFalse(os.path.exists(os.path.join(self.home, "tracked-pri-api")))
        self.assertNotIn("gauntlet/pri/api", helpers.git(repo, "branch", "--format=%(refname:short)"))
        self.assertEqual(len(helpers.git(repo, "worktree", "list", "--porcelain").split("\n\n")), 1)
        self.assertEqual(self.read_state("pri")["slices"], {})


class WorktreeRmTest(WorktreeTestCase):
    def build_loop(self):
        """Loop `pri` with slice `api` merged, `docs` merged with no commits, `ui` stopped with two unmerged commits."""
        self.start()
        api = self.new("api")["worktree"]
        self.commit(api, "api.txt", "api\n")
        self.merge("gauntlet/pri/api")
        self.new("docs")
        ui = self.new("ui")["worktree"]
        unmerged = [self.commit(ui, "ui1.txt", "1\n"), self.commit(ui, "ui2.txt", "2\n")]
        self.server.loop_update(loop="pri", slice="ui", status="stopped")
        return unmerged

    def test_removes_merged_slices_and_keeps_the_unmerged_one(self):
        # Scenario: Unmerged slice
        unmerged = self.build_loop()
        result = self.server.worktree_rm(loop="pri")
        removed = {entry["slice"]: entry for entry in result["removed"]}
        self.assertEqual(sorted(removed), ["api", "docs"])
        self.assertEqual(removed["api"]["worktree"], os.path.join(self.home, "proj-pri-api"))
        self.assertEqual(removed["api"]["branch"], "gauntlet/pri/api")
        kept = [entry for entry in result["kept"] if entry["slice"] == "ui"]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["worktree"], os.path.join(self.home, "proj-pri-ui"))
        self.assertEqual(kept[0]["branch"], "gauntlet/pri/ui")
        self.assertEqual(sorted(kept[0]["commits"]), sorted(unmerged))
        self.assertIn("unmerged", kept[0]["reason"])
        for name in ("api", "docs"):
            self.assertFalse(os.path.exists(os.path.join(self.home, "proj-pri-" + name)))
            self.assertNotIn("gauntlet/pri/" + name, self.branches())
        self.assertTrue(os.path.isfile(os.path.join(self.home, "proj-pri-ui", "ui2.txt")))
        self.assertIn("gauntlet/pri/ui", self.branches())

    def test_removal_leaves_the_shared_folder_contents_alone(self):
        self.build_loop()
        self.server.worktree_rm(loop="pri")
        self.assertTrue(os.path.isfile(os.path.join(self.repo, "node_modules", "left-pad", "index.js")))

    def test_removing_one_merged_slice_needs_no_one_else(self):
        self.build_loop()
        result = self.server.worktree_rm(loop="pri", slice="api")
        api = {"slice": "api", "worktree": os.path.join(self.home, "proj-pri-api"), "branch": "gauntlet/pri/api"}
        self.assertEqual(result, {"removed": [api], "kept": []})
        self.assertTrue(os.path.isdir(os.path.join(self.home, "proj-pri-docs")))
        self.assertIn("gauntlet/pri/docs", self.branches())

    def test_removing_one_unmerged_slice_keeps_it(self):
        unmerged = self.build_loop()
        result = self.server.worktree_rm(loop="pri", slice="ui")
        self.assertEqual(result["removed"], [])
        self.assertEqual(len(result["kept"]), 1)
        self.assertEqual(sorted(result["kept"][0]["commits"]), sorted(unmerged))

    def test_dirty_worktree_is_never_force_removed(self):
        self.start()
        path = self.new("api")["worktree"]
        with open(os.path.join(path, "scratch.txt"), "w") as f:
            f.write("work in progress\n")
        result = self.server.worktree_rm(loop="pri", slice="api")
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["kept"][0]["slice"], "api")
        self.assertIn("dirty", result["kept"][0]["reason"])
        self.assertTrue(os.path.isfile(os.path.join(path, "scratch.txt")))
        self.assertIn("gauntlet/pri/api", self.branches())

    def test_commits_on_a_detached_head_in_the_worktree_are_kept(self):
        self.start()
        path = self.new("api")["worktree"]
        helpers.git(path, "checkout", "-q", "--detach")
        sha = self.commit(path, "detached.txt", "x\n")
        result = self.server.worktree_rm(loop="pri", slice="api")
        self.assertEqual(result["removed"], [])
        self.assertEqual(result["kept"][0]["commits"], [sha])
        self.assertTrue(os.path.isfile(os.path.join(path, "detached.txt")))

    def test_removal_is_recorded_in_state(self):
        self.build_loop()
        self.server.worktree_rm(loop="pri")
        slices = self.read_state("pri")["slices"]
        self.assertIn("removed", slices["api"])
        self.assertIn("removed", slices["docs"])
        self.assertNotIn("removed", slices["ui"])
        self.assertEqual(slices["ui"]["status"], "stopped")

    def test_a_slice_can_be_created_again_after_removal(self):
        self.start()
        self.new("api")
        self.server.worktree_rm(loop="pri", slice="api")
        self.new("api")
        self.assertNotIn("removed", self.read_state("pri")["slices"]["api"])

    def test_main_checkout_and_integration_branch_are_never_removed(self):
        self.build_loop()
        result = self.server.worktree_rm(loop="pri")
        self.assertNotIn(self.repo, [entry["worktree"] for entry in result["removed"]])
        self.assertTrue(os.path.isfile(os.path.join(self.repo, ".gauntlet.json")))
        self.assertIn(self.repo, self.worktree_paths())
        self.assertIn("main", self.branches())

    def test_unknown_loop_is_refused(self):
        self.assertEqual(self.error_of(self.server.worktree_rm, loop="nope")["error"], "unknown_loop")

    def test_unknown_slice_is_refused(self):
        self.start()
        self.assertEqual(self.error_of(self.server.worktree_rm, loop="pri", slice="nope")["error"], "unknown_loop")


class IntegrationWorktreeRemovalTest(WorktreeTestCase):
    """Q1: `worktree rm <loop>` with no slice also removes a clean, merged, linked integration worktree."""

    def setUp(self):
        super().setUp()
        self.integration = self.linked_integration()
        self.server.loop_start(loop="pri", repo=self.integration, change="fix-pri", integration_branch="feat/x")
        api = self.new("api")["worktree"]
        self.commit(api, "api.txt", "api\n")
        self.merge("gauntlet/pri/api", into=self.integration)

    def test_whole_loop_removal_takes_the_integration_worktree_but_not_its_branch(self):
        result = self.server.worktree_rm(loop="pri")
        self.assertIn({"slice": None, "worktree": self.integration, "branch": "feat/x"}, result["removed"])
        self.assertFalse(os.path.exists(self.integration))
        self.assertIn("feat/x", self.branches())
        self.assertTrue(os.path.isdir(self.repo))

    def test_single_slice_removal_leaves_the_integration_worktree(self):
        self.server.worktree_rm(loop="pri", slice="api")
        self.assertTrue(os.path.isdir(self.integration))

    def test_dirty_integration_worktree_is_kept(self):
        with open(os.path.join(self.integration, "notes.txt"), "w") as f:
            f.write("x\n")
        result = self.server.worktree_rm(loop="pri")
        kept = [entry for entry in result["kept"] if entry["slice"] is None]
        self.assertEqual(len(kept), 1)
        self.assertIn("dirty", kept[0]["reason"])
        self.assertTrue(os.path.isfile(os.path.join(self.integration, "notes.txt")))

    def test_integration_worktree_with_commits_missing_from_the_integration_branch_is_kept(self):
        helpers.git(self.integration, "checkout", "-q", "-b", "side")
        sha = self.commit(self.integration, "side.txt", "side\n")
        result = self.server.worktree_rm(loop="pri")
        kept = [entry for entry in result["kept"] if entry["slice"] is None]
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["commits"], [sha])
        self.assertTrue(os.path.isdir(self.integration))

    def test_integration_worktree_used_by_another_running_loop_is_kept(self):
        self.server.loop_start(loop="other", repo=self.integration, change="other-change")
        result = self.server.worktree_rm(loop="pri")
        kept = [entry for entry in result["kept"] if entry["slice"] is None]
        self.assertEqual(len(kept), 1)
        self.assertIn("other", kept[0]["reason"])
        self.assertTrue(os.path.isdir(self.integration))

    def test_main_checkout_as_integration_worktree_is_kept_and_reported(self):
        self.server.loop_start(loop="mainline", repo=self.repo, change="main-change")
        result = self.server.worktree_rm(loop="mainline")
        self.assertEqual(result["removed"], [])
        self.assertEqual(len(result["kept"]), 1)
        self.assertIsNone(result["kept"][0]["slice"])
        self.assertIn("main checkout", result["kept"][0]["reason"])
        self.assertTrue(os.path.isdir(self.repo))


class WorktreeInterfacesTest(WorktreeTestCase):
    def test_stdio_calls_for_both_tools(self):
        self.start()
        with helpers.McpClient(self.home) as client:
            client.request("initialize", {"protocolVersion": "2025-06-18"})
            is_error, created = client.call("worktree_new", {"loop": "pri", "slice": "api"})
            self.assertFalse(is_error)
            self.assertEqual(created["worktree"], os.path.join(self.home, "proj-pri-api"))
            is_error, removed = client.call("worktree_rm", {"loop": "pri", "slice": "api"})
            self.assertFalse(is_error)
            self.assertEqual([entry["slice"] for entry in removed["removed"]], ["api"])
            is_error, err = client.call("worktree_new", {"loop": "nope", "slice": "api"})
            self.assertTrue(is_error)
            self.assertEqual(err["error"], "unknown_loop")

    def test_cli_new_and_rm_print_the_tool_result(self):
        self.start()
        proc = helpers.run_cli("worktree", "new", "pri", "api", home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["branch"], "gauntlet/pri/api")
        proc = helpers.run_cli("worktree", "rm", "pri", home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["removed"][0]["slice"], "api")
        proc = helpers.run_cli("worktree", "new", "nope", "api", home=self.home)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(json.loads(proc.stderr)["error"], "unknown_loop")


if __name__ == "__main__":
    unittest.main()
