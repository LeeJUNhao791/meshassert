# Local MCP stdio pilot

[English](mcp.md) · [简体中文](mcp.zh-CN.md)

This optional server exposes one read-only tool, `meshassert_verify`, through the [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk). It runs the existing MeshAssert CLI locally. The ordinary CLI and `python -B verify.py` still need only Python and Node.js, with no MCP package installation.

## Install and check

Use Python 3.11 or newer and Node.js on PATH (CI uses Python 3.11 and Node.js 22). From the repository root, create an environment outside the checkout. Installation needs package-index access; verification then runs locally without network requests from the tool.

PowerShell:

```powershell
$meshassertEnv = Join-Path $env:TEMP 'meshassert-mcp-venv'
python -m venv $meshassertEnv
$meshassertPython = Join-Path $meshassertEnv 'Scripts/python.exe'
& $meshassertPython -m pip install -r requirements-mcp.txt
& $meshassertPython -B -m unittest discover -s tests -v
python -B verify.py
```

Linux/macOS:

```sh
python3 -m venv ~/.venvs/meshassert-mcp
~/.venvs/meshassert-mcp/bin/python -m pip install -r requirements-mcp.txt
~/.venvs/meshassert-mcp/bin/python -B -m unittest discover -s tests -v
python3 -B verify.py
```

`requirements-mcp.txt` pins `mcp==2.3.0`. Start the server with that environment's Python and an absolute path to `server.py`. It waits for MCP messages on stdin; stdout is reserved for the protocol. Diagnostics go to stderr.

## Configure a client

For clients that use an `mcpServers` settings object, the launch settings are:

```json
{
  "mcpServers": {
    "meshassert": {
      "command": "C:/path/to/meshassert-mcp-venv/Scripts/python.exe",
      "args": ["-B", "C:/path/to/meshassert/server.py"]
    }
  }
}
```

Replace both paths with your absolute paths; on Linux/macOS use the environment's `bin/python`. Adapt the settings container to your client's format. Ensure Node.js is available to the launched process. Use absolute input paths when the client's working directory is unknown. Relative paths resolve against the server's launch working directory, which the adapter preserves; they are not relative to `server.py`.

All four tool arguments are required:

```json
{
  "expect_path": "C:/cad/expected.json",
  "stl_path": "C:/cad/part.stl",
  "stl_unit": "mm",
  "glb_path": "C:/cad/part.glb"
}
```

`stl_unit` is exactly `mm` or `m`. Paths may contain spaces or start with `--`; they are passed as values without a shell.

## Try the official client

Save the following as a temporary `meshassert_trial.py` outside the checkout:

```python
import asyncio
import json
from pathlib import Path
import sys

from mcp import Client, StdioServerParameters

repo = Path(sys.argv[1]).resolve()

async def main():
    async with Client(StdioServerParameters(
        command=sys.executable, args=["-B", str(repo / "server.py")], cwd=repo,
    )) as client:
        print("Tools:", [tool.name for tool in (await client.list_tools()).tools])
        print("Protocol:", client.protocol_version)
        for glb in ("ribbed_bracket.glb", "ribbed_bracket_tall.glb"):
            result = await client.call_tool("meshassert_verify", {
                "expect_path": "fixtures/ribbed-bracket/expected.json",
                "stl_path": "fixtures/ribbed-bracket/ribbed_bracket.stl",
                "stl_unit": "mm",
                "glb_path": "fixtures/ribbed-bracket/" + glb,
            })
            assert not result.is_error, result.content
            print(json.dumps(result.structured_content, indent=2))

asyncio.run(main())
```

From the repository root, run one of:

```powershell
& $meshassertPython "$env:TEMP/meshassert_trial.py" (Get-Location).Path
```

```sh
~/.venvs/meshassert-mcp/bin/python /tmp/meshassert_trial.py "$PWD"
```

Expect exactly one tool. The nominal bracket returns `exit_code: 0` and `report.status: pass`. The taller GLB returns `exit_code: 1`, `report.status: fail`, and CAD Z in that GLB's `out_of_tolerance_axes`. The result's `report` is the entire parsed CLI JSON, including per-asset paths and measurements.

## Results and limits

CLI exits `0/pass`, `1/fail`, and `2/invalid` are all normal MCP tool results with `is_error=False` and structured `{exit_code, report}`. A bad asset or dimension contract remains an `invalid` report. Missing required arguments, an unsupported STL unit, a process launch failure, or an unexpected CLI response instead produces an MCP tool error with no structured report. The adapter never turns a process failure into a passing dimension check.

The tool reads local files and runs the bundled checkers; it does not modify the inputs, fix geometry, or offer HTTP access. Only the existing overall CAD-axis spans are checked. Hole dimensions, topology, mirroring, manufactured-part quality, and physical-device behavior remain outside the check's scope. The stdio server has the local user's file permissions; read-only annotations do not restrict which local paths a client can supply. Connect only a client you trust with those files.

Local tests verify the official SDK's stdio transport, schema, both real CAD fixtures, complete CLI-report equality, repeatability, input hashes, and paths from an unrelated working directory. They do not establish compatibility with any particular desktop application's UI or every MCP protocol version. The trial prints the protocol actually negotiated by your installed SDK. GitHub Actions also defines Ubuntu and Windows MCP checks; consult the run before claiming hosted CI passed.
