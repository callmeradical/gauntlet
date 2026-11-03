#!/usr/bin/env python3
"""Switch this machine from the loose gauntlet agent and skill copies to the plugin.

    python3 scripts/cutover.py [--dry-run] [--rollback <backup dir>]

Refuses while any loop is running. Otherwise it backs up every target to
~/.local/state/gauntlet/cutover-<timestamp>/ (manifest.json plus copies), removes Claude Code's
loose copies, and replaces the other tools' copies with absolute symlinks into this checkout's
plugins/gauntlet. --rollback restores everything recorded in a backup's manifest. --dry-run prints
the plan and writes nothing. Links are never followed. Python 3.9+ standard library only.
"""

import argparse
import datetime
import importlib.util
import json
import os
import shutil
import stat
import sys

SCRIPT_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(SCRIPT_REPO, "plugins", "gauntlet", "server", "gauntlet.py")
AGENTS = ("alpha", "beta", "gamma", "delta", "epsilon")
SKILLS = ("intake", "gauntlet-loop")
MANIFEST = "manifest.json"


class CutoverError(Exception):
    """A refusal: nothing was changed."""


def targets(home, repo_root):
    """[(path, action, link_to)] in the order they are applied; link_to is None for removals."""
    plugin = os.path.join(os.path.abspath(repo_root), "plugins", "gauntlet")
    result = [(os.path.join(home, ".claude", "agents", a + ".md"), "remove", None) for a in AGENTS]
    result += [(os.path.join(home, ".claude", "skills", s), "remove", None) for s in SKILLS]
    result += [(os.path.join(home, ".augy", "skills", s), "link", os.path.join(plugin, "skills", s)) for s in SKILLS]
    result += [
        (os.path.join(home, ".agents", "agents", a + ".md"), "link", os.path.join(plugin, "agents", a + ".md"))
        for a in AGENTS
    ]
    return result


def running_loops(home):
    """Ids of running loops in <home>/.local/state/gauntlet, by the server's own rule (legacy files count)."""
    spec = importlib.util.spec_from_file_location("gauntlet_server", SERVER)
    server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server)
    saved = os.environ.get("HOME")
    os.environ["HOME"] = home  # the server's state_dir() reads $HOME on every call
    try:
        return [state["loop"] for state in server.running_loops()]
    finally:
        if saved is None:
            del os.environ["HOME"]
        else:
            os.environ["HOME"] = saved


def refuse_if_running(home):
    loops = running_loops(home)
    if loops:
        raise CutoverError("refusing: loops are running: %s. Nothing was changed." % ", ".join(loops))


def describe(path):
    """(type, link target, mode) of path without following it; type is None when it doesn't exist."""
    try:
        st = os.lstat(path)
    except FileNotFoundError:
        return None, None, None
    mode = "%04o" % stat.S_IMODE(st.st_mode)
    if stat.S_ISLNK(st.st_mode):
        return "symlink", os.readlink(path), mode
    if stat.S_ISDIR(st.st_mode):
        return "dir", None, mode
    return "file", None, mode


def plan(home, repo_root):
    """The steps a cutover would take: [{path, action, type, link, mode, link_to}] plus skipped paths."""
    missing = [link_to for _, action, link_to in targets(home, repo_root) if link_to and not os.path.exists(link_to)]
    if missing:
        raise CutoverError("refusing: link targets are missing in the repo: %s. Nothing was changed." % ", ".join(missing))
    steps, skipped = [], []
    for path, action, link_to in targets(home, repo_root):
        kind, link, mode = describe(path)
        if kind is None:
            skipped.append((path, "does not exist"))
        elif action == "link" and kind == "symlink" and link == link_to:
            skipped.append((path, "already linked"))
        else:
            steps.append({"path": path, "action": action, "type": kind, "link": link, "mode": mode, "link_to": link_to})
    return steps, skipped


def remove(path):
    """Delete path without following it: unlink files and links, remove real folders."""
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)


def restore(entry, backup):
    """Put entry's original back at its path (the path must not exist)."""
    path = entry["path"]
    if entry["type"] == "symlink":
        os.symlink(entry["link"], path)
        return
    source = os.path.join(backup, entry["content"])
    if entry["type"] == "dir":
        shutil.copytree(source, path, symlinks=True)
    else:
        shutil.copy2(source, path)
    os.chmod(path, int(entry["mode"], 8))


def new_backup_dir(home):
    base = os.path.join(home, ".local", "state", "gauntlet", "cutover-" + datetime.datetime.now().strftime("%Y%m%dT%H%M%S"))
    os.makedirs(os.path.dirname(base), exist_ok=True)
    path, n = base, 1
    while True:
        try:
            os.mkdir(path)
            return path
        except FileExistsError:
            n += 1
            path = "%s-%d" % (base, n)


