"""plugin-package: third-party skills are bundled with their license (scenario *License notice*).

`tdd` and `codebase-design` come from mattpocock/skills at a pinned commit. The only
allowed edits are link paths (reference files moved under references/) and one
attribution footer line at the end of each SKILL.md.
"""

import hashlib
import os
import re
import unittest

import helpers

UPSTREAM_REPO = "mattpocock/skills"
UPSTREAM_SHA = "4ae2317ddb22b046e26455e4f9c9b3aaaf62212d"
SKILLS = os.path.join(helpers.PLUGIN, "skills")

# Git blob SHAs of the upstream files at UPSTREAM_SHA, from the GitHub contents API.
UPSTREAM = {
    "tdd": {
        "SKILL.md": "01eadaa34e7c9a63a67d6dc3cce1cc81b0e49985",
        "references/tests.md": "7ab86479f925a1f9e8ba680af33cb3b12e015381",
        "references/mocking.md": "71cbfee674d93244ce81d1830b930ca9a69200bd",
        "LICENSE": "f1dd2c09108dde1a5f56097cee8461b3ea834499",
    },
    "codebase-design": {
        "SKILL.md": "3f63c8146dd2604b419c929e9876b90c30d410e9",
        "references/DEEPENING.md": "cd94075cfd754d147555c5d747a16431ed4c7dd8",
        "references/DESIGN-IT-TWICE.md": "aebdc9f8c05b40d7832de38e2fd8380e1e5507ac",
        "LICENSE": "f1dd2c09108dde1a5f56097cee8461b3ea834499",
    },
}

DESCRIPTIONS = {
    "tdd": (
        "Test-driven development. Use when the user wants to build features or fix bugs "
        'test-first, mentions "red-green-refactor", or wants integration tests.'
    ),
    "codebase-design": (
        "Shared vocabulary for designing deep modules. Use when the user wants to design or "
        "improve a module's interface, find deepening opportunities, decide where a seam goes, "
        "make code more testable or AI-navigable, or when another skill needs the deep-module "
        "vocabulary."
    ),
}

# Every relative link each file must carry after the rewrite, in order.
EXPECTED_LINKS = {
    "tdd": {
        "SKILL.md": ["references/tests.md", "references/mocking.md"],
        "references/tests.md": [],
        "references/mocking.md": [],
    },
    "codebase-design": {
        "SKILL.md": ["references/DEEPENING.md", "references/DESIGN-IT-TWICE.md"],
        "references/DEEPENING.md": ["../SKILL.md"],
        "references/DESIGN-IT-TWICE.md": [
            "../SKILL.md",
            "DEEPENING.md",
            "DEEPENING.md",
            "../SKILL.md",
            "DEEPENING.md",
        ],
    },
}

MIT_LICENSE = """MIT License

Copyright (c) 2026 Matt Pocock

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

INLINE_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
REFERENCE_LINK = re.compile(r"^\s*\[[^\]]+\]:\s*(\S+)", re.MULTILINE)
EXTERNAL = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|#|/)", re.IGNORECASE)


def attribution(name):
    return "Source: github.com/%s, skills/engineering/%s at %s. MIT, see LICENSE." % (
        UPSTREAM_REPO,
        name,
        UPSTREAM_SHA,
    )


def read(name, rel):
    with open(os.path.join(SKILLS, name, rel), encoding="utf-8") as f:
        return f.read()


def relative_links(text):
    targets = INLINE_LINK.findall(text) + REFERENCE_LINK.findall(text)
    return [t for t in targets if not EXTERNAL.match(t)]


def files_under(folder):
    found = set()
    for root, _dirs, names in os.walk(folder):
        for n in names:
            found.add(os.path.relpath(os.path.join(root, n), folder).replace(os.sep, "/"))
    return found


def git_blob_sha(text):
    data = text.encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def undo_allowed_edits(name, rel, text):
    """Reverse the permitted edits so the result can be compared with the upstream blob."""
    if rel == "SKILL.md":
        footer = "\n" + attribution(name) + "\n"
        if text.endswith(footer):
            text = text[: -len(footer)]
        return text.replace("](references/", "](")
    if rel.startswith("references/"):
        return text.replace("](../SKILL.md)", "](SKILL.md)")
    return text


class VendoredSkillsTest(unittest.TestCase):
    def test_each_folder_holds_exactly_the_listed_files(self):
        for name, files in UPSTREAM.items():
            with self.subTest(skill=name):
                self.assertEqual(files_under(os.path.join(SKILLS, name)), set(files))

    def test_each_folder_carries_the_mit_license(self):
        for name in UPSTREAM:
            with self.subTest(skill=name):
                self.assertEqual(read(name, "LICENSE"), MIT_LICENSE)

    def test_frontmatter_name_equals_folder_and_description_is_untouched(self):
        for name in UPSTREAM:
            with self.subTest(skill=name):
                front = helpers.read_frontmatter(os.path.join(SKILLS, name, "SKILL.md"))
                self.assertEqual(front.get("name"), name)
                self.assertEqual(front.get("description"), DESCRIPTIONS[name])

    def test_skill_md_ends_with_one_attribution_line_naming_repo_path_and_commit(self):
        for name in UPSTREAM:
            with self.subTest(skill=name):
                text = read(name, "SKILL.md")
                self.assertTrue(text.endswith("\n\n" + attribution(name) + "\n"), text[-300:])
                self.assertEqual(text.count("mattpocock/skills"), 1)
                self.assertEqual(text.count("skills/engineering/%s " % name), 1)

    def test_links_are_the_rewritten_set(self):
        for name, files in EXPECTED_LINKS.items():
            for rel, expected in files.items():
                with self.subTest(skill=name, file=rel):
                    self.assertEqual(relative_links(read(name, rel)), expected)

    def test_every_relative_markdown_link_resolves_inside_the_skill_folder(self):
        checked = 0
        for name in UPSTREAM:
            folder = os.path.realpath(os.path.join(SKILLS, name))
            for rel in sorted(files_under(folder)):
                if not rel.endswith(".md"):
                    continue
                base = os.path.dirname(os.path.join(folder, rel))
                for target in relative_links(read(name, rel)):
                    path = os.path.realpath(os.path.join(base, target.split("#", 1)[0]))
                    with self.subTest(skill=name, file=rel, link=target):
                        self.assertTrue(path.startswith(folder + os.sep), path)
                        self.assertTrue(os.path.isfile(path), path)
                    checked += 1
        self.assertEqual(checked, 10)

    def test_text_is_upstream_apart_from_link_paths_and_attribution(self):
        for name, files in UPSTREAM.items():
            for rel, blob in files.items():
                with self.subTest(skill=name, file=rel):
                    restored = undo_allowed_edits(name, rel, read(name, rel))
                    self.assertEqual(git_blob_sha(restored), blob)


class LinkExtractionTest(unittest.TestCase):
    def test_keeps_relative_targets_and_drops_external_anchor_and_absolute_ones(self):
        text = (
            "See [a](references/a.md) and [b](../SKILL.md \"title\").\n"
            "[web](https://example.com) [mail](mailto:x@y.z) [top](#top) [abs](/etc/x)\n"
            "[ref]: DEEPENING.md\n"
        )
        self.assertEqual(
            relative_links(text),
            ["references/a.md", "../SKILL.md", "DEEPENING.md"],
        )


if __name__ == "__main__":
    unittest.main()
