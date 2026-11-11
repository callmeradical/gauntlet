"""gauntlet-tools / MCP: JSON-RPC 2.0 over stdio, driven with real messages."""

import json
import os
import unittest

import helpers

TOOLS = {
    "loop_start",
    "loop_update",
    "loop_end",
    "worktree_new",
    "worktree_rm",
    "lock_acquire",
    "lock_release",
    "config_read",
    "status",
}

CONFIG = {"integration_branch": "main", "shared": ["node_modules"], "checks": [{"name": "test", "command": "true"}]}


def mcp_json_command():
    """The command the Agent Plugins mcp.json declares, with ${PLUGIN_ROOT} substituted."""
    with open(os.path.join(helpers.PLUGIN, "mcp.json")) as f:
        server = json.load(f)["mcpServers"]["gauntlet"]
    return [server["command"]] + [arg.replace("${PLUGIN_ROOT}", helpers.PLUGIN) for arg in server["args"]]


class McpTestCase(unittest.TestCase):
    def setUp(self):
        self._home = helpers.fake_home()
        self.home = self._home.__enter__()
        self.addCleanup(self._home.__exit__, None, None, None)

    def client(self, command=None):
        client = helpers.McpClient(self.home, command=command)
        self.addCleanup(client.close)
        return client


class EndToEndTest(McpTestCase):
    def test_plugin_command_serves_the_loop_lifecycle(self):
        repo = helpers.make_repo(self.home, "proj", config=CONFIG)
        client = self.client(mcp_json_command())

        init = client.request(
            "initialize",
            {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "0"}},
        )["result"]
        self.assertEqual(init["protocolVersion"], "2025-06-18")
        self.assertIn("tools", init["capabilities"])
        self.assertEqual(init["serverInfo"]["name"], "gauntlet")
        self.assertEqual(init["serverInfo"]["version"], helpers.load_server().VERSION)
        client.notify("notifications/initialized")

        tools = client.request("tools/list")["result"]["tools"]
        self.assertEqual({t["name"] for t in tools}, TOOLS)

        is_error, state = client.call("loop_start", {"loop": "pri", "repo": repo, "change": "fix-pri"})
        self.assertFalse(is_error, state)
        self.assertEqual((state["loop"], state["repo"], state["status"]), ("pri", repo, "running"))

        is_error, state = client.call(
            "loop_update", {"loop": "pri", "phase": "build", "slice": "tracer", "round": 1, "verdict": "HOLD"}
        )
        self.assertFalse(is_error, state)
        self.assertEqual(state["slices"]["tracer"], {"round": 1, "verdict": "HOLD"})

        is_error, state = client.call("loop_end", {"loop": "pri", "status": "done"})
        self.assertFalse(is_error, state)
        self.assertEqual(state["status"], "done")

        is_error, result = client.call("config_read", {"repo": repo})
        self.assertFalse(is_error, result)
        self.assertEqual(result["config"]["checks"], CONFIG["checks"])

        with open(os.path.join(self.home, ".local", "state", "gauntlet", "pri.json")) as f:
            self.assertEqual(json.load(f), state)


