"""gauntlet-tools: loop registration, updates, ends, and the state-folder helpers."""

import datetime
import json
import os
import unittest

import helpers

CONFIG = {"integration_branch": "main", "shared": ["node_modules"]}


def legacy_loop(loop, repo, change, status="running"):
    """A hand-written state file in the shape the live loops use: `loop` key, no schema, extra keys."""
    return {
        "loop": loop,
        "project": os.path.basename(repo),
        "repo": repo,
        "change": change,
        "integration_branch": "feat/decision-tree",
        "integration_worktree": repo,
        "phase": "build",
        "status": status,
        "baseline": "0d22149",
        "plan": "openspec/changes/%s/slices.%s.md" % (change, loop),
        "events": [{"at": "2026-11-03T09:00:00-08:00", "what": "slices planned"}],
        "slices": {"tracer": {"status": "merged", "round": 1, "verdict": "PASS"}},
    }


class StateTestCase(unittest.TestCase):
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)
        self.server = helpers.load_server()
        self.repo = helpers.make_repo(self.home, "proj", config=CONFIG)

    def state_path(self, loop):
        return os.path.join(self.home, ".local", "state", "gauntlet", loop + ".json")

    def write_state_file(self, name, content):
        os.makedirs(os.path.dirname(self.state_path("x")), exist_ok=True)
        path = os.path.join(os.path.dirname(self.state_path("x")), name)
        with open(path, "w") as f:
            f.write(content if isinstance(content, str) else json.dumps(content))
        return path

    def read_state(self, loop):
        with open(self.state_path(loop)) as f:
            return json.load(f)

    def error_of(self, func, **kwargs):
        with self.assertRaises(self.server.GauntletError) as ctx:
            func(**kwargs)
        return ctx.exception.to_dict()

    def start(self, loop="pri", change="fix-pri", repo=None, **kwargs):
        return self.server.loop_start(loop=loop, repo=repo or self.repo, change=change, **kwargs)


def is_iso_with_offset(text):
    parsed = datetime.datetime.fromisoformat(text)
    return parsed.utcoffset() is not None


