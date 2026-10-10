"""
Web Arama ve İçerik Çekme MCP Sunucusu
Bu sunucu, harici bir API anahtarı (API Key) veya ücretli servis gerektirmeden
DuckDuckGo üzerinden anlık internet araması yapar ve web sayfalarından
temiz metin içeriği çeker.
"""

import urllib.request
import re
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Web-Search-Tools")


@mcp.tool()
def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    İnternette güncel bilgi, dokümantasyon veya makale araması yapar.
    Herhangi bir API anahtarı gerektirmez (DuckDuckGo Search motorunu kullanır).

    Parametreler:
        query: Aranacak sorgu cümlesi veya anahtar kelimeler.
        max_results: Getirilecek sonuç sayısı (varsayılan: 5, en fazla 10 önerilir).
    """
    try:
        results = []
        with DDGS() as ddgs:
            raw_results = list(ddgs.text(query, max_results=max_results))
            for r in raw_results:
                results.append({
                    "baslik": r.get("title", "Başlıksız"),
                    "url": r.get("href", ""),
                    "ozet": r.get("body", "")
                })

        if not results:
            return [{"mesaj": f"'{query}' için internette sonuç bulunamadı."}]

        return results
    except Exception as e:
        return [{"hata": f"Web araması sırasında sorun oluştu: {str(e)}"}]


@mcp.tool()
def fetch_web_page_text(url: str, max_characters: int = 4000) -> str:
    """
    Belirtilen bir URL'nin HTML içeriğini indirir; reklam, script ve stilleri temizleyerek
    yalnızca okunabilir metin içeriğini getirir.

    Parametreler:
        url: Ziyaret edilecek web sayfasının tam adresi (http:// veya https://).
        max_characters: Yerel modelin bağlam penceresini korumak için çekilecek maksimum karakter sayısı (varsayılan: 4000).
    """
    if not url.startswith("http://") and not url.startswith("https://"):
        return "HATA: Geçerli bir URL girilmelidir (http:// veya https:// ile başlamalı)."

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="replace")

        soup = BeautifulSoup(html, "html.parser")

        # İlgisiz etiketleri temizle
        for element in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            element.decompose()

        # Metni al ve fazlalık boşlukları temizle
        text = soup.get_text(separator="\n")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        clean_text = "\n".join(lines)

        if len(clean_text) > max_characters:
            clean_text = clean_text[:max_characters] + f"\n\n... [İçerik {max_characters} karakter ile sınırlandırıldı] ..."

        return clean_text if clean_text else "Sayfada okunabilir metin bulunamadı."

    except Exception as e:
        return f"HATA: Web sayfası çekilirken hata oluştu: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
