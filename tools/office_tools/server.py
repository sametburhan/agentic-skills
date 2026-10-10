"""
Office Belgeleri Okuma MCP Sunucusu (DOCX & PPTX Tools)
Bu sunucu, yerel LLM'in Microsoft Word (.docx) raporlarını ve
Microsoft PowerPoint (.pptx) sunumlarını yapılandırılmış, hafif JSON ve metin formatında
açıp okumasını, arama yapmasını ve analiz etmesini sağlar.
"""

import os
from typing import Dict, Any, List, Optional
import docx
import pptx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Office-Document-Tools")


def _resolve_path(path_str: str) -> str:
    cleaned = path_str.strip()
    if cleaned.startswith("/") and not cleaned.startswith("//"):
        slash_path = cleaned.replace("/", "\\")
        return f"\\\\wsl$\\Ubuntu{slash_path}"
    return cleaned


# ==============================================================================
# 1. BÖLÜM: WORD (.DOCX) DOKÜMAN OKUMA ARAÇLARI
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
    clean_path = _resolve_path(file_path)
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
    Tüm belgeyi belleğe yüklemeden sadece eşleşen paragrafları ve tabloları döner.

    Parametreler:
        file_path: Word dosyası yolu.
        query: Aranacak kelime veya ifade.
        max_results: Getirilecek maksimum eşleşme sayısı (varsayılan: 5).
    """
    clean_path = _resolve_path(file_path)
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


# ==============================================================================
# 2. BÖLÜM: POWERPOINT (.PPTX) SUNUM OKUMA ARAÇLARI
# ==============================================================================

@mcp.tool()
def get_pptx_outline(file_path: str) -> Dict[str, Any]:
    """
    PowerPoint (.pptx) sunumunun slayt sayısını ve her slaydın başlığını (İçindekiler / Outline) çıkarır.
    Sunumun genel yapısını hızlıca anlamak için ilk çağrılacak araçtır.

    Parametreler:
        file_path: PowerPoint (.pptx) dosya yolu.
    """
    clean_path = _resolve_path(file_path)
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
        end_slide: Bitiş slayt numarası (opsiyonel, boş bırakılırsa tüm sunum veya ilk 15 slayt okunur).
    """
    clean_path = _resolve_path(file_path)
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
                # Başlık harici metin kutuları
                if shape.has_text_frame and shape != slide.shapes.title:
                    for para in shape.text_frame.paragraphs:
                        p_text = para.text.strip()
                        if p_text:
                            text_contents.append(p_text)

                # Tablolar
                if shape.has_table:
                    tbl = shape.table
                    matrix = []
                    for row in tbl.rows:
                        matrix.append([cell.text.strip().replace("\n", " ") for cell in row.cells])
                    if matrix:
                        tables_contents.append(matrix)

            # Konuşmacı notları (Speaker Notes)
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
    clean_path = _resolve_path(file_path)
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