class ProtocolTest(McpTestCase):
    def test_initialize_echoes_the_client_protocol_version(self):
        client = self.client()
        for version in ("2024-11-05", "2025-03-26"):
            self.assertEqual(client.request("initialize", {"protocolVersion": version})["result"]["protocolVersion"], version)

    def test_notifications_get_no_reply(self):
        client = self.client()
        client.notify("notifications/initialized")
        client.notify("notifications/cancelled", {"requestId": 9})
        client.notify("no/such/notification")
        self.assertTrue(client.no_message())
        self.assertEqual(client.request("ping")["result"], {})

    def test_ping_returns_empty_result(self):
        reply = self.client().request("ping")
        self.assertEqual(reply, {"jsonrpc": "2.0", "id": 1, "result": {}})

    def test_unknown_method_is_method_not_found(self):
        reply = self.client().request("resources/list")
        self.assertEqual(reply["error"]["code"], -32601)
        self.assertNotIn("result", reply)

    def test_unparseable_input_is_parse_error(self):
        client = self.client()
        client.send_raw("{this is not json")
        reply = client.read_message()
        self.assertEqual(reply["jsonrpc"], "2.0")
        self.assertIsNone(reply["id"])
        self.assertEqual(reply["error"]["code"], -32700)
        self.assertEqual(client.request("ping")["result"], {})

    def test_invalid_utf8_input_is_parse_error_and_server_keeps_running(self):
        client = self.client()
        client.proc.stdin.buffer.write(b"\xff\xfe\n")
        client.proc.stdin.buffer.flush()
        reply = client.read_message()
        self.assertEqual(reply["jsonrpc"], "2.0")
        self.assertIsNone(reply["id"])
        self.assertEqual(reply["error"]["code"], -32700)
        self.assertEqual(client.request("ping")["result"], {})
        self.assertIsNone(client.proc.poll())

    def test_invalid_utf8_inside_a_json_string_is_parse_error(self):
        client = self.client()
        client.proc.stdin.buffer.write(b'{"jsonrpc":"2.0","id":7,"method":"ping","params":{"x":"\xff"}}\n')
        client.proc.stdin.buffer.flush()
        self.assertEqual(client.read_message()["error"]["code"], -32700)
        self.assertEqual(client.request("ping")["result"], {})

    def test_non_object_params_are_invalid_params_and_server_keeps_running(self):
        client = self.client()
        for method, params in (("initialize", ["2025-06-18"]), ("tools/list", [1]), ("tools/call", "status"), ("ping", 3)):
            reply = client.request(method, params)
            self.assertEqual(reply.get("error", {}).get("code"), -32602, (method, params, reply))
        self.assertEqual(client.request("ping")["result"], {})
        self.assertIsNone(client.proc.poll())

    def test_non_string_tool_name_is_invalid_params(self):
        reply = self.client().request("tools/call", {"name": ["status"], "arguments": {}})
        self.assertEqual(reply["error"]["code"], -32602)

    def test_trailing_newline_loop_id_is_refused_over_mcp(self):
        repo = helpers.make_repo(self.home, "proj", config=CONFIG)
        client = self.client()
        self.assertFalse(client.call("loop_start", {"loop": "pri", "repo": repo, "change": "a"})[0])
        is_error, payload = client.call("loop_start", {"loop": "pri\n", "repo": repo, "change": "b"})
        self.assertTrue(is_error)
        self.assertEqual(payload["error"], "invalid_id")
        self.assertEqual(os.listdir(os.path.join(self.home, ".local", "state", "gauntlet")), ["pri.json"])

    def test_corrupt_state_file_is_an_error_result_not_a_crash(self):
        folder = os.path.join(self.home, ".local", "state", "gauntlet")
        os.makedirs(folder)
        with open(os.path.join(folder, "x.json"), "w") as f:
            f.write("{corrupt")
        client = self.client()
        is_error, payload = client.call("loop_update", {"loop": "x", "phase": "build"})
        self.assertTrue(is_error)
        self.assertEqual(payload["error"], "unknown_loop")
        self.assertTrue(payload["reason"])
        self.assertEqual(client.request("ping")["result"], {})

    def test_non_object_message_is_invalid_request(self):
        client = self.client()
        client.send_raw("[1, 2]")
        self.assertEqual(client.read_message()["error"]["code"], -32600)

    def test_tools_list_gives_object_input_schemas(self):
        tools = self.client().request("tools/list")["result"]["tools"]
        self.assertEqual(len(tools), 9)
        for tool in tools:
            self.assertTrue(tool["description"], tool["name"])
            self.assertEqual(tool["inputSchema"]["type"], "object", tool["name"])

    def test_input_schemas_match_the_contract(self):
        tools = {t["name"]: t["inputSchema"] for t in self.client().request("tools/list")["result"]["tools"]}
        expected = {
            "loop_start": ({"loop", "repo", "change", "integration_branch"}, {"loop", "repo", "change"}),
            "loop_update": (
                {"loop", "phase", "slice", "worktree", "branch", "status", "round", "commit", "verdict", "handoff"},
                {"loop"},
            ),
            "loop_end": ({"loop", "status"}, {"loop", "status"}),
            "worktree_new": ({"loop", "slice"}, {"loop", "slice"}),
            "worktree_rm": ({"loop", "slice"}, {"loop"}),
            "lock_acquire": ({"loop"}, {"loop"}),
            "lock_release": ({"loop"}, {"loop"}),
            "config_read": ({"repo"}, {"repo"}),
            "status": (set(), set()),
        }
        for name, (props, required) in expected.items():
            schema = tools[name]
            self.assertEqual(set(schema.get("properties", {})), props, name)
            self.assertEqual(set(schema.get("required", [])), required, name)
        self.assertEqual(tools["loop_end"]["properties"]["status"]["enum"], ["done", "stopped", "failed"])
        self.assertEqual(tools["loop_update"]["properties"]["round"]["type"], "integer")

    def test_tool_refusal_is_an_error_result_with_the_error_object(self):
        client = self.client()
        reply = client.request("tools/call", {"name": "loop_update", "arguments": {"loop": "nope", "phase": "x"}})
        result = reply["result"]
        self.assertTrue(result["isError"])
        self.assertEqual(result["content"][0]["type"], "text")
        payload = json.loads(result["content"][0]["text"])
        self.assertEqual(payload["error"], "unknown_loop")
        self.assertTrue(payload["message"])

    def test_config_missing_reaches_the_client_with_its_details(self):
        repo = helpers.make_repo(self.home, "bare")
        is_error, payload = self.client().call("loop_start", {"loop": "pri", "repo": repo, "change": "c"})
        self.assertTrue(is_error)
        self.assertEqual(payload["error"], "config_missing")
        self.assertEqual(payload["ask"], ["integration_branch", "shared", "checks", "setup"])

    def test_duplicate_loop_over_mcp(self):
        # Scenario: Duplicate id
        repo = helpers.make_repo(self.home, "proj", config=CONFIG)
        client = self.client()
        self.assertFalse(client.call("loop_start", {"loop": "pri", "repo": repo, "change": "a"})[0])
        is_error, payload = client.call("loop_start", {"loop": "pri", "repo": repo, "change": "b"})
        self.assertTrue(is_error)
        self.assertEqual((payload["error"], payload["running"]), ("duplicate_loop", "pri"))

    def test_unknown_tool_is_invalid_params(self):
        reply = self.client().request("tools/call", {"name": "rm_rf", "arguments": {}})
        self.assertEqual(reply["error"]["code"], -32602)

    def test_arguments_that_break_the_input_schema_are_invalid_params(self):
        client = self.client()
        bad_calls = [
            ("loop_start", {"loop": "pri", "repo": "/x"}),
            ("loop_end", {"loop": "pri", "status": "finished"}),
            ("loop_update", {"loop": "pri", "round": "two"}),
            ("loop_update", {"loop": "pri", "colour": "red"}),
            ("config_read", {"repo": 7}),
            ("status", {"extra": True}),
        ]
        for name, args in bad_calls:
            reply = client.request("tools/call", {"name": name, "arguments": args})
            self.assertEqual(reply.get("error", {}).get("code"), -32602, (name, args, reply))

    def test_null_optional_arguments_count_as_absent(self):
        repo = helpers.make_repo(self.home, "proj", config=CONFIG)
        is_error, state = self.client().call(
            "loop_start", {"loop": "pri", "repo": repo, "change": "c", "integration_branch": None}
        )
        self.assertFalse(is_error, state)
        self.assertEqual(state["integration_branch"], "main")

    def test_stdout_carries_only_protocol_messages_even_when_git_fails(self):
        plain = os.path.join(self.home, "plain")
        os.makedirs(plain)
        client = self.client()
        is_error, payload = client.call("loop_start", {"loop": "pri", "repo": plain, "change": "c"})
        self.assertTrue(is_error)
        self.assertEqual(payload["error"], "git_failed")
        self.assertEqual(client.request("ping")["result"], {})
        self.assertTrue(client.no_message())


if __name__ == "__main__":
    unittest.main()
