"""
Birleşik Yerel Geliştirici & Araştırma MCP Sunucusu (Unified Server)
Bu sunucu; PowerShell/Terminal erişimi, Chrome sekmesi açma, Akıllı PDF okuma (TOC + Vision),
ve DuckDuckGo Web Arama yeteneklerinin tümünü tek bir MCP sunucusunda birleştirir.

LM Studio'ya tek bir Python komutu ekleyerek tüm bu yeteneklere anında erişebilirsiniz.
"""

import atexit
import os
import re
import json
import logging
import time
import base64
import socket
import sqlite3
import subprocess
import shutil
import sys
import tempfile
import threading
import urllib.request
import urllib.error
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import docx
import pptx
from PIL import Image
import fitz  # PyMuPDF
from bs4 import BeautifulSoup
from ddgs import DDGS
from mcp.server.fastmcp import FastMCP
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect as websocket_client_connect

logging.getLogger("ddgs").setLevel(logging.WARNING)
logging.getLogger("primp").setLevel(logging.WARNING)

# Ana MCP Sunucusu
mcp = FastMCP("Local-Agentic-Dev-Suite")

PDF_CACHE_DIR = os.path.join(os.getcwd(), ".pdf_cache")
os.makedirs(PDF_CACHE_DIR, exist_ok=True)


