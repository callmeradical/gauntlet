"""setup-cutover: scripts/cutover.py refuses while a loop runs, has a dry run, cuts over, and rolls back.

Every test runs against a fake home laid out like the live one (real agent files in ~/.claude/agents,
~/.claude/skills links into ~/.augy/skills, ~/.agents a symlink into a dotfiles folder) and a fake
plugin tree, and compares full snapshots of the fake home.
"""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

import helpers

SCRIPT = os.path.join(helpers.REPO_ROOT, "scripts", "cutover.py")
AGENTS = ("alpha", "beta", "gamma", "delta", "epsilon")
SKILLS = ("intake", "gauntlet-loop")


def load_cutover():
    spec = importlib.util.spec_from_file_location("cutover_script", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path, text, mode=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    if mode is not None:
        os.chmod(path, mode)


def snapshot(root, exclude=()):
    """Every entry under root, links not followed: {relpath: (type, mode, link target or content)}."""
    result = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in dirnames + filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            if any(rel == ex or rel.startswith(ex + os.sep) for ex in exclude):
                continue
            st = os.lstat(path)
            mode = stat.S_IMODE(st.st_mode)
            if stat.S_ISLNK(st.st_mode):
                result[rel] = ("link", None, os.readlink(path))
            elif stat.S_ISDIR(st.st_mode):
                result[rel] = ("dir", mode, None)
            else:
                with open(path, "rb") as f:
                    result[rel] = ("file", mode, f.read())
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
    return result


def build_live_layout(home):
    """A fake home shaped like the live machine, plus a few entries the cutover must leave alone."""
    dotfiles = os.path.join(home, "Documents", "dotfiles", ".agents")
    for name in AGENTS:
        write(os.path.join(home, ".claude", "agents", name + ".md"), "claude copy of %s\n" % name)
        write(os.path.join(dotfiles, "agents", name + ".md"), "dotfiles copy of %s\n" % name)
    write(os.path.join(home, ".claude", "agents", "impeccable-documenter.md"), "unrelated agent\n")
    write(os.path.join(dotfiles, "agents", "other.md"), "unrelated dotfiles agent\n")
    os.symlink(dotfiles, os.path.join(home, ".agents"))
    for name in SKILLS + ("tdd",):
        write(os.path.join(home, ".augy", "skills", name, "SKILL.md"), "augy skill %s\n" % name)
    write(os.path.join(home, ".augy", "skills", "intake", "references", "notes.md"), "nested\n", mode=0o600)
    os.chmod(os.path.join(home, ".augy", "skills", "gauntlet-loop"), 0o700)
    write(os.path.join(home, ".opencode", "skills", "codebase-design", "SKILL.md"), "opencode skill\n")
    os.makedirs(os.path.join(home, ".claude", "skills"))
    for name in SKILLS + ("tdd",):
        os.symlink(os.path.join(home, ".augy", "skills", name), os.path.join(home, ".claude", "skills", name))
    os.symlink(
        os.path.join(home, ".opencode", "skills", "codebase-design"),
        os.path.join(home, ".claude", "skills", "codebase-design"),
    )
    # A removed agent that is itself a link, and a replaced agent that is a link: targets must survive.
    os.unlink(os.path.join(home, ".claude", "agents", "gamma.md"))
    write(os.path.join(home, "notes", "gamma.md"), "gamma kept elsewhere\n")
    os.symlink(os.path.join(home, "notes", "gamma.md"), os.path.join(home, ".claude", "agents", "gamma.md"))
    os.unlink(os.path.join(dotfiles, "agents", "delta.md"))
    write(os.path.join(home, "notes", "delta.md"), "delta kept elsewhere\n")
    os.symlink(os.path.join(home, "notes", "delta.md"), os.path.join(dotfiles, "agents", "delta.md"))
    os.chmod(os.path.join(dotfiles, "agents", "beta.md"), 0o600)
    os.makedirs(os.path.join(home, ".local", "state", "gauntlet"))  # exists on the live machine


def build_plugin_tree(repo, skip=()):
    """A fake checkout holding the plugin's skills and agents (they don't exist on this branch)."""
    plugin = os.path.join(repo, "plugins", "gauntlet")
    for name in SKILLS:
        if name not in skip:
            write(os.path.join(plugin, "skills", name, "SKILL.md"), "plugin skill %s\n" % name)
    for name in AGENTS:
        if name not in skip:
            write(os.path.join(plugin, "agents", name + ".md"), "plugin agent %s\n" % name)
    return plugin


def legacy_running(loop):
    """The live hand-written shape: `loop` key, no schema, extra keys."""
    return {
        "loop": loop,
        "project": "controltower",
        "repo": "/nonexistent/controltower-decision-tree",
        "change": "fix-pri",
        "integration_branch": "feat/decision-tree",
        "integration_worktree": "/nonexistent/controltower-decision-tree",
        "phase": "build",
        "status": "running",
        "baseline": "0d22149",
        "events": [{"at": "2026-11-03T09:00:00-08:00", "what": "slices planned"}],
    }


class CutoverTestCase(unittest.TestCase):
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)
        self.world = os.path.realpath(tempfile.mkdtemp(prefix="gauntlet-world-"))
        self.addCleanup(shutil.rmtree, self.world, True)
        self.repo = os.path.join(self.world, "gauntlet")
        self.plugin = build_plugin_tree(self.repo)
        build_live_layout(self.home)
        self.state = os.path.join(self.home, ".local", "state", "gauntlet")
        self.cutover = load_cutover()
        self.dotfiles_agents = os.path.join(self.home, "Documents", "dotfiles", ".agents", "agents")

    def run_main(self, *argv, repo=None):
        """Run cutover.main() against the fake home; return (exit code, stdout, stderr)."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = self.cutover.main(list(argv), home=self.home, repo_root=repo or self.repo)
        return code, out.getvalue(), err.getvalue()

    def write_state(self, name, content):
        write(os.path.join(self.state, name), content if isinstance(content, str) else json.dumps(content))

    def backups(self):
        return sorted(
            os.path.join(self.state, n) for n in os.listdir(self.state) if n.startswith("cutover-")
        )

    def snap(self, exclude_backups=False):
        exclude = ()
        if exclude_backups:
            exclude = tuple(os.path.relpath(b, self.home) for b in self.backups())
        return snapshot(self.home, exclude)

    def expected_after_cutover(self, before):
        """`before` with the Claude Code copies removed and the other tools' copies linked to the plugin."""
        expected = dict(before)

        def drop(rel):
            for key in [k for k in expected if k == rel or k.startswith(rel + os.sep)]:
                del expected[key]

        for name in AGENTS:
            drop(os.path.join(".claude", "agents", name + ".md"))
            rel = os.path.join("Documents", "dotfiles", ".agents", "agents", name + ".md")
            drop(rel)
            expected[rel] = ("link", None, os.path.join(self.plugin, "agents", name + ".md"))
        for name in SKILLS:
            drop(os.path.join(".claude", "skills", name))
            rel = os.path.join(".augy", "skills", name)
            drop(rel)
            expected[rel] = ("link", None, os.path.join(self.plugin, "skills", name))
        return expected


