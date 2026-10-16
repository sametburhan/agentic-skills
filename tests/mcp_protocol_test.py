"""Modüler sunucuların stdio MCP el sıkışmasını ve araç keşfini doğrular."""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def list_tool_names(script: Path):
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(script)],
        env={"PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            response = await session.list_tools()
            return {tool.name for tool in response.tools}


async def main():
    expected = {
        ROOT / "tools" / "system_tools" / "server.py": {
            "run_powershell", "get_system_environment_info", "python_run_code", "python_run_file",
            "python_create_venv", "python_install_packages", "python_install_requirements",
            "python_environment_info", "get_current_datetime", "convert_datetime",
            "calculate_datetime", "datetime_difference",
        },
        ROOT / "tools" / "git_tools" / "server.py": {"git_status", "git_diff", "git_log", "git_add"},
        ROOT / "tools" / "web_tools" / "search_server.py": {
            "web_search", "fetch_web_page_text", "observe_web_page", "research_web",
            "websocket_connect", "websocket_send", "websocket_receive", "websocket_ping",
            "websocket_close", "websocket_list_connections", "websocket_request",
        },
    }
    for script, required in expected.items():
        names = await asyncio.wait_for(list_tool_names(script), timeout=30)
        missing = required - names
        if missing:
            raise AssertionError(f"{script.name}: eksik araçlar: {sorted(missing)}")
        print(f"[OK] {script.parent.name}: {len(names)} araç")


if __name__ == "__main__":
    asyncio.run(main())
