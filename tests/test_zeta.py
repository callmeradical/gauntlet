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
            for match in re.finditer(r"(?<![\w:-])(%s)\b" % "|".join(AGENTS), text):
                self.fail("bare agent name %r in: %r" % (match.group(1), text[max(0, match.start() - 40) : match.end() + 40]))
        self.assertIn("gauntlet:alpha", body())

    def test_uses_codebase_design_vocabulary_but_not_its_sub_agent_pattern(self):
        text = body()
        self.assertIn("codebase-design", text)
        self.assertIn("DESIGN-IT-TWICE", text)


if __name__ == "__main__":
    unittest.main()