class RefusalTests(CutoverTestCase):
    def assert_refused(self, *loops, argv=()):
        before = self.snap()
        code, out, err = self.run_main(*argv)
        self.assertEqual(code, 1, out + err)
        for loop in loops:
            self.assertIn(loop, err)
        self.assertEqual(self.snap(), before)
        self.assertEqual(self.backups(), [])
        return err

    def test_loop_running_registered_by_the_server(self):
        project = helpers.make_repo(self.world, "proj", config={"integration_branch": "main"})
        helpers.load_server().loop_start(loop="pri-fixes", repo=project, change="fix-pri")
        self.assert_refused("pri-fixes")

    def test_loop_running_in_legacy_files(self):
        self.write_state("pri-fixes.json", legacy_running("pri-fixes"))
        self.write_state("pri-contract.json", {"loop_id": "pri-contract", "status": "running"})
        self.write_state("hand-made.json", {"status": "running", "phase": "build"})
        self.assert_refused("pri-fixes", "pri-contract", "hand-made")

    def test_dry_run_also_refuses(self):
        self.write_state("pri-fixes.json", legacy_running("pri-fixes"))
        self.assert_refused("pri-fixes", argv=("--dry-run",))

    def test_rollback_refuses_while_a_loop_runs(self):
        code, _, err = self.run_main()
        self.assertEqual(code, 0, err)
        backup = self.backups()[0]
        self.write_state("pri-fixes.json", legacy_running("pri-fixes"))
        before = self.snap()
        code, out, err = self.run_main("--rollback", backup)
        self.assertEqual(code, 1, out + err)
        self.assertIn("pri-fixes", err)
        self.assertEqual(self.snap(), before)

    def test_finished_loops_and_non_loop_files_do_not_block(self):
        done = legacy_running("wiki-ask")
        done["status"] = "done"
        self.write_state("wiki-ask.json", done)
        self.write_state("wiki-ask.bar.tracer.md", "a bar\n")
        self.write_state("pri-fixes.plan-full.md", "a plan\n")
        self.write_state("broken.json", "{not json")
        self.write_state("list.json", "[1, 2]")
        code, _, err = self.run_main()
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.backups()), 1)

    def test_refuses_when_a_link_target_is_missing_in_the_repo(self):
        shutil.rmtree(os.path.join(self.plugin, "skills", "gauntlet-loop"))
        os.unlink(os.path.join(self.plugin, "agents", "epsilon.md"))
        before = self.snap()
        code, out, err = self.run_main()
        self.assertEqual(code, 1, out + err)
        self.assertIn(os.path.join(self.plugin, "skills", "gauntlet-loop"), err)
        self.assertIn(os.path.join(self.plugin, "agents", "epsilon.md"), err)
        self.assertEqual(self.snap(), before)
        self.assertEqual(self.backups(), [])

    def test_terminal_run_names_the_running_loop(self):
        self.write_state("pri-fixes.json", legacy_running("pri-fixes"))
        before = self.snap()
        # Apple's /usr/bin/python3 otherwise caches bytecode under $HOME/Library/Caches.
        env = dict(os.environ, HOME=self.home, PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run(
            [sys.executable, SCRIPT],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=helpers.TIMEOUT,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("pri-fixes", proc.stderr)
        self.assertEqual(self.snap(), before)


class DryRunTests(CutoverTestCase):
    def test_prints_the_plan_and_writes_nothing(self):
        before = self.snap()
        code, out, err = self.run_main("--dry-run")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.snap(), before)
        for name in AGENTS:
            self.assertIn(os.path.join(self.home, ".claude", "agents", name + ".md"), out)
            self.assertIn(os.path.join(self.plugin, "agents", name + ".md"), out)
        for name in SKILLS:
            self.assertIn(os.path.join(self.home, ".claude", "skills", name), out)
            self.assertIn(os.path.join(self.plugin, "skills", name), out)
        self.assertNotIn("codebase-design", out)

    def test_rollback_dry_run_writes_nothing(self):
        self.run_main()
        backup = self.backups()[0]
        before = self.snap()
        code, out, err = self.run_main("--dry-run", "--rollback", backup)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.snap(), before)
        self.assertIn(os.path.join(self.home, ".claude", "agents", "alpha.md"), out)


