"""Modüler sistem MCP sunucusu; uygulamayı birleşik çekirdekten paylaşır."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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
def python_run_code(
    code: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """Python kodunu sistem veya venv yorumlayıcısıyla çalıştırır."""
    return core.python_run_code(code, args, cwd, python_path, venv_path, timeout_seconds)


@mcp.tool()
def python_run_file(
    file_path: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """Python dosyasını argümanlarıyla sistem veya venv yorumlayıcısında çalıştırır."""
    return core.python_run_file(file_path, args, cwd, python_path, venv_path, timeout_seconds)


@mcp.tool()
def python_create_venv(
    venv_path: str,
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    system_site_packages: bool = False,
    upgrade_deps: bool = False,
    timeout_seconds: int = 300,
) -> Dict[str, Any]:
    """Belirtilen dizinde Python sanal ortamı oluşturur."""
    return core.python_create_venv(
        venv_path, cwd, python_path, system_site_packages, upgrade_deps, timeout_seconds,
    )


@mcp.tool()
def python_install_packages(
    packages: List[str],
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    upgrade: bool = False,
    timeout_seconds: int = 600,
) -> Dict[str, Any]:
    """Paketleri pip ile sistem veya venv ortamına kurar."""
    return core.python_install_packages(packages, cwd, python_path, venv_path, upgrade, timeout_seconds)


@mcp.tool()
def python_install_requirements(
    requirements_path: str,
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    upgrade: bool = False,
    timeout_seconds: int = 600,
) -> Dict[str, Any]:
    """Requirements dosyasını pip ile sistem veya venv ortamına kurar."""
    return core.python_install_requirements(
        requirements_path, cwd, python_path, venv_path, upgrade, timeout_seconds,
    )


@mcp.tool()
def python_environment_info(
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Python yorumlayıcısının sürüm, platform, venv ve pip bilgilerini döndürür."""
    return core.python_environment_info(cwd, python_path, venv_path)


@mcp.tool()
def get_current_datetime(timezone_name: str = "local") -> Dict[str, Any]:
    """Güncel tarih, saat, UTC karşılığı, saat dilimi ve Unix zamanını döndürür."""
    return core.get_current_datetime(timezone_name)


@mcp.tool()
def convert_datetime(
    datetime_value: str,
    target_timezone: str,
    source_timezone: str = "local",
) -> Dict[str, Any]:
    """ISO 8601 tarih/saat değerini hedef saat dilimine dönüştürür."""
    return core.convert_datetime(datetime_value, target_timezone, source_timezone)


@mcp.tool()
def calculate_datetime(
    datetime_value: Optional[str] = None,
    timezone_name: str = "local",
    days: float = 0,
    hours: float = 0,
    minutes: float = 0,
    seconds: float = 0,
) -> Dict[str, Any]:
    """Bir tarihe zaman ekler veya negatif değerlerle tarihten zaman çıkarır."""
    return core.calculate_datetime(datetime_value, timezone_name, days, hours, minutes, seconds)


@mcp.tool()
def datetime_difference(
    start_datetime: str,
    end_datetime: str,
    timezone_name: str = "local",
    absolute: bool = False,
) -> Dict[str, Any]:
    """İki tarih/saat arasındaki süre farkını hesaplar."""
    return core.datetime_difference(start_datetime, end_datetime, timezone_name, absolute)


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
