"""PowerShell, Git ve web araçları için bağımsız smoke testleri."""

import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from websockets.sync.server import serve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import unified_server as server


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def test_powershell():
    result = server.run_powershell("Write-Output MCP_POWERSHELL_OK", timeout_seconds=20)
    require("MCP_POWERSHELL_OK" in result, result)
    require("[Çıkış Kodu: 0]" in result, result)


def test_git():
    with tempfile.TemporaryDirectory(prefix="mcp-git-test-") as directory:
        def git(*args):
            return subprocess.run(
                ["git", "-C", directory, *args], check=True,
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding="utf-8", errors="replace",
            )

        git("init")
        git("config", "user.email", "mcp-test@example.invalid")
        git("config", "user.name", "MCP Test")
        Path(directory, "hello.txt").write_text("hello\n", encoding="utf-8")

        status = server.git_status(directory)
        require(status.get("basarili") is True, str(status))
        require("hello.txt" in status.get("cikti", ""), str(status))

        added = server.git_add(directory, ["hello.txt"])
        require(added.get("basarili") is True, str(added))
        committed = server.git_commit(directory, "test: initial commit")
        require(committed.get("basarili") is True, str(committed))
        log = server.git_log(directory, 1)
        require(log.get("commitler", [{}])[0].get("mesaj") == "test: initial commit", str(log))

        branch = server.git_create_branch(directory, "test-branch")
        require(branch.get("basarili") is True, str(branch))
        require(server.git_status(directory).get("dal") == "test-branch", "Dal değiştirilemedi")


def test_web():
    text = server.fetch_web_page_text("https://example.com", 2000)
    require("Example Domain" in text, text)
    observed = server.observe_web_page("https://example.com", 2000, False, 20)
    require(observed.get("baslik") == "Example Domain", str(observed))
    require("documentation examples" in observed.get("metin", ""), str(observed))
    results = server.web_search("Model Context Protocol", 3)
    require(results and results[0].get("url"), str(results))
    research = server.research_web("Model Context Protocol", 3, 1500, 3, 15)
    require(research.get("basarili") is True, str(research))
    require(research.get("okunan_sayfa", 0) >= 1, str(research))
    require(len(research.get("sayfalar", [])) <= 3, str(research))


def test_websocket():
    def echo(connection):
        for message in connection:
            connection.send(message)

    ws_server = serve(echo, "127.0.0.1", 0)
    port = ws_server.socket.getsockname()[1]
    thread = threading.Thread(target=ws_server.serve_forever, daemon=True)
    thread.start()
    url = f"ws://127.0.0.1:{port}"
    try:
        opened = server.websocket_connect(url, open_timeout_seconds=5)
        require(opened.get("basarili") is True, str(opened))
        connection_id = opened["connection_id"]

        sent = server.websocket_send(connection_id, '{"hello":"world"}')
        require(sent.get("basarili") is True, str(sent))
        received = server.websocket_receive(connection_id, timeout_seconds=5)
        require(received.get("mesaj") == '{"hello":"world"}', str(received))

        binary_sent = server.websocket_send(connection_id, "AAEC", binary_base64=True)
        require(binary_sent.get("basarili") is True, str(binary_sent))
        binary_received = server.websocket_receive(connection_id, timeout_seconds=5)
        require(binary_received.get("base64") == "AAEC", str(binary_received))

        pong = server.websocket_ping(connection_id, "mcp", timeout_seconds=5)
        require(pong.get("pong_alindi") is True, str(pong))
        listed = server.websocket_list_connections()
        require(listed.get("baglanti_sayisi") == 1, str(listed))
        closed = server.websocket_close(connection_id)
        require(closed.get("basarili") is True, str(closed))

        exchanged = server.websocket_request(url, "one-shot", timeout_seconds=5)
        require(exchanged.get("basarili") is True, str(exchanged))
        require(exchanged.get("yanitlar", [{}])[0].get("mesaj") == "one-shot", str(exchanged))
        require(server.websocket_list_connections().get("baglanti_sayisi") == 0, "Bağlantı havuzu temizlenmedi")
    finally:
        server._close_all_websockets()
        ws_server.shutdown()
        thread.join(timeout=5)


if __name__ == "__main__":
    test_powershell()
    print("[OK] PowerShell")
    test_git()
    print("[OK] Git")
    test_web()
    print("[OK] Web")
    test_websocket()
    print("[OK] WebSocket")
