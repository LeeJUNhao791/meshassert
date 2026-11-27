"""Exercise the optional server through the official MCP stdio client."""

import asyncio
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from mcp import Client, StdioServerParameters


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server.py"
CLI = ROOT / "meshassert.py"
PLATE = ROOT / "fixtures/mounting-plate"
BRACKET = ROOT / "fixtures/ribbed-bracket"


class MeshAssertStdioTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="meshassert mcp ")
        self.addCleanup(directory.cleanup)
        self.cwd = Path(directory.name)
        self.paths = {
            "expect_path": "--contract data.json",
            "stl_path": "--plate data.stl",
            "stl_unit": "mm",
            "glb_path": "--preview data.glb",
        }
        for key, source in (
            ("expect_path", PLATE / "expected.json"),
            ("stl_path", PLATE / "mounting_plate.stl"),
            ("glb_path", PLATE / "mounting_plate.glb"),
        ):
            shutil.copyfile(source, self.cwd / self.paths[key])

    def client(self, server=SERVER):
        self.assertTrue(server.is_file(), "MCP server entry point is missing")
        return Client(StdioServerParameters(
            command=sys.executable, args=["-B", str(server)], cwd=self.cwd,
        ))

    async def check(self, client, code, status, **overrides):
        paths = {**self.paths, **overrides}
        inputs = [self.cwd / paths[key] for key in ("expect_path", "stl_path", "glb_path")]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs if path.is_file()}
        direct = await asyncio.to_thread(
            subprocess.run,
            [sys.executable, "-I", str(CLI), f"--expect={paths['expect_path']}",
             f"--stl={paths['stl_path']}", f"--stl-unit={paths['stl_unit']}", f"--glb={paths['glb_path']}"],
            cwd=self.cwd, stdin=subprocess.DEVNULL, capture_output=True,
        )
        self.assertEqual(direct.returncode, code, direct.stderr or direct.stdout)
        self.assertFalse(direct.stderr)
        report = json.loads(direct.stdout)
        self.assertEqual(report["status"], status)
        for _ in range(2):
            result = await client.call_tool("meshassert_verify", paths)
            self.assertFalse(result.is_error, result.content)
            self.assertEqual(result.structured_content, {"exit_code": code, "report": report})
        self.assertEqual(before, {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before})
        return report

    async def test_lists_only_one_tool_with_required_schema_and_annotations(self):
        async with self.client() as client:
            tools = (await client.list_tools()).tools
            self.assertEqual([tool.name for tool in tools], ["meshassert_verify"])
            schema = tools[0].input_schema
            self.assertEqual(set(schema["properties"]), set(self.paths))
            self.assertEqual(set(schema["required"]), set(self.paths))
            self.assertEqual(schema["properties"]["stl_unit"]["enum"], ["mm", "m"])
            for key in self.paths:
                self.assertEqual(schema["properties"][key]["type"], "string")
            self.assertTrue(tools[0].annotations.read_only_hint)
            self.assertFalse(tools[0].annotations.open_world_hint)

    async def test_preserves_both_real_cad_fixture_reports(self):
        async with self.client() as client:
            for folder, name in ((PLATE, "mounting_plate"), (BRACKET, "ribbed_bracket")):
                with self.subTest(fixture=name):
                    await self.check(client, 0, "pass", expect_path=str(folder / "expected.json"),
                                     stl_path=str(folder / f"{name}.stl"), glb_path=str(folder / f"{name}.glb"))

    async def test_preserves_stl_and_glb_dimension_failures(self):
        async with self.client() as client:
            for key, source in (("stl_path", PLATE / "controls/wide.stl"),
                                ("glb_path", PLATE / "controls/thick.glb")):
                with self.subTest(asset=key):
                    target = self.cwd / source.name
                    shutil.copyfile(source, target)
                    await self.check(client, 1, "fail", **{key: target.name})
            await self.check(client, 1, "fail", expect_path=str(BRACKET / "expected.json"),
                             stl_path=str(BRACKET / "ribbed_bracket.stl"),
                             glb_path=str(BRACKET / "ribbed_bracket_tall.glb"))

    async def test_preserves_invalid_assets_contract_and_precedence(self):
        async with self.client() as client:
            for key, filename in (("stl_path", "broken.stl"), ("glb_path", "broken.glb"),
                                  ("expect_path", "broken.json")):
                with self.subTest(input=key):
                    (self.cwd / filename).write_bytes(b"invalid input")
                    await self.check(client, 2, "invalid", **{key: filename})
            shutil.copyfile(PLATE / "controls/wide.stl", self.cwd / "wide.stl")
            await self.check(client, 2, "invalid", stl_path="wide.stl", glb_path="broken.glb")
            await self.check(client, 2, "invalid", stl_path="missing.stl")

    async def test_handles_spaces_switch_like_paths_and_unrelated_working_directory(self):
        self.assertNotEqual(self.cwd, ROOT)
        async with self.client() as client:
            await self.check(client, 0, "pass")
            await self.check(client, 0, "pass", **{
                key: str(self.cwd / value) for key, value in self.paths.items() if key != "stl_unit"
            })
            await self.check(client, 1, "fail", stl_unit="m")

    async def test_rejects_missing_inputs_and_unknown_units(self):
        async with self.client() as client:
            for key in self.paths:
                with self.subTest(missing=key):
                    result = await client.call_tool("meshassert_verify", {
                        name: value for name, value in self.paths.items() if name != key
                    })
                    self.assertTrue(result.is_error, result)
                    self.assertIsNone(result.structured_content)
            result = await client.call_tool("meshassert_verify", {**self.paths, "stl_unit": "cm"})
            self.assertTrue(result.is_error, result)
            self.assertIsNone(result.structured_content)

    async def test_reports_cli_process_and_protocol_errors_without_a_report(self):
        self.assertTrue(SERVER.is_file(), "MCP server entry point is missing")
        server = self.cwd / "server.py"
        shutil.copyfile(SERVER, server)
        fake_cli = self.cwd / "meshassert.py"
        failures = (
            (None, "valid JSON"),
            ("print('not JSON')", "valid JSON"),
            ("print('[]')", "Unexpected MeshAssert CLI response"),
            ("print('{\"status\":\"fail\"}')", "Unexpected MeshAssert CLI response"),
            ("print('{\"status\":\"invalid\"}'); raise SystemExit(3)", "Unexpected MeshAssert CLI response"),
        )
        for source, message in failures:
            with self.subTest(source=source):
                if source is not None:
                    fake_cli.write_text(source, encoding="utf-8")
                async with self.client(server) as client:
                    result = await client.call_tool("meshassert_verify", self.paths)
                    self.assertTrue(result.is_error, result)
                    self.assertIsNone(result.structured_content)
                    self.assertIn(message, " ".join(item.text for item in result.content))

    async def test_reports_unlaunchable_path_as_a_tool_error(self):
        async with self.client() as client:
            result = await client.call_tool("meshassert_verify", {**self.paths, "stl_path": "\0"})
            self.assertTrue(result.is_error, result)
            self.assertIsNone(result.structured_content)
            self.assertIn("Could not start MeshAssert CLI", " ".join(item.text for item in result.content))


class LaunchErrorTest(unittest.TestCase):
    def test_reports_os_launch_error(self):
        import server
        from mcp.server.mcpserver.exceptions import ToolError

        with patch.object(server.subprocess, "run", side_effect=OSError("launch denied")):
            with self.assertRaisesRegex(ToolError, "Could not start MeshAssert CLI: launch denied"):
                server.meshassert_verify("expected.json", "part.stl", "mm", "part.glb")
