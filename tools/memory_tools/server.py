"""
Kalıcı Proje Hafızası MCP Sunucusu (Persistent Memory Tools)
Bu sunucu, yerel LLM'in kullanıcı tercihlerini, mimari kararları,
proje kurallarını ve oturumlar arası önemli bilgileri kalıcı olarak saklamasını sağlar.
"""

import os
import json
from typing import Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Persistent-Memory-Tools")

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
    Önemli bir bilgiyi, kuralı veya kararı kalıcı hafızaya kaydeder veya günceller.
    (Örn: key='kod_stili', value='Her zaman 4 boşluk girinti ve camelCase kullan', category='standartlar')

    Parametreler:
        key: Bilginin benzersiz anahtarı (kısa ve açıklayıcı).
        value: Saklanacak detaylı bilgi veya kural.
        category: Bilgi kategorisi (Örn: 'mimari', 'kod_stili', 'kullanici_tercihi', 'genel').
    """
    data = _load_memory()
    data[key] = {
        "deger": value,
        "kategori": category
    }
    _save_memory_file(data)
    return f"BAŞARILI: '{key}' bilgisi ({category} kategorisinde) kalıcı hafızaya kaydedildi."


@mcp.tool()
def read_memory(key: str) -> str:
    """
    Kalıcı hafızadan belirli bir anahtara ait bilgiyi getirir.

    Parametreler:
        key: Sorgulanacak anahtar.
    """
    data = _load_memory()
    if key in data:
        item = data[key]
        return f"[{key.upper()} - Kategori: {item.get('kategori', 'genel')}]\n{item.get('deger')}"
    return f"HATA: '{key}' anahtarıyla kayıtlı bir bilgi bulunamadı."


@mcp.tool()
def list_memories(category: Optional[str] = None) -> str:
    """
    Kalıcı hafızadaki tüm kayıtları veya belirtilen kategorideki kayıtları listeler.

    Parametreler:
        category: Filtrelenecek kategori (opsiyonel). Boş bırakılırsa tüm hafıza dökülür.
    """
    data = _load_memory()
    if not data:
        return "Kalıcı hafızada henüz kayıtlı bir bilgi bulunmamaktadır."

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
    Kalıcı hafızadan eski veya artık geçersiz olan bir bilgiyi siler.

    Parametreler:
        key: Silinecek anahtar.
    """
    data = _load_memory()
    if key in data:
        del data[key]
        _save_memory_file(data)
        return f"BAŞARILI: '{key}' bilgisi hafızadan silindi."
    return f"HATA: '{key}' anahtarı hafızada bulunamadı."


if __name__ == "__main__":
    mcp.run(transport="stdio")
