"""plugin-package: zeta, the design advisor alpha may consult.

The behaviour ("Composition question") is agent behaviour exercised by the main
session after the plugin loads; these tests check the definition itself.
"""

import os
import re
import unittest

import helpers

ZETA = os.path.join(helpers.PLUGIN, "agents", "zeta.md")
AGENTS = ("alpha", "beta", "gamma", "delta", "epsilon", "zeta")


def read_text():
    with open(ZETA, encoding="utf-8") as f:
        return f.read()


def body():
    text = read_text()
    return text.split("\n---\n", 1)[1]


def tools():
    return [t.strip() for t in helpers.read_frontmatter(ZETA).get("tools", "").split(",") if t.strip()]


def flat(text):
    return " ".join(text.split())


def section(heading):
    """The flattened text under `## <heading>` up to the next heading; '' if absent."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", body(), re.MULTILINE | re.DOTALL)
    return flat(match.group(1)) if match else ""


def clauses(text):
    return re.split(r"[.;]\s|:\s", flat(text))


class ZetaFrontmatterTest(unittest.TestCase):
    def test_name_is_zeta_with_a_description(self):
        fm = helpers.read_frontmatter(ZETA)
        self.assertEqual(fm.get("name"), "zeta")
        self.assertTrue(fm.get("description", "").strip())

    def test_tools_are_read_only_and_cannot_start_agents(self):
        self.assertEqual(sorted(tools()), sorted(["Read", "Glob", "Grep", "Skill"]))
        for forbidden in ("Agent", "Write", "Edit", "NotebookEdit", "Bash"):
            with self.subTest(tool=forbidden):
                self.assertNotIn(forbidden, tools())


class ZetaTextTest(unittest.TestCase):
    def test_written_as_a_directive_without_persona(self):
        self.assertIsNone(re.search(r"\byou(\s+are|'re)\b", read_text(), re.IGNORECASE))

    def test_no_home_folder_paths(self):
        self.assertIsNone(re.search(r"~/\.(claude|agents|augy)\b|/Users/", read_text()))

    def test_agents_are_named_with_the_plugin_prefix(self):
        description = helpers.read_frontmatter(ZETA)["description"]
        for text in (description, body()):
            for match in re.finditer(r"(?<![\w:-])(" + "|".join(AGENTS) + r")\b", text):
                self.fail(f"bare agent name {match.group(1)!r} in: {text[max(0, match.start() - 40) : match.end() + 40]!r}")
        self.assertIn("gauntlet:alpha", body())

    def test_uses_codebase_design_vocabulary_but_not_its_sub_agent_pattern(self):
        text = " ".join(body().split())
        self.assertRegex(text, r"Load the bundled `codebase-design` skill")
        self.assertRegex(text, r"Use it for vocabulary only\.")
        self.assertRegex(text, r"Never run its DESIGN-IT-TWICE pattern or any other step that starts sub-agents")
        self.assertRegex(text, r"must not spawn\.")

    def test_never_instructs_running_design_it_twice_or_starting_agents(self):
        description = helpers.read_frontmatter(ZETA)["description"]
        text = " ".join((description + "\n" + body()).split())
        spawning = re.compile(r"DESIGN-IT-TWICE|sub-agents?|\bspawn|\bstart\w*\s+(\w+\s+)?agents?\b", re.IGNORECASE)
        negated = re.compile(r"\b(never|not|no|don't)\b", re.IGNORECASE)
        for clause in re.split(r"[.;]\s|:\s", text):
            if spawning.search(clause):
                with self.subTest(clause=clause):
                    self.assertRegex(clause, negated)


class ZetaContentTest(unittest.TestCase):
    """Rules behind the "Composition question" scenario, pinned at zeta.md on disk."""

    def test_composition_question(self):
        # THEN: a recommendation, the repo files showing the existing pattern, and reasons; no code.
        answer = section("Answer")
        self.assertIn("Reply with these three parts and nothing else", answer)
        self.assertRegex(
            answer,
            r"1\. \*\*Recommendation:\*\* one choice"
            r".*2\. \*\*Existing pattern:\*\* the files \(path and line\) that show it"
            r".*3\. \*\*Reasons:\*\*",
        )
        self.assertIn("Read code; write none.", section("Code"))

    def test_writes_no_code_and_quotes_repo_code_only_with_a_citation(self):
        code = section("Code")
        self.assertIn("Read code; write none.", code)
        self.assertIn("No new code in the answer, not even illustrative snippets", code)
        self.assertIn("Quote existing repo code only as evidence, briefly, with its path and line.", code)
        self.assertIn("No edits, diffs, or implementations.", code)

    def test_grounding_order_is_repo_then_language_then_principles(self):
        grounding = section("Grounding")
        self.assertIn(
            "Work through these sources in order. Use a later one only where the earlier ones don't settle the question.",
            grounding,
        )
        self.assertRegex(
            grounding,
            r"1\. \*\*The repo's existing patterns\.\*\*.*Cite every file used, by path and line\."
            r".*2\. \*\*The language's conventions:\*\*"
            r".*3\. \*\*General design principles\.\*\*",
        )

    def test_answers_only_the_question_asked(self):
        self.assertIn("Answer one design question from gauntlet:alpha.", flat(body()))
        self.assertIn("Answer only the question asked, limited to that question.", section("Scope"))

    def test_never_assesses_alphas_work(self):
        self.assertIn("Never assess gauntlet:alpha's work", section("Decline"))
        self.assertIn("do not write or edit code, start agents, or assess work.", flat(body()))

    def test_declines_a_bar_or_a_review_request(self):
        decline = section("Decline")
        self.assertIn(
            "Decline when the message contains a critic bar (gauntlet:beta's evaluation criteria), "
            "or asks for a review, a grade, or a verdict on gauntlet:alpha's work.",
            decline,
        )
        self.assertIn("give no assessment.", decline)

    def test_no_clause_asks_for_code_grading_or_ignoring_the_repo(self):
        description = helpers.read_frontmatter(ZETA)["description"]
        contrary = re.compile(
            r"\b(write|give|provide|produce)\b[^.;]*\b(code|implementations?|snippets?)\b"
            r"|\bfull code\b|\bgrad(e|es|ing)\b|\bassess|\bverdict\b|\bignore\b",
            re.IGNORECASE,
        )
        negated = re.compile(r"\b(never|not|no|nothing|don't|decline)\b", re.IGNORECASE)
        for clause in clauses(description + "\n" + body()):
            if contrary.search(clause):
                with self.subTest(clause=clause):
                    self.assertRegex(clause, negated)


if __name__ == "__main__":
    unittest.main()
