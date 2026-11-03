"""gauntlet-tools: merge locks per repo and integration branch (lock_acquire, lock_release)."""

import datetime
import json
import os
import subprocess
import sys
import time
import unittest

import helpers

CONFIG = {"integration_branch": "feat/decision-tree"}
LOCK_NAME = "controltower--feat%2Fdecision-tree.lock"


def iso_minutes_ago(minutes):
    moment = datetime.datetime.now().astimezone() - datetime.timedelta(minutes=minutes)
    return moment.isoformat(timespec="seconds")


def parse_iso(text):
    return datetime.datetime.fromisoformat(text)


class LockTestCase(unittest.TestCase):
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)
        self.server = helpers.load_server()
        self.repo = helpers.make_repo(self.home, "controltower", config=CONFIG)
        self.state = os.path.join(self.home, ".local", "state", "gauntlet")

    def start(self, loop, repo=None, change=None, **kwargs):
        return self.server.loop_start(loop=loop, repo=repo or self.repo, change=change or loop, **kwargs)

    def lock_path(self, name=LOCK_NAME):
        return os.path.join(self.state, name)

    def read_lock(self, name=LOCK_NAME):
        with open(self.lock_path(name)) as f:
            return json.load(f)

    def write_lock(self, loop, acquired, name=LOCK_NAME, branch="feat/decision-tree"):
        """A literal lock file in the contract format, as another loop would have left it."""
        os.makedirs(self.state, exist_ok=True)
        with open(self.lock_path(name), "w") as f:
            json.dump({"loop": loop, "repo": self.repo, "branch": branch, "acquired": acquired}, f)

    def error_of(self, func, **kwargs):
        with self.assertRaises(self.server.GauntletError) as ctx:
            func(**kwargs)
        return ctx.exception.to_dict()


