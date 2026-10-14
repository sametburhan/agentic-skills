"""Modüler web arama ve sayfa gözlemleme MCP sunucusu."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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


@mcp.tool()
def websocket_connect(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    subprotocols: Optional[List[str]] = None,
    open_timeout_seconds: int = 10,
    max_message_bytes: int = 1_048_576,
) -> Dict[str, Any]:
    """Kalıcı bir ws:// veya wss:// bağlantısı açar."""
    return core.websocket_connect(url, headers, subprotocols, open_timeout_seconds, max_message_bytes)


@mcp.tool()
def websocket_send(connection_id: str, message: str, binary_base64: bool = False) -> Dict[str, Any]:
    """Açık bağlantıya metin veya Base64 kodlu ikili mesaj gönderir."""
    return core.websocket_send(connection_id, message, binary_base64)


@mcp.tool()
def websocket_receive(connection_id: str, timeout_seconds: int = 10) -> Dict[str, Any]:
    """Açık bağlantıdan sıradaki mesajı alır."""
    return core.websocket_receive(connection_id, timeout_seconds)


@mcp.tool()
def websocket_ping(connection_id: str, payload: str = "", timeout_seconds: int = 10) -> Dict[str, Any]:
    """Ping gönderir ve pong yanıtını bekler."""
    return core.websocket_ping(connection_id, payload, timeout_seconds)


@mcp.tool()
def websocket_close(connection_id: str) -> Dict[str, Any]:
    """Bağlantıyı kapatıp bağlantı havuzundan çıkarır."""
    return core.websocket_close(connection_id)


@mcp.tool()
def websocket_list_connections() -> Dict[str, Any]:
    """Sunucu belleğinde tutulan WebSocket bağlantılarını listeler."""
    return core.websocket_list_connections()


@mcp.tool()
def websocket_request(
    url: str,
    message: str,
    headers: Optional[Dict[str, str]] = None,
    subprotocols: Optional[List[str]] = None,
    receive_count: int = 1,
    timeout_seconds: int = 10,
    binary_base64: bool = False,
    max_message_bytes: int = 1_048_576,
) -> Dict[str, Any]:
    """Tek çağrıda bağlanır, mesaj gönderir, yanıtları alır ve bağlantıyı kapatır."""
    return core.websocket_request(
        url, message, headers, subprotocols, receive_count,
        timeout_seconds, binary_base64, max_message_bytes,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
