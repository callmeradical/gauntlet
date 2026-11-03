"""plugin-package: Agent Plugins 1.0.0 conformance and the Claude Code manifests."""

import copy
import hashlib
import json
import os
import re
import unittest

import helpers
import jsonschema_subset

SCHEMAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas")
PLUGIN_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"


def load(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as f:
        return json.load(f)


def schema(name):
    return load(SCHEMAS, name)


class VendoredSchemasTest(unittest.TestCase):
    def test_schemas_match_the_recorded_sha256(self):
        with open(os.path.join(SCHEMAS, "SOURCE")) as f:
            source = f.read()
        for name, url in (("plugin.schema.json", PLUGIN_SCHEMA_ID), ("mcp.schema.json", MCP_SCHEMA_ID)):
            self.assertIn(url, source)
            with open(os.path.join(SCHEMAS, name), "rb") as f:
                digest = hashlib.sha256(f.read()).hexdigest()
            self.assertRegex(source, r"%s\s+%s\s+sha256 %s" % (re.escape(name), re.escape(url), digest))
            self.assertEqual(schema(name)["$id"], url)

    def test_validator_understands_every_keyword_the_schemas_use(self):
        for name in ("plugin.schema.json", "mcp.schema.json"):
            unknown = jsonschema_subset.unsupported_keywords(schema(name))
            self.assertEqual(unknown, set(), name)


class AgentPluginsManifestTest(unittest.TestCase):
    def setUp(self):
        self.manifest = load(helpers.PLUGIN, "plugin.json")
        self.schema = schema("plugin.schema.json")

    def errors(self, instance):
        return jsonschema_subset.validate(instance, self.schema)

    def test_plugin_json_validates(self):
        # Scenario: Schema validation
        self.assertEqual(self.errors(self.manifest), [])

    def test_plugin_json_carries_the_spec_fields(self):
        self.assertEqual(self.manifest["$schema"], PLUGIN_SCHEMA_ID)
        self.assertEqual(self.manifest["name"], "gauntlet")
        for key in ("version", "description", "repository", "license"):
            self.assertTrue(self.manifest.get(key), key)
        self.assertTrue(self.manifest["author"].get("name"))

    def test_schema_rejects_broken_manifests(self):
        broken = {
            "unknown field": dict(self.manifest, mcpServers="./mcp.json"),
            "author as string": dict(self.manifest, author="Lars"),
            "unknown author field": dict(self.manifest, author={"name": "x", "twitter": "@x"}),
            "wrong $schema": dict(self.manifest, **{"$schema": "https://example.com/schema.json"}),
            "uppercase name": dict(self.manifest, name="Gauntlet"),
            "double hyphen name": dict(self.manifest, name="gaunt--let"),
            "trailing newline name": dict(self.manifest, name="gauntlet\n"),
            "version not string": dict(self.manifest, version=1),
            "keywords not strings": dict(self.manifest, keywords=["a", 2]),
        }
        missing_name = dict(self.manifest)
        del missing_name["name"]
        broken["missing name"] = missing_name
        for label, instance in broken.items():
            self.assertNotEqual(self.errors(instance), [], label)


class AgentPluginsMcpTest(unittest.TestCase):
    def setUp(self):
        self.config = load(helpers.PLUGIN, "mcp.json")
        self.schema = schema("mcp.schema.json")

    def errors(self, instance):
        return jsonschema_subset.validate(instance, self.schema)

    def with_server(self, **changes):
        instance = copy.deepcopy(self.config)
        server = instance["mcpServers"]["gauntlet"]
        for key, value in changes.items():
            if value is None:
                server.pop(key, None)
            else:
                server[key] = value
        return instance

    def test_mcp_json_validates(self):
        # Scenario: Schema validation
        self.assertEqual(self.errors(self.config), [])

    def test_declares_the_gauntlet_stdio_server(self):
        self.assertEqual(self.config["$schema"], MCP_SCHEMA_ID)
        server = self.config["mcpServers"]["gauntlet"]
        self.assertEqual(server["type"], "stdio")
        self.assertEqual(server["command"], "python3")
        self.assertEqual(server["args"], ["${PLUGIN_ROOT}/server/gauntlet.py"])
        script = server["args"][0].replace("${PLUGIN_ROOT}", helpers.PLUGIN)
        self.assertTrue(os.path.isfile(script))

    def test_schema_rejects_broken_configs(self):
        broken = {
            "missing type": self.with_server(type=None),
            "unknown type": self.with_server(type="pipe"),
            "empty command": self.with_server(command=""),
            "args not strings": self.with_server(args=["a", 1]),
            "cwd outside plugin roots": self.with_server(cwd="/tmp"),
            "env sets PLUGIN_ROOT": self.with_server(env={"PLUGIN_ROOT": "/x"}),
            "env value not string": self.with_server(env={"A": 1}),
            "stdio with url": self.with_server(url="http://localhost"),
            "missing $schema": {"mcpServers": self.config["mcpServers"]},
            "extra top-level key": dict(self.config, servers={}),
        }
        for label, instance in broken.items():
            self.assertNotEqual(self.errors(instance), [], label)

    def test_schema_accepts_valid_variants(self):
        good = {
            "plugin-relative cwd": self.with_server(cwd="./server"),
            "PLUGIN_ROOT cwd": self.with_server(cwd="${PLUGIN_ROOT}"),
            "env": self.with_server(env={"GAUNTLET_DEBUG": "1"}),
        }
        for label, instance in good.items():
            self.assertEqual(self.errors(instance), [], label)
        http = {"$schema": MCP_SCHEMA_ID, "mcpServers": {"x": {"type": "streamable-http", "url": "http://h"}}}
        self.assertEqual(self.errors(http), [])


class ClaudeCodePackageTest(unittest.TestCase):
    def setUp(self):
        self.marketplace = load(helpers.REPO_ROOT, ".claude-plugin", "marketplace.json")
        self.manifest = load(helpers.PLUGIN, ".claude-plugin", "plugin.json")
        self.mcp = load(helpers.PLUGIN, ".mcp.json")

    def test_marketplace_lists_the_plugin_without_a_version(self):
        self.assertEqual(self.marketplace["name"], "gauntlet")
        self.assertTrue(self.marketplace["owner"]["name"])
        entries = [p for p in self.marketplace["plugins"] if p["name"] == "gauntlet"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["source"], "./plugins/gauntlet")
        self.assertNotIn("version", entries[0])
        self.assertEqual(
            os.path.realpath(os.path.join(helpers.REPO_ROOT, entries[0]["source"])), os.path.realpath(helpers.PLUGIN)
        )

    def test_claude_manifest_fields(self):
        self.assertEqual(self.manifest["name"], "gauntlet")
        for key in ("version", "description"):
            self.assertTrue(self.manifest.get(key), key)
        self.assertTrue(self.manifest["author"].get("name"))
        self.assertEqual(self.manifest["mcpServers"], "./.mcp.json")

    def test_plugin_relative_paths_start_with_dot_slash_and_stay_inside(self):
        path = self.manifest["mcpServers"]
        self.assertTrue(path.startswith("./"))
        full = os.path.realpath(os.path.join(helpers.PLUGIN, path))
        self.assertTrue(full.startswith(os.path.realpath(helpers.PLUGIN) + os.sep))
        self.assertTrue(os.path.isfile(full))

    def test_claude_mcp_file_has_no_agent_plugins_fields(self):
        server = self.mcp["mcpServers"]["gauntlet"]
        self.assertNotIn("$schema", self.mcp)
        self.assertNotIn("type", server)

    def test_both_mcp_files_declare_the_same_server(self):
        agent_plugins = load(helpers.PLUGIN, "mcp.json")["mcpServers"]
        claude = self.mcp["mcpServers"]
        self.assertEqual(set(agent_plugins), set(claude))
        for name in agent_plugins:
            a, c = agent_plugins[name], claude[name]
            self.assertEqual(a["command"], c["command"], name)
            self.assertEqual(
                [arg.replace("${PLUGIN_ROOT}", "<root>") for arg in a["args"]],
                [arg.replace("${CLAUDE_PLUGIN_ROOT}", "<root>") for arg in c["args"]],
                name,
            )
            self.assertNotIn("${PLUGIN_ROOT}", json.dumps(c))

    def test_versions_agree(self):
        agent_plugins = load(helpers.PLUGIN, "plugin.json")
        server = helpers.load_server()
        self.assertEqual(server.VERSION, "0.1.0")
        self.assertEqual(agent_plugins["version"], server.VERSION)
        self.assertEqual(self.manifest["version"], server.VERSION)


class ServerLayoutTest(unittest.TestCase):
    def test_banner_sections_in_contract_order(self):
        with open(os.path.join(helpers.PLUGIN, "server", "gauntlet.py")) as f:
            source = f.read()
        rule = "# " + "=" * 76
        found = re.findall(r"^%s\n# (.+)\n%s$" % (re.escape(rule), re.escape(rule)), source, re.M)
        self.assertEqual(found, ["core", "worktrees", "locks", "status", "registry + MCP + CLI"])


if __name__ == "__main__":
    unittest.main()
