#!/usr/bin/env python3
"""gauntlet: loop state, worktrees, merge locks and status for the gauntlet.

Run with no arguments to serve MCP over stdio; run with arguments for the CLI
(`gauntlet status`, `gauntlet loop start ...`). Python 3.9+ standard library and git only.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile

VERSION = "0.1.0"


# ============================================================================
# core
# ============================================================================


class GauntletError(Exception):
    """A refusal or failure reported to the caller as {"error": code, "message", ...details}."""

    def __init__(self, code, message, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details

    def to_dict(self):
        result = {"error": self.code, "message": self.message}
        result.update(self.details)
        return result


SCHEMA = 1
ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
ID_MAX = 24
END_STATUSES = ("done", "stopped", "failed")
SLICE_FIELDS = ("worktree", "branch", "status", "round", "commit", "verdict")


def now_iso():
    """Local time with its UTC offset, to the second."""
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def validate_id(value, kind="loop"):
    """Loop and slice ids are kebab-case, at most 24 characters."""
    if not isinstance(value, str) or len(value) > ID_MAX or not ID_PATTERN.fullmatch(value):
        raise GauntletError(
            "invalid_id",
            "%s id %r must be kebab-case (a-z, 0-9, single hyphens), at most %d characters" % (kind, value, ID_MAX),
            kind=kind,
        )
    return value


def run_git(cwd, *args):
    """Run git in cwd; return stripped stdout or raise git_failed."""
    command = ["git", "-C", cwd, *args]
    try:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    except OSError as exc:
        raise GauntletError("git_failed", "could not run git: %s" % exc, command=command)
    if proc.returncode != 0:
        raise GauntletError(
            "git_failed",
            "git %s failed in %s: %s" % (" ".join(args), cwd, proc.stderr.strip()),
            command=command,
            stderr=proc.stderr.strip(),
        )
    return proc.stdout.strip()


def main_worktree(path):
    """Absolute path of the main worktree of the repo containing `path`."""
    common = run_git(path, "rev-parse", "--git-common-dir")
    return os.path.dirname(os.path.realpath(os.path.join(path, common)))


def state_dir():
    """$HOME/.local/state/gauntlet, read from the environment on every call."""
    return os.path.join(os.environ.get("HOME") or os.path.expanduser("~"), ".local", "state", "gauntlet")


def _state_path(loop):
    return os.path.join(state_dir(), validate_id(loop) + ".json")


LOOP_KEYS = ("loop", "loop_id", "status")


def _as_loop(name, data):
    """The state dict if `data` is a loop file's content, else None (amendment Q4a).

    A loop file holds a JSON object with a `loop`, `loop_id` or `status` key. Its id is `loop`,
    else `loop_id`, else the file name without `.json`; the id is set as `loop` in the returned dict.
    """
    if not isinstance(data, dict) or not any(key in data for key in LOOP_KEYS):
        return None
    for key in ("loop", "loop_id"):
        if isinstance(data.get(key), str) and data[key]:
            data["loop"] = data[key]
            break
    else:
        data["loop"] = name
    return data


def load_loop(loop):
    """The loop's state dict (legacy files included); unknown_loop, with a reason, if there is none."""
    path = _state_path(loop)

    def unknown(reason):
        return GauntletError("unknown_loop", "no loop %r in %s: %s" % (loop, state_dir(), reason), loop=loop, reason=reason)

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise unknown("no state file")
    except (OSError, ValueError) as exc:
        raise unknown("%s is unreadable or not valid JSON: %s" % (path, exc))
    state = _as_loop(loop, data)
    if state is None:
        raise unknown("%s is not a loop file (needs an object with a loop, loop_id or status key)" % path)
    return state


def save_loop(state):
    """Stamp `updated` and write the state atomically (temp file in the same dir, then os.replace)."""
    path = _state_path(state["loop"])
    state["updated"] = now_iso()
    text = json.dumps(state, indent=2) + "\n"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix="." + state["loop"] + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise
    return state


def list_loops():
    """Every loop in the state dir: top-level *.json loop files (see _as_loop); others are skipped."""
    folder = state_dir()
    try:
        names = sorted(os.listdir(folder))
    except FileNotFoundError:
        return []
    loops = []
    for name in names:
        path = os.path.join(folder, name)
        if not name.endswith(".json") or not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        state = _as_loop(name[: -len(".json")], data)
        if state is not None:
            loops.append(state)
    return loops


