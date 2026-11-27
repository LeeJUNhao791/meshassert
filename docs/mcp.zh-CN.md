# 本地 MCP stdio 试点

[English](mcp.md) · [简体中文](mcp.zh-CN.md)

这个可选服务通过[官方 Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) 提供唯一的只读工具 `meshassert_verify`，在本地调用现有 MeshAssert 命令行检查器。普通命令行和 `python -B verify.py` 仍只需要 Python 与 Node.js，无需安装 MCP 包。

## 安装与验证

使用 Python 3.11 或更新版本，并确保 Node.js 在 PATH 中可用（CI 使用 Python 3.11 与 Node.js 22）。从仓库根目录执行以下命令，将环境建在仓库之外。安装依赖需要访问包索引；安装后的工具在本地检查，不发起网络请求。

PowerShell：

```powershell
$meshassertEnv = Join-Path $env:TEMP 'meshassert-mcp-venv'
python -m venv $meshassertEnv
$meshassertPython = Join-Path $meshassertEnv 'Scripts/python.exe'
& $meshassertPython -m pip install -r requirements-mcp.txt
& $meshassertPython -B -m unittest discover -s tests -v
python -B verify.py
```

Linux/macOS：

```sh
python3 -m venv ~/.venvs/meshassert-mcp
~/.venvs/meshassert-mcp/bin/python -m pip install -r requirements-mcp.txt
~/.venvs/meshassert-mcp/bin/python -B -m unittest discover -s tests -v
python3 -B verify.py
```

`requirements-mcp.txt` 固定使用 `mcp==2.3.0`。用该环境的 Python 和 `server.py` 的绝对路径启动服务。服务等待标准输入中的 MCP 消息，标准输出专用于协议，诊断信息写入标准错误。

## 配置客户端

对于使用 `mcpServers` 配置对象的客户端，启动配置如下：

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

将两个路径替换成自己的绝对路径；Linux/macOS 使用环境中的 `bin/python`。配置容器应按实际客户端的格式调整，并确保启动的进程能找到 Node.js。不确定客户端的工作目录时，请使用绝对输入路径。相对路径以服务启动时的工作目录为基准，适配层保留该目录；它们不以 `server.py` 所在目录为基准。

工具的四个参数均为必填项：

```json
{
  "expect_path": "C:/cad/expected.json",
  "stl_path": "C:/cad/part.stl",
  "stl_unit": "mm",
  "glb_path": "C:/cad/part.glb"
}
```

`stl_unit` 只能是 `mm` 或 `m`。路径允许包含空格或以 `--` 开头；它们直接作为参数值传递，不经过 shell。

## 用官方客户端试用

将以下内容保存为仓库之外的临时文件 `meshassert_trial.py`：

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

在仓库根目录选择对应命令运行：

```powershell
& $meshassertPython "$env:TEMP/meshassert_trial.py" (Get-Location).Path
```

```sh
~/.venvs/meshassert-mcp/bin/python /tmp/meshassert_trial.py "$PWD"
```

应当只列出一个工具。正常支架返回 `exit_code: 0`、`report.status: pass`。加高的 GLB 返回 `exit_code: 1`、`report.status: fail`，并在该 GLB 的 `out_of_tolerance_axes` 中列出 CAD Z。结果中的 `report` 是完整解析后的命令行 JSON，包括各文件路径和测量结果。

## 结果与边界

命令行的 `0/pass`、`1/fail`、`2/invalid` 均为正常 MCP 工具结果，`is_error=False`，结构化内容为 `{exit_code, report}`。无效模型或尺寸约定仍返回 `invalid` 报告。缺少必填参数、不支持的 STL 单位、进程无法启动或命令行返回异常内容时，返回 MCP 工具错误，不提供结构化报告。适配层不会把进程错误变成尺寸检查通过。

工具只读取本地文件并运行内置检查器，不修改输入、不修复几何，也不提供 HTTP 接口。检查范围仍限于 CAD 各轴的整体跨度；孔尺寸、拓扑、镜像、实物制造质量及设备运行不在验证范围内。stdio 服务具有当前用户的本地文件权限；只读注解不会限制客户端能够传入的文件路径。只应连接你信任其访问这些文件的客户端。

本地测试验证官方 SDK 的 stdio 传输、参数约束、两组真实 CAD 示例、与命令行完整报告一致、可重复性、输入哈希以及无关工作目录中的路径。这不代表某个桌面应用的界面或全部 MCP 协议版本已经通过兼容性验证。试用命令会打印当前 SDK 实际协商的协议。GitHub Actions 另定义了 Ubuntu 与 Windows MCP 检查，托管 CI 是否通过应以实际运行记录为准。
