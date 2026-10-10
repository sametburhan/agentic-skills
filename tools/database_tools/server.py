"""
Yerel Veritabanı & SQLite İnceleme MCP Sunucusu (Database Tools)
Bu sunucu, yerel LLM'in SQLite veritabanlarını incelemesini, tablo şemalarını çıkarmasını
ve güvenli SQL sorguları çalıştırarak veri katmanında analiz yapmasını sağlar.
"""

import os
import sqlite3
from typing import Dict, Any, List
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Database-Tools")


@mcp.tool()
def get_database_schema(db_path: str) -> Dict[str, Any]:
    """
    Belirtilen SQLite veritabanının tüm tablo şemalarını, sütun isimlerini,
    veri tiplerini ve birincil anahtarlarını (Primary Key) listeler.

    Parametreler:
        db_path: SQLite veritabanı dosyasının yolu (.db, .sqlite, .sqlite3).
    """
    if not os.path.exists(db_path):
        return {"hata": f"Veritabanı dosyası bulunamadı: {db_path}"}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Tabloları listele
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
        tables = [row[0] for row in cursor.fetchall()]

        schema_report = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table});")
            columns_info = cursor.fetchall()
            
            cols = []
            for col in columns_info:
                cid, name, col_type, notnull, dflt_value, pk = col
                cols.append({
                    "sutun": name,
                    "tip": col_type or "BLOB",
                    "not_null": bool(notnull),
                    "primary_key": bool(pk)
                })

            # Satır sayısını al
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]

            schema_report[table] = {
                "toplam_kayit": count,
                "sutunlar": cols
            }

        conn.close()
        return {
            "veritabani": os.path.basename(db_path),
            "tablo_sayisi": len(tables),
            "tablolar": schema_report
        }

    except Exception as e:
        return {"hata": f"Şema okunurken hata oluştu: {str(e)}"}


@mcp.tool()
def execute_sql_query(db_path: str, query: str, max_rows: int = 25) -> Dict[str, Any]:
    """
    SQLite veritabanı üzerinde SQL sorgusu (SELECT, INSERT, UPDATE, DELETE vb.) çalıştırır.

    Parametreler:
        db_path: SQLite veritabanı dosyasının yolu.
        query: Çalıştırılacak SQL sorgu cümlesi.
        max_rows: SELECT sorgularında dönecek maksimum satır sayısı (varsayılan: 25).
    """
    if not os.path.exists(db_path):
        return {"hata": f"Veritabanı dosyası bulunamadı: {db_path}"}

    cleaned_query = query.strip()
    is_select = cleaned_query.upper().startswith("SELECT") or cleaned_query.upper().startswith("PRAGMA")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(cleaned_query)

        if is_select:
            col_names = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchmany(max_rows)
            formatted_rows = [dict(zip(col_names, row)) for row in rows]
            conn.close()

            return {
                "durum": "Başarılı",
                "sutunlar": col_names,
                "satir_sayisi": len(formatted_rows),
                "sonuclar": formatted_rows
            }
        else:
            conn.commit()
            affected = cursor.rowcount
            conn.close()

            return {
                "durum": "Başarılı",
                "etkilenen_satir_sayisi": affected,
                "mesaj": "Sorgu başarıyla çalıştırıldı ve değişiklikler kaydedildi."
            }

    except Exception as e:
        return {"hata": f"SQL çalıştırma hatası: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