def running_loops():
    return [state for state in list_loops() if state.get("status") == "running"]


def _same_repo_key(path):
    try:
        return main_worktree(path)
    except GauntletError:
        return os.path.realpath(path)


def loop_start(loop, repo, change, integration_branch=None):
    """Register a running loop; refuse duplicate ids and the same change in the same main repo."""
    validate_id(loop)
    running = running_loops()
    for other in running:
        if other["loop"] == loop:
            raise GauntletError("duplicate_loop", "loop %r is already running" % loop, running=loop)
    repo = os.path.realpath(run_git(repo, "rev-parse", "--show-toplevel"))
    config = config_read(repo)["config"]
    key = _same_repo_key(repo)
    for other in running:
        other_repo = other.get("repo") or other.get("integration_worktree")
        if other.get("change") == change and other_repo and _same_repo_key(other_repo) == key:
            raise GauntletError(
                "duplicate_loop",
                "loop %r is already running change %r in this repo" % (other["loop"], change),
                running=other["loop"],
            )
    started = now_iso()
    return save_loop(
        {
            "schema": SCHEMA,
            "loop": loop,
            "repo": repo,
            "change": change,
            "integration_branch": integration_branch or config["integration_branch"],
            "integration_worktree": repo,
            "phase": "start",
            "status": "running",
            "started": started,
            "updated": started,
            "ended": None,
            "slices": {},
        }
    )


def loop_update(
    loop, phase=None, slice=None, worktree=None, branch=None, status=None, round=None, commit=None, verdict=None
):
    """Record the loop's phase and/or one slice's fields; unknown keys are preserved."""
    values = dict(worktree=worktree, branch=branch, status=status, round=round, commit=commit, verdict=verdict)
    given = {key: values[key] for key in SLICE_FIELDS if values[key] is not None}
    state = load_loop(loop)
    if slice is not None or given:
        validate_id(slice, "slice")
        state.setdefault("slices", {}).setdefault(slice, {}).update(given)
    if phase is not None:
        state["phase"] = phase
    return save_loop(state)


def loop_end(loop, status):
    """Mark the loop done, stopped or failed and record when it ended."""
    if status not in END_STATUSES:
        raise GauntletError(
            "invalid_id",
            "end status %r must be one of %s" % (status, ", ".join(END_STATUSES)),
            kind="status",
            allowed=list(END_STATUSES),
        )
    state = load_loop(loop)
    state["status"] = status
    state["ended"] = now_iso()
    return save_loop(state)


CONFIG_NAME = ".gauntlet.json"
CONFIG_ASK = ["integration_branch", "shared", "checks", "setup"]


def _nonempty_string(value):
    return isinstance(value, str) and value != ""


def _check_shared(value):
    if not isinstance(value, list):
        return None, "must be a list of relative paths"
    cleaned = []
    for i, entry in enumerate(value):
        if not _nonempty_string(entry):
            return None, "entry %d must be a non-empty string" % i
        if os.path.isabs(entry) or ".." in entry.split("/"):
            return None, "entry %d (%r) must be a relative path without '..'" % (i, entry)
        norm = os.path.normpath(entry)
        if norm == ".":
            return None, "entry %d (%r) must name a folder" % (i, entry)
        cleaned.append(norm)
    return cleaned, None


def _check_checks(value):
    if not isinstance(value, list):
        return "must be a list of {name, command} objects"
    for i, entry in enumerate(value):
        if not isinstance(entry, dict) or set(entry) != {"name", "command"}:
            return "entry %d must be an object with exactly 'name' and 'command'" % i
        if not (_nonempty_string(entry["name"]) and _nonempty_string(entry["command"])):
            return "entry %d needs non-empty string 'name' and 'command'" % i
    return None


