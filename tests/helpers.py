"""Shared test helpers: fake home, temp git repos, server loading, CLI and MCP drivers.

Every test that touches state or git runs inside fake_home(), so the real
~/.claude, ~/.local/state/gauntlet and friends are never read or written.
"""

import contextlib
import importlib.util
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLUGIN = os.path.join(REPO_ROOT, "plugins", "gauntlet")
SERVER = os.path.join(PLUGIN, "server", "gauntlet.py")

GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "Gauntlet Test",
    "GIT_AUTHOR_EMAIL": "test@example.invalid",
    "GIT_COMMITTER_NAME": "Gauntlet Test",
    "GIT_COMMITTER_EMAIL": "test@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}

TIMEOUT = 30


@contextlib.contextmanager
def fake_home():
    """Point HOME (and git's config lookup) at a fresh temp dir; restore on exit."""
    home = os.path.realpath(tempfile.mkdtemp(prefix="gauntlet-home-"))
    overrides = dict(GIT_IDENTITY, HOME=home, XDG_CONFIG_HOME=os.path.join(home, ".config"))
    saved = {key: os.environ.get(key) for key in overrides}
    os.environ.update(overrides)
    try:
        yield home
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        shutil.rmtree(home, ignore_errors=True)


def git(cwd, *args):
    """Run git in cwd and return stripped stdout; raise with stderr on failure."""
    proc = subprocess.run(
        ["git", *args], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    if proc.returncode != 0:
        raise AssertionError("git %s failed in %s: %s" % (" ".join(args), cwd, proc.stderr.strip()))
    return proc.stdout.strip()


def make_repo(parent, name, branch="main", config=None, files=None):
    """Create a git repo at parent/name with one commit on `branch`; return its real path.

    `config` (a dict) is written as .gauntlet.json; `files` maps relative paths to text.
    """
    path = os.path.join(parent, name)
    os.makedirs(path)
    git(path, "init", "-q")
    git(path, "symbolic-ref", "HEAD", "refs/heads/" + branch)
    for rel, text in (files or {}).items():
        full = os.path.join(path, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w") as f:
            f.write(text)
    if config is not None:
        with open(os.path.join(path, ".gauntlet.json"), "w") as f:
            json.dump(config, f, indent=2)
    git(path, "add", "-A")
    git(path, "commit", "-q", "--allow-empty", "-m", "initial")
    return os.path.realpath(path)


_server = None


def load_server():
    """Import plugins/gauntlet/server/gauntlet.py as a module (once per test process)."""
    global _server
    if _server is None:
        spec = importlib.util.spec_from_file_location("gauntlet_server", SERVER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _server = module
    return _server


def _env(home):
    env = dict(os.environ)
    env.update(GIT_IDENTITY)
    env["HOME"] = home
    env["XDG_CONFIG_HOME"] = os.path.join(home, ".config")
    return env


def run_cli(*args, home):
    """Run the server as a CLI with sys.executable; return the CompletedProcess (text)."""
    return subprocess.run(
        [sys.executable, SERVER, *args],
        env=_env(home),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=TIMEOUT,
    )


class McpClient:
    """Drive the server over MCP stdio, one JSON-RPC message per line.

    `command` defaults to running the server with sys.executable.
    """

    def __init__(self, home, command=None):
        self.proc = subprocess.Popen(
            command or [sys.executable, SERVER],
            env=_env(home),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
        )
        self._next_id = 0
        self._lines = queue.Queue()
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        for line in self.proc.stdout:
            self._lines.put(line)
        self._lines.put(None)

    def send_raw(self, text):
        self.proc.stdin.write(text + "\n")
        self.proc.stdin.flush()

    def read_message(self, timeout=TIMEOUT):
        """Return the next message from stdout as a dict (raises if stdout is not JSON)."""
        line = self._lines.get(timeout=timeout)
        if line is None:
            raise AssertionError("server closed stdout; stderr: %s" % self.proc.stderr.read())
        return json.loads(line)

    def no_message(self, timeout=0.5):
        """True when nothing arrives on stdout within `timeout` seconds."""
        try:
            line = self._lines.get(timeout=timeout)
        except queue.Empty:
            return True
        self._lines.put(line)
        return False

    def request(self, method, params=None):
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": self._next_id, "method": method}
        if params is not None:
            message["params"] = params
        self.send_raw(json.dumps(message))
        reply = self.read_message()
        if reply.get("id") != self._next_id:
            raise AssertionError("reply id %r does not match request id %r" % (reply.get("id"), self._next_id))
        return reply

    def notify(self, method, params=None):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.send_raw(json.dumps(message))

    def call(self, tool, args):
        """Call a tool; return (is_error, payload) where payload is the parsed text content."""
        reply = self.request("tools/call", {"name": tool, "arguments": args})
        if "error" in reply:
            raise AssertionError("tools/call %s returned a protocol error: %r" % (tool, reply["error"]))
        result = reply["result"]
        return result["isError"], json.loads(result["content"][0]["text"])

    def close(self):
        if self.proc.poll() is None:
            self.proc.stdin.close()
            try:
                self.proc.wait(timeout=TIMEOUT)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()
        self.proc.stdout.close()
        self.proc.stderr.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def _unquote(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _block_scalar(style, chomp, lines):
    indents = [len(l) - len(l.lstrip(" ")) for l in lines if l.strip()]
    cut = min(indents) if indents else 0
    lines = [l[cut:] if l.strip() else "" for l in lines]
    while lines and not lines[-1]:
        lines.pop()
    if style == "|":
        text = "\n".join(lines)
    else:
        paragraphs, current = [], []
        for line in lines:
            if line:
                current.append(line)
            else:
                paragraphs.append(" ".join(current))
                current = []
        paragraphs.append(" ".join(current))
        text = "\n".join(p for p in paragraphs if p)
    return text if chomp == "-" else text + "\n"


def read_frontmatter(path):
    """Parse a markdown file's YAML frontmatter: `key: value`, plus `>` and `|` block scalars.

    Returns a dict of strings; {} when the file has no frontmatter.
    """
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    body = lines[1:end]
    result = {}
    i = 0
    while i < len(body):
        line = body[i]
        i += 1
        if not line.strip() or line.lstrip().startswith("#") or line.startswith((" ", "\t")):
            continue
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if value[:1] in (">", "|") and value[1:] in ("", "-", "+"):
            block = []
            while i < len(body) and (not body[i].strip() or body[i].startswith((" ", "\t"))):
                block.append(body[i])
                i += 1
            result[key] = _block_scalar(value[0], value[1:], block)
        else:
            result[key] = _unquote(value)
    return result
