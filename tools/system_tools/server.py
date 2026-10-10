"""
PowerShell, Terminal ve Sistem Yönetimi MCP Sunucusu
Bu sunucu, LM Studio veya herhangi bir MCP istemcisinin yerel sistemde
PowerShell komutları çalıştırmasını, PATH üzerindeki araçlara (python, pip, node, npm, git vb.)
erişmesini ve yerel sunucuları Chrome sekmesinde açmasını sağlar.
"""

import os
import socket
import subprocess
from typing import Optional
from mcp.server.fastmcp import FastMCP

# FastMCP Sunucu Başlatma
mcp = FastMCP("System-Dev-Tools")

@mcp.tool()
def run_powershell(command: str, cwd: Optional[str] = None, timeout_seconds: int = 60) -> str:
    """
    Windows PowerShell üzerinde komut çalıştırır.
    Sistem PATH'inde bulunan tüm CLI araçları (python, pip, node, npm, git, docker, npx vb.) kullanılabilir.

    Parametreler:
        command: Çalıştırılacak PowerShell komut satırı stringi.
        cwd: Komutun çalıştırılacağı çalışma dizini (boş bırakılırsa geçerli dizin kullanılır).
        timeout_seconds: Komutun zaman aşımı süresi (varsayılan: 60 saniye).
    """
    working_directory = cwd if cwd and os.path.exists(cwd) else os.getcwd()
    
    # Windows Türkçe karakter desteği ve UTF-8 çıktı için PowerShell ön-komutu
    wrapped_command = f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {command}"

    try:
        process = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", wrapped_command],
            cwd=working_directory,
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
            response.append(f"Çıktı (stdout):\n{stdout}")
        if stderr:
            response.append(f"Hata / Bilgi (stderr):\n{stderr}")
        if not stdout and not stderr:
            response.append("Komut başarıyla tamamlandı (çıktı üretmedi).")

        response.append(f"\n[Çıkış Kodu: {process.returncode}]")
        return "\n\n".join(response)

    except subprocess.TimeoutExpired:
        return f"HATA: Komut {timeout_seconds} saniye içinde tamamlanamadı ve zaman aşımına uğradı."
    except Exception as e:
        return f"HATA: Komut çalıştırılırken bir istisna oluştu: {str(e)}"


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
    Belirtilen web adresini (özellikle yerel localhost sunucularını) sistemdeki Google Chrome tarayıcısında yeni sekmede açar.

    Parametreler:
        url: Açılacak adres (Örn: http://localhost:3000, http://localhost:5173, https://google.com).
    """
    cleaned_url = url.strip()
    if not cleaned_url.startswith("http://") and not cleaned_url.startswith("https://"):
        cleaned_url = "http://" + cleaned_url

    try:
        # Önce doğrudan chrome komutuyla açmayı dener
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", f'Start-Process chrome "{cleaned_url}"'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            # Chrome bulunamazsa sistemin varsayılan tarayıcısını dener
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", f'Start-Process "{cleaned_url}"'],
                check=True
            )
        return f"Başarılı: '{cleaned_url}' adresi tarayıcıda açıldı."
    except Exception as e:
        return f"HATA: Tarayıcı açılırken sorun oluştu: {str(e)}"


@mcp.tool()
def check_localhost_service(port: int = 3000, host: str = "127.0.0.1") -> str:
    """
    Belirtilen yerel portta (localhost) bir web sunucusunun (Vite, Next.js, Flask, FastAPI vb.)
    dinlemede olup olmadığını kontrol eder.

    Parametreler:
        port: Kontrol edilecek port numarası (Örn: 3000, 5173, 8000, 8080).
        host: Host adresi (varsayılan: 127.0.0.1).
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            return f"DURUM: {host}:{port} portu AKTİF ve istekleri kabul ediyor. 'open_in_chrome' ile önizleyebilirsiniz."
        else:
            return f"DURUM: {host}:{port} portunda çalışan bir servis bulunamadı (port kapalı)."
    except Exception as e:
        return f"HATA: Port kontrolü sırasında hata: {str(e)}"
    finally:
        sock.close()


@mcp.tool()
def get_system_environment_info() -> str:
    """
    Sistemde yüklü olan geliştirici araçlarının (Python, Pip, Node, NPM, Git)
    versiyonlarını ve PATH durumunu kontrol edip özetler.
    """
    tools = [
        ("Python", "python --version"),
        ("Pip", "pip --version"),
        ("Node.js", "node --version"),
        ("NPM", "npm --version"),
        ("Git", "git --version")
    ]
    report = ["=== Sistem Geliştirici Araçları Durumu ==="]
    for name, cmd in tools:
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=5
            )
            val = res.stdout.strip() if res.stdout else res.stderr.strip()
            if res.returncode == 0:
                report.append(f"✓ {name}: {val}")
            else:
                report.append(f"✗ {name}: Yüklü değil veya hata verdi ({val})")
        except Exception:
            report.append(f"✗ {name}: Bulunamadı")
    return "\n".join(report)


if __name__ == "__main__":
    # Standalone olarak çalıştırıldığında stdio üzerinden MCP sunucusunu dinler
    mcp.run(transport="stdio")
