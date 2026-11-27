"""Optional local stdio MCP adapter for the existing MeshAssert CLI."""

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Literal

from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations


CLI = Path(__file__).resolve().parent / "meshassert.py"
mcp = MCPServer("meshassert")


@dataclass
class VerificationResult:
    exit_code: int
    report: dict[str, Any]


@mcp.tool(annotations=ToolAnnotations(read_only_hint=True, open_world_hint=False))
def meshassert_verify(
    expect_path: str, stl_path: str, stl_unit: Literal["mm", "m"], glb_path: str,
) -> VerificationResult:
    """Check local STL and Y-up GLB overall CAD-axis spans against a JSON contract.

    All paths are local; relative paths use the server's launch working directory.
    Return the CLI exit code and complete JSON report, including fail and invalid.
    """
    try:
        completed = subprocess.run(
            [sys.executable, "-I", str(CLI), f"--expect={expect_path}", f"--stl={stl_path}",
             f"--stl-unit={stl_unit}", f"--glb={glb_path}"],
            stdin=subprocess.DEVNULL, capture_output=True,
        )
    except (OSError, ValueError) as error:
        raise ToolError(f"Could not start MeshAssert CLI: {error}") from error

    try:
        report = json.loads(completed.stdout)
    except (ValueError, RecursionError) as error:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ToolError(
            f"MeshAssert CLI did not return valid JSON (exit {completed.returncode}). {detail}"
        ) from error
    if (completed.returncode not in (0, 1, 2) or not isinstance(report, dict)
            or report.get("status") != ("pass", "fail", "invalid")[completed.returncode]):
        raise ToolError(f"Unexpected MeshAssert CLI response (exit {completed.returncode}).")
    return VerificationResult(exit_code=completed.returncode, report=report)


if __name__ == "__main__":
    mcp.run(transport="stdio")