class LoopStartTest(StateTestCase):
    def test_records_the_loop_in_the_state_folder(self):
        state = self.start()
        self.assertEqual(state, self.read_state("pri"))
        self.assertEqual(state["schema"], 1)
        self.assertEqual(state["loop"], "pri")
        self.assertEqual(state["repo"], self.repo)
        self.assertEqual(state["integration_worktree"], self.repo)
        self.assertEqual(state["change"], "fix-pri")
        self.assertEqual(state["integration_branch"], "main")
        self.assertEqual(state["status"], "running")
        self.assertEqual(state["slices"], {})
        self.assertIsNone(state["ended"])
        self.assertTrue(is_iso_with_offset(state["started"]))
        self.assertTrue(is_iso_with_offset(state["updated"]))
        self.assertIn("phase", state)

    def test_repo_is_recorded_as_the_worktree_top_level(self):
        sub = os.path.join(self.repo, "src")
        os.makedirs(sub)
        self.assertEqual(self.start(repo=sub)["repo"], self.repo)

    def test_integration_branch_argument_overrides_config(self):
        self.assertEqual(self.start(integration_branch="feat/x")["integration_branch"], "feat/x")

    def test_duplicate_id_is_refused_naming_the_running_loop(self):
        # Scenario: Duplicate id
        self.start(loop="pri", change="one")
        other = helpers.make_repo(self.home, "other", config=CONFIG)
        err = self.error_of(self.server.loop_start, loop="pri", repo=other, change="two")
        self.assertEqual(err["error"], "duplicate_loop")
        self.assertEqual(err["running"], "pri")
        self.assertIn("pri", err["message"])
        self.assertEqual(self.read_state("pri")["change"], "one")

    def test_duplicate_id_counts_legacy_running_files(self):
        self.write_state_file("pri-fixes.json", legacy_loop("pri-fixes", "/elsewhere/controltower", "pri"))
        err = self.error_of(self.server.loop_start, loop="pri-fixes", repo=self.repo, change="new")
        self.assertEqual(err["error"], "duplicate_loop")
        self.assertEqual(err["running"], "pri-fixes")

    def test_same_change_in_same_repo_is_refused(self):
        self.start(loop="first", change="fix-pri")
        err = self.error_of(self.server.loop_start, loop="second", repo=self.repo, change="fix-pri")
        self.assertEqual(err["error"], "duplicate_loop")
        self.assertEqual(err["running"], "first")
        self.assertFalse(os.path.exists(self.state_path("second")))

    def test_same_change_through_a_linked_worktree_is_the_same_repo(self):
        self.start(loop="first", change="fix-pri")
        linked = os.path.join(self.home, "proj-integration")
        helpers.git(self.repo, "worktree", "add", "-q", "-b", "integration", linked)
        err = self.error_of(self.server.loop_start, loop="second", repo=linked, change="fix-pri")
        self.assertEqual(err["running"], "first")

    def test_same_change_counts_legacy_running_files(self):
        self.write_state_file("old.json", legacy_loop("old", self.repo, "fix-pri"))
        err = self.error_of(self.server.loop_start, loop="new", repo=self.repo, change="fix-pri")
        self.assertEqual(err["error"], "duplicate_loop")
        self.assertEqual(err["running"], "old")

    def test_legacy_file_pointing_at_a_vanished_repo_does_not_break_start(self):
        self.write_state_file("old.json", legacy_loop("old", "/no/such/repo", "fix-pri"))
        self.assertEqual(self.start(loop="new", change="fix-pri")["status"], "running")

    def test_same_change_elsewhere_or_other_change_here_is_allowed(self):
        self.start(loop="first", change="fix-pri")
        other = helpers.make_repo(self.home, "other", config=CONFIG)
        self.assertEqual(self.start(loop="second", change="fix-pri", repo=other)["status"], "running")
        self.assertEqual(self.start(loop="third", change="other-change")["status"], "running")

    def test_finished_loops_do_not_block(self):
        self.write_state_file("done.json", legacy_loop("done", self.repo, "fix-pri", status="done"))
        self.assertEqual(self.start(loop="next", change="fix-pri")["status"], "running")

    def test_reusing_a_finished_loop_id_replaces_its_state(self):
        self.start(loop="pri", change="one")
        self.server.loop_update(loop="pri", slice="a", status="merged")
        self.server.loop_end(loop="pri", status="done")
        state = self.start(loop="pri", change="two")
        self.assertEqual(state["change"], "two")
        self.assertEqual(state["status"], "running")
        self.assertEqual(state["slices"], {})
        self.assertEqual(self.read_state("pri"), state)

    def test_loop_ids_must_be_kebab_case_up_to_24_chars(self):
        for bad in ("Pri", "pri_fixes", "-pri", "pri-", "a--b", "pri fixes", "", "x" * 25, "../etc", "pri\n", "a\n"):
            err = self.error_of(self.server.loop_start, loop=bad, repo=self.repo, change="c")
            self.assertEqual(err["error"], "invalid_id", bad)
        self.assertEqual(self.start(loop="a" * 24)["loop"], "a" * 24)
        self.assertEqual(self.start(loop="pri-2-fixes", change="other")["loop"], "pri-2-fixes")

    def test_trailing_newline_cannot_bypass_the_duplicate_id_check(self):
        self.start(loop="pri", change="one")
        other = helpers.make_repo(self.home, "other", config=CONFIG)
        err = self.error_of(self.server.loop_start, loop="pri\n", repo=other, change="two")
        self.assertEqual(err["error"], "invalid_id")
        self.assertEqual(os.listdir(self.server.state_dir()), ["pri.json"])

    def test_missing_config_reports_config_missing_and_writes_nothing(self):
        bare = helpers.make_repo(self.home, "bare")
        err = self.error_of(self.server.loop_start, loop="pri", repo=bare, change="c")
        self.assertEqual(err["error"], "config_missing")
        self.assertEqual(err["ask"], ["integration_branch", "shared", "checks", "setup"])
        self.assertEqual(err["path"], os.path.join(bare, ".gauntlet.json"))
        self.assertEqual(self.server.list_loops(), [])

    def test_invalid_config_is_reported_by_field(self):
        bad = helpers.make_repo(self.home, "bad", config={"integration_branch": "main", "shared": "node_modules"})
        err = self.error_of(self.server.loop_start, loop="pri", repo=bad, change="c")
        self.assertEqual(err["error"], "config_invalid")
        self.assertEqual(list(err["fields"]), ["shared"])

    def test_non_git_folder_is_git_failed(self):
        plain = os.path.join(self.home, "plain")
        os.makedirs(plain)
        err = self.error_of(self.server.loop_start, loop="pri", repo=plain, change="c")
        self.assertEqual(err["error"], "git_failed")


