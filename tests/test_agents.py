"""plugin-package: the five packaged agent definitions (alpha, beta, gamma, delta, epsilon).

The behavioural scenarios (Refactor request, Missing scenario test, Hand-back lists
questions, epsilon creates a slice, New project, Template location) are agent
behaviour; these tests check the definitions that drive it.
"""

import os
import re
import unittest

import helpers

AGENTS_DIR = os.path.join(helpers.PLUGIN, "agents")
AGENTS = ("alpha", "beta", "gamma", "delta", "epsilon")
ALL_AGENT_NAMES = AGENTS + ("zeta",)

SERVER_TOOLS = (
    "loop_start",
    "loop_update",
    "loop_end",
    "worktree_new",
    "worktree_rm",
    "lock_acquire",
    "lock_release",
    "config_read",
    "status",
)
MCP_PREFIX = "mcp__plugin_gauntlet_gauntlet__"

# Decision Q8 in openspec/changes/package-gauntlet-plugin/slices.gauntlet-plugin.md.
EXPECTED_TOOLS = {
    "alpha": {"Read", "Write", "Edit", "Bash", "Glob", "Grep", "Skill", "WebFetch", "WebSearch", "Agent"},
    "beta": {"Read", "Bash", "Glob", "Grep", "Skill", "WebFetch", "WebSearch"},
    "epsilon": {"Read", "Write", "Edit", "Bash", "Glob", "Grep", "Skill", "Agent", "SendMessage"}
    | {MCP_PREFIX + tool for tool in SERVER_TOOLS},
}

TEMPLATE = "${CLAUDE_PLUGIN_ROOT}/skills/gauntlet-loop/references/progress.html"
FORBIDDEN_PATHS = re.compile(r"(~|\$HOME|\$\{HOME\})/\.(claude|agents|augy)\b|/Users/")
PERSONA = re.compile(r"\byou(\s+are|'re)\b", re.IGNORECASE)
BARE_AGENT_NAME = re.compile(r"(?<!gauntlet:)\b(%s)s?\b" % "|".join(ALL_AGENT_NAMES), re.IGNORECASE)


def path(agent):
    return os.path.join(AGENTS_DIR, agent + ".md")


def text(agent):
    with open(path(agent), encoding="utf-8") as f:
        return f.read()


def body(agent):
    """The markdown after the closing frontmatter fence."""
    return text(agent).split("\n---\n", 1)[1]


def tools(agent):
    return {t.strip() for t in helpers.read_frontmatter(path(agent))["tools"].split(",") if t.strip()}


class FrontmatterTest(unittest.TestCase):
    def test_each_agent_is_named_after_its_file_and_described(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                meta = helpers.read_frontmatter(path(agent))
                self.assertEqual(meta.get("name"), agent)
                self.assertTrue(meta.get("description", "").strip())

    def test_tools_match_decision_q8(self):
        for agent, expected in EXPECTED_TOOLS.items():
            with self.subTest(agent=agent):
                self.assertEqual(tools(agent), expected)

    def test_agent_is_in_alpha_and_epsilon_tools_and_not_in_beta(self):
        self.assertIn("Agent", tools("alpha"))
        self.assertIn("Agent", tools("epsilon"))
        self.assertNotIn("Agent", tools("beta"))

    def test_gamma_and_delta_keep_the_source_definitions_without_a_tools_line(self):
        for agent in ("gamma", "delta"):
            with self.subTest(agent=agent):
                self.assertNotIn("tools", helpers.read_frontmatter(path(agent)))

    def test_epsilon_server_tools_are_exactly_the_servers_registered_tools(self):
        named = {t[len(MCP_PREFIX):] for t in tools("epsilon") if t.startswith(MCP_PREFIX)}
        self.assertEqual(named, set(helpers.load_server().TOOLS))


class WordingTest(unittest.TestCase):
    def test_no_persona_phrasing(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.assertIsNone(PERSONA.search(text(agent)))

    def test_no_home_folder_install_paths(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.assertIsNone(FORBIDDEN_PATHS.search(text(agent)))

    def test_agents_are_always_named_with_the_plugin_namespace(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                lines = [line for line in text(agent).split("\n") if not line.startswith("name:")]
                self.assertEqual(BARE_AGENT_NAME.findall("\n".join(lines)), [])

    def test_no_agent_spells_out_git_worktree_steps(self):
        for agent in AGENTS:
            with self.subTest(agent=agent):
                self.assertNotIn("git worktree", text(agent))


class AlphaTest(unittest.TestCase):
    def test_alpha_follows_the_bundled_tdd_skill(self):
        self.assertIn("`tdd`", body("alpha"))

    def test_alpha_knows_zeta_by_its_plugin_name(self):
        self.assertIn("`gauntlet:zeta`", body("alpha"))

    def test_zeta_is_the_only_agent_alpha_names(self):
        named = set(re.findall(r"gauntlet:(\w+)", body("alpha")))
        self.assertEqual(named, {"zeta"})


class BetaTest(unittest.TestCase):
    def test_beta_takes_the_test_anti_patterns_from_the_tdd_skill(self):
        self.assertIn("`tdd`", body("beta"))


class EpsilonTest(unittest.TestCase):
    def test_epsilon_uses_every_server_tool_by_name(self):
        for tool in SERVER_TOOLS:
            with self.subTest(tool=tool):
                self.assertIn("`%s`" % tool, body("epsilon"))

    def test_epsilon_starts_the_namespaced_agents(self):
        for agent in ("delta", "alpha", "beta", "gamma"):
            with self.subTest(agent=agent):
                self.assertIn("`gauntlet:%s`" % agent, body("epsilon"))


class GammaTest(unittest.TestCase):
    def test_gamma_reads_the_template_from_the_installed_plugin(self):
        self.assertIn(TEMPLATE, body("gamma"))


if __name__ == "__main__":
    unittest.main()