def config_read(repo):
    """Read and validate <repo>/.gauntlet.json; return {path, config} with defaults filled in."""
    path = os.path.join(os.path.realpath(repo), CONFIG_NAME)
    if not os.path.isfile(path):
        raise GauntletError(
            "config_missing",
            "%s not found; provide integration_branch, shared, checks and setup to create it" % path,
            path=path,
            ask=list(CONFIG_ASK),
        )
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
    except ValueError as exc:
        raise GauntletError("config_invalid", "%s is not valid JSON" % path, path=path, fields={"$": str(exc)})
    if not isinstance(raw, dict):
        raise GauntletError(
            "config_invalid", "%s must hold a JSON object" % path, path=path, fields={"$": "must be a JSON object"}
        )

    fields = {}
    config = {"integration_branch": raw.get("integration_branch"), "shared": [], "checks": [], "setup": None}
    if not _nonempty_string(config["integration_branch"]):
        fields["integration_branch"] = "required; must be a non-empty string"
    if "shared" in raw:
        config["shared"], problem = _check_shared(raw["shared"])
        if problem:
            fields["shared"] = problem
    if "checks" in raw:
        problem = _check_checks(raw["checks"])
        if problem:
            fields["checks"] = problem
        config["checks"] = raw["checks"]
    if "setup" in raw:
        if raw["setup"] is not None and not isinstance(raw["setup"], str):
            fields["setup"] = "must be a string or null"
        config["setup"] = raw["setup"]
    for key in raw:
        if key not in config:
            fields[key] = "unknown field"
    if fields:
        raise GauntletError(
            "config_invalid", "%s has invalid fields: %s" % (path, ", ".join(sorted(fields))), path=path, fields=fields
        )
    return {"path": path, "config": config}


# ============================================================================
# worktrees
# ============================================================================


def worktree_new(loop, slice):
    """Create the slice's worktree and branch from the loop's integration branch."""
    raise GauntletError("not_implemented", "worktree_new is not implemented yet")


def worktree_rm(loop, slice=None):
    """Remove merged slice worktrees (or one slice's); keep and report unmerged or dirty ones."""
    raise GauntletError("not_implemented", "worktree_rm is not implemented yet")


# ============================================================================
# locks
# ============================================================================


def lock_acquire(loop):
    """Take the merge lock for the loop's repo and integration branch."""
    raise GauntletError("not_implemented", "lock_acquire is not implemented yet")


def lock_release(loop):
    """Release the merge lock the loop holds."""
    raise GauntletError("not_implemented", "lock_release is not implemented yet")


# ============================================================================
# status
# ============================================================================


def status():
    """Every loop with its worktrees and lock; finished loops with leftovers are flagged."""
    raise GauntletError("not_implemented", "status is not implemented yet")


# ============================================================================
# registry + MCP + CLI
# ============================================================================


def _string(description):
    return {"type": "string", "description": description}


def _schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required), "additionalProperties": False}


LOOP_ARG = _string("Loop id: kebab-case, at most 24 characters.")
SLICE_ARG = _string("Slice name: kebab-case, at most 24 characters.")

