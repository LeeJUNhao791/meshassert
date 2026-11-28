# 本地 MCP stdio 接入

[English](mcp.md) · [简体中文](mcp.zh-CN.md)

这个可选服务通过[官方 Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk) 提供唯一的只读工具 `meshassert_verify`，在本地调用现有 MeshAssert 命令行检查器。普通命令行和 `python -B verify.py` 仍只需要 Python 与 Node.js，无需安装 MCP 包。

## 安装与验证

使用 Python 3.11 或更新版本，并确保 Node.js 在 PATH 中可用（CI 使用 Python 3.11 与 Node.js 22）。从仓库根目录执行以下命令，将环境建在仓库之外。安装依赖需要访问包索引；安装后的工具在本地检查，不发起网络请求。

PowerShell：

```powershell
$meshassertEnv = Join-Path $env:USERPROFILE '.venvs/meshassert-mcp'
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

## 接入 Codex

使用长期保留的仓库或解压后的发布目录，以及持久的 Python 环境。在 `~/.codex/config.toml` 中添加下表，把三个路径替换为自己的绝对路径。若已有 `meshassert` 配置，请修改原表，避免重复；保留其他设置。

```toml
[mcp_servers.meshassert]
command = "C:/Users/YOUR_NAME/.venvs/meshassert-mcp/Scripts/python.exe"
args = ["-B", "C:/cad-tools/meshassert/server.py"]
cwd = "C:/cad-tools/meshassert"
```

Linux/macOS 使用环境中的 `bin/python` 和仓库的绝对路径。`cwd` 必须指向仍会保留的目录。若继承了已被清理的聊天工作目录，即使 Python 和 `server.py` 的绝对路径正确，服务仍可能无法启动。

桌面端与 CLI 共用这份配置。保存后重启桌面客户端，确认能找到 `meshassert_verify`。`codex mcp get meshassert` 只确认配置已登记；实际工具调用才确认能够工作。[Codex 官方 MCP 配置说明](https://learn.chatgpt.com/docs/extend/mcp)

启动的服务还必须能够找到 Node.js。Windows 可用 `(Get-Command node).Source` 查看位置。若桌面端继承的 PATH 没有包含它，可单独为该服务配置 PATH，替换为实际的 Node 与 Windows 目录，例如：

```toml
[mcp_servers.meshassert.env]
PATH = "C:/Program Files/nodejs;C:/Windows/System32;C:/Windows"
```

下面四个输入参数均使用绝对路径。先让 Codex 实际调用 `meshassert_verify`，检查长期保留仓库中 `fixtures/ribbed-bracket` 下的 `expected.json`、`ribbed_bracket.stl` 和 `ribbed_bracket.glb`，`stl_unit` 设为 `mm`。再换成 `ribbed_bracket_tall.glb` 重试：预期是 GLB 的 CAD Z 返回 `1/fail`，这不是传输错误。

## 配置其他客户端

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

## 真实产品 CAD 的 Codex 调用记录

2026-11-28，Windows 上的 Codex 桌面端通过已注册的 MCP 工具直接检查了 Hammond 1590B 外壳。正常 STL 与 GLB 的 CAD X/Y/Z 均约为 **112.400 × 31.000 × 60.500 mm**，显示至小数点后三位。原 STEP 的 X 为长、Y 为高、Z 为宽。标称值来自[厂家图纸](https://www.hammfg.com/files/parts/pdf/1590B.pdf)；本例 **±0.10 mm** 只是数字导出比对阈值，不是厂家规定的实物制造公差。

| 检查 | 退出码 / 状态 | 分文件结果 |
| --- | --- | --- |
| 正常模型对 | `0/pass` | 两份导出均通过 |
| 已有的 1000 倍 GLB 对照 | `1/fail` | STL 通过；GLB 的 X/Y/Z 超差 |
| 将毫米 STL 声明为米 | `1/fail` | STL 的 X/Y/Z 超差；GLB 通过 |
| 将 Y、Z 标称值对调 | `1/fail` | 两份导出的 Y/Z 超差 |
| 损坏的 GLB | `2/invalid` | 保留 STL 结果；GLB 报告无效 |

五项均返回正常 MCP 结果，原输入文件哈希未变。[实测报告、来源与哈希](evidence/hammond-1590b-mcp.json) 记录了实际调用，公开版本将本地路径缩为文件名。仓库不包含第三方 CAD 文件。这是公开真实产品的案例，不代表客户生产项目已经验收。

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

本地测试验证官方 SDK 的 stdio 传输、参数约束、两组真实 CAD 示例、与命令行完整报告一致、可重复性、输入哈希以及无关工作目录中的路径。上面的 Codex 记录另行验证了一次 Windows 桌面端调用；其他客户端与协议版本仍需单独试用。试用命令会打印当前 SDK 实际协商的协议。GitHub Actions 另定义了 Ubuntu 与 Windows MCP 检查，托管 CI 是否通过应以实际运行记录为准。
