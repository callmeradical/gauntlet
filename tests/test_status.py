"""gauntlet-tools: status lists loops, their worktrees and locks, and flags finished loops with leftovers."""

import datetime
import hashlib
import json
import os
import time
import unittest

import helpers

BRANCH = "feat/decision-tree"
CONFIG = {"integration_branch": BRANCH}


def snapshot(*roots):
    """{path: (mtime_ns, sha256)} for every file and folder under the roots, to prove nothing was written."""
    result = {}
    for root in roots:
        for folder, dirs, files in os.walk(root):
            result[folder] = (os.stat(folder).st_mtime_ns, None)
            for name in files:
                path = os.path.join(folder, name)
                with open(path, "rb") as f:
                    result[path] = (os.stat(path).st_mtime_ns, hashlib.sha256(f.read()).hexdigest())
    return result


class StatusTestCase(unittest.TestCase):
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)
        self.server = helpers.load_server()
        self.repo = helpers.make_repo(self.home, "controltower", config=CONFIG)
        helpers.git(self.repo, "branch", BRANCH)
        self.state = os.path.join(self.home, ".local", "state", "gauntlet")

    def integration_worktree(self, name="controltower-decision-tree"):
        """A linked integration worktree on the integration branch, made with plain git."""
        path = os.path.join(self.home, name)
        helpers.git(self.repo, "worktree", "add", "-q", path, BRANCH)
        return os.path.realpath(path)

    def slice_worktree(self, loop, slice, base):
        """A slice worktree made with plain git and recorded through loop_update."""
        path = os.path.join(self.home, "controltower-%s-%s" % (loop, slice))
        branch = "gauntlet/%s/%s" % (loop, slice)
        helpers.git(base, "worktree", "add", "-q", "-b", branch, path, BRANCH)
        path = os.path.realpath(path)
        self.server.loop_update(loop=loop, slice=slice, worktree=path, branch=branch, status="building")
        return path, branch

    def start(self, loop, repo, change=None):
        return self.server.loop_start(loop=loop, repo=repo, change=change or loop)

    def write_state_file(self, name, content):
        os.makedirs(self.state, exist_ok=True)
        path = os.path.join(self.state, name)
        with open(path, "w") as f:
            f.write(content if isinstance(content, str) else json.dumps(content))
        return path

    def entry(self, loop):
        entries = [e for e in self.server.status()["loops"] if e["loop"] == loop]
        self.assertEqual(len(entries), 1, entries)
        return entries[0]


class FinishedLoopTest(StatusTestCase):
    def test_done_loop_whose_integration_worktree_remains_is_finished_with_one_worktree_left(self):
        integration = self.integration_worktree()
        self.start("a", integration, change="decision-tree")
        self.server.loop_update(loop="a", phase="merge")
        self.server.loop_end(loop="a", status="done")
        self.assertEqual(
            self.server.status(),
            {
                "loops": [
                    {
                        "loop": "a",
                        "repo": integration,
                        "change": "decision-tree",
                        "phase": "merge",
                        "status": "done",
                        "finished": True,
                        "leftover": True,
                        "worktrees": [{"name": "integration", "path": integration, "branch": BRANCH}],
                        "lock": None,
                    }
                ]
            },
        )

    def test_stopped_and_failed_loops_are_finished_too(self):
        for loop, end in (("s", "stopped"), ("f", "failed")):
            self.start(loop, self.repo)
            self.server.loop_end(loop=loop, status=end)
            self.assertTrue(self.entry(loop)["finished"])

    def test_done_loop_with_nothing_left_on_disk_is_not_a_leftover(self):
        self.start("a", self.repo)
        path, _ = self.slice_worktree("a", "s1", self.repo)
        helpers.git(self.repo, "worktree", "remove", path)
        self.server.loop_end(loop="a", status="done")
        entry = self.entry("a")
        self.assertEqual((entry["finished"], entry["leftover"], entry["worktrees"]), (True, False, []))

    def test_main_checkout_as_integration_worktree_is_never_listed(self):
        self.start("a", self.repo)
        self.assertEqual(self.entry("a")["worktrees"], [])
        self.server.loop_end(loop="a", status="done")
        self.assertEqual((self.entry("a")["worktrees"], self.entry("a")["leftover"]), ([], False))

    def test_done_loop_with_a_slice_worktree_left_is_a_leftover(self):
        self.start("a", self.repo)
        path, branch = self.slice_worktree("a", "s1", self.repo)
        self.server.loop_end(loop="a", status="done")
        entry = self.entry("a")
        self.assertTrue(entry["leftover"])
        self.assertEqual(entry["worktrees"], [{"name": "s1", "path": path, "branch": branch}])