class AcquireTest(LockTestCase):
    def test_lock_file_is_named_for_repo_and_encoded_branch_and_holds_the_holder(self):
        self.start("a")
        result = self.server.lock_acquire(loop="a")
        self.assertEqual(result["lock"], self.lock_path())
        self.assertEqual(result["loop"], "a")
        self.assertEqual(result["repo"], self.repo)
        self.assertEqual(result["branch"], "feat/decision-tree")
        self.assertIsNotNone(parse_iso(result["acquired"]).utcoffset())
        self.assertEqual(
            self.read_lock(),
            {"loop": "a", "repo": self.repo, "branch": "feat/decision-tree", "acquired": result["acquired"]},
        )

    def test_concurrent_merge_refuses_the_second_loop_naming_the_holder_and_time(self):
        self.start("a")
        self.start("b")
        held = self.server.lock_acquire(loop="a")
        error = self.error_of(self.server.lock_acquire, loop="b")
        self.assertEqual(error["error"], "lock_held")
        self.assertEqual(error["holder"], "a")
        self.assertEqual(error["acquired"], held["acquired"])
        self.assertIn("a", error["message"])
        self.assertEqual(self.read_lock()["loop"], "a")

    def test_lock_name_uses_the_main_worktree_even_from_a_linked_integration_worktree(self):
        integration = os.path.join(self.home, "controltower-decision-tree")
        helpers.git(self.repo, "worktree", "add", "-q", "-b", "feat/decision-tree", integration)
        self.start("a", repo=integration)
        result = self.server.lock_acquire(loop="a")
        self.assertEqual(result["lock"], self.lock_path())
        self.assertEqual(result["repo"], self.repo)

    def test_loops_sharing_an_integration_worktree_share_its_lock(self):
        integration = os.path.join(self.home, "controltower-decision-tree")
        helpers.git(self.repo, "worktree", "add", "-q", "-b", "feat/decision-tree", integration)
        self.start("a", repo=integration, change="one")
        self.start("b", repo=self.repo, change="two")
        self.server.lock_acquire(loop="a")
        self.assertEqual(self.error_of(self.server.lock_acquire, loop="b")["holder"], "a")

    def test_other_branches_and_other_repos_have_their_own_locks(self):
        other_repo = helpers.make_repo(self.home, "wiki", config={"integration_branch": "main"})
        self.start("a")
        self.start("b", integration_branch="main")
        self.start("c", repo=other_repo)
        self.assertEqual(self.server.lock_acquire(loop="a")["lock"], self.lock_path())
        self.assertEqual(self.server.lock_acquire(loop="b")["lock"], self.lock_path("controltower--main.lock"))
        self.assertEqual(self.server.lock_acquire(loop="c")["lock"], self.lock_path("wiki--main.lock"))

    def test_stale_lock_is_taken_over(self):
        self.start("b")
        self.write_lock("a", iso_minutes_ago(31))
        result = self.server.lock_acquire(loop="b")
        self.assertEqual(result["loop"], "b")
        self.assertEqual(self.read_lock()["loop"], "b")
        self.assertEqual(self.read_lock()["acquired"], result["acquired"])

    def test_lock_younger_than_thirty_minutes_is_respected(self):
        self.start("b")
        taken = iso_minutes_ago(29)
        self.write_lock("a", taken)
        error = self.error_of(self.server.lock_acquire, loop="b")
        self.assertEqual((error["error"], error["holder"], error["acquired"]), ("lock_held", "a", taken))
        self.assertEqual(self.read_lock()["loop"], "a")

    def test_holder_reacquiring_succeeds_and_refreshes_the_time(self):
        self.start("a")
        self.write_lock("a", iso_minutes_ago(10))
        result = self.server.lock_acquire(loop="a")
        self.assertEqual(result["loop"], "a")
        refreshed = parse_iso(self.read_lock()["acquired"])
        self.assertLess(abs((datetime.datetime.now().astimezone() - refreshed).total_seconds()), 60)
        self.assertEqual(self.read_lock()["acquired"], result["acquired"])

    def test_unreadable_lock_file_counts_as_held_until_stale(self):
        self.start("b")
        os.makedirs(self.state, exist_ok=True)
        with open(self.lock_path(), "w") as f:
            f.write("")
        error = self.error_of(self.server.lock_acquire, loop="b")
        self.assertEqual(error["error"], "lock_held")
        self.assertIsNone(error["holder"])
        old = time.time() - 31 * 60
        os.utime(self.lock_path(), (old, old))
        self.assertEqual(self.server.lock_acquire(loop="b")["loop"], "b")

    def test_unknown_loop_is_refused_without_creating_a_lock(self):
        error = self.error_of(self.server.lock_acquire, loop="ghost")
        self.assertEqual(error["error"], "unknown_loop")
        self.assertFalse(os.path.exists(self.state) and [n for n in os.listdir(self.state) if n.endswith(".lock")])

    def test_invalid_id_is_refused(self):
        self.assertEqual(self.error_of(self.server.lock_acquire, loop="../x")["error"], "invalid_id")

    def test_simultaneous_acquires_from_separate_processes_yield_exactly_one_holder(self):
        loops = ["p%d" % i for i in range(8)]
        for loop in loops:
            self.start(loop)
        self.assertEqual(self.race(loops), 1)

    def test_simultaneous_takeovers_of_a_stale_lock_yield_exactly_one_holder(self):
        loops = ["p%d" % i for i in range(8)]
        for loop in loops:
            self.start(loop)
        self.write_lock("gone", iso_minutes_ago(45))
        self.assertEqual(self.race(loops), 1)
        self.assertIn(self.read_lock()["loop"], loops)

    def race(self, loops):
        """Start one `gauntlet lock acquire` process per loop at once; return how many succeeded."""
        env = dict(os.environ)
        procs = [
            subprocess.Popen(
                [sys.executable, helpers.SERVER, "lock", "acquire", loop],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for loop in loops
        ]
        codes = []
        for proc in procs:
            proc.communicate(timeout=helpers.TIMEOUT)
            codes.append(proc.returncode)
        self.assertTrue(set(codes) <= {0, 1}, codes)
        return codes.count(0)


class ReleaseTest(LockTestCase):
    def test_holder_releases_and_the_next_loop_can_acquire(self):
        self.start("a")
        self.start("b")
        self.server.lock_acquire(loop="a")
        self.assertEqual(self.server.lock_release(loop="a"), {"released": True, "lock": self.lock_path()})
        self.assertFalse(os.path.exists(self.lock_path()))
        self.assertEqual(self.server.lock_acquire(loop="b")["loop"], "b")

    def test_only_the_holder_can_release(self):
        self.start("a")
        self.start("b")
        held = self.server.lock_acquire(loop="a")
        error = self.error_of(self.server.lock_release, loop="b")
        self.assertEqual(error["error"], "not_holder")
        self.assertEqual(error["holder"], "a")
        self.assertEqual(self.read_lock()["acquired"], held["acquired"])

    def test_a_stale_lock_still_belongs_to_its_holder(self):
        self.start("b")
        self.write_lock("a", iso_minutes_ago(90))
        self.assertEqual(self.error_of(self.server.lock_release, loop="b")["error"], "not_holder")
        self.assertTrue(os.path.exists(self.lock_path()))

    def test_releasing_with_no_lock_is_refused(self):
        self.start("a")
        error = self.error_of(self.server.lock_release, loop="a")
        self.assertEqual(error["error"], "not_holder")
        self.assertIsNone(error["holder"])

    def test_unknown_loop_is_refused(self):
        self.assertEqual(self.error_of(self.server.lock_release, loop="ghost")["error"], "unknown_loop")


class InterfaceTest(LockTestCase):
    def test_stdio_acquire_refusal_and_release(self):
        self.start("a")
        self.start("b")
        with helpers.McpClient(self.home) as client:
            client.request("initialize", {"protocolVersion": "2025-06-18"})
            is_error, held = client.call("lock_acquire", {"loop": "a"})
            self.assertFalse(is_error)
            self.assertEqual(held, dict(self.read_lock(), lock=self.lock_path()))
            is_error, refused = client.call("lock_acquire", {"loop": "b"})
            self.assertTrue(is_error)
            self.assertEqual((refused["error"], refused["holder"]), ("lock_held", "a"))
            self.assertEqual(refused["acquired"], held["acquired"])
            is_error, refused = client.call("lock_release", {"loop": "b"})
            self.assertEqual((is_error, refused["error"]), (True, "not_holder"))
            is_error, released = client.call("lock_release", {"loop": "a"})
            self.assertEqual((is_error, released), (False, {"released": True, "lock": self.lock_path()}))

    def test_terminal_acquire_and_release(self):
        self.start("a")
        self.start("b")
        proc = helpers.run_cli("lock", "acquire", "a", home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["loop"], "a")
        proc = helpers.run_cli("lock", "acquire", "b", home=self.home)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(json.loads(proc.stderr)["holder"], "a")
        proc = helpers.run_cli("lock", "release", "a", home=self.home)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), {"released": True, "lock": self.lock_path()})


if __name__ == "__main__":
    unittest.main()
