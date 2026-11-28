# Local MCP stdio integration

[English](mcp.md) · [简体中文](mcp.zh-CN.md)

This optional server exposes one read-only tool, `meshassert_verify`, through the [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk). It runs the existing MeshAssert CLI locally. The ordinary CLI and `python -B verify.py` still need only Python and Node.js, with no MCP package installation.

## Install and check

Use Python 3.11 or newer and Node.js on PATH (CI uses Python 3.11 and Node.js 22). From the repository root, create an environment outside the checkout. Installation needs package-index access; verification then runs locally without network requests from the tool.

PowerShell:

```powershell
$meshassertEnv = Join-Path $env:USERPROFILE '.venvs/meshassert-mcp'
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

## Connect Codex

Use a permanent checkout or extracted release folder and a persistent Python environment. Add this table to `~/.codex/config.toml`, replacing all three paths with your own. If `meshassert` is already configured, update that table instead of adding a duplicate; preserve the other settings.

```toml
[mcp_servers.meshassert]
command = "C:/Users/YOUR_NAME/.venvs/meshassert-mcp/Scripts/python.exe"
args = ["-B", "C:/cad-tools/meshassert/server.py"]
cwd = "C:/cad-tools/meshassert"
```

On Linux/macOS, use the environment's `bin/python` and absolute repository paths. Set `cwd` to a directory that will remain available. A deleted chat worktree can otherwise prevent the server from starting even when Python and `server.py` use valid absolute paths.

The desktop client and CLI share this configuration. Save it and restart the desktop client before checking that `meshassert_verify` is available. `codex mcp get meshassert` confirms registration; an actual tool call confirms that it works. [Official Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp)

Node.js must also be visible to the launched server. On Windows, find its location with `(Get-Command node).Source`. If the desktop client's inherited PATH does not include it, add a server-specific PATH using your actual Node and Windows directories, for example:

```toml
[mcp_servers.meshassert.env]
PATH = "C:/Program Files/nodejs;C:/Windows/System32;C:/Windows"
```

Use absolute paths for the four input arguments below. First ask Codex to call `meshassert_verify` on `fixtures/ribbed-bracket/expected.json`, `ribbed_bracket.stl` and `ribbed_bracket.glb` under your permanent repository, with `stl_unit` set to `mm`. Then repeat with `ribbed_bracket_tall.glb`: the expected result is `1/fail` on GLB CAD Z, not a transport error.

## Configure another client

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

## Recorded Codex trial on a real product CAD model

On 2026-11-28, the Codex desktop client on Windows directly called the registered MCP tool for a Hammond 1590B enclosure. The nominal STL and GLB measured **112.400 × 31.000 × 60.500 mm** in CAD X/Y/Z, rounded to three decimals. The source STEP uses X = length, Y = height, Z = width. The nominal values came from the [manufacturer drawing](https://www.hammfg.com/files/parts/pdf/1590B.pdf); the **±0.10 mm** threshold was a digital-export comparison threshold, not a manufacturer-specified physical tolerance.

| Trial | Exit / status | Per-file result |
| --- | --- | --- |
| Nominal pair | `0/pass` | Both exports pass |
| Existing 1000× GLB control | `1/fail` | STL passes; GLB fails X/Y/Z |
| Millimetre STL declared as metres | `1/fail` | STL fails X/Y/Z; GLB passes |
| Y and Z nominal values swapped | `1/fail` | Both exports fail Y/Z |
| Broken GLB | `2/invalid` | STL result retained; GLB reported invalid |

All five were normal MCP results, and the original input hashes remained unchanged. [Measured reports, source links and hashes](evidence/hammond-1590b-mcp.json) record the direct calls with local file paths reduced to basenames. The third-party CAD files are not included in this repository. This real-product example is not customer production acceptance.

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

Local tests verify the official SDK's stdio transport, schema, both real CAD fixtures, complete CLI-report equality, repeatability, input hashes, and paths from an unrelated working directory. The separate Codex trial above records one Windows desktop acceptance run; other clients and protocol versions still need their own trial. The trial prints the protocol actually negotiated by your installed SDK. GitHub Actions also defines Ubuntu and Windows MCP checks; consult the run before claiming hosted CI passed.
