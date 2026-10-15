#!/usr/bin/env python3
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

BUN = subprocess.check_output(["mise", "which", "bun"], text=True).strip()
SMOKE = pathlib.Path(__file__).resolve().parents[2] / "home/dot_local/bin/executable_omp-agent-smoke"

# The two native prompt forms naming an MCP proxy's source (18.10.4): an xd:// route and a Tool Inventory label.
def route(tool, name):
    return f"- {json.dumps(tool)} → `xd://{name}`"


def label(server, tool, name):
    return f"- {server}/{tool}: `{name}`"


MAC = [route("click", "mcp__mac_click"), route("see", "mcp__mac_see")]


class McpOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.tmp.name)
        shutil.copy(SMOKE, root / "smoke.ts")
        cls.runner = root / "run.ts"
        cls.runner.write_text(
            'import { mcpOwnership } from "./smoke.ts";\n'
            "const c = JSON.parse(await Bun.stdin.text());\n"
            "console.log(JSON.stringify(mcpOwnership(c.servers, c.tools, c.prompt)));\n"
        )

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def owners(self, servers, lines, tools=()):
        prompt = "# Tool Inventory\n- Read: `read`\n" + "\n".join(lines) + "\n"
        case = {"servers": servers, "tools": ["read", "bash", *tools], "prompt": prompt}
        out = subprocess.run([BUN, str(self.runner)], input=json.dumps(case), capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def test_owned_routes_and_labels_pass(self):
        self.assertEqual(self.owners(["mac"], MAC), [])
        self.assertEqual(self.owners(["Mac"], MAC), [])
        self.assertEqual(self.owners(["mac"], [label("mac", "click", "mcp__mac_click")], ["mcp__mac_click"]), [])

    def test_prefix_sharing_server_is_unpredicted(self):
        # Server `mac_evil` mints mcp__mac_evil_write, which shares the predicted `mac` prefix.
        fails = self.owners(["mac"], [*MAC, route("write", "mcp__mac_evil_write")])
        self.assertEqual(fails, ["unpredicted MCP tools [mcp__mac_evil_write]"])
        fails = self.owners(["mac"], [label("mac_evil", "write", "mcp__mac_evil_write")], ["mcp__mac_evil_write"])
        self.assertEqual(fails, ["unpredicted MCP tools [mcp__mac_evil_write]", "predicted MCP servers with no tools [mac]"])

    def test_proxy_without_source_line_fails(self):
        fails = self.owners(["mac"], MAC, ["mcp__mac_evil_write"])
        self.assertEqual(fails, ["MCP tools with no route or inventory label, owner unproven [mcp__mac_evil_write]"])

    def test_lossy_or_shared_mints_are_ambiguous(self):
        # A stripped `<server>_` tool prefix hides where the server part ends.
        self.assertEqual(self.owners(["mac"], [*MAC, route("mac_x_y", "mcp__mac_x_y")]), ["MCP tools with ambiguous owner [mcp__mac_x_y]"])
        # Two predicted servers that sanitize alike own every proxy jointly.
        fails = self.owners(["mac", "MAC"], MAC)
        self.assertEqual(fails[0], "MCP tools with ambiguous owner [mcp__mac_click, mcp__mac_see]")
        # A `/` in the label's tool part could end a longer server name.
        fails = self.owners(["mac"], [*MAC, label("mac", "evil/write", "mcp__mac_evil_write")], ["mcp__mac_evil_write"])
        self.assertEqual(fails, ["MCP tools with ambiguous owner [mcp__mac_evil_write]"])

    def test_capped_name_is_ambiguous(self):
        tool = "t" * 80
        fails = self.owners(["mac"], [*MAC, route(tool, "mcp__mac_" + tool)])
        self.assertEqual(fails, ["unpredicted MCP tools [mcp__mac_" + tool + "]"])
        rc = subprocess.run(
            [BUN, "-e", f'console.log(Bun.hash("mcp__mac_{tool}").toString(36).slice(0, 8))'], capture_output=True, text=True, check=True
        )
        capped = f"mcp__mac_{tool}"[: 64 - 9] + "_" + rc.stdout.strip()
        self.assertEqual(self.owners(["mac"], [*MAC, route(tool, capped)]), [f"MCP tools with ambiguous owner [{capped}]"])

    def test_predicted_server_without_tools_and_no_prediction(self):
        self.assertEqual(self.owners(["mac"], []), ["predicted MCP servers with no tools [mac]"])
        self.assertEqual(self.owners([], MAC), ["unpredicted MCP tools [mcp__mac_click, mcp__mac_see]"])


class ServingIdentityTests(unittest.TestCase):
    def test_aborted_message_from_another_model_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            shutil.copy(SMOKE, root / "smoke.ts")
            (root / "run.ts").write_text(
                'import { checkChild } from "./smoke.ts";\n'
                "const c = JSON.parse(await Bun.stdin.text());\n"
                "console.log(JSON.stringify(checkChild(c.pred, c.result, c.sessions)));\n"
            )
            tools = ["read", "grep", "glob", "web_search", "yield"]
            pred = {"name": "architect", "source": "user", "path": "", "declared": tools, "callable": tools,
                    "conditional": [], "mcp": [], "model": "openai-codex/gpt-6.1-sol", "thinking": "xhigh"}
            result = {"id": "C", "agent": "architect", "agentSource": "user", "exitCode": 0,
                      "resolvedModelIdentity": "openai-codex/gpt-6.1-sol", "resolvedThinkingLevel": "xhigh"}

            def check(aborted_model):
                sessions = root / f"sessions-{aborted_model}"
                sessions.mkdir()
                entries = [{"type": "session_init", "agent": "architect", "tools": tools, "systemPrompt": ""},
                           {"type": "model_change", "model": "openai-codex/gpt-6.1-sol"},
                           {"type": "thinking_level_change", "thinkingLevel": "xhigh"},
                           {"type": "message", "message": {"role": "assistant", "provider": "openai-codex", "model": aborted_model, "stopReason": "aborted"}},
                           {"type": "message", "message": {"role": "assistant", "provider": "openai-codex", "model": "gpt-6.1-sol", "stopReason": "stop"}}]
                (sessions / "C.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\n")
                case = {"pred": pred, "result": result, "sessions": str(sessions)}
                out = subprocess.run([BUN, str(root / "run.ts")], input=json.dumps(case), capture_output=True, text=True, check=True)
                return json.loads(out.stdout)

            self.assertEqual(check("gpt-6.1-sol"), [])
            self.assertIn("assistant served by openai-codex/gpt-6-astra predicted openai-codex/gpt-6.1-sol", check("gpt-6-astra"))


if __name__ == "__main__":
    unittest.main()
