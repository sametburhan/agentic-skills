"""Yerel ve bağımlılıksız Git MCP sunucusu."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unified_server as core

mcp = FastMCP("Git-Tools")


@mcp.tool()
def git_status(repository_path: str) -> Dict[str, Any]:
    """Dal ve çalışma ağacı durumunu döndürür."""
    return core.git_status(repository_path)


@mcp.tool()
def git_diff(repository_path: str, staged: bool = False, max_characters: int = 50000) -> Dict[str, Any]:
    """Stage edilmiş veya edilmemiş değişikliklerin diff çıktısını döndürür."""
    return core.git_diff(repository_path, staged, max_characters)


@mcp.tool()
def git_log(repository_path: str, max_count: int = 10) -> Dict[str, Any]:
    """Son commitleri listeler."""
    return core.git_log(repository_path, max_count)


@mcp.tool()
def git_branches(repository_path: str) -> Dict[str, Any]:
    """Yerel ve uzak dalları listeler."""
    return core.git_branches(repository_path)


@mcp.tool()
def git_add(repository_path: str, paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """Dosyaları staging alanına ekler."""
    return core.git_add(repository_path, paths)


@mcp.tool()
def git_commit(repository_path: str, message: str) -> Dict[str, Any]:
    """Stage edilmiş değişiklikleri commit eder."""
    return core.git_commit(repository_path, message)


@mcp.tool()
def git_create_branch(repository_path: str, branch_name: str, checkout: bool = True) -> Dict[str, Any]:
    """Yeni dal oluşturur ve isteğe bağlı olarak dala geçer."""
    return core.git_create_branch(repository_path, branch_name, checkout)


@mcp.tool()
def git_checkout(repository_path: str, ref: str) -> Dict[str, Any]:
    """Var olan bir dala geçer."""
    return core.git_checkout(repository_path, ref)


if __name__ == "__main__":
    mcp.run(transport="stdio")