class IntegrationWorktreeRuleTest(StatusTestCase):
    """Q1: a finished loop's integration worktree counts only if linked, clean, merged and not in use."""

    def test_dirty_integration_worktree_of_a_finished_loop_is_not_counted(self):
        integration = self.integration_worktree()
        self.start("a", integration)
        self.server.loop_end(loop="a", status="done")
        with open(os.path.join(integration, "scratch.txt"), "w") as f:
            f.write("uncommitted\n")
        entry = self.entry("a")
        self.assertEqual((entry["worktrees"], entry["leftover"]), ([], False))

    def test_integration_worktree_with_commits_missing_from_the_integration_branch_is_not_counted(self):
        integration = self.integration_worktree()
        self.start("a", integration)
        self.server.loop_end(loop="a", status="done")
        helpers.git(integration, "checkout", "-q", "--detach")
        helpers.git(integration, "commit", "-q", "--allow-empty", "-m", "not on the integration branch")
        entry = self.entry("a")
        self.assertEqual((entry["worktrees"], entry["leftover"]), ([], False))

    def test_integration_worktree_used_by_another_running_loop_is_not_counted(self):
        integration = self.integration_worktree()
        self.start("a", integration, change="one")
        self.server.loop_end(loop="a", status="done")
        self.start("b", integration, change="two")
        done, running = self.entry("a"), self.entry("b")
        self.assertEqual((done["worktrees"], done["leftover"]), ([], False))
        self.assertEqual(running["worktrees"], [{"name": "integration", "path": integration, "branch": BRANCH}])


class RunningLoopTest(StatusTestCase):
    def test_running_loop_lists_its_existing_worktrees_and_is_not_a_leftover(self):
        integration = self.integration_worktree()
        self.start("a", integration, change="decision-tree")
        self.server.loop_update(loop="a", phase="build")
        s1, b1 = self.slice_worktree("a", "s1", integration)
        s2, _ = self.slice_worktree("a", "s2", integration)
        helpers.git(integration, "worktree", "remove", s2)
        with open(os.path.join(integration, "scratch.txt"), "w") as f:
            f.write("mid-merge\n")
        entry = self.entry("a")
        self.assertEqual(
            (entry["repo"], entry["change"], entry["phase"], entry["status"]),
            (integration, "decision-tree", "build", "running"),
        )
        self.assertEqual((entry["finished"], entry["leftover"]), (False, False))
        self.assertEqual(
            entry["worktrees"],
            [
                {"name": "integration", "path": integration, "branch": BRANCH},
                {"name": "s1", "path": s1, "branch": b1},
            ],
        )


class LockShownTest(StatusTestCase):
    def test_status_shows_the_lock_a_loop_holds(self):
        self.start("a", self.repo, change="one")
        self.start("b", self.repo, change="two")
        held = self.server.lock_acquire(loop="a")
        self.assertEqual(
            self.entry("a")["lock"],
            {
                "lock": held["lock"],
                "loop": "a",
                "repo": self.repo,
                "branch": BRANCH,
                "acquired": held["acquired"],
                "stale": False,
            },
        )
        self.assertIsNone(self.entry("b")["lock"])

    def test_a_stale_lock_is_shown_as_stale(self):
        self.start("a", self.repo)
        old = (datetime.datetime.now().astimezone() - datetime.timedelta(minutes=45)).isoformat(timespec="seconds")
        self.write_state_file(
            "controltower--feat%2Fdecision-tree.lock",
            {"loop": "a", "repo": self.repo, "branch": BRANCH, "acquired": old},
        )
        lock = self.entry("a")["lock"]
        self.assertEqual((lock["acquired"], lock["stale"]), (old, True))


