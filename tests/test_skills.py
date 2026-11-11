"""plugin-package: the intake and gauntlet-loop skills, the progress template, and plugin-wide references."""

import os
import re
import shlex
import shutil
import tempfile
import unittest

import helpers

SKILLS = os.path.join(helpers.PLUGIN, "skills")
OWNED = ("intake", "gauntlet-loop", "handoff")
AGENTS = ("delta", "alpha", "beta", "gamma", "epsilon", "zeta", "eta")
TEMPLATE = os.path.join(SKILLS, "gauntlet-loop", "references", "progress.html")
# The server's error codes (shared contract); they share the tools' snake_case shape.
ERROR_CODES = (
    "invalid_id", "duplicate_loop", "unknown_loop", "config_missing", "config_invalid",
    "exists", "lock_held", "not_holder", "git_failed", "not_implemented",
)

# Q9: home-folder locations are forbidden; runtime data paths (~/wiki, ~/.local/state/gauntlet) are allowed.
FORBIDDEN_PATH = re.compile(r"~/\.(agents|claude|augy)\b|\$HOME/\.(agents|claude|augy)\b|/Users/")
PLUGIN_ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+)")
RELATIVE_REF = re.compile(r"(?<![\w./-])(references/[\w.-][\w./-]*)")


def skill_md(name):
    return os.path.join(SKILLS, name, "SKILL.md")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def files_under(root):
    for parent, _, names in os.walk(root):
        for name in names:
            yield os.path.join(parent, name)


def unresolved_references(plugin_root):
    """Return (file, reference) pairs in plugin_root/**/*.md whose target doesn't exist.

    `${CLAUDE_PLUGIN_ROOT}/x` resolves against plugin_root; a bare `references/x` against the file's folder.
    """
    missing = []
    for path in sorted(files_under(plugin_root)):
        if not path.endswith(".md"):
            continue
        text = read(path)
        refs = [(plugin_root, m) for m in PLUGIN_ROOT_REF.findall(text)]
        refs += [(os.path.dirname(path), m) for m in RELATIVE_REF.findall(text)]
        for base, ref in refs:
            ref = ref.rstrip(".")
            if not os.path.exists(os.path.join(base, ref)):
                missing.append((os.path.relpath(path, plugin_root), ref))
    return missing


def list_items(text):
    """Split markdown into top-level list items (numbered or bulleted), continuation lines included."""
    items, current = [], None
    for line in text.split("\n"):
        if re.match(r"^(\d+\.|-) ", line):
            current = [line]
            items.append(current)
        elif current is not None and line.startswith("   ") and line.strip():
            current.append(line)
        else:
            current = None
    return [" ".join(part.strip() for part in item) for item in items]


class SkillFormatTest(unittest.TestCase):
    def test_each_skill_folder_has_agent_skills_frontmatter(self):
        for name in OWNED:
            with self.subTest(skill=name):
                self.assertTrue(os.path.isfile(skill_md(name)))
                meta = helpers.read_frontmatter(skill_md(name))
                self.assertEqual(meta.get("name"), name)
                self.assertRegex(name, r"^[a-z0-9]+(-[a-z0-9]+)*$")
                self.assertLessEqual(len(name), 64)
                description = meta.get("description", "").strip()
                self.assertTrue(description)
                self.assertLessEqual(len(description), 1024)

    def test_skill_bodies_are_not_empty(self):
        for name in OWNED:
            with self.subTest(skill=name):
                body = read(skill_md(name)).split("\n---\n", 1)[1]
                self.assertRegex(body, r"(?m)^# \S")


