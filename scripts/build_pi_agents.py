#!/usr/bin/env python3
"""Generate the pi-subagents agent files from the Claude Code agent files.

Source: plugins/gauntlet/agents/*.md. Claude Code reads `tools:` (Claude Code
names) and ignores the `pi-*` keys. Output: plugins/gauntlet/pi-agents/*.md,
where each `pi-<key>: value` becomes `<key>: value` (replacing any `<key>` the
source has), so pi sees only pi tool names. The body is copied unchanged.

Usage: build_pi_agents.py [--src DIR] [--out DIR] [--check]
"""

import argparse
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "plugins", "gauntlet", "agents")
OUT = os.path.join(ROOT, "plugins", "gauntlet", "pi-agents")


def key_of(line):
    if line[:1] in (" ", "\t") or ":" not in line:
        return None
    return line.split(":", 1)[0].strip()


def convert(text, name):
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{name}: no frontmatter")
    end = lines.index("---", 1)
    front = lines[1:end]
    overrides = {}
    for line in front:
        key = key_of(line)
        if key and key.startswith("pi-"):
            overrides[key[3:]] = line.split(":", 1)[1].strip()
    result, skipping = [], False
    for line in front:
        key = key_of(line)
        if key is not None:
            skipping = key.startswith("pi-") or key in overrides
            if key in overrides:
                result.append(f"{key}: {overrides.pop(key)}")
                continue
        if not skipping:
            result.append(line)
    # Keys the source only sets for pi: emit in source order.
    for line in front:
        key = key_of(line)
        if key and key.startswith("pi-") and key[3:] in overrides:
            result.append(f"{key[3:]}: {overrides.pop(key[3:])}")
    body = "\n".join(lines[end + 1:])
    return "---\n" + "\n".join(result) + "\n---\n" + body


def build(src, out, check):
    expected = {}
    for path in sorted(glob.glob(os.path.join(src, "*.md"))):
        name = os.path.basename(path)
        with open(path, encoding="utf-8") as f:
            expected[name] = convert(f.read(), name)
    stale = []
    existing = {os.path.basename(p) for p in glob.glob(os.path.join(out, "*.md"))}
    for name in sorted(existing - set(expected)):
        stale.append(name)
        if not check:
            os.remove(os.path.join(out, name))
    for name, content in expected.items():
        target = os.path.join(out, name)
        current = None
        if os.path.exists(target):
            with open(target, encoding="utf-8") as f:
                current = f.read()
        if current != content:
            stale.append(name)
            if not check:
                os.makedirs(out, exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(content)
    if check and stale:
        print("stale pi agent files (run scripts/build_pi_agents.py): " + ", ".join(stale))
        return 1
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--src", default=SRC)
    parser.add_argument("--out", default=OUT)
    parser.add_argument("--check", action="store_true", help="fail if the output is out of date; write nothing")
    args = parser.parse_args(argv)
    return build(args.src, args.out, args.check)


if __name__ == "__main__":
    sys.exit(main())