class StateFolderTest(StatusTestCase):
    def test_legacy_loop_files_are_listed(self):
        self.write_state_file(
            "pri-fixes.json",
            {
                "loop": "pri-fixes",
                "project": "controltower",
                "repo": "/no/such/controltower-decision-tree",
                "change": "pri",
                "integration_branch": BRANCH,
                "phase": "build",
                "status": "running",
                "events": [{"at": "2026-11-03T09:00:00-08:00", "what": "slices planned"}],
                "slices": {"tracer": {"status": "merged", "worktree": "/no/such/wt"}, "odd": "not-an-object"},
            },
        )
        self.write_state_file("pri-contract.json", {"loop_id": "pri-contract", "status": "done", "slices": []})
        self.write_state_file("bare.json", {"status": "done"})
        entries = {e["loop"]: e for e in self.server.status()["loops"]}
        self.assertEqual(sorted(entries), ["bare", "pri-contract", "pri-fixes"])
        self.assertEqual(
            entries["pri-fixes"],
            {
                "loop": "pri-fixes",
                "repo": "/no/such/controltower-decision-tree",
                "change": "pri",
                "phase": "build",
                "status": "running",
                "finished": False,
                "leftover": False,
                "worktrees": [],
                "lock": None,
            },
        )
        self.assertEqual(
            entries["bare"],
            {
                "loop": "bare",
                "repo": None,
                "change": None,
                "phase": None,
                "status": "done",
                "finished": True,
                "leftover": False,
                "worktrees": [],
                "lock": None,
            },
        )

    def test_non_loop_files_do_not_break_status(self):
        self.start("a", self.repo)
        self.write_state_file("pri-fixes.bar.beta.md", "# bar\n")
        self.write_state_file("pri-fixes.brief.alpha.md", "# brief\n")
        self.write_state_file("pri-fixes.plan-full.md", "# plan\n")
        self.write_state_file("garbage.json", "{not json")
        self.write_state_file("list.json", "[1, 2]")
        self.write_state_file("empty.lock", "")
        self.write_state_file("list--main.lock", "[]")
        os.makedirs(os.path.join(self.state, "cutover-20261103T090000"))
        os.makedirs(os.path.join(self.state, "folder.lock"))
        self.assertEqual([e["loop"] for e in self.server.status()["loops"]], ["a"])

    def test_no_state_folder_means_no_loops_and_nothing_is_created(self):
        self.assertEqual(self.server.status(), {"loops": []})
        self.assertFalse(os.path.exists(self.state))

    def test_status_never_writes(self):
        integration = self.integration_worktree()
        self.start("a", integration, change="one")
        self.slice_worktree("a", "s1", integration)
        self.server.lock_acquire(loop="a")
        self.server.loop_end(loop="a", status="done")
        self.start("b", self.repo, change="two")
        tracked = os.path.join(integration, ".gauntlet.json")
        later = time.time() + 5
        os.utime(tracked, (later, later))  # a stat change git status would otherwise refresh the index for
        self.write_state_file("notes.plan-full.md", "# plan\n")
        before = snapshot(self.state, self.repo, integration)
        self.server.status()
        self.assertEqual(snapshot(self.state, self.repo, integration), before)


class InterfaceTest(StatusTestCase):
    def test_terminal_status_prints_the_same_information_as_the_status_tool(self):
        integration = self.integration_worktree()
        self.start("a", integration, change="one")
        self.slice_worktree("a", "s1", integration)
        self.server.lock_acquire(loop="a")
        self.start("b", self.repo, change="two")
        self.server.loop_end(loop="b", status="done")
        self.write_state_file("old.json", {"loop": "old", "status": "done", "repo": "/gone"})
        self.write_state_file("old.brief.alpha.md", "# brief\n")
        with helpers.McpClient(self.home) as client:
            client.request("initialize", {"protocolVersion": "2025-06-18"})
            is_error, tool_result = client.call("status", {})
        self.assertFalse(is_error)
        proc = helpers.run_cli("status", home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        self.assertEqual(json.loads(proc.stdout), tool_result)
        self.assertEqual(proc.stdout, json.dumps(tool_result, indent=2) + "\n")
        self.assertEqual([e["loop"] for e in tool_result["loops"]], ["a", "b", "old"])
        self.assertEqual(tool_result, self.server.status())


if __name__ == "__main__":
    unittest.main()
