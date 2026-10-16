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


def test_python_tools():
    code_result = server.python_run_code(
        "import sys; print('PYTHON_CODE_OK:' + sys.argv[1])",
        args=["argument"],
        timeout_seconds=20,
    )
    require(code_result.get("basarili") is True, str(code_result))
    require("PYTHON_CODE_OK:argument" in code_result.get("stdout", ""), str(code_result))

    with tempfile.TemporaryDirectory(prefix="mcp-python-test-") as directory:
        script_path = Path(directory, "hello.py")
        script_path.write_text("import sys\nprint('PYTHON_FILE_OK:' + sys.argv[1])\n", encoding="utf-8")
        file_result = server.python_run_file(str(script_path), args=["argument"], timeout_seconds=20)
        require(file_result.get("basarili") is True, str(file_result))
        require("PYTHON_FILE_OK:argument" in file_result.get("stdout", ""), str(file_result))

        venv_path = Path(directory, ".venv")
        created = server.python_create_venv(str(venv_path), timeout_seconds=120)
        require(created.get("basarili") is True, str(created))
        require(Path(created.get("venv_python", "")).is_file(), str(created))

        environment = server.python_environment_info(venv_path=str(venv_path))
        require(environment.get("basarili") is True, str(environment))
        require(environment.get("in_venv") is True, str(environment))

        requirements_path = Path(directory, "requirements-empty.txt")
        requirements_path.write_text("# intentionally empty\n", encoding="utf-8")
        installed = server.python_install_requirements(
            str(requirements_path), venv_path=str(venv_path), timeout_seconds=120,
        )
        require(installed.get("basarili") is True, str(installed))

        rejected = server.python_install_packages(["--user"], venv_path=str(venv_path))
        require(rejected.get("basarili") is False, str(rejected))


def test_datetime_tools():
    current = server.get_current_datetime("Europe/Istanbul")
    require(current.get("basarili") is True, str(current))
    require(current.get("utc_offset") == "+03:00", str(current))

    converted = server.convert_datetime("2026-10-14T12:00:00Z", "Europe/Istanbul")
    require(converted.get("basarili") is True, str(converted))
    require(converted.get("datetime", "").startswith("2026-10-14T15:00:00"), str(converted))

    calculated = server.calculate_datetime(
        "2026-10-14T15:00:00+03:00", "Europe/Istanbul", days=1, hours=2,
    )
    require(calculated.get("datetime", "").startswith("2026-10-15T17:00:00"), str(calculated))

    difference = server.datetime_difference(
        "2026-10-14T12:00:00Z", "2026-10-16T00:00:00Z",
    )
    require(difference.get("total_hours") == 36, str(difference))


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
    test_python_tools()
    print("[OK] Python")
    test_datetime_tools()
    print("[OK] DateTime")
    test_git()
    print("[OK] Git")
    test_web()
    print("[OK] Web")
    test_websocket()
    print("[OK] WebSocket")