class LoopUpdateTest(StateTestCase):
    def test_records_phase_and_slice_fields(self):
        self.start()
        state = self.server.loop_update(
            loop="pri",
            phase="build",
            slice="tracer",
            worktree="/tmp/w",
            branch="gauntlet/pri/tracer",
            status="building",
            round=1,
            commit="abc123",
            verdict="HOLD",
        )
        self.assertEqual(state["phase"], "build")
        self.assertEqual(
            state["slices"]["tracer"],
            {
                "worktree": "/tmp/w",
                "branch": "gauntlet/pri/tracer",
                "status": "building",
                "round": 1,
                "commit": "abc123",
                "verdict": "HOLD",
            },
        )
        self.assertEqual(self.read_state("pri"), state)

    def test_later_updates_keep_earlier_slice_fields(self):
        self.start()
        self.server.loop_update(loop="pri", slice="tracer", branch="gauntlet/pri/tracer", round=1)
        state = self.server.loop_update(loop="pri", slice="tracer", round=2, verdict="PASS")
        self.assertEqual(state["slices"]["tracer"], {"branch": "gauntlet/pri/tracer", "round": 2, "verdict": "PASS"})
        self.assertEqual(state["phase"], self.read_state("pri")["phase"])

    def test_updates_preserve_unknown_keys_of_legacy_files(self):
        legacy = legacy_loop("old", self.repo, "fix-pri")
        self.write_state_file("old.json", legacy)
        state = self.server.loop_update(loop="old", phase="merge", slice="next", status="building")
        saved = self.read_state("old")
        self.assertEqual(saved, state)
        for key in ("project", "events", "plan", "baseline", "integration_worktree"):
            self.assertEqual(saved[key], legacy[key], key)
        self.assertEqual(saved["slices"]["tracer"], legacy["slices"]["tracer"])
        self.assertEqual(saved["slices"]["next"], {"status": "building"})
        self.assertEqual(saved["phase"], "merge")

    def test_update_stamps_updated(self):
        legacy = legacy_loop("old", self.repo, "fix-pri")
        self.write_state_file("old.json", legacy)
        self.assertTrue(is_iso_with_offset(self.server.loop_update(loop="old", phase="merge")["updated"]))

    def test_unknown_loop(self):
        self.assertEqual(self.error_of(self.server.loop_update, loop="nope", phase="x")["error"], "unknown_loop")

    def test_slice_fields_need_a_valid_slice_name(self):
        self.start()
        self.assertEqual(self.error_of(self.server.loop_update, loop="pri", status="merged")["error"], "invalid_id")
        for bad in ("Bad Slice", "tracer\n", "a\n"):
            err = self.error_of(self.server.loop_update, loop="pri", slice=bad, status="merged")
            self.assertEqual(err["error"], "invalid_id", repr(bad))
        self.assertEqual(self.read_state("pri")["slices"], {})


class LoopEndTest(StateTestCase):
    def test_bad_status_is_a_gauntlet_error_and_changes_nothing(self):
        self.start()
        before = self.read_state("pri")
        err = self.error_of(self.server.loop_end, loop="pri", status="finished")
        self.assertEqual(err["error"], "invalid_id")
        self.assertIn("finished", err["message"])
        self.assertEqual(self.read_state("pri"), before)

    def test_records_final_status_and_end_time(self):
        self.start()
        for status in ("done", "stopped", "failed"):
            state = self.server.loop_end(loop="pri", status=status)
            self.assertEqual(state["status"], status)
            self.assertTrue(is_iso_with_offset(state["ended"]))
            self.assertEqual(self.read_state("pri"), state)

    def test_ended_loop_is_no_longer_running(self):
        self.start()
        self.server.loop_end(loop="pri", status="stopped")
        self.assertEqual(self.server.running_loops(), [])
        self.assertEqual(self.start(loop="again")["status"], "running")

    def test_unknown_loop(self):
        self.assertEqual(self.error_of(self.server.loop_end, loop="nope", status="done")["error"], "unknown_loop")