def write_backup(backup, steps, home, repo_root):
    """Copy every non-link target into backup/files and write the manifest; sets each step's `content`."""
    os.mkdir(os.path.join(backup, "files"))
    for i, step in enumerate(steps):
        step["content"] = None
        if step["type"] != "symlink":
            step["content"] = os.path.join("files", "%02d-%s" % (i, os.path.basename(step["path"])))
            copy = os.path.join(backup, step["content"])
            if step["type"] == "dir":
                shutil.copytree(step["path"], copy, symlinks=True)
            else:
                shutil.copy2(step["path"], copy)
    manifest = {
        "created": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "home": home,
        "repo": os.path.abspath(repo_root),
        "entries": steps,
    }
    with open(os.path.join(backup, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


def cutover(home=None, repo_root=None, dry_run=False):
    """Run (or with dry_run, only plan) the cutover; return {steps, skipped, backup}. Raises CutoverError."""
    home = home or os.path.expanduser("~")
    repo_root = repo_root or SCRIPT_REPO
    refuse_if_running(home)
    steps, skipped = plan(home, repo_root)
    if dry_run or not steps:
        return {"steps": steps, "skipped": skipped, "backup": None}

    backup = new_backup_dir(home)
    try:
        write_backup(backup, steps, home, repo_root)
    except OSError as exc:
        shutil.rmtree(backup, ignore_errors=True)
        raise CutoverError("refusing: could not back up the targets (%s). Nothing was changed." % exc)

    applied = []
    try:
        for step in steps:
            applied.append(step)
            remove(step["path"])
            if step["action"] == "link":
                os.symlink(step["link_to"], step["path"])
    except OSError as exc:
        failed = applied[-1]["path"]
        for step in reversed(applied):
            if step["action"] == "link" and describe(step["path"])[:2] == ("symlink", step["link_to"]):
                os.unlink(step["path"])
            if not os.path.lexists(step["path"]):
                restore(step, backup)
        raise CutoverError(
            "cutover failed at %s (%s); the changes before it were undone. Backup kept at %s." % (failed, exc, backup)
        )
    return {"steps": steps, "skipped": skipped, "backup": backup}


def rollback(backup, home=None, dry_run=False):
    """Restore every entry in backup's manifest; return the entries. Raises CutoverError."""
    home = home or os.path.expanduser("~")
    backup = os.path.abspath(backup)
    refuse_if_running(home)
    try:
        with open(os.path.join(backup, MANIFEST), encoding="utf-8") as f:
            entries = json.load(f)["entries"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CutoverError("refusing: no readable manifest in %s (%s). Nothing was changed." % (backup, exc))
    conflicts = []
    for entry in entries:
        kind, link, _ = describe(entry["path"])
        left_as_cut = kind is None if entry["action"] == "remove" else (kind == "symlink" and link == entry["link_to"])
        if not left_as_cut:
            conflicts.append(entry["path"])
    if conflicts:
        raise CutoverError(
            "refusing: these paths are no longer as the cutover left them: %s. Nothing was changed."
            % ", ".join(conflicts)
        )
    if not dry_run:
        for entry in entries:
            if entry["action"] == "link":
                os.unlink(entry["path"])
            restore(entry, backup)
    return entries


def _original(entry):
    return "symlink -> %s" % entry["link"] if entry["type"] == "symlink" else entry["type"]


def main(argv=None, home=None, repo_root=None):
    parser = argparse.ArgumentParser(description="Switch from the loose gauntlet copies to the plugin.")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and write nothing")
    parser.add_argument("--rollback", metavar="BACKUP_DIR", help="restore everything from a cutover backup")
    args = parser.parse_args(argv)
    prefix = "would " if args.dry_run else ""
    try:
        if args.rollback:
            for entry in rollback(args.rollback, home=home, dry_run=args.dry_run):
                print("%srestore %s (%s)" % (prefix, entry["path"], _original(entry)))
            return 0
        result = cutover(home=home, repo_root=repo_root, dry_run=args.dry_run)
    except CutoverError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for step in result["steps"]:
        if step["action"] == "remove":
            print("%sremove %s (%s)" % (prefix, step["path"], _original(step)))
        else:
            print("%slink %s -> %s (was %s)" % (prefix, step["path"], step["link_to"], _original(step)))
    for path, reason in result["skipped"]:
        print("skip %s (%s)" % (path, reason))
    if result["backup"]:
        print("backup: %s" % result["backup"])
        print("roll back with: python3 %s --rollback %s" % (os.path.abspath(__file__), result["backup"]))
    elif not result["steps"]:
        print("nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main())
