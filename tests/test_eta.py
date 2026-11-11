"""Tests for gauntlet:eta and orthogonal review lenses."""

import os
import unittest

import helpers

AGENTS_DIR = os.path.join(helpers.PLUGIN, "agents")


def text(filename):
    with open(os.path.join(AGENTS_DIR, filename), encoding="utf-8") as f:
        return f.read()


class EtaTest(unittest.TestCase):
    def test_eta_agent_file_exists(self):
        path = os.path.join(AGENTS_DIR, "eta.md")
        self.assertTrue(os.path.exists(path), "eta.md must exist in agents directory")

    def test_eta_frontmatter_and_tools(self):
        path = os.path.join(AGENTS_DIR, "eta.md")
        meta = helpers.read_frontmatter(path)
        self.assertEqual(meta.get("name"), "eta")
        tools = {t.strip() for t in meta.get("tools", "").split(",") if t.strip()}
        expected = {"Read", "Glob", "Grep", "Skill", "WebFetch", "WebSearch"}
        self.assertEqual(tools, expected)

    def test_eta_audits_prd_and_openspec_together(self):
        body = text("eta.md")
        self.assertIn("PRD", body)
        self.assertIn("OpenSpec", body)
        self.assertIn("together", body.lower())

    def test_eta_four_orthogonal_lenses(self):
        body = text("eta.md")
        self.assertIn("Comprehension", body)
        self.assertIn("Invariant Safety", body)
        self.assertIn("Blast Radius", body)
        self.assertIn("Surface Minimization", body)

    def test_eta_verdict_format(self):
        body = text("eta.md")
        self.assertIn("PASS", body)
        self.assertIn("HOLD", body)
        self.assertIn("single biggest", body.lower())


class BetaLensesTest(unittest.TestCase):
    def test_beta_four_orthogonal_lenses(self):
        body = text("beta.md")
        self.assertIn("Comprehension", body)
        self.assertIn("Invariant Safety", body)
        self.assertIn("Blast Radius", body)
        self.assertIn("Surface Minimization", body)

    def test_beta_forbids_cosmetic_nitpicks(self):
        body = text("beta.md")
        self.assertTrue(
            "cosmetic" in body.lower() or "style" in body.lower(),
            "beta must explicitly forbid cosmetic or style preferences as reasons for a HOLD"
        )


if __name__ == "__main__":
    unittest.main()
