"""
REST API & HTTP İstemci MCP Sunucusu (API Client Tools)
Bu sunucu, yerel LLM'in yerel veya uzak API servislerini (FastAPI, Express, Flask, Spring Boot vb.)
test etmesini, GET/POST/PUT/DELETE istekleri göndermesini ve yanıtları analiz etmesini sağlar.
"""

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("API-Client-Tools")


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
    Belirtilen adrese HTTP isteği gönderir (REST API testi için idealdir).

    Parametreler:
        method: HTTP metodu ('GET', 'POST', 'PUT', 'DELETE', 'PATCH').
        url: İstek yapılacak tam adres (Örn: 'http://localhost:8000/api/users').
        headers: İsteğe eklenecek HTTP başlıkları (Örn: {'Authorization': 'Bearer ...'}).
        json_body: POST/PUT istekleri için JSON veri gövdesi (dict, list veya primitive).
        params: URL'ye eklenecek query parametreleri (Örn: {'limit': '10'}).
        timeout: İstek zaman aşımı süresi saniye cinsinden (varsayılan: 15).
    """
    cleaned_method = method.upper().strip()
    req_headers = headers.copy() if headers else {}

    # Query parametrelerini ekle
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
            
            # JSON olarak parse etmeyi dene
            try:
                parsed_body = json.loads(raw_body)
            except Exception:
                parsed_body = raw_body

            return {
                "durum_kodu": response.status,
                "sure_ms": elapsed_ms,
                "yanit": parsed_body,
                "basarili": True
            }

    except urllib.error.HTTPError as e:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        error_body = e.read().decode("utf-8", errors="replace")
        try:
            parsed_err = json.loads(error_body)
        except Exception:
            parsed_err = error_body

        return {
            "durum_kodu": e.code,
            "hata": f"HTTP {e.code}: {e.reason}",
            "yanit": parsed_err,
            "sure_ms": elapsed_ms,
            "basarili": False
        }
    except Exception as e:
        return {
            "hata": f"Bağlantı hatası: {str(e)}",
            "basarili": False
        }


if __name__ == "__main__":
    mcp.run(transport="stdio")