def _creation_flags() -> int:
    """Prevent child console windows without breaking non-Windows imports/tests."""
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _run_process(
    args: Sequence[str],
    cwd: Optional[str] = None,
    timeout_seconds: int = 60,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Run a non-interactive child process with deterministic UTF-8 output."""
    if not args:
        raise ValueError("Çalıştırılacak komut boş olamaz.")

    working_directory = os.path.abspath(cwd or os.getcwd())
    if not os.path.isdir(working_directory):
        raise FileNotFoundError(f"Çalışma dizini bulunamadı: {working_directory}")

    completed = subprocess.run(
        list(args),
        cwd=working_directory,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=max(1, min(int(timeout_seconds), 900)),
        env=env,
        shell=False,
        creationflags=_creation_flags(),
    )
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _powershell_executable() -> Optional[str]:
    """Prefer an absolute Windows PowerShell path, then PowerShell 7/PATH fallbacks."""
    candidates: List[Optional[str]] = []
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidates.append(os.path.join(system_root, "System32", "WindowsPowerShell", "v1.0", "powershell.exe"))
    candidates.extend([shutil.which("pwsh.exe"), shutil.which("pwsh"), shutil.which("powershell.exe"), shutil.which("powershell")])
    for candidate in candidates:
        if candidate and (os.path.isfile(candidate) or shutil.which(candidate)):
            return candidate
    return None


def _format_process_result(result: Dict[str, Any], stdout_label: str = "Çıktı") -> str:
    chunks: List[str] = []
    if result.get("stdout"):
        chunks.append(f"{stdout_label} (stdout):\n{result['stdout']}")
    if result.get("stderr"):
        chunks.append(f"Hata / Bilgi (stderr):\n{result['stderr']}")
    if not chunks:
        chunks.append("Komut başarıyla tamamlandı (çıktı üretmedi).")
    chunks.append(f"[Çıkış Kodu: {result.get('returncode', -1)}]")
    return "\n\n".join(chunks)


def _resolve_python_executable(
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    cwd: Optional[str] = None,
) -> str:
    """Resolve a system or virtual-environment Python executable without shell parsing."""
    if python_path and venv_path:
        raise ValueError("python_path ve venv_path aynı anda kullanılamaz.")

    base_directory = os.path.abspath(cwd or os.getcwd())
    if venv_path:
        expanded_venv = os.path.expandvars(os.path.expanduser(venv_path.strip()))
        absolute_venv = expanded_venv if os.path.isabs(expanded_venv) else os.path.join(base_directory, expanded_venv)
        candidates = [
            os.path.join(absolute_venv, "Scripts", "python.exe"),
            os.path.join(absolute_venv, "bin", "python"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
        raise FileNotFoundError(f"Sanal ortam Python yorumlayıcısı bulunamadı: {absolute_venv}")

    if python_path:
        cleaned = os.path.expandvars(os.path.expanduser(python_path.strip()))
        if not cleaned:
            raise ValueError("python_path boş olamaz.")
        if os.path.isabs(cleaned) or os.path.dirname(cleaned):
            candidate = cleaned if os.path.isabs(cleaned) else os.path.join(base_directory, cleaned)
            if os.path.isfile(candidate):
                return os.path.abspath(candidate)
            raise FileNotFoundError(f"Python yorumlayıcısı bulunamadı: {candidate}")
        resolved = shutil.which(cleaned)
        if resolved:
            return resolved
        raise FileNotFoundError(f"Python komutu PATH üzerinde bulunamadı: {cleaned}")

    return sys.executable


def _python_process_response(
    executable: str,
    arguments: Sequence[str],
    cwd: Optional[str],
    timeout_seconds: int,
) -> Dict[str, Any]:
    """Run Python directly and return bounded, structured output."""
    try:
        environment = os.environ.copy()
        environment.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
        result = _run_process(
            [executable, *[str(argument) for argument in arguments]],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
            env=environment,
        )
        output_limit = 100_000
        stdout = result["stdout"]
        stderr = result["stderr"]
        stdout_truncated = len(stdout) > output_limit
        stderr_truncated = len(stderr) > output_limit
        return {
            "basarili": result["returncode"] == 0,
            "returncode": result["returncode"],
            "python": executable,
            "cwd": os.path.abspath(cwd or os.getcwd()),
            "stdout": stdout[:output_limit],
            "stderr": stderr[:output_limit],
            "stdout_kirpildi": stdout_truncated,
            "stderr_kirpildi": stderr_truncated,
        }
    except subprocess.TimeoutExpired:
        return {
            "basarili": False,
            "python": executable,
            "zaman_asimi": True,
            "hata": f"Python işlemi {timeout_seconds} saniye içinde tamamlanamadı.",
        }
    except Exception as exc:
        return {"basarili": False, "python": executable, "hata": str(exc)}


def _clean_python_arguments(arguments: Optional[List[str]]) -> List[str]:
    cleaned: List[str] = []
    for argument in arguments or []:
        value = str(argument)
        if "\x00" in value:
            raise ValueError("Python argümanları NUL karakteri içeremez.")
        cleaned.append(value)
    return cleaned


def _clean_package_specs(packages: List[str]) -> List[str]:
    cleaned: List[str] = []
    for package in packages or []:
        value = str(package).strip()
        if not value:
            continue
        if value.startswith("-") or "\r" in value or "\n" in value or "\x00" in value:
            raise ValueError(f"Geçersiz paket belirtimi: {value!r}")
        cleaned.append(value)
    if not cleaned:
        raise ValueError("En az bir paket belirtilmelidir.")
    if len(cleaned) > 100:
        raise ValueError("Tek çağrıda en fazla 100 paket kurulabilir.")
    return cleaned


def _resolve_timezone(timezone_name: Optional[str]):
    cleaned = (timezone_name or "local").strip()
    if cleaned.lower() in {"local", "system", "yerel"}:
        return datetime.now().astimezone().tzinfo, "local"
    if cleaned.upper() in {"UTC", "Z"}:
        return timezone.utc, "UTC"
    try:
        return ZoneInfo(cleaned), cleaned
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Saat dilimi bulunamadı: {cleaned}") from exc


def _parse_datetime_value(value: str, default_timezone_name: Optional[str] = "local") -> datetime:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError("Tarih/saat değeri boş olamaz.")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError as exc:
        raise ValueError("Tarih/saat ISO 8601 biçiminde olmalıdır; örnek: 2026-10-14T15:30:00+03:00") from exc
    if parsed.tzinfo is None:
        tzinfo, _ = _resolve_timezone(default_timezone_name)
        parsed = parsed.replace(tzinfo=tzinfo)
    return parsed


def _datetime_payload(value: datetime, requested_timezone: str) -> Dict[str, Any]:
    offset = value.utcoffset() or timedelta(0)
    total_offset_seconds = int(offset.total_seconds())
    sign = "+" if total_offset_seconds >= 0 else "-"
    absolute_offset = abs(total_offset_seconds)
    offset_text = f"{sign}{absolute_offset // 3600:02d}:{(absolute_offset % 3600) // 60:02d}"
    iso_calendar = value.isocalendar()
    return {
        "datetime": value.isoformat(),
        "date": value.date().isoformat(),
        "time": value.timetz().isoformat(),
        "timezone": requested_timezone,
        "timezone_name": value.tzname(),
        "utc_offset": offset_text,
        "unix_timestamp": value.timestamp(),
        "weekday": value.strftime("%A"),
        "weekday_index": value.weekday(),
        "iso_week": iso_calendar.week,
        "iso_year": iso_calendar.year,
    }


# ==============================================================================
# 1. BÖLÜM: SİSTEM, TERMİNAL VE LOCALHOST YÖNETİMİ
# ==============================================================================

@mcp.tool()
def run_powershell(command: str, cwd: Optional[str] = None, timeout_seconds: int = 60) -> str:
    """
    Windows PowerShell üzerinde komut çalıştırır.
    Sistem PATH'inde bulunan tüm CLI araçları (python, pip, node, npm, git, docker, npx vb.) kullanılabilir.

    Parametreler:
        command: Çalıştırılacak PowerShell komut satırı.
        cwd: Komutun çalıştırılacağı çalışma dizini (boş bırakılırsa geçerli dizin kullanılır).
        timeout_seconds: Komutun zaman aşımı süresi (varsayılan: 60 saniye).
    """
    try:
        if not command or not command.strip():
            return "HATA: PowerShell komutu boş olamaz."
        executable = _powershell_executable()
        if not executable:
            return "HATA: PowerShell bulunamadı (powershell.exe veya pwsh PATH üzerinde değil)."
        wrapped_command = (
            "$ErrorActionPreference='Continue'; "
            "[Console]::InputEncoding=[System.Text.UTF8Encoding]::new($false); "
            "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false); "
            "$OutputEncoding=[System.Text.UTF8Encoding]::new($false); "
            + command
        )
        result = _run_process(
            [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", wrapped_command],
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        return _format_process_result(result)
    except subprocess.TimeoutExpired:
        return f"HATA: Komut {timeout_seconds} saniye içinde tamamlanamadı ve zaman aşımına uğradı."
    except Exception as e:
        return f"HATA: Komut çalıştırılırken bir istisna oluştu: {str(e)}"


@mcp.tool()
def python_run_code(
    code: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """Python kodunu sistem veya venv yorumlayıcısıyla doğrudan çalıştırır."""
    try:
        if not code or not code.strip():
            return {"basarili": False, "hata": "Python kodu boş olamaz."}
        if len(code) > 500_000:
            return {"basarili": False, "hata": "Python kodu 500.000 karakter sınırını aşıyor."}
        executable = _resolve_python_executable(python_path, venv_path, cwd)
        return _python_process_response(
            executable,
            ["-c", code, *_clean_python_arguments(args)],
            cwd,
            max(1, min(int(timeout_seconds), 900)),
        )
    except Exception as exc:
        return {"basarili": False, "hata": f"Python kodu çalıştırılamadı: {exc}"}


@mcp.tool()
def python_run_file(
    file_path: str,
    args: Optional[List[str]] = None,
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    timeout_seconds: int = 60,
) -> Dict[str, Any]:
    """Bir Python dosyasını argümanlarıyla sistem veya venv yorumlayıcısında çalıştırır."""
    try:
        base_directory = os.path.abspath(cwd or os.getcwd())
        expanded_file = os.path.expandvars(os.path.expanduser((file_path or "").strip()))
        absolute_file = expanded_file if os.path.isabs(expanded_file) else os.path.join(base_directory, expanded_file)
        absolute_file = os.path.abspath(absolute_file)
        if not os.path.isfile(absolute_file):
            return {"basarili": False, "hata": f"Python dosyası bulunamadı: {absolute_file}"}
        working_directory = os.path.abspath(cwd) if cwd else os.path.dirname(absolute_file)
        executable = _resolve_python_executable(python_path, venv_path, working_directory)
        return _python_process_response(
            executable,
            [absolute_file, *_clean_python_arguments(args)],
            working_directory,
            max(1, min(int(timeout_seconds), 900)),
        )
    except Exception as exc:
        return {"basarili": False, "hata": f"Python dosyası çalıştırılamadı: {exc}"}


@mcp.tool()
def python_create_venv(
    venv_path: str,
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    system_site_packages: bool = False,
    upgrade_deps: bool = False,
    timeout_seconds: int = 300,
) -> Dict[str, Any]:
    """Belirtilen dizinde yeni bir Python sanal ortamı oluşturur."""
    try:
        base_directory = os.path.abspath(cwd or os.getcwd())
        expanded_venv = os.path.expandvars(os.path.expanduser((venv_path or "").strip()))
        if not expanded_venv:
            return {"basarili": False, "hata": "venv_path boş olamaz."}
        absolute_venv = expanded_venv if os.path.isabs(expanded_venv) else os.path.join(base_directory, expanded_venv)
        absolute_venv = os.path.abspath(absolute_venv)
        if os.path.isdir(absolute_venv) and os.listdir(absolute_venv):
            return {"basarili": False, "hata": f"Hedef sanal ortam dizini boş değil: {absolute_venv}"}
        os.makedirs(os.path.dirname(absolute_venv), exist_ok=True)
        executable = _resolve_python_executable(python_path, None, base_directory)
        command = ["-m", "venv"]
        if system_site_packages:
            command.append("--system-site-packages")
        if upgrade_deps:
            command.append("--upgrade-deps")
        command.append(absolute_venv)
        response = _python_process_response(
            executable,
            command,
            base_directory,
            max(30, min(int(timeout_seconds), 900)),
        )
        response["venv_path"] = absolute_venv
        if response.get("basarili"):
            response["venv_python"] = _resolve_python_executable(None, absolute_venv, base_directory)
        return response
    except Exception as exc:
        return {"basarili": False, "hata": f"Sanal ortam oluşturulamadı: {exc}"}


@mcp.tool()
def python_install_packages(
    packages: List[str],
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    upgrade: bool = False,
    timeout_seconds: int = 600,
) -> Dict[str, Any]:
    """Doğrulanmış paket belirtimlerini pip ile sistem veya venv ortamına kurar."""
    try:
        clean_packages = _clean_package_specs(packages)
        executable = _resolve_python_executable(python_path, venv_path, cwd)
        command = ["-m", "pip", "install", "--disable-pip-version-check", "--no-input"]
        if upgrade:
            command.append("--upgrade")
        command.extend(clean_packages)
        response = _python_process_response(
            executable,
            command,
            cwd,
            max(30, min(int(timeout_seconds), 900)),
        )
        response["paketler"] = clean_packages
        return response
    except Exception as exc:
        return {"basarili": False, "hata": f"Python paketleri kurulamadı: {exc}"}


@mcp.tool()
def python_install_requirements(
    requirements_path: str,
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
    upgrade: bool = False,
    timeout_seconds: int = 600,
) -> Dict[str, Any]:
    """Bir requirements dosyasını pip ile sistem veya venv ortamına kurar."""
    try:
        base_directory = os.path.abspath(cwd or os.getcwd())
        expanded = os.path.expandvars(os.path.expanduser((requirements_path or "").strip()))
        absolute_requirements = expanded if os.path.isabs(expanded) else os.path.join(base_directory, expanded)
        absolute_requirements = os.path.abspath(absolute_requirements)
        if not os.path.isfile(absolute_requirements):
            return {"basarili": False, "hata": f"Requirements dosyası bulunamadı: {absolute_requirements}"}
        executable = _resolve_python_executable(python_path, venv_path, base_directory)
        command = [
            "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
            "-r", absolute_requirements,
        ]
        if upgrade:
            command.insert(5, "--upgrade")
        response = _python_process_response(
            executable,
            command,
            base_directory,
            max(30, min(int(timeout_seconds), 900)),
        )
        response["requirements_path"] = absolute_requirements
        return response
    except Exception as exc:
        return {"basarili": False, "hata": f"Requirements kurulamadı: {exc}"}


@mcp.tool()
def python_environment_info(
    cwd: Optional[str] = None,
    python_path: Optional[str] = None,
    venv_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Seçilen Python yorumlayıcısının sürüm, platform, venv ve pip bilgilerini döndürür."""
    try:
        executable = _resolve_python_executable(python_path, venv_path, cwd)
        inspection_code = (
            "import json,platform,sys;"
            "print(json.dumps({'executable':sys.executable,'version':platform.python_version(),"
            "'implementation':platform.python_implementation(),'platform':platform.platform(),"
            "'prefix':sys.prefix,'base_prefix':sys.base_prefix,'in_venv':sys.prefix!=sys.base_prefix},"
            "ensure_ascii=False))"
        )
        response = _python_process_response(executable, ["-c", inspection_code], cwd, 30)
        if not response.get("basarili"):
            return response
        info = json.loads(response.get("stdout") or "{}")
        pip_response = _python_process_response(executable, ["-m", "pip", "--version"], cwd, 30)
        info.update({
            "basarili": True,
            "pip": pip_response.get("stdout") if pip_response.get("basarili") else None,
            "pip_hatasi": (
                pip_response.get("stderr") or pip_response.get("hata")
                if not pip_response.get("basarili")
                else None
            ),
        })
        return info
    except Exception as exc:
        return {"basarili": False, "hata": f"Python ortam bilgisi alınamadı: {exc}"}


@mcp.tool()
def get_current_datetime(timezone_name: str = "local") -> Dict[str, Any]:
    """Belirtilen saat dilimindeki güncel tarih, saat, UTC karşılığı ve Unix zamanını döndürür."""
    try:
        tzinfo, timezone_label = _resolve_timezone(timezone_name)
        current = datetime.now(tzinfo)
        result = {"basarili": True, **_datetime_payload(current, timezone_label)}
        result["utc_datetime"] = current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        return result
    except Exception as exc:
        return {"basarili": False, "hata": f"Güncel tarih/saat alınamadı: {exc}"}


@mcp.tool()
def convert_datetime(
    datetime_value: str,
    target_timezone: str,
    source_timezone: str = "local",
) -> Dict[str, Any]:
    """ISO 8601 tarih/saat değerini hedef saat dilimine dönüştürür."""
    try:
        source = _parse_datetime_value(datetime_value, source_timezone)
        target_tz, target_label = _resolve_timezone(target_timezone)
        converted = source.astimezone(target_tz)
        return {
            "basarili": True,
            "source_datetime": source.isoformat(),
            **_datetime_payload(converted, target_label),
        }
    except Exception as exc:
        return {"basarili": False, "hata": f"Tarih/saat dönüştürülemedi: {exc}"}


@mcp.tool()
def calculate_datetime(
    datetime_value: Optional[str] = None,
    timezone_name: str = "local",
    days: float = 0,
    hours: float = 0,
    minutes: float = 0,
    seconds: float = 0,
) -> Dict[str, Any]:
    """Bir tarihe gün, saat, dakika ve saniye ekler; negatif değerlerle çıkarma yapar."""
    try:
        tzinfo, timezone_label = _resolve_timezone(timezone_name)
        starting = (
            _parse_datetime_value(datetime_value, timezone_name).astimezone(tzinfo)
            if datetime_value
            else datetime.now(tzinfo)
        )
        delta = timedelta(days=float(days), hours=float(hours), minutes=float(minutes), seconds=float(seconds))
        calculated = starting + delta
        return {
            "basarili": True,
            "source_datetime": starting.isoformat(),
            "delta_seconds": delta.total_seconds(),
            **_datetime_payload(calculated, timezone_label),
        }
    except Exception as exc:
        return {"basarili": False, "hata": f"Tarih hesabı yapılamadı: {exc}"}


@mcp.tool()
def datetime_difference(
    start_datetime: str,
    end_datetime: str,
    timezone_name: str = "local",
    absolute: bool = False,
) -> Dict[str, Any]:
    """İki ISO 8601 tarih/saat arasındaki imzalı veya mutlak süre farkını hesaplar."""
    try:
        start = _parse_datetime_value(start_datetime, timezone_name)
        end = _parse_datetime_value(end_datetime, timezone_name)
        signed_seconds = (end - start).total_seconds()
        result_seconds = abs(signed_seconds) if absolute else signed_seconds
        human_seconds = abs(result_seconds)
        whole_seconds = int(human_seconds)
        days_part, remainder = divmod(whole_seconds, 86_400)
        hours_part, remainder = divmod(remainder, 3_600)
        minutes_part, seconds_part = divmod(remainder, 60)
        return {
            "basarili": True,
            "start_datetime": start.isoformat(),
            "end_datetime": end.isoformat(),
            "absolute": bool(absolute),
            "total_seconds": result_seconds,
            "total_minutes": result_seconds / 60,
            "total_hours": result_seconds / 3_600,
            "total_days": result_seconds / 86_400,
            "sign": 0 if result_seconds == 0 else (1 if result_seconds > 0 else -1),
            "components": {
                "days": days_part,
                "hours": hours_part,
                "minutes": minutes_part,
                "seconds": seconds_part,
            },
        }
    except Exception as exc:
        return {"basarili": False, "hata": f"Tarih farkı hesaplanamadı: {exc}"}


@mcp.tool()
def run_wsl(command: str, distro: Optional[str] = "Ubuntu", working_dir: Optional[str] = None, timeout_seconds: int = 60) -> str:
    """
    WSL (Windows Subsystem for Linux) ortamında yerel Linux komutları çalıştırır.
    Linux paket yöneticileri (apt, yum), derleyiciler (gcc, g++, make), Docker, bash betikleri vb. doğrudan çalıştırılabilir.

    Parametreler:
        command: Çalıştırılacak Linux/Bash komutu (Örn: 'gcc -o main main.c', 'apt list --installed', 'uname -a').
        distro: Hedef Linux dağıtımı (varsayılan: 'Ubuntu').
        working_dir: Linux içindeki çalışma dizini (Örn: '/home/kullanici/proje' veya boş bırakılırsa varsayılan).
        timeout_seconds: Zaman aşımı süresi (varsayılan: 60 saniye).
    """
    cmd_args = ["wsl"]
    if distro:
        cmd_args.extend(["-d", distro])
    if working_dir:
        cmd_args.extend(["--cd", working_dir])
    
    cmd_args.extend(["-e", "bash", "-c", command])

    try:
        process = subprocess.run(
            cmd_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds
        )

        stdout = process.stdout.strip()
        stderr = process.stderr.strip()

        response = []
        if stdout:
            response.append(f"WSL Çıktı (stdout):\n{stdout}")
        if stderr:
            response.append(f"WSL Hata/Bilgi (stderr):\n{stderr}")
        if not stdout and not stderr:
            response.append("Komut başarıyla tamamlandı (çıktı üretmedi).")

        response.append(f"\n[Çıkış Kodu: {process.returncode}]")
        return "\n\n".join(response)

    except subprocess.TimeoutExpired:
        return f"HATA: WSL komutu {timeout_seconds} saniye içinde tamamlanamadı."
    except Exception as e:
        return f"HATA: WSL çalıştırılırken istisna: {str(e)}"


@mcp.tool()
def get_wsl_status() -> str:
    """
    Sistemde yüklü olan WSL dağıtımlarını, çalışma durumlarını (Running/Stopped) ve WSL versiyonunu listeler.
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "wsl --list --verbose"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10
        )
        output = res.stdout.strip() if res.stdout else res.stderr.strip()
        return f"=== WSL Dağıtım Durumu ===\n{output}"
    except Exception as e:
        return f"HATA: WSL durumu alınırken hata: {str(e)}"


@mcp.tool()
def open_in_chrome(url: str = "http://localhost:3000") -> str:
    """
    Belirtilen web adresini (özellikle yerel localhost projelerini) Google Chrome'da yeni sekmede açar.

    Parametreler:
        url: Açılacak web adresi (Örn: http://localhost:3000, http://localhost:5173).
    """
    cleaned_url = url.strip()
    if not cleaned_url.startswith("http://") and not cleaned_url.startswith("https://"):
        cleaned_url = "http://" + cleaned_url

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f'Start-Process chrome "{cleaned_url}"'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f'Start-Process "{cleaned_url}"'],
                check=True
            )
        return f"Başarılı: '{cleaned_url}' tarayıcıda açıldı."
    except Exception as e:
        return f"HATA: Tarayıcı açılırken sorun oluştu: {str(e)}"


@mcp.tool()
def check_localhost_service(port: int = 3000, host: str = "127.0.0.1") -> str:
    """
    Belirtilen yerel portta bir web sunucusunun (Vite, Next.js, FastAPI vb.) aktif olup olmadığını kontrol eder.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            return f"DURUM: {host}:{port} portu AKTİF ve yanıt veriyor. 'open_in_chrome' ile açabilirsiniz."
        else:
            return f"DURUM: {host}:{port} portunda çalışan servis bulunamadı (port kapalı)."
    except Exception as e:
        return f"HATA: Port kontrolü hatası: {str(e)}"
    finally:
        sock.close()


@mcp.tool()
def get_system_environment_info() -> str:
    """
    Sistemde yüklü olan Python, Pip, Node, NPM ve Git versiyonlarını özetler.
    """
    tools = [
        ("Python", ["python", "--version"]),
        ("Pip", ["python", "-m", "pip", "--version"]),
        ("Node.js", ["node", "--version"]),
        ("NPM", ["npm.cmd" if os.name == "nt" else "npm", "--version"]),
        ("Git", ["git", "--version"]),
    ]
    report = ["=== Sistem Geliştirici Araçları Durumu ==="]
    for name, command_args in tools:
        try:
            executable = shutil.which(command_args[0])
            if not executable:
                report.append(f"[X] {name}: PATH üzerinde bulunamadı")
                continue
            res = _run_process([executable, *command_args[1:]], timeout_seconds=8)
            val = res["stdout"] or res["stderr"]
            if res["returncode"] == 0:
                report.append(f"[OK] {name}: {val}")
            else:
                report.append(f"[X] {name}: Hata ({val})")
        except Exception as exc:
            report.append(f"[X] {name}: {exc}")
    return "\n".join(report)


# ==============================================================================
# 2. BÖLÜM: AKILLI PDF OKUMA & VISION ANALİZİ
# ==============================================================================

@mcp.tool()
def get_pdf_info_and_toc(file_path: str) -> Dict[str, Any]:
    """
    Uzun bir PDF'in toplam sayfa sayısını ve İçindekiler Tablosunu (TOC / Hiyerarşi) listeler.
    Büyük dokümanlarda ilk incelenmesi gereken araçtır.
    """
    if not os.path.exists(file_path):
        return {"hata": f"Dosya bulunamadı: {file_path}"}

    try:
        doc = fitz.open(file_path)
        toc = doc.get_toc()
        metadata = doc.metadata or {}

        formatted_toc = []
        for level, title, page in toc:
            indent = "  " * (level - 1)
            formatted_toc.append(f"{indent}- {title} (Sayfa: {page})")

        return {
            "toplam_sayfa": len(doc),
            "baslik": metadata.get("title") or os.path.basename(file_path),
            "yazar": metadata.get("author", "Bilinmiyor"),
            "icindekiler_tablosu": formatted_toc if formatted_toc else "Yerleşik içindekiler tablosu bulunamadı."
        }
    except Exception as e:
        return {"hata": f"PDF meta verisi okunurken hata: {str(e)}"}


@mcp.tool()
def search_pdf(file_path: str, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Uzun PDF dokümanında anahtar kelime veya kelime öbeği araması yapar. Sayfa numarası ve metin kesiti döner.
    """
    if not os.path.exists(file_path):
        return [{"hata": f"Dosya bulunamadı: {file_path}"}]

    try:
        doc = fitz.open(file_path)
        results = []

        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text()
            if query.lower() in text.lower():
                idx = text.lower().find(query.lower())
                start = max(0, idx - 150)
                end = min(len(text), idx + 250)
                snippet = text[start:end].replace("\n", " ").strip()

                results.append({
                    "sayfa": page_idx + 1,
                    "kesit": f"...{snippet}..."
                })

                if len(results) >= max_results:
                    break

        return results if results else [{"mesaj": f"'{query}' ifadesi dokümanda bulunamadı."}]
    except Exception as e:
        return [{"hata": f"Arama hatası: {str(e)}"}]


@mcp.tool()
def read_pdf_page_range(file_path: str, start_page: int, end_page: int) -> str:
    """
    PDF dokümanının belirtilen sayfa aralığındaki metinleri döner (1-indeksli).
    """
    if not os.path.exists(file_path):
        return f"HATA: Dosya bulunamadı: {file_path}"

    try:
        doc = fitz.open(file_path)
        total = len(doc)
        if start_page < 1 or start_page > total:
            return f"HATA: Geçersiz sayfa ({start_page}). Toplam: {total}"
        
        extracted = []
        for page_num in range(start_page - 1, min(end_page, total)):
            page_text = doc[page_num].get_text()
            extracted.append(f"### [Sayfa {page_num + 1} / {total}]\n{page_text.strip()}")

        return "\n\n---\n\n".join(extracted)
    except Exception as e:
        return f"HATA: Sayfalar okunurken istisna: {str(e)}"


@mcp.tool()
def extract_pdf_pages_as_json(
    file_path: str,
    start_page: int,
    end_page: int,
    extract_tables: bool = True
) -> Dict[str, Any]:
    """
    PDF sayfalarındaki içeriği saf metin, başlık blokları ve veri tabloları (2D satır-sütun)
    halinde yapılandırılmış hafif bir JSON formatında çıkarır.
    Görsel işlemeden çok daha hızlıdır ve modelin token/bağlam penceresini korur.

    Parametreler:
        file_path: PDF dosya yolu.
        start_page: Başlangıç sayfası (1'den başlar).
        end_page: Bitiş sayfası (dahil).
        extract_tables: Sayfalardaki tablolar özel olarak 2D liste olarak çıkarılsın mı? (varsayılan: True).
    """
    if not os.path.exists(file_path):
        return {"hata": f"Dosya bulunamadı: {file_path}"}

    try:
        doc = fitz.open(file_path)
        total = len(doc)
        if start_page < 1 or start_page > total:
            return {"hata": f"Geçersiz başlangıç sayfası ({start_page}). Toplam: {total}"}

        actual_end = min(end_page, total)
        pages_data = []

        for page_idx in range(start_page - 1, actual_end):
            page = doc[page_idx]
            page_info = {
                "sayfa_no": page_idx + 1,
                "tablolar": [],
                "metin_bloklari": []
            }

            if extract_tables:
                try:
                    tabs = page.find_tables()
                    for tab in tabs.tables:
                        mat = tab.extract()
                        if mat:
                            page_info["tablolar"].append(mat)
                except Exception:
                    pass

            blocks = page.get_text("blocks")
            for b in blocks:
                if b[6] == 0:
                    text = b[4].strip()
                    if text:
                        clean_para = " ".join([line.strip() for line in text.splitlines() if line.strip()])
                        page_info["metin_bloklari"].append(clean_para)

            pages_data.append(page_info)

        return {
            "dosya": os.path.basename(file_path),
            "sayfa_araligi": f"{start_page}-{actual_end}",
            "toplam_sayfa": total,
            "sayfalar": pages_data
        }
    except Exception as e:
        return {"hata": f"Yapılandırılmış JSON çıkarılırken hata: {str(e)}"}


@mcp.tool()
def render_pdf_page_to_image(file_path: str, page_number: int, dpi: int = 150) -> Dict[str, Any]:
    """
    Diyagram, tablo veya formül içeren bir sayfayı PNG formatında kaydeder.
    Vision özellikli model bu görsel dosyasını inceleyebilir.
    """
    if not os.path.exists(file_path):
        return {"hata": f"Dosya bulunamadı: {file_path}"}

    try:
        doc = fitz.open(file_path)
        if page_number < 1 or page_number > len(doc):
            return {"hata": f"Geçersiz sayfa ({page_number}). Toplam: {len(doc)}"}

        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=dpi)
        filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_p{page_number}.png"
        output_path = os.path.join(PDF_CACHE_DIR, filename)
        pix.save(output_path)

        return {
            "durum": "Başarılı",
            "sayfa_no": page_number,
            "gorsel_dosya_yolu": os.path.abspath(output_path),
            "mesaj": "Sayfa PNG olarak kaydedildi. Vision yeteneğiniz ile inceleyebilirsiniz."
        }
    except Exception as e:
        return {"hata": f"Görsel oluşturma hatası: {str(e)}"}


BROWSER_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
]

DEFAULT_MD_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1f2937;
    line-height: 1.6;
    padding: 40px;
    margin: 0 auto;
    max-width: 900px;
}
h1, h2, h3, h4 { color: #111827; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; margin-top: 24px; }
h1 { font-size: 28px; }
h2 { font-size: 22px; }
table { border-collapse: collapse; width: 100%; margin: 20px 0; }
th, td { border: 1px solid #d1d5db; padding: 10px 14px; text-align: left; }
th { background-color: #f9fafb; font-weight: 600; }
pre, code { font-family: Consolas, "Courier New", monospace; background-color: #f3f4f6; border-radius: 4px; }
pre { padding: 14px; overflow-x: auto; border: 1px solid #e5e7eb; }
code { padding: 2px 6px; }
blockquote { border-left: 4px solid #3b82f6; margin: 0; padding-left: 16px; color: #4b5563; font-style: italic; }
ul, ol { padding-left: 24px; }
li { margin-bottom: 4px; }
hr { border: 0; border-top: 1px solid #e5e7eb; margin: 24px 0; }
"""


@mcp.tool()
def convert_markdown_to_pdf(
    input_md_path: str,
    output_pdf_path: str,
    custom_css: Optional[str] = None
) -> Dict[str, Any]:
    """
    Markdown (.md) dosyasını şık stillendirilmiş yüksek kaliteli bir PDF dokümanına dönüştürür.
    WSL (/home/... veya \\wsl$\\Ubuntu\\...) ve Windows dizinleri arasındaki dönüşümleri doğrudan destekler.
    """
    import markdown
    import tempfile

    clean_input = input_md_path.strip()
    if clean_input.startswith("/") and not clean_input.startswith("//"):
        slash_path = clean_input.replace("/", "\\")
        clean_input = f"\\\\wsl$\\Ubuntu{slash_path}"

    clean_output = output_pdf_path.strip()
    if clean_output.startswith("/") and not clean_output.startswith("//"):
        slash_out = clean_output.replace("/", "\\")
        clean_output = f"\\\\wsl$\\Ubuntu{slash_out}"

    if not os.path.exists(clean_input):
        return {"hata": f"Kaynak Markdown dosyası bulunamadı: {clean_input}"}

    out_dir = os.path.dirname(os.path.abspath(clean_output))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    browser_exe = None
    for bp in BROWSER_PATHS:
        if os.path.exists(bp):
            browser_exe = bp
            break

    if not browser_exe:
        return {"hata": "PDF derlemesi için sistemde Edge veya Chrome bulunamadı."}

    try:
        with open(clean_input, "r", encoding="utf-8", errors="replace") as f:
            md_text = f.read()

        html_body = markdown.markdown(md_text, extensions=["tables", "fenced_code", "toc"])
        css_style = custom_css if custom_css else DEFAULT_MD_CSS

        full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
{css_style}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".html", delete=False) as temp_html:
            temp_html.write(full_html)
            temp_html_path = temp_html.name

        abs_out_pdf = os.path.abspath(clean_output)
        abs_temp_html = os.path.abspath(temp_html_path)

        subprocess.run(
            [browser_exe, "--headless=new", "--disable-gpu", f"--print-to-pdf={abs_out_pdf}", abs_temp_html],
            check=True,
            capture_output=True,
            timeout=30
        )

        try:
            os.remove(temp_html_path)
        except Exception:
            pass

        if os.path.exists(abs_out_pdf):
            size_kb = round(os.path.getsize(abs_out_pdf) / 1024, 2)
            return {
                "durum": "Başarılı",
                "kaynak_md": clean_input,
                "hedef_pdf": abs_out_pdf,
                "boyut_kb": size_kb,
                "mesaj": f"Markdown başarıyla PDF'e dönüştürüldü ve '{abs_out_pdf}' konumuna kaydedildi."
            }
        else:
            return {"hata": "PDF dosyası oluşturulamadı."}

    except Exception as e:
        return {"hata": f"Dönüştürme sırasında hata oluştu: {str(e)}"}



# ==============================================================================
# 3. BÖLÜM: SIFIR API-KEY İNTERNET ARAMASI & SAYFA İÇERİĞİ
# ==============================================================================

WEB_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

MAX_WEBSOCKET_CONNECTIONS = 32
MAX_WEBSOCKET_MESSAGE_BYTES = 16 * 1024 * 1024
_WEBSOCKET_CONNECTIONS: Dict[str, Dict[str, Any]] = {}
_WEBSOCKET_REGISTRY_LOCK = threading.RLock()


def _normalize_http_url(url: str) -> str:
    cleaned = (url or "").strip()
    parsed = urllib.parse.urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Geçerli bir http:// veya https:// URL'si girilmelidir.")
    return cleaned


def _normalize_websocket_url(url: str) -> str:
    cleaned = (url or "").strip()
    parsed = urllib.parse.urlparse(cleaned)
    if parsed.scheme not in {"ws", "wss"} or not parsed.netloc:
        raise ValueError("Geçerli bir ws:// veya wss:// URL'si girilmelidir.")
    return cleaned


def _websocket_headers(headers: Optional[Dict[str, str]]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for raw_name, raw_value in (headers or {}).items():
        name = str(raw_name).strip()
        value = str(raw_value).strip()
        if not name or any(char in name for char in "\r\n:"):
            raise ValueError("WebSocket başlık adı geçersiz.")
        if "\r" in value or "\n" in value:
            raise ValueError(f"'{name}' başlığının değeri geçersiz.")
        result[name] = value
    return result


def _get_websocket_connection(connection_id: str) -> Dict[str, Any]:
    cleaned_id = (connection_id or "").strip()
    with _WEBSOCKET_REGISTRY_LOCK:
        entry = _WEBSOCKET_CONNECTIONS.get(cleaned_id)
    if entry is None:
        raise KeyError(f"WebSocket bağlantısı bulunamadı: {cleaned_id}")
    return entry


def _remove_websocket_connection(connection_id: str) -> bool:
    with _WEBSOCKET_REGISTRY_LOCK:
        entry = _WEBSOCKET_CONNECTIONS.pop(connection_id, None)
    if entry is None:
        return False
    try:
        with entry["lock"]:
            entry["connection"].close()
    except Exception:
        pass
    return True


def _close_all_websockets() -> None:
    with _WEBSOCKET_REGISTRY_LOCK:
        connection_ids = list(_WEBSOCKET_CONNECTIONS)
    for connection_id in connection_ids:
        _remove_websocket_connection(connection_id)


atexit.register(_close_all_websockets)


def _download_html(url: str, timeout: int = 20, max_bytes: int = 5_000_000) -> Dict[str, Any]:
    cleaned = _normalize_http_url(url)
    request = urllib.request.Request(
        cleaned,
        headers={
            "User-Agent": WEB_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.8,*/*;q=0.5",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    )
    with urllib.request.urlopen(request, timeout=max(1, min(timeout, 60))) as response:
        content_type = response.headers.get("Content-Type", "")
        raw = response.read(max_bytes + 1)
        truncated = len(raw) > max_bytes
        raw = raw[:max_bytes]
        charset = response.headers.get_content_charset() or "utf-8"
        return {
            "url": response.geturl(),
            "status": getattr(response, "status", 200),
            "content_type": content_type,
            "html": raw.decode(charset, errors="replace"),
            "truncated": truncated,
        }


def _extract_page_content(html: str, base_url: str, max_characters: int) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()

    main = soup.find("main") or soup.find("article") or soup.body or soup
    lines = [line.strip() for line in main.get_text("\n").splitlines() if line.strip()]
    text = "\n".join(lines)
    limit = max(200, min(int(max_characters), 100_000))
    was_truncated = len(text) > limit
    if was_truncated:
        text = text[:limit] + f"\n\n... [İçerik {limit} karakter ile sınırlandırıldı] ..."

    links: List[Dict[str, str]] = []
    seen = set()
    for anchor in soup.find_all("a", href=True):
        href = urllib.parse.urljoin(base_url, anchor.get("href", "").strip())
        label = " ".join(anchor.get_text(" ", strip=True).split())
        if href.startswith(("http://", "https://")) and href not in seen:
            seen.add(href)
            links.append({"metin": label[:200], "url": href})
            if len(links) >= 50:
                break
    return {"baslik": title, "metin": text, "baglantilar": links, "kirpildi": was_truncated}


def _duckduckgo_html_search(query: str, max_results: int) -> List[Dict[str, str]]:
    search_url = "https://html.duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
    downloaded = _download_html(search_url, timeout=20)
    soup = BeautifulSoup(downloaded["html"], "html.parser")
    results: List[Dict[str, str]] = []
    for result in soup.select(".result"):
        anchor = result.select_one(".result__a")
        if not anchor:
            continue
        href = anchor.get("href", "")
        parsed = urllib.parse.urlparse(href)
        if "uddg" in urllib.parse.parse_qs(parsed.query):
            href = urllib.parse.unquote(urllib.parse.parse_qs(parsed.query)["uddg"][0])
        snippet_node = result.select_one(".result__snippet")
        results.append({
            "baslik": anchor.get_text(" ", strip=True),
            "url": href,
            "ozet": snippet_node.get_text(" ", strip=True) if snippet_node else "",
        })
        if len(results) >= max_results:
            break
    return results

@mcp.tool()
def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    DuckDuckGo üzerinden internette ücretsiz ve API key gerektirmeyen anlık arama yapar.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return [{"hata": "Arama sorgusu boş olamaz."}]
    result_limit = max(1, min(int(max_results), 20))
    errors: List[str] = []
    try:
        results: List[Dict[str, str]] = []
        with DDGS(timeout=15) as ddgs:
            raw_results = list(ddgs.text(cleaned_query, max_results=result_limit))
            for r in raw_results:
                results.append({
                    "baslik": r.get("title", "Başlıksız"),
                    "url": r.get("href", ""),
                    "ozet": r.get("body", "")
                })
        if results:
            return results
    except Exception as e:
        errors.append(f"DDGS: {e}")

    try:
        fallback_results = _duckduckgo_html_search(cleaned_query, result_limit)
        if fallback_results:
            return fallback_results
    except Exception as e:
        errors.append(f"DuckDuckGo HTML: {e}")
    return [{"hata": "Web araması başarısız: " + " | ".join(errors)}]


@mcp.tool()
def fetch_web_page_text(url: str, max_characters: int = 4000) -> str:
    """
    Belirtilen web sayfasının okunabilir temiz metnini getirir.
    """
    try:
        downloaded = _download_html(url)
        page = _extract_page_content(downloaded["html"], downloaded["url"], max_characters)
        clean_text = page["metin"]
        if page["baslik"] and page["baslik"] not in clean_text[:500]:
            clean_text = f"{page['baslik']}\n\n{clean_text}".strip()
        return clean_text if clean_text else "Sayfada okunabilir metin bulunamadı."
    except Exception as e:
        return f"HATA: Sayfa çekilemedi: {str(e)}"


def _find_chromium() -> Optional[str]:
    candidates = [
        shutil.which("chrome.exe"), shutil.which("chrome"),
        shutil.which("msedge.exe"), shutil.which("msedge"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


@mcp.tool()
def observe_web_page(
    url: str,
    max_characters: int = 12000,
    render_javascript: bool = True,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    """Bir web sayfasının başlığını, okunabilir metnini ve ilk bağlantılarını gözlemler.

    JavaScript gereken sayfalarda yüklü Chrome/Edge'i headless modda kullanır; tarayıcı
    bulunamazsa otomatik olarak güvenilir statik HTTP indirmesine geri döner.
    """
    try:
        cleaned_url = _normalize_http_url(url)
        html = ""
        final_url = cleaned_url
        mode = "static-http"
        render_error = None

        if render_javascript:
            browser = _find_chromium()
            if browser:
                try:
                    result = _run_process(
                        [
                            browser, "--headless=new", "--disable-gpu", "--no-first-run",
                            "--disable-extensions", "--disable-background-networking",
                            f"--virtual-time-budget={max(1000, min(timeout_seconds * 1000, 30000))}",
                            "--dump-dom", cleaned_url,
                        ],
                        timeout_seconds=timeout_seconds,
                    )
                    if result["returncode"] == 0 and "<" in result["stdout"]:
                        html = result["stdout"]
                        mode = "headless-browser"
                    else:
                        render_error = result["stderr"] or "Tarayıcı DOM üretmedi."
                except Exception as exc:
                    render_error = str(exc)
            else:
                render_error = "Chrome/Edge bulunamadı."

        if not html:
            downloaded = _download_html(cleaned_url, timeout=timeout_seconds)
            html = downloaded["html"]
            final_url = downloaded["url"]

        page = _extract_page_content(html, final_url, max_characters)
        return {
            "url": final_url,
            "mod": mode,
            "baslik": page["baslik"],
            "metin": page["metin"],
            "baglantilar": page["baglantilar"],
            "kirpildi": page["kirpildi"],
            "render_uyarisi": render_error,
        }
    except Exception as exc:
        return {"hata": f"Web sayfası gözlemlenemedi: {exc}"}


@mcp.tool()
def research_web(
    query: str,
    max_pages: int = 20,
    max_characters_per_page: int = 4000,
    concurrency: int = 5,
    timeout_seconds: int = 15,
) -> Dict[str, Any]:
    """Bir sorgunun ilk sonuçlarını paralel okuyarak toplu araştırma verisi üretir.

    Önce web araması yapar, benzersiz sonuç URL'lerini sıralar ve en fazla 20 sayfayı
    sınırlı paralellikle indirir. Her sayfa için arama özeti, başlık, nihai URL ve
    temiz metin döndürür. JavaScript tarayıcısı kullanmaz; hız ve kaynak verimliliği
    için statik HTTP tercih edilir.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return {"basarili": False, "hata": "Araştırma sorgusu boş olamaz."}

    page_limit = max(1, min(int(max_pages), 20))
    text_limit = max(500, min(int(max_characters_per_page), 10_000))
    worker_limit = max(1, min(int(concurrency), 8, page_limit))
    request_timeout = max(5, min(int(timeout_seconds), 30))
    started_at = time.time()

    search_results = web_search(cleaned_query, page_limit)
    if not search_results or search_results[0].get("hata"):
        return {
            "basarili": False,
            "sorgu": cleaned_query,
            "hata": search_results[0].get("hata", "Arama sonucu bulunamadı."),
            "sayfalar": [],
        }

    unique_results: List[Dict[str, str]] = []
    seen_urls = set()
    for result in search_results:
        url = (result.get("url") or "").strip()
        if not url or url in seen_urls:
            continue
        try:
            _normalize_http_url(url)
        except ValueError:
            continue
        seen_urls.add(url)
        unique_results.append(result)
        if len(unique_results) >= page_limit:
            break

    def fetch_result(rank: int, search_result: Dict[str, str]) -> Dict[str, Any]:
        url = search_result["url"]
        downloaded = _download_html(url, timeout=request_timeout, max_bytes=3_000_000)
        content_type = (downloaded.get("content_type") or "").lower()
        if content_type and not any(token in content_type for token in ("html", "text", "json", "xml")):
            raise ValueError(f"Desteklenmeyen içerik türü: {content_type}")
        page = _extract_page_content(downloaded["html"], downloaded["url"], text_limit)
        return {
            "sira": rank,
            "arama_basligi": search_result.get("baslik", ""),
            "arama_ozeti": search_result.get("ozet", ""),
            "url": url,
            "nihai_url": downloaded["url"],
            "sayfa_basligi": page["baslik"],
            "metin": page["metin"],
            "kirpildi": page["kirpildi"] or downloaded.get("truncated", False),
            "icerik_turu": downloaded.get("content_type", ""),
        }

    pages_by_rank: Dict[int, Dict[str, Any]] = {}
    failures: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=worker_limit, thread_name_prefix="web-research") as executor:
        futures = {
            executor.submit(fetch_result, rank, result): (rank, result)
            for rank, result in enumerate(unique_results, start=1)
        }
        for future in as_completed(futures):
            rank, result = futures[future]
            try:
                pages_by_rank[rank] = future.result()
            except Exception as exc:
                failures.append({
                    "sira": rank,
                    "baslik": result.get("baslik", ""),
                    "url": result.get("url", ""),
                    "hata": str(exc),
                })

    pages = [pages_by_rank[index] for index in sorted(pages_by_rank)]
    failures.sort(key=lambda item: item["sira"])
    return {
        "basarili": bool(pages),
        "sorgu": cleaned_query,
        "istenen_sayfa": page_limit,
        "bulunan_benzersiz_sonuc": len(unique_results),
        "okunan_sayfa": len(pages),
        "basarisiz_sayfa": len(failures),
        "eszamanlilik": worker_limit,
        "sure_ms": round((time.time() - started_at) * 1000, 2),
        "sayfalar": pages,
        "hatalar": failures,
    }


@mcp.tool()
def websocket_connect(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    subprotocols: Optional[List[str]] = None,
    open_timeout_seconds: int = 10,
    max_message_bytes: int = 1_048_576,
) -> Dict[str, Any]:
    """Bir ws:// veya wss:// adresine kalıcı bağlantı açar ve connection_id döndürür.

    Özel HTTP başlıkları ve WebSocket alt protokolleri desteklenir. Bağlantı MCP
    sunucusu belleğinde tutulur; sunucu yeniden başlatılırsa bağlantı kaybolur.
    """
    connection = None
    try:
        cleaned_url = _normalize_websocket_url(url)
        clean_headers = _websocket_headers(headers)
        clean_subprotocols = [str(item).strip() for item in (subprotocols or []) if str(item).strip()]
        timeout = max(1, min(int(open_timeout_seconds), 120))
        message_limit = max(1_024, min(int(max_message_bytes), MAX_WEBSOCKET_MESSAGE_BYTES))

        with _WEBSOCKET_REGISTRY_LOCK:
            if len(_WEBSOCKET_CONNECTIONS) >= MAX_WEBSOCKET_CONNECTIONS:
                return {
                    "basarili": False,
                    "hata": f"En fazla {MAX_WEBSOCKET_CONNECTIONS} eşzamanlı WebSocket bağlantısı açılabilir.",
                }

        connection = websocket_client_connect(
            cleaned_url,
            additional_headers=clean_headers or None,
            subprotocols=clean_subprotocols or None,
            open_timeout=timeout,
            close_timeout=timeout,
            max_size=message_limit,
        )
        connection_id = uuid.uuid4().hex
        entry = {
            "connection": connection,
            "lock": threading.RLock(),
            "url": cleaned_url,
            "created_at": time.time(),
            "subprotocol": connection.subprotocol,
            "max_message_bytes": message_limit,
        }
        with _WEBSOCKET_REGISTRY_LOCK:
            if len(_WEBSOCKET_CONNECTIONS) >= MAX_WEBSOCKET_CONNECTIONS:
                connection.close()
                return {
                    "basarili": False,
                    "hata": f"En fazla {MAX_WEBSOCKET_CONNECTIONS} eşzamanlı WebSocket bağlantısı açılabilir.",
                }
            _WEBSOCKET_CONNECTIONS[connection_id] = entry
        return {
            "basarili": True,
            "connection_id": connection_id,
            "url": cleaned_url,
            "subprotocol": connection.subprotocol,
            "max_message_bytes": message_limit,
        }
    except Exception as exc:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
        return {"basarili": False, "hata": f"WebSocket bağlantısı açılamadı: {exc}"}


@mcp.tool()
def websocket_send(connection_id: str, message: str, binary_base64: bool = False) -> Dict[str, Any]:
    """Açık WebSocket bağlantısına metin veya Base64 kodlu ikili mesaj gönderir."""
    try:
        entry = _get_websocket_connection(connection_id)
        if binary_base64:
            payload = base64.b64decode(message or "", validate=True)
            message_type = "binary"
        else:
            payload = message or ""
            message_type = "text"
        payload_size = len(payload if isinstance(payload, bytes) else payload.encode("utf-8"))
        if payload_size > entry["max_message_bytes"]:
            return {
                "basarili": False,
                "hata": f"Mesaj {entry['max_message_bytes']} bayt bağlantı sınırını aşıyor.",
            }
        with entry["lock"]:
            entry["connection"].send(payload)
        return {"basarili": True, "connection_id": connection_id, "tur": message_type, "bayt": payload_size}
    except ConnectionClosed as exc:
        _remove_websocket_connection(connection_id)
        return {"basarili": False, "hata": f"WebSocket bağlantısı kapalı: {exc}"}
    except Exception as exc:
        return {"basarili": False, "hata": f"WebSocket mesajı gönderilemedi: {exc}"}


@mcp.tool()
def websocket_receive(connection_id: str, timeout_seconds: int = 10) -> Dict[str, Any]:
    """Açık WebSocket bağlantısından bir sonraki metin veya ikili mesajı alır."""
    try:
        entry = _get_websocket_connection(connection_id)
        timeout = max(0.1, min(float(timeout_seconds), 300.0))
        with entry["lock"]:
            message = entry["connection"].recv(timeout=timeout)
        if isinstance(message, bytes):
            return {
                "basarili": True,
                "connection_id": connection_id,
                "tur": "binary",
                "base64": base64.b64encode(message).decode("ascii"),
                "bayt": len(message),
            }
        return {
            "basarili": True,
            "connection_id": connection_id,
            "tur": "text",
            "mesaj": message,
            "bayt": len(message.encode("utf-8")),
        }
    except TimeoutError:
        return {"basarili": False, "zaman_asimi": True, "hata": "Bekleme süresinde WebSocket mesajı gelmedi."}
    except ConnectionClosed as exc:
        _remove_websocket_connection(connection_id)
        return {"basarili": False, "hata": f"WebSocket bağlantısı kapandı: {exc}"}
    except Exception as exc:
        return {"basarili": False, "hata": f"WebSocket mesajı alınamadı: {exc}"}


@mcp.tool()
def websocket_ping(connection_id: str, payload: str = "", timeout_seconds: int = 10) -> Dict[str, Any]:
    """WebSocket bağlantısına ping gönderir ve eşleşen pong yanıtını bekler."""
    try:
        entry = _get_websocket_connection(connection_id)
        timeout = max(0.1, min(float(timeout_seconds), 120.0))
        ping_payload = (payload or "").encode("utf-8")
        if len(ping_payload) > 125:
            return {"basarili": False, "hata": "Ping yükü WebSocket sınırı olan 125 baytı aşamaz."}
        with entry["lock"]:
            pong_event = entry["connection"].ping(ping_payload)
            pong_received = pong_event.wait(timeout)
        return {
            "basarili": bool(pong_received),
            "connection_id": connection_id,
            "pong_alindi": bool(pong_received),
            "hata": None if pong_received else "Pong yanıtı zaman aşımına uğradı.",
        }
    except ConnectionClosed as exc:
        _remove_websocket_connection(connection_id)
        return {"basarili": False, "hata": f"WebSocket bağlantısı kapandı: {exc}"}
    except Exception as exc:
        return {"basarili": False, "hata": f"WebSocket ping gönderilemedi: {exc}"}


@mcp.tool()
def websocket_close(connection_id: str) -> Dict[str, Any]:
    """Kalıcı WebSocket bağlantısını kapatır ve bağlantı havuzundan çıkarır."""
    removed = _remove_websocket_connection((connection_id or "").strip())
    if not removed:
        return {"basarili": False, "hata": f"WebSocket bağlantısı bulunamadı: {connection_id}"}
    return {"basarili": True, "connection_id": connection_id, "kapandi": True}


@mcp.tool()
def websocket_list_connections() -> Dict[str, Any]:
    """Sunucu belleğinde tutulan açık WebSocket bağlantılarını listeler."""
    now = time.time()
    with _WEBSOCKET_REGISTRY_LOCK:
        connections = [
            {
                "connection_id": connection_id,
                "url": entry["url"],
                "subprotocol": entry["subprotocol"],
                "acik_sure_saniye": round(now - entry["created_at"], 2),
                "max_message_bytes": entry["max_message_bytes"],
            }
            for connection_id, entry in _WEBSOCKET_CONNECTIONS.items()
        ]
    return {"basarili": True, "baglanti_sayisi": len(connections), "baglantilar": connections}


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
    """Bağlan, mesaj gönder, belirli sayıda yanıt al ve bağlantıyı kapat akışını tek çağrıda yapar."""
    opened = websocket_connect(url, headers, subprotocols, timeout_seconds, max_message_bytes)
    if not opened.get("basarili"):
        return opened
    connection_id = opened["connection_id"]
    responses: List[Dict[str, Any]] = []
    try:
        sent = websocket_send(connection_id, message, binary_base64)
        if not sent.get("basarili"):
            return sent
        for _ in range(max(0, min(int(receive_count), 20))):
            received = websocket_receive(connection_id, timeout_seconds)
            responses.append(received)
            if not received.get("basarili"):
                break
        return {
            "basarili": all(response.get("basarili") for response in responses) if responses else True,
            "url": opened["url"],
            "subprotocol": opened.get("subprotocol"),
            "gonderim": sent,
            "yanitlar": responses,
        }
    finally:
        _remove_websocket_connection(connection_id)


# ==============================================================================
# 4. BÖLÜM: KOD TABANI İNCELEME, DOSYA OLUŞTURMA, DÜZENLEME & SİLME
# ==============================================================================

DEFAULT_IGNORE_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv",
    "__pycache__", ".pytest_cache", "build", "dist", ".pdf_cache",
    ".idea", ".vscode", "target", "bin", "obj"
}


@mcp.tool()
def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    Belirtilen kaynak kod dosyasını (C++, Python, HTML, CSS, JS vb.) okur.
    Büyük dosyalarda context window'u korumak için satır aralığı (start_line, end_line) belirtilebilir (1-indeksli).
    """
    if not os.path.exists(file_path):
        return f"HATA: Dosya bulunamadı: {file_path}"
    if os.path.isdir(file_path):
        return f"HATA: '{file_path}' bir dizindir. 'list_codebase_tree' kullanın."

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if start_line is not None or end_line is not None:
            s = max(1, start_line if start_line is not None else 1)
            e = min(total_lines, end_line if end_line is not None else total_lines)
            selected = lines[s - 1:e]
            content = "".join([f"{idx:4d} | {line}" for idx, line in enumerate(selected, start=s)])
            return f"--- [{file_path} (Satır {s}-{e} / Toplam {total_lines})] ---\n\n{content}"
        else:
            if total_lines > 500:
                snippet = "".join([f"{idx:4d} | {line}" for idx, line in enumerate(lines[:500], start=1)])
                return f"--- [{file_path} (İlk 500 satır gösteriliyor, Toplam: {total_lines})] ---\n\n{snippet}\n\n... [Dosya uzun olduğu için kesildi. Devamı için start_line=501 ile çağırın] ..."
            else:
                return "".join([f"{idx:4d} | {line}" for idx, line in enumerate(lines, start=1)])
    except Exception as e:
        return f"HATA: Dosya okunurken sorun: {str(e)}"


@mcp.tool()
def write_file(file_path: str, content: str, overwrite: bool = True) -> str:
    """
    Sıfırdan dosya oluşturur veya mevcut dosyanın üzerine yazar.
    HTML, CSS, C++, Python ve diğer tüm kaynak kod dosyalarını tırnak veya karakter bozulması olmadan kaydeder.
    """
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        if os.path.exists(file_path) and not overwrite:
            return f"HATA: '{file_path}' zaten mevcut ve 'overwrite=False' seçilmiş."

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"BAŞARILI: '{file_path}' dosyası başarıyla yazıldı ({len(content)} karakter)."
    except Exception as e:
        return f"HATA: Dosya yazılırken sorun: {str(e)}"


@mcp.tool()
def edit_file_snippet(file_path: str, target_snippet: str, replacement_snippet: str) -> str:
    """
    Mevcut bir kaynak kod dosyasında belirli bir kod bloğunu veya fonksiyonu cerrahi olarak değiştirir (Search & Replace).
    Tüm dosyayı baştan yazmak yerine sadece değişmesi gereken satırları güncellemek için idealdir.
    """
    if not os.path.exists(file_path):
        return f"HATA: Dosya bulunamadı: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if target_snippet not in content:
            return f"HATA: Değiştirilmek istenen 'target_snippet' dosya içerisinde tam olarak bulunamadı. Lütfen 'read_file' ile dosyadaki mevcut satırları kontrol edin."

        occurrence_count = content.count(target_snippet)
        if occurrence_count > 1:
            return f"UYARI: Değiştirilmek istenen blok dosyada {occurrence_count} kez geçiyor. Lütfen daha belirgin bir hedef blok seçin."

        new_content = content.replace(target_snippet, replacement_snippet, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"BAŞARILI: '{file_path}' dosyasındaki hedef kod parçası güncellendi."
    except Exception as e:
        return f"HATA: Düzenleme sırasında sorun: {str(e)}"


@mcp.tool()
def delete_file(file_path: str) -> str:
    """
    Belirtilen bir dosyayı diskten siler.
    """
    if not os.path.exists(file_path):
        return f"HATA: Dosya bulunamadı: {file_path}"
    if os.path.isdir(file_path):
        return f"HATA: '{file_path}' bir klasördür. Bu araç yalnızca dosya silmek içindir."

    try:
        os.remove(file_path)
        return f"BAŞARILI: '{file_path}' dosyası başarıyla silindi."
    except Exception as e:
        return f"HATA: Dosya silinirken sorun: {str(e)}"


@mcp.tool()
def list_codebase_tree(directory_path: str = ".", max_depth: int = 3) -> str:
    """
    Bir kod projesinin dizin ve dosya hiyerarşisini (ağaç yapısını) çıkarır.
    'node_modules', '.git', 'venv' gibi gürültü oluşturan klasörleri otomatik olarak atlar.
    """
    if not os.path.exists(directory_path):
        return f"HATA: Dizin bulunamadı: {directory_path}"

    root_abs = os.path.abspath(directory_path)
    tree_lines = [f"[DIR] {os.path.basename(root_abs) or root_abs}/"]

    def build_tree(current_dir: str, depth: int, prefix: str):
        if depth > max_depth:
            return

        try:
            entries = sorted(os.listdir(current_dir))
        except PermissionError:
            return

        dirs = [e for e in entries if os.path.isdir(os.path.join(current_dir, e)) and e not in DEFAULT_IGNORE_DIRS]
        files = [e for e in entries if os.path.isfile(os.path.join(current_dir, e))]

        total_items = len(dirs) + len(files)
        counter = 0

        for d in dirs:
            counter += 1
            is_last = (counter == total_items)
            branch = "`-- " if is_last else "|-- "
            tree_lines.append(f"{prefix}{branch}[DIR] {d}/")
            next_prefix = prefix + ("    " if is_last else "|   ")
            build_tree(os.path.join(current_dir, d), depth + 1, next_prefix)

        for f in files:
            counter += 1
            is_last = (counter == total_items)
            branch = "`-- " if is_last else "|-- "
            tree_lines.append(f"{prefix}{branch}[FILE] {f}")

    build_tree(root_abs, 1, "")
    return "\n".join(tree_lines)


@mcp.tool()
def search_code(
    query: str,
    directory_path: str = ".",
    file_extensions: Optional[List[str]] = None,
    max_matches: int = 10
) -> List[Dict[str, Any]]:
    """
    Kod tabanındaki dosyalarda fonksiyon, sınıf, değişken veya anahtar kelime araması yapar.
    (C++, Python, HTML, CSS dosyalarında satır numarası ve kod satırını döner).
    """
    if not os.path.exists(directory_path):
        return [{"hata": f"Dizin bulunamadı: {directory_path}"}]

    clean_exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in file_extensions] if file_extensions else None
    matches = []

    for root, dirs, files in os.walk(directory_path):
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if clean_exts and ext not in clean_exts:
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, start=1):
                        if query.lower() in line.lower():
                            matches.append({
                                "dosya": os.path.relpath(file_path, directory_path),
                                "satir_no": line_idx,
                                "kod": line.strip()
                            })
                            if len(matches) >= max_matches:
                                return matches
            except Exception:
                continue

    return matches if matches else [{"mesaj": f"'{query}' ifadesi eşleşen dosyalarda bulunamadı."}]


# ==============================================================================
# 5. BÖLÜM: KALICI PROJE HAFIZASI (PERSISTENT MEMORY)
# ==============================================================================

MEMORY_FILE = os.path.join(os.getcwd(), ".agent_memory.json")


def _load_memory() -> Dict[str, Any]:
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_memory_file(data: Dict[str, Any]) -> None:
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@mcp.tool()
def save_memory(key: str, value: str, category: str = "genel") -> str:
    """
    Önemli bir kuralı, kararı veya tercihi kalıcı hafızaya kaydeder.
    """
    data = _load_memory()
    data[key] = {"deger": value, "kategori": category}
    _save_memory_file(data)
    return f"BAŞARILI: '{key}' bilgisi ({category}) kalıcı hafızaya kaydedildi."


@mcp.tool()
def read_memory(key: str) -> str:
    """
    Kalıcı hafızadan belirli bir anahtara ait bilgiyi getirir.
    """
    data = _load_memory()
    if key in data:
        item = data[key]
        return f"[{key.upper()} - Kategori: {item.get('kategori', 'genel')}]\n{item.get('deger')}"
    return f"HATA: '{key}' anahtarıyla kayıtlı bilgi bulunamadı."


@mcp.tool()
def list_memories(category: Optional[str] = None) -> str:
    """
    Kalıcı hafızadaki tüm kayıtları veya belirtilen kategorideki kayıtları listeler.
    """
    data = _load_memory()
    if not data:
        return "Kalıcı hafızada henüz kayıtlı bilgi bulunmamaktadır."

    lines = ["=== Proje Kalıcı Hafızası ==="]
    for k, v in data.items():
        cat = v.get("kategori", "genel")
        if category and cat.lower() != category.lower():
            continue
        lines.append(f"- [{cat}] {k}: {v.get('deger')}")

    if len(lines) == 1 and category:
        return f"'{category}' kategorisinde kayıtlı bilgi bulunamadı."

    return "\n".join(lines)


@mcp.tool()
def delete_memory(key: str) -> str:
    """
    Kalıcı hafızadan eski veya geçersiz bir bilgiyi siler.
    """
    data = _load_memory()
    if key in data:
        del data[key]
        _save_memory_file(data)
        return f"BAŞARILI: '{key}' bilgisi silindi."
    return f"HATA: '{key}' anahtarı bulunamadı."


# ==============================================================================
# 6. BÖLÜM: OTONOM PLAN & GÖREV TAKİPÇİSİ (TASK PLANNER)
# ==============================================================================

PLAN_FILE = os.path.join(os.getcwd(), ".agent_plan.json")


def _load_plan() -> Dict[str, Any]:
    if os.path.exists(PLAN_FILE):
        try:
            with open(PLAN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"gorevler": []}
    return {"gorevler": []}


def _save_plan_file(data: Dict[str, Any]) -> None:
    with open(PLAN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@mcp.tool()
def create_plan(tasks: List[str]) -> str:
    """
    Çok adımlı bir görev için yeni bir iş planı başlatır.
    """
    if not tasks:
        return "HATA: En az bir görev tanımlanmalıdır."

    plan_items = [{"id": idx, "gorev": t, "durum": "todo", "not": ""} for idx, t in enumerate(tasks, start=1)]
    _save_plan_file({"gorevler": plan_items})
    return f"BAŞARILI: {len(tasks)} adımlık plan oluşturuldu."


@mcp.tool()
def update_task_status(task_id: int, status: str, note: Optional[str] = None) -> str:
    """
    Belirli bir görevin durumunu günceller ('todo', 'in_progress', 'completed', 'failed').
    """
    valid_statuses = {"todo", "in_progress", "completed", "failed"}
    if status.lower() not in valid_statuses:
        return f"HATA: Geçersiz durum '{status}'."

    data = _load_plan()
    tasks = data.get("gorevler", [])
    for item in tasks:
        if item["id"] == task_id:
            item["durum"] = status.lower()
            if note:
                item["not"] = note
            _save_plan_file(data)
            return f"BAŞARILI: Görev #{task_id} durumu '{status}' olarak güncellendi."

    return f"HATA: ID={task_id} olan görev bulunamadı."


@mcp.tool()
def get_current_plan() -> str:
    """
    Mevcut planı, tamamlanan adımları ve kalan görevleri görüntüler.
    """
    data = _load_plan()
    tasks = data.get("gorevler", [])
    if not tasks:
        return "Aktif bir görev planı bulunmuyor."

    total = len(tasks)
    completed = sum(1 for t in tasks if t["durum"] == "completed")
    icons = {"todo": "[ ]", "in_progress": "[→]", "completed": "[✓]", "failed": "[✗]"}

    lines = [f"=== Ajan Görev Planı ({completed}/{total} Tamamlandı) ==="]
    for t in tasks:
        icon = icons.get(t["durum"], "[?]")
        note_str = f" (Not: {t['not']})" if t.get("not") else ""
        lines.append(f"{icon} #{t['id']}: {t['gorev']} [{t['durum']}]{note_str}")

    return "\n".join(lines)


@mcp.tool()
def clear_plan() -> str:
    """
    Mevcut planı sıfırlar.
    """
    _save_plan_file({"gorevler": []})
    return "Mevcut plan sıfırlandı."


# ==============================================================================
# 7. BÖLÜM: REST API & HTTP İSTEMCİSİ
# ==============================================================================

@mcp.tool()
def http_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    json_body: Optional[Any] = None,
    params: Optional[Dict[str, str]] = None,
    timeout: int = 15
) -> Dict[str, Any]:
    """
    HTTP isteği gönderir (GET, POST, PUT, DELETE, PATCH).
    """
    cleaned_method = method.upper().strip()
    req_headers = headers.copy() if headers else {}

    final_url = url
    if params:
        query_string = urllib.parse.urlencode(params)
        final_url = f"{final_url}?{query_string}" if "?" not in final_url else f"{final_url}&{query_string}"

    data_bytes = None
    if json_body is not None:
        data_bytes = json.dumps(json_body).encode("utf-8")
        if "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"

    if "User-Agent" not in req_headers:
        req_headers["User-Agent"] = "Local-Agentic-Dev/1.0"

    req = urllib.request.Request(final_url, data=data_bytes, headers=req_headers, method=cleaned_method)
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            raw_body = response.read().decode("utf-8", errors="replace")
            try:
                parsed_body = json.loads(raw_body)
            except Exception:
                parsed_body = raw_body

            return {"durum_kodu": response.status, "sure_ms": elapsed_ms, "yanit": parsed_body, "basarili": True}

    except urllib.error.HTTPError as e:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed_err = json.loads(error_body)
        except Exception:
            parsed_err = error_body
        return {"durum_kodu": e.code, "hata": f"HTTP {e.code}: {e.reason}", "yanit": parsed_err, "sure_ms": elapsed_ms, "basarili": False}
    except Exception as e:
        return {"hata": f"Bağlantı hatası: {str(e)}", "basarili": False}


# ==============================================================================
# 8. BÖLÜM: YEREL GÖRSEL & MOCKUP İNCELEME (VISION)
# ==============================================================================

VISION_CACHE_DIR = os.path.join(os.getcwd(), ".vision_cache")
os.makedirs(VISION_CACHE_DIR, exist_ok=True)


@mcp.tool()
def inspect_local_image(image_path: str, max_dimension: int = 1280) -> Dict[str, Any]:
    """
    Yerel bir görseli (UI mockup, şema) VRAM dostu boyuta optimize eder ve incelenmeye hazır hale getirir.
    """
    if not os.path.exists(image_path):
        return {"hata": f"Görsel bulunamadı: {image_path}"}

    try:
        with Image.open(image_path) as img:
            orig_width, orig_height = img.size
            if max(orig_width, orig_height) > max_dimension:
                ratio = min(max_dimension / orig_width, max_dimension / orig_height)
                new_width, new_height = int(orig_width * ratio), int(orig_height * ratio)
                resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                out_path = os.path.join(VISION_CACHE_DIR, f"{base_name}_opt_{new_width}x{new_height}.png")
                
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    resized.save(out_path, "PNG")
                else:
                    resized.convert("RGB").save(out_path, "PNG")

                return {
                    "durum": "Optimize Edildi",
                    "orijinal_boyut": f"{orig_width}x{orig_height}",
                    "optimize_boyut": f"{new_width}x{new_height}",
                    "gorsel_dosya_yolu": os.path.abspath(out_path),
                    "mesaj": "Görsel VRAM sınırlarını korumak için optimize edildi. Vision yeteneğiniz ile inceleyebilirsiniz."
                }
            else:
                return {
                    "durum": "Doğrudan Hazır",
                    "boyut": f"{orig_width}x{orig_height}",
                    "gorsel_dosya_yolu": os.path.abspath(image_path),
                    "mesaj": "Görsel boyutu ideal. Vision yeteneğiniz ile doğrudan inceleyebilirsiniz."
                }
    except Exception as e:
        return {"hata": f"Görsel işlenirken hata: {str(e)}"}


@mcp.tool()
def get_image_metadata(image_path: str) -> Dict[str, Any]:
    """
    Görselin dosya boyutu, formatı ve çözünürlük bilgilerini döner.
    """
    if not os.path.exists(image_path):
        return {"hata": f"Dosya bulunamadı: {image_path}"}

    try:
        file_size_kb = round(os.path.getsize(image_path) / 1024, 2)
        with Image.open(image_path) as img:
            return {
                "dosya_adi": os.path.basename(image_path),
                "format": img.format,
                "cozunurluk": f"{img.width}x{img.height}",
                "boyut_kb": file_size_kb
            }
    except Exception as e:
        return {"hata": f"Meta veri hatası: {str(e)}"}


# ==============================================================================
# 9. BÖLÜM: YEREL VERİTABANI & SQLITE İNCELEME
# ==============================================================================

@mcp.tool()
def get_database_schema(db_path: str) -> Dict[str, Any]:
    """
    SQLite veritabanının tüm tablo şemalarını, sütun isimlerini ve veri tiplerini listeler.
    """
    if not os.path.exists(db_path):
        return {"hata": f"Veritabanı bulunamadı: {db_path}"}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]

        schema_report = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            cols = [{"sutun": c[1], "tip": c[2] or "BLOB", "pk": bool(c[5])} for c in cursor.fetchall()]
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            schema_report[table] = {"kayit_sayisi": count, "sutunlar": cols}

        conn.close()
        return {"veritabani": os.path.basename(db_path), "tablo_sayisi": len(tables), "tablolar": schema_report}
    except Exception as e:
        return {"hata": f"Şema hatası: {str(e)}"}


@mcp.tool()
def execute_sql_query(db_path: str, query: str, max_rows: int = 25) -> Dict[str, Any]:
    """
    SQLite veritabanında SQL sorgusu çalıştırır.
    """
    if not os.path.exists(db_path):
        return {"hata": f"Veritabanı bulunamadı: {db_path}"}

    cleaned = query.strip()
    is_select = cleaned.upper().startswith("SELECT") or cleaned.upper().startswith("PRAGMA")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(cleaned)

        if is_select:
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(max_rows)
            formatted = [dict(zip(col_names, r)) for r in rows]
            conn.close()
            return {"durum": "Başarılı", "sutunlar": col_names, "satir_sayisi": len(formatted), "sonuclar": formatted}
        else:
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return {"durum": "Başarılı", "etkilenen_satir": affected}
    except Exception as e:
        return {"hata": f"SQL hatası: {str(e)}"}


# ==============================================================================
# 10. BÖLÜM: MERMAID DİYAGRAM VE MARKDOWN TO PNG ARAÇLARI
# ==============================================================================

DIAGRAM_CACHE_DIR = os.path.join(os.getcwd(), ".diagram_cache")
os.makedirs(DIAGRAM_CACHE_DIR, exist_ok=True)


def _resolve_wsl(path_str: str) -> str:
    cleaned = path_str.strip()
    if cleaned.startswith("/") and not cleaned.startswith("//"):
        slash_path = cleaned.replace("/", "\\")
        return f"\\\\wsl$\\Ubuntu{slash_path}"
    return cleaned


@mcp.tool()
def render_mermaid_to_png(
    mermaid_code_or_file: str,
    output_png_path: str,
    theme: str = "default",
    scale: int = 2
) -> Dict[str, Any]:
    """
    Mermaid formatındaki akış şeması veya mimari diyagramı doğrudan yüksek kaliteli PNG görseline dönüştürür.
    Doğrudan ham Mermaid kodu veya içinde mermaid kodu olan bir dosya yolu verilebilir.
    """
    input_str = mermaid_code_or_file.strip()
    clean_output = _resolve_wsl(output_png_path)
    clean_input_path = _resolve_wsl(input_str)

    mermaid_code = input_str
    if os.path.exists(clean_input_path) and os.path.isfile(clean_input_path):
        try:
            with open(clean_input_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            match = re.search(r"```mermaid\s*\n(.*?)\n```", content, re.DOTALL)
            mermaid_code = match.group(1).strip() if match else content.strip()
        except Exception as e:
            return {"hata": f"Dosya okunurken hata: {str(e)}"}

    out_dir = os.path.dirname(os.path.abspath(clean_output))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    try:
        final_mermaid = mermaid_code
        if theme and theme != "default":
            final_mermaid = f"%%{{init: {{'theme': '{theme}'}}}}%%\n{mermaid_code}"

        b64_code = base64.urlsafe_b64encode(final_mermaid.encode("utf-8")).decode("ascii")
        img_url = f"https://mermaid.ink/img/{b64_code}"

        req = urllib.request.Request(
            img_url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

        with urllib.request.urlopen(req, timeout=20) as response:
            png_bytes = response.read()

        abs_out = os.path.abspath(clean_output)
        with open(abs_out, "wb") as f:
            f.write(png_bytes)

        size_kb = round(len(png_bytes) / 1024, 2)
        return {
            "durum": "Başarılı",
            "hedef_png": abs_out,
            "boyut_kb": size_kb,
            "tema": theme,
            "mesaj": f"Mermaid diyagramı başarıyla PNG olarak kaydedildi ({size_kb} KB)."
        }
    except Exception as e:
        return {"hata": f"Diyagram PNG'ye dönüştürülürken hata: {str(e)}"}


@mcp.tool()
def extract_and_render_all_mermaid_diagrams(
    input_md_path: str,
    output_directory: str
) -> Dict[str, Any]:
    """
    Bir Markdown (.md) dosyasındaki TÜM ```mermaid ... ``` kod bloklarını bulur ve
    her birini ayrı ayrı PNG dosyası olarak belirtilen klasöre kaydeder.
    """
    clean_md = _resolve_wsl(input_md_path)
    clean_out_dir = _resolve_wsl(output_directory)

    if not os.path.exists(clean_md):
        return {"hata": f"Markdown dosyası bulunamadı: {clean_md}"}

    os.makedirs(clean_out_dir, exist_ok=True)
    try:
        with open(clean_md, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        diagrams = re.findall(r"```mermaid\s*\n(.*?)\n```", content, re.DOTALL)
        if not diagrams:
            return {"mesaj": "Markdown dosyasında herhangi bir ```mermaid bloğu bulunamadı."}

        rendered_files = []
        for idx, diag in enumerate(diagrams, start=1):
            out_file = os.path.join(clean_out_dir, f"diagram_{idx}.png")
            res = render_mermaid_to_png(mermaid_code_or_file=diag, output_png_path=out_file)
            if res.get("durum") == "Başarılı":
                rendered_files.append(res.get("hedef_png"))

        return {
            "durum": "Başarılı",
            "toplam_diyagram": len(diagrams),
            "basarili_sayisi": len(rendered_files),
            "uretilen_dosyalar": rendered_files
        }
    except Exception as e:
        return {"hata": f"Diyagramlar taranırken hata: {str(e)}"}


@mcp.tool()
def convert_markdown_to_png(
    input_md_path: str,
    output_png_path: str,
    page_number: int = 1,
    dpi: int = 150
) -> Dict[str, Any]:
    """
    Bir Markdown dosyasını yüksek kaliteli PNG görseli olarak kaydeder.
    """
    clean_md = _resolve_wsl(input_md_path)
    clean_out_png = _resolve_wsl(output_png_path)

    temp_pdf = os.path.join(DIAGRAM_CACHE_DIR, f"temp_{os.getpid()}.pdf")
    try:
        pdf_res = convert_markdown_to_pdf(clean_md, temp_pdf)
        if "hata" in pdf_res:
            return pdf_res

        doc = fitz.open(temp_pdf)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            return {"hata": f"Geçersiz sayfa numarası ({page_number}). Toplam sayfa: {len(doc)}"}

        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=dpi)

        abs_out = os.path.abspath(clean_out_png)
        out_dir = os.path.dirname(abs_out)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        pix.save(abs_out)
        doc.close()
        try:
            os.remove(temp_pdf)
        except Exception:
            pass

        return {
            "durum": "Başarılı",
            "kaynak_md": clean_md,
            "hedef_png": abs_out,
            "cozunurluk": f"{pix.width}x{pix.height}",
            "mesaj": f"Markdown sayfası başarıyla PNG olarak kaydedildi."
        }
    except Exception as e:
        return {"hata": f"Markdown PNG'ye dönüştürülürken hata: {str(e)}"}


# ==============================================================================
# 11. BÖLÜM: OFİS BELGELERİ (WORD .DOCX & POWERPOINT .PPTX) OKUMA ARAÇLARI
# ==============================================================================

@mcp.tool()
def read_docx(file_path: str, extract_tables: bool = True) -> Dict[str, Any]:
    """
    Microsoft Word (.docx) belgesini açar; başlıkları, paragrafları ve tabloları
    yapılandırılmış temiz bir JSON formatında döner.

    Parametreler:
        file_path: Okunacak Word (.docx) dosyasının yolu (WSL veya Windows yolu).
        extract_tables: Belgedeki tablolar 2D liste matrisi olarak çıkarılsın mı? (varsayılan: True).
    """
    clean_path = _resolve_wsl(file_path)
    if not os.path.exists(clean_path):
        return {"hata": f"Word dosyası bulunamadı: {clean_path}"}

    try:
        doc = docx.Document(clean_path)
        paragraphs_data = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                style_name = p.style.name if p.style else "Normal"
                paragraphs_data.append({
                    "stil": style_name,
                    "metin": text
                })

        tables_data = []
        if extract_tables:
            for t_idx, table in enumerate(doc.tables, start=1):
                table_matrix = []
                for row in table.rows:
                    row_cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    table_matrix.append(row_cells)
                if table_matrix:
                    tables_data.append({
                        "tablo_no": t_idx,
                        "satirlar": table_matrix
                    })

        return {
            "dosya": os.path.basename(clean_path),
            "toplam_paragraf": len(paragraphs_data),
            "toplam_tablo": len(tables_data),
            "icerik": paragraphs_data,
            "tablolar": tables_data
        }

    except Exception as e:
        return {"hata": f"DOCX dosyası okunurken hata oluştu: {str(e)}"}


@mcp.tool()
def search_docx(file_path: str, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Word (.docx) dokümanında anahtar kelime araması yapar.
    Tüm belgeyi belleğe yüklemeden sadece eşleşen paragrafları döner.

    Parametreler:
        file_path: Word dosyası yolu.
        query: Aranacak kelime veya ifade.
        max_results: Getirilecek maksimum eşleşme sayısı (varsayılan: 5).
    """
    clean_path = _resolve_wsl(file_path)
    if not os.path.exists(clean_path):
        return [{"hata": f"Dosya bulunamadı: {clean_path}"}]

    try:
        doc = docx.Document(clean_path)
        results = []

        for idx, p in enumerate(doc.paragraphs, start=1):
            if query.lower() in p.text.lower():
                results.append({
                    "tip": "paragraf",
                    "konum": f"Paragraf #{idx}",
                    "metin": p.text.strip()
                })
                if len(results) >= max_results:
                    break

        return results if results else [{"mesaj": f"'{query}' ifadesi belgede bulunamadı."}]
    except Exception as e:
        return [{"hata": f"DOCX araması sırasında hata: {str(e)}"}]


@mcp.tool()
def get_pptx_outline(file_path: str) -> Dict[str, Any]:
    """
    PowerPoint (.pptx) sunumunun slayt sayısını ve her slaydın başlığını (İçindekiler / Outline) çıkarır.
    Sunumun genel yapısını hızlıca anlamak için ilk çağrılacak hafif araçtır.

    Parametreler:
        file_path: PowerPoint (.pptx) dosya yolu.
    """
    clean_path = _resolve_wsl(file_path)
    if not os.path.exists(clean_path):
        return {"hata": f"Sunum dosyası bulunamadı: {clean_path}"}

    try:
        prs = pptx.Presentation(clean_path)
        outline = []

        for idx, slide in enumerate(prs.slides, start=1):
            title = "Başlıksız Slayt"
            if slide.shapes.title and slide.shapes.title.text:
                title = slide.shapes.title.text.strip()
            outline.append(f"Slayt {idx}: {title}")

        return {
            "dosya": os.path.basename(clean_path),
            "toplam_slayt": len(prs.slides),
            "slayt_basliklari": outline
        }
    except Exception as e:
        return {"hata": f"PPTX özeti çıkarılırken hata: {str(e)}"}


@mcp.tool()
def read_pptx(
    file_path: str,
    start_slide: int = 1,
    end_slide: Optional[int] = None
) -> Dict[str, Any]:
    """
    PowerPoint (.pptx) sunumunun belirtilen slayt aralığındaki metinleri, maddeleri,
    tabloları ve Varsa Konuşmacı Notlarını (Speaker Notes) yapılandırılmış JSON formatında okur.

    Parametreler:
        file_path: PowerPoint (.pptx) dosya yolu.
        start_slide: Başlangıç slayt numarası (1-indeksli).
        end_slide: Bitiş slayt numarası (opsiyonel, boş bırakılırsa tüm sunum okunur).
    """
    clean_path = _resolve_wsl(file_path)
    if not os.path.exists(clean_path):
        return {"hata": f"Sunum dosyası bulunamadı: {clean_path}"}

    try:
        prs = pptx.Presentation(clean_path)
        total_slides = len(prs.slides)

        if start_slide < 1 or start_slide > total_slides:
            return {"hata": f"Geçersiz başlangıç slaydı ({start_slide}). Toplam slayt: {total_slides}"}

        target_end = min(end_slide if end_slide else total_slides, total_slides)
        slides_data = []

        for slide_idx in range(start_slide - 1, target_end):
            slide = prs.slides[slide_idx]
            slide_no = slide_idx + 1

            title = "Başlıksız"
            if slide.shapes.title and slide.shapes.title.text:
                title = slide.shapes.title.text.strip()

            text_contents = []
            tables_contents = []

            for shape in slide.shapes:
                if shape.has_text_frame and shape != slide.shapes.title:
                    for para in shape.text_frame.paragraphs:
                        p_text = para.text.strip()
                        if p_text:
                            text_contents.append(p_text)

                if shape.has_table:
                    tbl = shape.table
                    matrix = []
                    for row in tbl.rows:
                        matrix.append([cell.text.strip().replace("\n", " ") for cell in row.cells])
                    if matrix:
                        tables_contents.append(matrix)

            notes_text = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes_text = slide.notes_slide.notes_text_frame.text.strip()

            slides_data.append({
                "slayt_no": slide_no,
                "baslik": title,
                "maddeler": text_contents,
                "tablolar": tables_contents,
                "konusmaci_notlari": notes_text if notes_text else None
            })

        return {
            "dosya": os.path.basename(clean_path),
            "okunan_aralik": f"{start_slide}-{target_end}",
            "toplam_slayt": total_slides,
            "slaytlar": slides_data
        }

    except Exception as e:
        return {"hata": f"PPTX okunurken hata: {str(e)}"}


@mcp.tool()
def search_pptx(file_path: str, query: str) -> List[Dict[str, Any]]:
    """
    PowerPoint (.pptx) sunumunda anahtar kelime araması yapar.
    Hangi slaytlarda geçtiğini ve içerik kesitini döner.

    Parametreler:
        file_path: PowerPoint (.pptx) dosya yolu.
        query: Aranacak metin veya kelime.
    """
    clean_path = _resolve_wsl(file_path)
    if not os.path.exists(clean_path):
        return [{"hata": f"Dosya bulunamadı: {clean_path}"}]

    try:
        prs = pptx.Presentation(clean_path)
        matches = []

        for idx, slide in enumerate(prs.slides, start=1):
            slide_text = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    slide_text.append(shape.text_frame.text)

            full_slide_content = " ".join(slide_text)
            if query.lower() in full_slide_content.lower():
                matches.append({
                    "slayt_no": idx,
                    "baslik": slide.shapes.title.text.strip() if slide.shapes.title and slide.shapes.title.text else "Başlıksız",
                    "kesit": f"...{full_slide_content[:200].strip()}..."
                })

        return matches if matches else [{"mesaj": f"'{query}' ifadesi sunumda bulunamadı."}]
    except Exception as e:
        return [{"hata": f"PPTX araması sırasında hata: {str(e)}"}]


# ==============================================================================
# 11. BÖLÜM: YEREL GIT ARAÇLARI
# ==============================================================================

def _git_executable() -> str:
    executable = shutil.which("git.exe") or shutil.which("git")
    if not executable:
        raise FileNotFoundError("Git PATH üzerinde bulunamadı.")
    return executable


def _git_repository(repository_path: str) -> str:
    path = os.path.abspath(os.path.expanduser((repository_path or "").strip()))
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Depo dizini bulunamadı: {path}")
    probe = _run_process([_git_executable(), "-C", path, "rev-parse", "--show-toplevel"], timeout_seconds=15)
    if probe["returncode"] != 0:
        raise ValueError(probe["stderr"] or f"Git deposu değil: {path}")
    return probe["stdout"].strip()


def _run_git(repository_path: str, git_args: Sequence[str], timeout_seconds: int = 60) -> Dict[str, Any]:
    root = _git_repository(repository_path)
    result = _run_process(
        [_git_executable(), "-C", root, "-c", "color.ui=false", *git_args],
        timeout_seconds=timeout_seconds,
    )
    return {"depo": root, **result}


def _git_response(result: Dict[str, Any], max_characters: int = 50000) -> Dict[str, Any]:
    stdout = result.get("stdout", "")
    stderr = result.get("stderr", "")
    limit = max(1000, min(int(max_characters), 200000))
    truncated = len(stdout) > limit
    if truncated:
        stdout = stdout[:limit] + f"\n... [Çıktı {limit} karakterde kesildi]"
    return {
        "basarili": result.get("returncode") == 0,
        "cikis_kodu": result.get("returncode"),
        "depo": result.get("depo"),
        "cikti": stdout,
        "hata": stderr or None,
        "kirpildi": truncated,
    }


@mcp.tool()
def git_status(repository_path: str) -> Dict[str, Any]:
    """Bir Git deposunun dalını ve kısa çalışma ağacı durumunu döndürür."""
    try:
        branch = _run_git(repository_path, ["branch", "--show-current"])
        status = _run_git(repository_path, ["status", "--short", "--branch"])
        response = _git_response(status)
        response["dal"] = branch["stdout"] or None
        response["temiz"] = status["returncode"] == 0 and not any(
            line and not line.startswith("##") for line in status["stdout"].splitlines()
        )
        return response
    except Exception as exc:
        return {"basarili": False, "hata": str(exc)}


@mcp.tool()
def git_diff(repository_path: str, staged: bool = False, max_characters: int = 50000) -> Dict[str, Any]:
    """Stage edilmiş veya edilmemiş Git değişikliklerinin diff çıktısını döndürür."""
    try:
        args = ["diff"]
        if staged:
            args.append("--cached")
        args.extend(["--no-ext-diff", "--"])
        return _git_response(_run_git(repository_path, args), max_characters)
    except Exception as exc:
        return {"basarili": False, "hata": str(exc)}


@mcp.tool()
def git_log(repository_path: str, max_count: int = 10) -> Dict[str, Any]:
    """Son Git commitlerini makine tarafından kolay okunabilir bir biçimde listeler."""
    try:
        count = max(1, min(int(max_count), 100))
        result = _run_git(
            repository_path,
            ["log", f"--max-count={count}", "--date=iso-strict", "--pretty=format:%H%x09%an%x09%ad%x09%s"],
        )
        commits = []
        for line in result["stdout"].splitlines():
            fields = line.split("\t", 3)
            if len(fields) == 4:
                commits.append({"hash": fields[0], "yazar": fields[1], "tarih": fields[2], "mesaj": fields[3]})
        return {"basarili": result["returncode"] == 0, "depo": result["depo"], "commitler": commits, "hata": result["stderr"] or None}
    except Exception as exc:
        return {"basarili": False, "hata": str(exc)}


@mcp.tool()
def git_branches(repository_path: str) -> Dict[str, Any]:
    """Yerel ve uzak Git dallarını listeler."""
    try:
        result = _run_git(repository_path, ["branch", "--all", "--no-color", "--format=%(refname:short)"])
        return {
            "basarili": result["returncode"] == 0,
            "depo": result["depo"],
            "dallar": [line.strip() for line in result["stdout"].splitlines() if line.strip()],
            "hata": result["stderr"] or None,
        }
    except Exception as exc:
        return {"basarili": False, "hata": str(exc)}


@mcp.tool()
def git_add(repository_path: str, paths: Optional[List[str]] = None) -> Dict[str, Any]:
    """Belirtilen yolları, yol verilmezse tüm değişiklikleri Git staging alanına ekler."""
    try:
        clean_paths = [str(path) for path in (paths or []) if str(path).strip()]
        args = ["add", "--", *(clean_paths or ["."])]
        return _git_response(_run_git(repository_path, args))
    except Exception as exc:
        return {"basarili": False, "hata": str(exc)}


@mcp.tool()
def git_commit(repository_path: str, message: str) -> Dict[str, Any]:
    """Stage edilmiş değişiklikleri verilen mesajla commit eder."""
    try:
        cleaned = (message or "").strip()
        if not cleaned:
            return {"basarili": False, "hata": "Commit mesajı boş olamaz."}
        return _git_response(_run_git(repository_path, ["commit", "-m", cleaned], timeout_seconds=120))
    except Exception as exc:
        return {"basarili": False, "hata": str(exc)}


@mcp.tool()
def git_create_branch(repository_path: str, branch_name: str, checkout: bool = True) -> Dict[str, Any]:
    """Yeni bir Git dalı oluşturur ve varsayılan olarak o dala geçer."""
    try:
        cleaned = (branch_name or "").strip()
        if not cleaned or cleaned.startswith("-"):
            return {"basarili": False, "hata": "Geçersiz dal adı."}
        check = _run_git(repository_path, ["check-ref-format", "--branch", cleaned])
        if check["returncode"] != 0:
            return _git_response(check)
        args = ["switch", "-c", cleaned] if checkout else ["branch", cleaned]
        return _git_response(_run_git(repository_path, args))
    except Exception as exc:
        return {"basarili": False, "hata": str(exc)}


@mcp.tool()
def git_checkout(repository_path: str, ref: str) -> Dict[str, Any]:
    """Var olan bir Git dalına veya ref'e geçer; yeni dal oluşturmaz."""
    try:
        cleaned = (ref or "").strip()
        if not cleaned or cleaned.startswith("-"):
            return {"basarili": False, "hata": "Geçersiz Git ref değeri."}
        return _git_response(_run_git(repository_path, ["switch", cleaned]))
    except Exception as exc:
        return {"basarili": False, "hata": str(exc)}


if __name__ == "__main__":
    mcp.run(transport="stdio")
