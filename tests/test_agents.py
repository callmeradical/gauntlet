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
AGENTS = ("alpha", "beta", "gamma", "delta", "epsilon", "eta")
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

# Claude Code names only; pi's names live in `pi-tools` (see tests/test_harness_tools.py).
# Decision Q8 in openspec/changes/package-gauntlet-plugin/slices.gauntlet-plugin.md.
EXPECTED_TOOLS = {
    "alpha": {"Read", "Write", "Edit", "Bash", "Glob", "Grep", "Skill", "WebFetch", "WebSearch", "Agent"},
    "beta": {"Read", "Bash", "Glob", "Grep", "Skill", "WebFetch", "WebSearch"},
    "eta": {"Read", "Glob", "Grep", "Skill", "WebFetch", "WebSearch"},
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


def blocks(agent):
    """The body split on blank lines, each block with its line wrapping collapsed to single spaces."""
    return [" ".join(block.split()) for block in re.split(r"\n\s*\n", body(agent)) if block.strip()]


def rule(agent, marker):
    """The one block of the agent's body containing `marker` (case-insensitive); fails if there is none."""
    found = [b for b in blocks(agent) if marker.lower() in b.lower()]
    if len(found) != 1:
        raise AssertionError("%s.md: expected one block containing %r, found %d" % (agent, marker, len(found)))
    return found[0]


def raw_section(agent, heading):
    """The body text under a `## ` heading, up to the next one, as written."""
    match = re.search(r"^## %s\n(.*?)(?=^## |\Z)" % re.escape(heading), body(agent), re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError("%s.md has no '## %s' section" % (agent, heading))
    return match.group(1)


def section(agent, heading):
    """The body text under a `## ` heading, up to the next one, with line wrapping collapsed."""
    return " ".join(raw_section(agent, heading).split())


def step(agent, heading, marker):
    """The one top-level numbered item of a section containing `marker`, line wrapping collapsed.

    Indented sub-items and continuation paragraphs stay with their item.
    """
    items = [" ".join(i.split()) for i in re.split(r"\n(?=\d+\. )", raw_section(agent, heading))]
    found = [i for i in items if re.match(r"\d+\. ", i) and marker.lower() in i.lower()]
    if len(found) != 1:
        raise AssertionError("%s.md '## %s': expected one step containing %r, found %d" % (agent, heading, marker, len(found)))
    return found[0]


class ScenarioTest(unittest.TestCase):
    """One test per scenario of the slice, at its seam: the definition file the agent runs from."""

    def assertSays(self, text, *phrases):
        for phrase in phrases:
            self.assertIn(phrase.lower(), text.lower())

    def assertSaysInOrder(self, text, *phrases):
        """Each phrase appears, and after the one before it."""
        position = 0
        for phrase in phrases:
            found = text.lower().find(phrase.lower(), position)
            self.assertGreaterEqual(found, 0, "%r not found after position %d in: %s" % (phrase, position, text))
            position = found + len(phrase)

    def test_epsilon_creates_a_slice(self):
        """Tracer and fan-out each create the worktree with worktree_new, then run gauntlet:alpha in it."""
        self.assertSaysInOrder(
            step("epsilon", "Loop", "**Tracer.**"),
            "create the tracer's worktree and branch with `worktree_new`",
            "run `gauntlet:alpha` in it",
        )
        self.assertSaysInOrder(
            step("epsilon", "Loop", "**Fan out.**"),
            "create one worktree and branch per remaining slice with `worktree_new`",
            "run one `gauntlet:alpha` per slice, in that slice's worktree",
        )

    def test_epsilon_merges_under_the_lock_then_removes_the_slice(self):
        """Merge step: lock_acquire, merge, checks, lock_release, then worktree_rm for that slice."""
        self.assertSaysInOrder(
            step("epsilon", "Loop", "**Merge**"),
            "take the merge lock with `lock_acquire`",
            "merge the slice branch into the integration branch",
            "run the full checks from `config_read`",
            "release the lock with `lock_release`",
            "remove that slice's worktree and branch right away with `worktree_rm` (loop, slice)",
        )

    def test_refactor_request(self):
        """alpha refactors only on the critic's HOLD or the slice brief, suite green before and after."""
        text = rule("alpha", "Refactor only on request")
        self.assertSays(
            text,
            "refactor only when the critic's HOLD",
            "or the slice brief asks for it",
            "full suite green before the refactor and again after it",
            "change nothing beyond what was asked",
            "no speculative refactoring",
        )

    def test_missing_scenario_test(self):
        """Every beta bar requires a test per scenario at its seam; a HOLD names the untested scenario."""
        text = rule("beta", "Scenario coverage is part of every bar")
        self.assertSays(
            text,
            "whether or not the bar says so",
            "each scenario in the slice has a test at its seam",
            "no test is tautological or coupled to implementation details",
            "`tdd` skill",
            "the HOLD names that scenario",
        )

    def test_hand_back_lists_questions(self):
        """alpha knows when and how to start gauntlet:zeta, and lists its questions without zeta's reasoning."""
        text = section("alpha", "Design questions: `gauntlet:zeta`")
        self.assertSays(
            text,
            "neither the slice brief nor the codebase's existing patterns settle",
            "start `gauntlet:zeta` with one specific question and the paths of the relevant files",
            "`gauntlet:zeta` is the only agent to start",
            "the decision stays here",
            "in the hand-back, list each design question asked, without `gauntlet:zeta`'s reasoning",
        )

    def test_new_project(self):
        """On config_missing epsilon returns the four questions and offers to write .gauntlet.json."""
        text = rule("epsilon", "Missing config.")
        self.assertSays(
            text,
            "when `loop_start` reports `config_missing`, do not guess",
            "return to the caller the four questions",
            "integration branch, shared folders, checks",
            "and setup",
            "offer to write `.gauntlet.json`",
            "do not commit it",
        )


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
        for agent in ("delta", "alpha", "beta", "gamma", "eta"):
            with self.subTest(agent=agent):
                self.assertIn("`gauntlet:%s`" % agent, body("epsilon"))


class GammaTest(unittest.TestCase):
    def test_gamma_reads_the_template_from_the_installed_plugin(self):
        self.assertIn(TEMPLATE, body("gamma"))


if __name__ == "__main__":
    unittest.main()