class CutoverTests(CutoverTestCase):
    def test_changes_exactly_the_targets(self):
        before = self.snap()
        code, out, err = self.run_main()
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.snap(exclude_backups=True), self.expected_after_cutover(before))
        self.assertIn(self.backups()[0], out)

    def test_links_are_absolute_and_resolve_into_the_plugin(self):
        self.run_main()
        link = os.path.join(self.home, ".agents", "agents", "alpha.md")
        self.assertTrue(os.path.isabs(os.readlink(link)))
        with open(link) as f:
            self.assertEqual(f.read(), "plugin agent alpha\n")
        with open(os.path.join(self.home, ".augy", "skills", "intake", "SKILL.md")) as f:
            self.assertEqual(f.read(), "plugin skill intake\n")

    def test_manifest_records_type_link_content_and_mode(self):
        self.run_main()
        backup = self.backups()[0]
        self.assertTrue(os.path.basename(backup).startswith("cutover-"))
        with open(os.path.join(backup, "manifest.json")) as f:
            manifest = json.load(f)
        entries = {e["path"]: e for e in manifest["entries"]}
        self.assertEqual(len(entries), 14)

        alpha = entries[os.path.join(self.home, ".claude", "agents", "alpha.md")]
        self.assertEqual((alpha["type"], alpha["action"], alpha["link"]), ("file", "remove", None))
        self.assertEqual(alpha["mode"], "0644")
        with open(os.path.join(backup, alpha["content"])) as f:
            self.assertEqual(f.read(), "claude copy of alpha\n")

        gamma = entries[os.path.join(self.home, ".claude", "agents", "gamma.md")]
        self.assertEqual((gamma["type"], gamma["link"]), ("symlink", os.path.join(self.home, "notes", "gamma.md")))

        beta = entries[os.path.join(self.home, ".agents", "agents", "beta.md")]
        self.assertEqual((beta["type"], beta["action"], beta["mode"]), ("file", "link", "0600"))
        self.assertEqual(beta["link_to"], os.path.join(self.plugin, "agents", "beta.md"))

        loop_skill = entries[os.path.join(self.home, ".augy", "skills", "gauntlet-loop")]
        self.assertEqual((loop_skill["type"], loop_skill["mode"]), ("dir", "0700"))
        with open(os.path.join(backup, loop_skill["content"], "SKILL.md")) as f:
            self.assertEqual(f.read(), "augy skill gauntlet-loop\n")

        link = entries[os.path.join(self.home, ".claude", "skills", "intake")]
        self.assertEqual((link["type"], link["link"]), ("symlink", os.path.join(self.home, ".augy", "skills", "intake")))

    def test_rerun_is_a_no_op(self):
        self.run_main()
        after_first = self.snap()
        code, out, err = self.run_main()
        self.assertEqual(code, 0, err)
        self.assertEqual(self.snap(), after_first)
        self.assertEqual(len(self.backups()), 1)

    def test_targets_that_do_not_exist_are_skipped(self):
        shutil.rmtree(os.path.join(self.home, ".augy"))
        os.unlink(os.path.join(self.home, ".claude", "agents", "beta.md"))
        os.unlink(os.path.join(self.dotfiles_agents, "epsilon.md"))
        before = self.snap()
        code, _, err = self.run_main()
        self.assertEqual(code, 0, err)
        after = self.snap(exclude_backups=True)
        self.assertFalse(os.path.lexists(os.path.join(self.home, ".augy")))
        self.assertFalse(os.path.lexists(os.path.join(self.dotfiles_agents, "epsilon.md")))
        expected = self.expected_after_cutover(before)
        del expected[os.path.join("Documents", "dotfiles", ".agents", "agents", "epsilon.md")]
        for name in SKILLS:
            del expected[os.path.join(".augy", "skills", name)]
        self.assertEqual(after, expected)

    def test_a_target_that_cannot_be_backed_up_changes_nothing(self):
        unreadable = os.path.join(self.home, ".augy", "skills", "intake", "references", "notes.md")
        os.chmod(unreadable, 0o000)
        self.addCleanup(os.chmod, unreadable, 0o600)
        before = self.snap_without(unreadable)
        code, out, err = self.run_main()
        self.assertEqual(code, 1, out + err)
        self.assertIn("back up", err)
        self.assertEqual(self.snap_without(unreadable), before)
        self.assertEqual(self.backups(), [])

    def snap_without(self, path):
        return snapshot(self.home, exclude=(os.path.relpath(path, self.home),))

    def test_a_failure_part_way_restores_what_was_changed(self):
        before = self.snap()
        os.chmod(self.dotfiles_agents, 0o555)
        self.addCleanup(os.chmod, self.dotfiles_agents, 0o755)
        code, out, err = self.run_main()
        os.chmod(self.dotfiles_agents, 0o755)
        self.assertEqual(code, 1, out + err)
        self.assertEqual(self.snap(exclude_backups=True), before)


class RollbackTests(CutoverTestCase):
    def test_every_file_and_link_is_as_it_was_before(self):
        before = self.snap()
        self.run_main()
        backup = self.backups()[0]
        code, out, err = self.run_main("--rollback", backup)
        self.assertEqual(code, 0, err)
        self.assertEqual(self.snap(exclude_backups=True), before)

    def test_refuses_a_path_changed_since_the_cutover(self):
        self.run_main()
        backup = self.backups()[0]
        changed = os.path.join(self.home, ".claude", "agents", "alpha.md")
        write(changed, "written after the cutover\n")
        before = self.snap()
        code, out, err = self.run_main("--rollback", backup)
        self.assertEqual(code, 1, out + err)
        self.assertIn(changed, err)
        self.assertEqual(self.snap(), before)

    def test_refuses_a_folder_without_a_manifest(self):
        empty = os.path.join(self.world, "not-a-backup")
        os.makedirs(empty)
        before = self.snap()
        code, out, err = self.run_main("--rollback", empty)
        self.assertEqual(code, 1, out + err)
        self.assertIn("manifest", err)
        self.assertEqual(self.snap(), before)


if __name__ == "__main__":
    unittest.main()
