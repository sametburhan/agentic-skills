"""Modüler sistem MCP sunucusu; uygulamayı birleşik çekirdekten paylaşır."""

import sys
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unified_server as core

mcp = FastMCP("System-Dev-Tools")


@mcp.tool()
def run_powershell(command: str, cwd: Optional[str] = None, timeout_seconds: int = 60) -> str:
    """PowerShell komutunu etkileşimsiz, UTF-8 çıktı ve kesin zaman aşımıyla çalıştırır."""
    return core.run_powershell(command, cwd, timeout_seconds)


@mcp.tool()
def run_wsl(
    command: str,
    distro: Optional[str] = "Ubuntu",
    working_dir: Optional[str] = None,
    timeout_seconds: int = 60,
) -> str:
    """Bir WSL dağıtımında Bash komutu çalıştırır."""
    return core.run_wsl(command, distro, working_dir, timeout_seconds)


@mcp.tool()
def get_wsl_status() -> str:
    """Yüklü WSL dağıtımlarını ve durumlarını listeler."""
    return core.get_wsl_status()


@mcp.tool()
def open_in_chrome(url: str = "http://localhost:3000") -> str:
    """URL'yi tarayıcıda açar."""
    return core.open_in_chrome(url)


@mcp.tool()
def check_localhost_service(port: int = 3000, host: str = "127.0.0.1") -> str:
    """Yerel TCP portunun açık olup olmadığını kontrol eder."""
    return core.check_localhost_service(port, host)


@mcp.tool()
def get_system_environment_info() -> str:
    """Python, Pip, Node, NPM ve Git sürümlerini listeler."""
    return core.get_system_environment_info()


if __name__ == "__main__":
    mcp.run(transport="stdio")