class StateFolderTest(StateTestCase):
    def test_state_dir_follows_home_on_every_call(self):
        first = self.server.state_dir()
        os.environ["HOME"] = os.path.join(self.home, "elsewhere")
        try:
            self.assertEqual(self.server.state_dir(), os.path.join(self.home, "elsewhere", ".local", "state", "gauntlet"))
        finally:
            os.environ["HOME"] = self.home
        self.assertEqual(first, os.path.join(self.home, ".local", "state", "gauntlet"))

    def test_load_loop_reads_legacy_files_and_rejects_unknown(self):
        self.write_state_file("old.json", legacy_loop("old", self.repo, "fix-pri"))
        self.assertEqual(self.server.load_loop("old")["project"], "proj")
        self.assertEqual(self.error_of(self.server.load_loop, loop="nope")["error"], "unknown_loop")
        self.assertEqual(self.error_of(self.server.load_loop, loop="../x")["error"], "invalid_id")

    def test_save_loop_writes_and_leaves_no_temp_files(self):
        state = self.start()
        state["phase"] = "slice"
        self.server.save_loop(state)
        self.assertEqual(self.read_state("pri")["phase"], "slice")
        self.assertEqual(os.listdir(self.server.state_dir()), ["pri.json"])

    def test_failed_save_keeps_the_previous_file_whole(self):
        self.start()
        before = self.read_state("pri")
        broken = dict(before, phase=object())
        with self.assertRaises(TypeError):
            self.server.save_loop(broken)
        self.assertEqual(self.read_state("pri"), before)
        self.assertEqual(os.listdir(self.server.state_dir()), ["pri.json"])

    def test_list_loops_includes_legacy_and_skips_non_loop_files(self):
        self.start(loop="new", change="one")
        self.write_state_file("old.json", legacy_loop("old", self.repo, "two", status="done"))
        self.write_state_file("pri-fixes.bar.tracer.md", "# bar\n")
        self.write_state_file("pri-fixes.brief.tracer.md", "# brief\n")
        self.write_state_file("pri-fixes.plan-full.md", "# plan\n")
        self.write_state_file("proj--main.lock", {"loop": "new", "repo": self.repo, "branch": "main"})
        self.write_state_file("notes.json", {"something": "else"})
        self.write_state_file("list.json", [1, 2])
        self.write_state_file("broken.json", "{oops")
        os.makedirs(os.path.join(self.server.state_dir(), "cutover-20261103T120000", "x.json"))
        self.assertEqual(sorted(s["loop"] for s in self.server.list_loops()), ["new", "old"])

    def test_list_loops_without_state_folder_is_empty(self):
        self.assertEqual(self.server.list_loops(), [])
        self.assertEqual(self.server.running_loops(), [])

    def test_running_loops_counts_legacy_files(self):
        self.write_state_file("pri-fixes.json", legacy_loop("pri-fixes", "/x/controltower", "pri"))
        self.write_state_file("wiki-ask.json", legacy_loop("wiki-ask", "/x/wiki", "ask", status="done"))
        self.start(loop="mine", change="c")
        self.assertEqual(sorted(s["loop"] for s in self.server.running_loops()), ["mine", "pri-fixes"])


class MainWorktreeTest(StateTestCase):
    def test_from_main_linked_and_subfolder(self):
        linked = os.path.join(self.home, "proj-integration")
        helpers.git(self.repo, "worktree", "add", "-q", "-b", "integration", linked)
        sub = os.path.join(linked, "deep", "er")
        os.makedirs(sub)
        for path in (self.repo, linked, sub):
            self.assertEqual(self.server.main_worktree(path), self.repo, path)

    def test_non_git_folder_is_git_failed(self):
        plain = os.path.join(self.home, "plain")
        os.makedirs(plain)
        self.assertEqual(self.error_of(self.server.main_worktree, path=plain)["error"], "git_failed")


if __name__ == "__main__":
    unittest.main()
