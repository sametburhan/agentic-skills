"""Modüler web arama ve sayfa gözlemleme MCP sunucusu."""

import sys
from pathlib import Path
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import unified_server as core

mcp = FastMCP("Web-Search-Tools")


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """DDGS ve HTML geri dönüşüyle internette arama yapar."""
    return core.web_search(query, max_results)


@mcp.tool()
def fetch_web_page_text(url: str, max_characters: int = 4000) -> str:
    """Bir URL'den okunabilir temiz metin çıkarır."""
    return core.fetch_web_page_text(url, max_characters)


@mcp.tool()
def observe_web_page(
    url: str,
    max_characters: int = 12000,
    render_javascript: bool = True,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """Sayfa başlığı, metni ve bağlantılarıyla yapılandırılmış web gözlemi yapar."""
    return core.observe_web_page(url, max_characters, render_javascript, timeout_seconds)


@mcp.tool()
def research_web(
    query: str,
    max_pages: int = 20,
    max_characters_per_page: int = 4000,
    concurrency: int = 5,
    timeout_seconds: int = 15,
) -> Dict[str, Any]:
    """İlk arama sonuçlarını paralel okuyarak toplu araştırma verisi döndürür."""
    return core.research_web(query, max_pages, max_characters_per_page, concurrency, timeout_seconds)


if __name__ == "__main__":
    mcp.run(transport="stdio")
