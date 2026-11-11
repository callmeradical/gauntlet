"""context-handoff: the handoff skill, the handoff rule in every role and the loop skill, pi tool names."""

import os
import re
import unittest

import helpers

AGENTS_DIR = os.path.join(helpers.PLUGIN, "agents")
SKILLS = os.path.join(helpers.PLUGIN, "skills")
ROLES = ("alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta")
CRITICS = ("beta", "eta")
WORKERS = ("alpha", "beta", "gamma", "delta", "zeta", "eta")
# pi's built-in tool names (pi-subagents treats the `tools` field as a strict, case-sensitive allowlist).
PI_TOOLS = {"read", "bash", "edit", "write", "grep", "find", "ls"}
PI_WRITE_TOOLS = {"bash", "edit", "write"}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def flat(text):
    return " ".join(text.split()).lower()


def agent(name):
    return read(os.path.join(AGENTS_DIR, name + ".md"))


def handoff_section(text):
    match = re.search(r"^## Context handoffs\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError("no '## Context handoffs' section")
    return flat(match.group(1))


def skill():
    return read(os.path.join(SKILLS, "handoff", "SKILL.md"))


class HandoffSkillTest(unittest.TestCase):
    def test_skill_has_agent_skills_frontmatter(self):
        meta = helpers.read_frontmatter(os.path.join(SKILLS, "handoff", "SKILL.md"))
        self.assertEqual(meta.get("name"), "handoff")
        self.assertTrue(meta.get("description", "").strip())

    def test_skill_credits_its_source(self):
        self.assertIn("mattpocock/skills", skill())
        self.assertIn("productivity/handoff", skill())

    def test_skill_lands_in_the_durable_state_folder(self):
        text = flat(skill())
        self.assertIn("~/.local/state/gauntlet/handoffs/<loop-or-pane>-<role>-<yyyymmdd-hhmm>.md", text)
        self.assertIn("not the workspace and not `/tmp`", text)

    def test_skill_names_the_required_contents(self):
        text = flat(skill())
        for phrase in (
            "loop", "slice or queue item", "branch", "worktree", "exact head commit",
            "done and proven", "evidence", "ordered checklist", "open decisions", "owner",
            "promises", "running subagents", "background jobs", "environment rules",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_skill_references_artifacts_redacts_secrets_and_marks_unverified(self):
        text = flat(skill())
        self.assertIn("reference them by path", text)
        self.assertIn("never copy", text)
        self.assertIn("redact", text)
        self.assertIn('"unverified"', text)

    def test_skill_ends_with_suggested_skills(self):
        headings = re.findall(r"(?m)^## (.+)$", skill())
        self.assertEqual(headings[-1], "Suggested skills")

    def test_successor_prompt_and_no_shell_paste(self):
        text = flat(skill())
        self.assertIn('"continue from handoff <path>"', text)
        self.assertIn("never paste a handoff into a shell command", text)


class RoleRuleTest(unittest.TestCase):
    def test_every_role_has_the_handoff_rule_and_names_the_skill(self):
        for name in ROLES:
            with self.subTest(agent=name):
                text = handoff_section(agent(name))
                for phrase in (
                    "`handoff.context_threshold`", "65%", "clean point", "finish or revert",
                    "restore", "kill your own hung processes", "`handoff` skill",
                    "successor of the same role", '"continue from handoff <path>"',
                    "the coordination channel, if any",
                ):
                    self.assertIn(phrase.lower(), text, phrase)

    def test_workers_report_to_the_orchestrator(self):
        for name in WORKERS:
            with self.subTest(agent=name):
                self.assertIn("report the handoff path to the orchestrator, which starts the successor", handoff_section(agent(name)))

    def test_critics_report_incomplete_not_a_verdict(self):
        for name in CRITICS:
            with self.subTest(agent=name):
                text = handoff_section(agent(name))
                self.assertIn("never issue a verdict from partial evidence", text)
                self.assertIn('report "incomplete" and the handoff path', text)
                self.assertIn("successor redoes every bar item whose evidence is not recorded", text)

    def test_epsilon_starts_its_own_successor_and_records_the_handoff(self):
        text = handoff_section(agent("epsilon"))
        self.assertIn("start your own successor", text)
        self.assertIn("`loop_update` with `handoff`", text)
        self.assertIn("launch the successor of the same role", text)

    def test_loop_skill_has_the_rule(self):
        text = handoff_section(read(os.path.join(SKILLS, "gauntlet-loop", "SKILL.md")))
        for phrase in (
            "`handoff` skill", "`handoff.context_threshold`", "65%", "clean point",
            'report "incomplete"', "`loop_update` with `handoff`", "the coordination channel, if any",
            '"continue from handoff <path>"',
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), text)


class PiToolsTest(unittest.TestCase):
    """The generated pi variants in plugins/gauntlet/pi-agents/ carry pi's names."""

    def tools(self, name):
        meta = helpers.read_frontmatter(os.path.join(helpers.PLUGIN, "pi-agents", name + ".md"))
        if "tools" not in meta:
            return None
        return {t.strip() for t in meta["tools"].split(",") if t.strip()}

    def test_every_tool_list_includes_a_pi_builtin(self):
        for name in ROLES:
            tools = self.tools(name)
            if tools is None:
                continue
            with self.subTest(agent=name):
                self.assertTrue(tools & PI_TOOLS, f"{name} lists no pi tool: {sorted(tools)}")

    def test_read_only_roles_get_no_pi_write_tools(self):
        for name in ("eta", "zeta"):
            with self.subTest(agent=name):
                self.assertEqual((self.tools(name) or set()) & PI_WRITE_TOOLS, set())

    def test_pi_names_mirror_the_claude_code_names(self):
        for name in ROLES:
            tools = self.tools(name)
            if tools is None:
                continue
            with self.subTest(agent=name):
                mirrored = {"Read": "read", "Bash": "bash", "Edit": "edit", "Write": "write", "Grep": "grep", "Glob": "find"}
                claude = {t.strip() for t in helpers.read_frontmatter(os.path.join(AGENTS_DIR, name + ".md"))["tools"].split(",")}
                expected = {pi for c, pi in mirrored.items() if c in claude}
                if "Glob" in claude:
                    expected.add("ls")
                self.assertEqual(tools & PI_TOOLS, expected)


if __name__ == "__main__":
    unittest.main()
