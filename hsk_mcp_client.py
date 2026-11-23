# W10 最小 MCP 客户端：连上 hsk_mcp_server.py，列出并调用两个工具
# 依赖：python -m pip install "mcp[cli]"
# 运行：python hsk_mcp_client.py
#       python hsk_mcp_client.py --print-config   # 打印可粘贴到桌面客户端的 JSON
"""用官方 Python SDK 走一遍完整 MCP 流程，作为"调用证据"的可复现来源。

流程：启动子进程(stdin/stdout) → initialize 握手 → list_tools → call_tool ×2。
不依赖任何大模型，也不需要 API key；服务器只读本地 CSV。
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
from pathlib import Path

SERVER = Path(__file__).resolve().with_name("hsk_mcp_server.py")


def build_config(command: str | None = None) -> dict:
    """生成桌面客户端可直接粘贴的 mcpServers 配置。"""
    return {
        "mcpServers": {
            "hsk-tools": {
                "command": command or sys.executable,
                "args": [str(SERVER)],
            }
        }
    }


def print_config(command: str | None = None) -> None:
    print(json.dumps(build_config(command), ensure_ascii=False, indent=2))


def _result_text(result: object) -> str:
    """从 CallToolResult 里取出文本；兼容 content / structuredContent 两种返回。"""
    parts = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text is not None:
            parts.append(str(text))
    if not parts:
        structured = _get(result, "structured_content", "structuredContent", default=None)
        if structured:
            parts.append(json.dumps(structured, ensure_ascii=False))
    return "\n".join(parts).strip() or "(空结果)"


def _server_env() -> dict[str, str]:
    """只把运行必需的变量传给服务端子进程。

    不整包传 os.environ：第三方 MCP 服务端能读到你给它的每一个环境变量，
    这里刻意不把 API key 之类的秘密递过去（与第 10 讲安全红线一致）。
    """
    allow = (
        "PATH", "PYTHONPATH", "PYTHONIOENCODING", "PYTHONUTF8",
        "SYSTEMROOT", "SYSTEMDRIVE", "WINDIR",
        "TEMP", "TMP", "HOME", "USERPROFILE", "LANG", "LC_ALL",
    )
    return {k: os.environ[k] for k in allow if k in os.environ}


def _get(obj: object, *names: str, default=None):
    """兼容 mcp 1.x 的 camelCase 与 2.x 的 snake_case 字段名。"""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return default


async def _run(word: str, level: str, as_json: bool) -> int:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError:
        print(
            '未找到 MCP 客户端库。请先安装：python -m pip install "mcp[cli]"',
            file=sys.stderr,
        )
        return 2

    if not SERVER.is_file():
        print("找不到服务端脚本：%s" % SERVER, file=sys.stderr)
        return 2

    params = StdioServerParameters(
        command=sys.executable, args=[str(SERVER)], env=_server_env()
    )
    evidence: dict = {"server": str(SERVER), "command": sys.executable, "tools": []}

    started = time.perf_counter()
    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                info = _get(init, "server_info", "serverInfo", default=None)
                evidence["serverInfo"] = {
                    "name": _get(info, "name", default="?"),
                    "version": _get(info, "version", default="?"),
                }
                evidence["protocolVersion"] = _get(
                    init, "protocol_version", "protocolVersion", default="?"
                )

                listed = await session.list_tools()
                for tool in getattr(listed, "tools", []) or []:
                    schema = _get(tool, "input_schema", "inputSchema", default={}) or {}
                    evidence["tools"].append(
                        {
                            "name": tool.name,
                            "description": getattr(tool, "description", "") or "",
                            "required": schema.get("required", []),
                            "properties": list((schema.get("properties") or {}).keys()),
                        }
                    )

                calls = []
                for name, arguments in (("hsk_level", {"word": word}),
                                        ("list_by_level", {"level": level})):
                    result = await session.call_tool(name, arguments)
                    calls.append(
                        {
                            "tool": name,
                            "arguments": arguments,
                            "isError": bool(
                                _get(result, "is_error", "isError", default=False)
                            ),
                            "text": _result_text(result),
                        }
                    )
                evidence["calls"] = calls
    except Exception as exc:  # 连接失败时给出可操作的提示，而不是一屏 traceback
        print("[失败] %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        if os.environ.get("MCP_DEBUG") == "1":
            traceback.print_exc()
        print(
            "排查顺序：1) 依赖是否装好；2) 是否在 week10_MCP 目录；"
            "3) 单独运行 python hsk_mcp_server.py 看能否挂起等待连接。",
            file=sys.stderr,
        )
        return 1

    evidence["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    tool_names = {t["name"] for t in evidence["tools"]}
    ok_names = {"hsk_level", "list_by_level"}.issubset(tool_names)
    ok_call = all(not c["isError"] and c["text"] for c in evidence["calls"])
    ok = ok_names and ok_call

    if as_json:
        print(json.dumps(evidence, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    label = ("%s %s" % (
        evidence["serverInfo"]["name"], evidence["serverInfo"]["version"]
    )).strip()
    print("[1] 握手成功：server=%s，protocol=%s" % (label, evidence["protocolVersion"]))
    print("[2] 工具列表（%d 个）：%s" % (
        len(evidence["tools"]),
        "、".join(t["name"] for t in evidence["tools"]),
    ))
    for tool in evidence["tools"]:
        print("    - %s  必填参数=%s" % (tool["name"], tool["required"]))
    print("[3] 调用结果：")
    for call in evidence["calls"]:
        print("    %s(%s) -> %s" % (
            call["tool"],
            json.dumps(call["arguments"], ensure_ascii=False),
            call["text"],
        ))
    print("[通过] MCP 全链路耗时 %.3f 秒。" % evidence["elapsed_seconds"])
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="HSK MCP 最小客户端")
    parser.add_argument("--word", default="把", help="要查的词，默认「把」")
    parser.add_argument("--level", default="3", help="要列出的等级，默认「3」")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出调用证据")
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="打印桌面客户端配置 JSON（不连接服务器）",
    )
    parser.add_argument(
        "--python",
        default=None,
        help="--print-config 时写入的 python 命令，默认当前解释器绝对路径",
    )
    args = parser.parse_args()

    if args.print_config:
        print_config(args.python)
        return 0
    return asyncio.run(_run(args.word, args.level, args.json))


if __name__ == "__main__":
    raise SystemExit(main())