class LocationsTest(unittest.TestCase):
    def test_no_home_folder_paths_in_either_skill_folder(self):
        for name in OWNED:
            for path in files_under(os.path.join(SKILLS, name)):
                with self.subTest(file=os.path.relpath(path, SKILLS)):
                    self.assertEqual(FORBIDDEN_PATH.findall(read(path)), [])

    def test_skills_refer_to_bundled_files_relative_to_the_skill_folder(self):
        for name in OWNED:
            with self.subTest(skill=name):
                text = read(skill_md(name))
                self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text)
                self.assertNotIn("${PLUGIN_ROOT}", text)
        self.assertIn("references/progress.html", read(skill_md("gauntlet-loop")))

    def test_template_is_bundled_and_self_contained(self):
        self.assertTrue(os.path.isfile(TEMPLATE))
        html = read(TEMPLATE)
        self.assertTrue(html.lstrip().lower().startswith("<!doctype html>"))
        for placeholder in ("{{LOOP_ID}}", "{{PROJECT}}", "{{CHANGE}}", "{{MERGED}}", "{{VERDICT}}"):
            self.assertIn(placeholder, html)
        self.assertNotRegex(html, r"(?i)<script|<link\b|\b(src|href)\s*=\s*[\"']?(https?:)?//")


class PluginReferencesTest(unittest.TestCase):
    def test_every_plugin_root_and_relative_reference_in_the_plugin_exists(self):
        self.assertEqual(unresolved_references(helpers.PLUGIN), [])

    def test_the_reference_scan_checks_the_template_reference(self):
        text = read(skill_md("gauntlet-loop"))
        self.assertIn("references/progress.html", RELATIVE_REF.findall(text))

    def test_the_reference_scan_flags_missing_targets(self):
        root = tempfile.mkdtemp(prefix="gauntlet-refs-")
        self.addCleanup(shutil.rmtree, root)
        os.makedirs(os.path.join(root, "skills", "s", "references"))
        os.makedirs(os.path.join(root, "agents"))
        with open(os.path.join(root, "skills", "s", "references", "here.html"), "w") as f:
            f.write("")
        with open(os.path.join(root, "skills", "s", "SKILL.md"), "w") as f:
            f.write("Use `references/here.html` and `references/gone.md`.\n")
        with open(os.path.join(root, "agents", "a.md"), "w") as f:
            f.write("Read ${CLAUDE_PLUGIN_ROOT}/skills/s/references/here.html, not ${CLAUDE_PLUGIN_ROOT}/nope.txt.\n")
        self.assertEqual(
            unresolved_references(root),
            [("agents/a.md", "nope.txt"), (os.path.join("skills", "s", "SKILL.md"), "references/gone.md")],
        )


class AgentNamesTest(unittest.TestCase):
    def agent_table(self):
        rows = {}
        for line in read(skill_md("gauntlet-loop")).split("\n"):
            match = re.match(r"^\| \*\*(\S+)\*\* \|(.*)\|$", line)
            if match:
                rows[match.group(1).strip("`")] = [cell.strip() for cell in match.group(2).split("|")]
        return rows

    def test_agent_table_lists_all_agents_by_plugin_name(self):
        self.assertEqual(set(self.agent_table()), {"gauntlet:" + a for a in AGENTS})

    def test_zeta_receives_alphas_question_and_never_betas_bar(self):
        role, receives, never = self.agent_table()["gauntlet:zeta"]
        self.assertIn("alpha", role)
        self.assertRegex(receives, r"question")
        self.assertRegex(receives, r"files")
        self.assertRegex(never, r"bar")

    def test_every_plugin_agent_name_is_a_real_agent(self):
        for name in OWNED:
            with self.subTest(skill=name):
                for agent in re.findall(r"gauntlet:([a-z][a-z-]*)", read(skill_md(name))):
                    self.assertIn(agent, AGENTS)

    def test_agents_are_started_by_their_plugin_names(self):
        bare_start = re.compile(
            r"(?i)\b(start|starts|spawn|run|delegate to)\s+\**(" + "|".join(AGENTS) + r")\b"
        )
        for name in OWNED:
            with self.subTest(skill=name):
                self.assertEqual(bare_start.findall(read(skill_md(name))), [])
        self.assertIn("`gauntlet:epsilon`", read(skill_md("intake")))

    def test_old_definition_locations_are_gone(self):
        for name in OWNED:
            with self.subTest(skill=name):
                self.assertNotRegex(read(skill_md(name)), r"(?i)defined in|mirrored in")


class ServerToolsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = helpers.load_server()
        cls.text = read(skill_md("gauntlet-loop"))

    def test_gauntlet_loop_names_all_nine_server_tools(self):
        self.assertEqual(len(self.server.TOOLS), 9)
        for tool in self.server.TOOLS:
            with self.subTest(tool=tool):
                self.assertIn(f"`{tool}`", self.text)

    def test_every_tool_named_in_the_skills_exists_in_the_server(self):
        known = set(self.server.TOOLS) | set(ERROR_CODES)
        for name in OWNED:
            for token in re.findall(r"`((?:loop|worktree|lock|config)_[a-z_]+)`", read(skill_md(name))):
                with self.subTest(skill=name, token=token):
                    self.assertIn(token, known)

    def test_every_gauntlet_command_in_the_skills_parses(self):
        parser = self.server.build_parser()
        commands = [c for name in OWNED for c in re.findall(r"`gauntlet ([^`]+)`", read(skill_md(name)))]
        self.assertIn("status", commands)
        for command in commands:
            with self.subTest(command=command):
                try:
                    parser.parse_args(shlex.split(command))
                except SystemExit:
                    self.fail(f"`gauntlet {command}` is not a valid CLI command")

    def test_running_loops_come_from_status_not_the_folder(self):
        self.assertNotRegex(self.text, r"(?i)list the folder")
        self.assertIn("`status`", self.text)
        self.assertIn("`gauntlet status`", self.text)

    def test_each_merge_takes_the_lock_and_removes_the_slice_worktree(self):
        merge = [item for item in list_items(self.text) if "**Merge:**" in item]
        self.assertEqual(len(merge), 1)
        for tool in ("lock_acquire", "lock_release", "worktree_rm"):
            self.assertIn(f"`{tool}`", merge[0])

    def test_integration_worktree_and_unmerged_slices_stay_for_the_user(self):
        self.assertRegex(self.text, r"(?is)integration worktree.{0,80}unmerged slices?.{0,40}stay")

    def test_missing_config_returns_the_questions(self):
        self.assertIn("`config_missing`", self.text)
        for field in ("integration branch", "shared folders", "checks", "setup"):
            self.assertIn(field, self.text)


class ProjectConfigTest(unittest.TestCase):
    def test_project_specifics_come_from_gauntlet_json(self):
        text = read(skill_md("gauntlet-loop"))
        self.assertIn(".gauntlet.json", text)
        for key in ("`shared`", "`checks`", "`setup`"):
            self.assertIn(key, text)

    def test_no_project_specific_folders_or_commands(self):
        for name in OWNED:
            with self.subTest(skill=name):
                self.assertNotRegex(read(skill_md(name)), r"node_modules|native module|\bnpm\b|\bnpx\b")


class IntakeSkillTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(skill_md("intake"))

    def test_prd_authoring_requires_historical_retrieval(self):
        self.assertRegex(self.text, r"(?is)docs/prd/.*openspec/changes/archive")
        self.assertIn("settled decisions", self.text.lower())
        self.assertIn("rejected alternatives", self.text.lower())

    def test_intake_requires_pre_grilling_shootdown(self):
        self.assertIn("shootdown", self.text.lower())
        for dim in ("failure mode", "blast radius", "migration", "minimalism"):
            self.assertIn(dim, self.text.lower())

    def test_grilling_requires_multiple_choice_and_forbids_open_ended(self):
        self.assertIn("multiple-choice", self.text.lower())
        self.assertIn("(recommended)", self.text.lower())
        self.assertRegex(self.text, r"(?is)open-ended questions?.*?(forbidden|disallowed|never)")

    def test_superseding_settled_decisions_requires_explicit_attribution(self):
        self.assertIn("`Supersedes: NNN/DX`", self.text)

    def test_gate_checks_historical_consistency(self):
        self.assertRegex(self.text, r"(?i)settled decisions?")
        self.assertIn("gate", self.text.lower())


if __name__ == "__main__":
    unittest.main()