TOOLS = {
    "loop_start": (
        loop_start,
        "Register a running loop: id, repo (integration worktree), OpenSpec change, integration branch "
        "(defaults to .gauntlet.json's). Refuses a duplicate id or the same change in the same repo; "
        "reports config_missing when the repo has no .gauntlet.json.",
        _schema(
            {
                "loop": LOOP_ARG,
                "repo": _string("Path of the integration worktree."),
                "change": _string("OpenSpec change name."),
                "integration_branch": _string("Integration branch; defaults to the config's."),
            },
            ["loop", "repo", "change"],
        ),
    ),
    "loop_update": (
        loop_update,
        "Record a loop's phase and/or one slice's worktree, branch, status, round, latest commit and verdict.",
        _schema(
            {
                "loop": LOOP_ARG,
                "phase": _string("Loop phase."),
                "slice": SLICE_ARG,
                "worktree": _string("Slice worktree path."),
                "branch": _string("Slice branch."),
                "status": _string("Slice status."),
                "round": {"type": "integer", "description": "Review round."},
                "commit": _string("Latest commit of the slice."),
                "verdict": _string("Latest review verdict (PASS or HOLD)."),
            },
            ["loop"],
        ),
    ),
    "loop_end": (
        loop_end,
        "End a loop as done, stopped or failed.",
        _schema(
            {"loop": LOOP_ARG, "status": {"type": "string", "enum": list(END_STATUSES), "description": "Final status."}},
            ["loop", "status"],
        ),
    ),
    "worktree_new": (
        worktree_new,
        "Create a slice worktree and branch gauntlet/<loop>/<slice> from the loop's integration branch, "
        "link the project's shared folders, and record it in the loop's state.",
        _schema({"loop": LOOP_ARG, "slice": SLICE_ARG}, ["loop", "slice"]),
    ),
    "worktree_rm": (
        worktree_rm,
        "Remove a loop's merged slice worktrees and branches (or one slice's); unmerged or dirty ones are kept "
        "and reported.",
        _schema({"loop": LOOP_ARG, "slice": SLICE_ARG}, ["loop"]),
    ),
    "lock_acquire": (
        lock_acquire,
        "Take the merge lock for the loop's repo and integration branch; refused while another loop holds it.",
        _schema({"loop": LOOP_ARG}, ["loop"]),
    ),
    "lock_release": (
        lock_release,
        "Release the merge lock the loop holds.",
        _schema({"loop": LOOP_ARG}, ["loop"]),
    ),
    "config_read": (
        config_read,
        "Read and validate a project's .gauntlet.json: integration branch, shared folders, checks, setup.",
        _schema({"repo": _string("Path of the project (a worktree root).")}, ["repo"]),
    ),
    "status": (
        status,
        "List loops with repo, change, phase, worktrees and merge lock; flag finished loops with leftovers.",
        _schema({}),
    ),
}

_JSON_TYPES = {"string": str, "integer": int, "object": dict}


class InvalidParams(Exception):
    pass


def _check_arguments(name, args):
    """Validate tool arguments against the tool's input schema; null values count as absent."""
    if not isinstance(name, str) or name not in TOOLS:
        raise InvalidParams("unknown tool %r" % (name,))
    if not isinstance(args, dict):
        raise InvalidParams("arguments must be an object")
    schema = TOOLS[name][2]
    args = {key: value for key, value in args.items() if value is not None}
    for key in schema["required"]:
        if key not in args:
            raise InvalidParams("%s: missing required argument %r" % (name, key))
    for key, value in args.items():
        spec = schema["properties"].get(key)
        if spec is None:
            raise InvalidParams("%s: unknown argument %r" % (name, key))
        kind = _JSON_TYPES[spec["type"]]
        if not isinstance(value, kind) or isinstance(value, bool):
            raise InvalidParams("%s: argument %r must be a %s" % (name, key, spec["type"]))
        if "enum" in spec and value not in spec["enum"]:
            raise InvalidParams("%s: argument %r must be one of %s" % (name, key, ", ".join(spec["enum"])))
    return args


def call_tool(name, args):
    """Validate and run a tool; returns its result dict or raises GauntletError / InvalidParams."""
    args = _check_arguments(name, args)
    return TOOLS[name][0](**args)


def _dump(value):
    return json.dumps(value, indent=2)


def _mcp_result(message_id, result):
    return {"jsonrpc": "2.0", "id": message_id, "result": result}


def _mcp_error(message_id, code, text):
    return {"jsonrpc": "2.0", "id": message_id, "error": {"code": code, "message": text}}


def handle_message(message):
    """Answer one JSON-RPC message; returns the reply dict, or None for notifications and responses."""
    if not isinstance(message, dict) or not isinstance(message.get("method"), str):
        if isinstance(message, dict) and "method" not in message and ("result" in message or "error" in message):
            return None
        return _mcp_error(message.get("id") if isinstance(message, dict) else None, -32600, "Invalid Request")
    if "id" not in message:
        return None
    message_id, method = message["id"], message["method"]
    params = message.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return _mcp_error(message_id, -32602, "Invalid params: params must be an object")
    if method == "initialize":
        return _mcp_result(
            message_id,
            {
                "protocolVersion": params.get("protocolVersion", "2025-06-18"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "gauntlet", "version": VERSION},
            },
        )
    if method == "ping":
        return _mcp_result(message_id, {})
    if method == "tools/list":
        tools = [{"name": n, "description": d, "inputSchema": s} for n, (_, d, s) in TOOLS.items()]
        return _mcp_result(message_id, {"tools": tools})
    if method == "tools/call":
        try:
            result, is_error = call_tool(params.get("name"), params.get("arguments") or {}), False
        except InvalidParams as exc:
            return _mcp_error(message_id, -32602, str(exc))
        except GauntletError as exc:
            result, is_error = exc.to_dict(), True
        except Exception as exc:  # a bug, not a refusal: report it without killing the server
            return _mcp_error(message_id, -32603, "internal error: %s: %s" % (type(exc).__name__, exc))
        return _mcp_result(message_id, {"content": [{"type": "text", "text": _dump(result)}], "isError": is_error})
    return _mcp_error(message_id, -32601, "Method not found: %s" % method)


def serve(stdin, stdout):
    """MCP stdio loop: one JSON-RPC message per line in (stdin is binary), one per line out.

    Each line is decoded as UTF-8 inside the parse step, so invalid bytes get -32700 like bad JSON.
    """
    for line in iter(stdin.readline, b""):
        if not line.strip():
            continue
        try:
            message = json.loads(line.decode("utf-8"))
        except ValueError:  # includes UnicodeDecodeError
            reply = _mcp_error(None, -32700, "Parse error")
        else:
            reply = handle_message(message)
        if reply is not None:
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()


def build_parser():
    """argparse CLI; each leaf subcommand sets `tool` and its arguments use the tool's argument names."""
    parser = argparse.ArgumentParser(prog="gauntlet", description="Gauntlet loops, worktrees, locks and status.")
    commands = parser.add_subparsers(dest="command", metavar="command")
    commands.required = True

    def leaf(group, name, tool, text):
        sub = group.add_parser(name, help=text, description=text)
        sub.set_defaults(tool=tool)
        return sub

    def group(name, text):
        sub = commands.add_parser(name, help=text, description=text).add_subparsers(dest="action", metavar="action")
        sub.required = True
        return sub

    leaf(commands, "status", "status", "List loops, worktrees and locks.")

    worktree = group("worktree", "Create or remove slice worktrees.")
    sub = leaf(worktree, "new", "worktree_new", "Create a slice worktree and branch.")
    sub.add_argument("loop")
    sub.add_argument("slice")
    sub = leaf(worktree, "rm", "worktree_rm", "Remove a loop's (or one slice's) merged worktrees.")
    sub.add_argument("loop")
    sub.add_argument("slice", nargs="?")

    lock = group("lock", "Take or release a merge lock.")
    leaf(lock, "acquire", "lock_acquire", "Take the loop's merge lock.").add_argument("loop")
    leaf(lock, "release", "lock_release", "Release the loop's merge lock.").add_argument("loop")

    loop = group("loop", "Register, update and end loops.")
    sub = leaf(loop, "start", "loop_start", "Register a running loop.")
    sub.add_argument("loop")
    sub.add_argument("--repo", required=True, help="integration worktree")
    sub.add_argument("--change", required=True, help="OpenSpec change")
    sub.add_argument("--integration-branch", dest="integration_branch", help="defaults to .gauntlet.json's")
    sub = leaf(loop, "update", "loop_update", "Record a loop's phase or a slice's fields.")
    sub.add_argument("loop")
    for name in ("phase", "slice", "worktree", "branch", "status", "commit", "verdict"):
        sub.add_argument("--" + name)
    sub.add_argument("--round", type=int)
    sub = leaf(loop, "end", "loop_end", "End a loop.")
    sub.add_argument("loop")
    sub.add_argument("status", choices=END_STATUSES)

    leaf(commands, "config", "config_read", "Read and validate a project's .gauntlet.json.").add_argument("repo")
    return parser


def run_cli(argv):
    """Run one CLI command: the tool's result as indented JSON on stdout, or its error on stderr (exit 1)."""
    namespace = vars(build_parser().parse_args(argv))
    tool = namespace.pop("tool")
    args = {key: value for key, value in namespace.items() if key not in ("command", "action")}
    try:
        result = call_tool(tool, args)
    except GauntletError as exc:
        sys.stderr.write(_dump(exc.to_dict()) + "\n")
        return 1
    sys.stdout.write(_dump(result) + "\n")
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        serve(sys.stdin.buffer, sys.stdout)
        return 0
    return run_cli(argv)


if __name__ == "__main__":
    sys.exit(main())
