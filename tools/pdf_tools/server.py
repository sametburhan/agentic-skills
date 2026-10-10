"""
Akıllı PDF Okuma ve Vision Analiz MCP Sunucusu
Bu sunucu, özellikle yüzlerce sayfalık uzun PDF belgelerini yerel LLM'in
bağlam penceresini (context window) doldurmadan etkili bir şekilde okumasını,
arama yapmasını ve grafik/tablo içeren sayfaları görsel (vision) olarak incelemesini sağlar.
"""

import os
import subprocess
import tempfile
import markdown
import fitz  # PyMuPDF
from typing import Dict, Any, List, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Smart-PDF-Tools")

CACHE_DIR = os.path.join(os.getcwd(), ".pdf_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


@mcp.tool()
def get_pdf_info_and_toc(file_path: str) -> Dict[str, Any]:
    """
    Uzun bir PDF'in meta verilerini, toplam sayfa sayısını ve İçindekiler Tablosunu (TOC / Hiyerarşi) getirir.
    Büyük belgelerde hangi sayfalara odaklanılacağını belirlemek için ilk çağrılacak araçtır.

    Parametreler:
        file_path: Okunacak PDF dosyasının tam veya göreceli yolu.
    """
    if not os.path.exists(file_path):
        return {"hata": f"Dosya bulunamadı: {file_path}"}

    try:
        doc = fitz.open(file_path)
        toc = doc.get_toc()  # [[lvl, title, page], ...]
        metadata = doc.metadata or {}

        formatted_toc = []
        for level, title, page in toc:
            indent = "  " * (level - 1)
            formatted_toc.append(f"{indent}- {title} (Sayfa: {page})")

        return {
            "toplam_sayfa": len(doc),
            "baslik": metadata.get("title") or os.path.basename(file_path),
            "yazar": metadata.get("author", "Bilinmiyor"),
            "icindekiler_tablosu": formatted_toc if formatted_toc else "Yerleşik içindekiler tablosu (bookmarks) bulunamadı.",
            "oneri": "İhtiyacınız olan bölümü belirledikten sonra 'read_pdf_page_range' veya 'search_pdf' aracını kullanın."
        }
    except Exception as e:
        return {"hata": f"PDF meta verisi okunurken hata: {str(e)}"}


@mcp.tool()
def search_pdf(file_path: str, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Uzun PDF içinde anahtar kelime veya kelime grubu araması yapar.
    Tüm dokümanı bağlama yüklemeden ilgili bölümleri ve sayfa numaralarını bulur.

    Parametreler:
        file_path: PDF dosya yolu.
        query: Aranacak anahtar kelime veya kelime grubu.
        max_results: Getirilecek maksimum sonuç sayısı (varsayılan: 5).
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
                # Eşleşen kelimenin etrafındaki kesiti çıkar
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

        if not results:
            return [{"mesaj": f"'{query}' ifadesi dokümanda bulunamadı."}]

        return results
    except Exception as e:
        return [{"hata": f"Arama sırasında hata: {str(e)}"}]


@mcp.tool()
def read_pdf_page_range(file_path: str, start_page: int, end_page: int) -> str:
    """
    PDF dokümanının belirtilen sayfa aralığındaki metin içeriğini getirir. (1-indeksli)
    Örnek: 15 ile 18 arasındaki sayfaları okumak için start_page=15, end_page=18.

    Parametreler:
        file_path: PDF dosya yolu.
        start_page: Başlangıç sayfası (1'den başlar).
        end_page: Bitiş sayfası (dahil).
    """
    if not os.path.exists(file_path):
        return f"HATA: Dosya bulunamadı: {file_path}"

    try:
        doc = fitz.open(file_path)
        total = len(doc)
        
        if start_page < 1 or start_page > total:
            return f"HATA: Geçersiz başlangıç sayfası ({start_page}). Toplam sayfa sayısı: {total}"
        
        actual_end = min(end_page, total)
        extracted = []

        for page_num in range(start_page - 1, actual_end):
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
            return {"hata": f"Geçersiz başlangıç sayfası ({start_page}). Toplam sayfa: {total}"}

        actual_end = min(end_page, total)
        pages_data = []

        for page_idx in range(start_page - 1, actual_end):
            page = doc[page_idx]
            page_info = {
                "sayfa_no": page_idx + 1,
                "tablolar": [],
                "metin_bloklari": []
            }

            # 1. Tabloları yapılandırılmış satırlar olarak çıkar
            if extract_tables:
                try:
                    tabs = page.find_tables()
                    for tab in tabs.tables:
                        table_matrix = tab.extract()
                        if table_matrix:
                            page_info["tablolar"].append(table_matrix)
                except Exception:
                    pass

            # 2. Metin bloklarını temiz ve yapılandırılmış şekilde al
            blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, block_type)
            for b in blocks:
                if b[6] == 0:  # 0 = metin bloğu (1 = resim)
                    text = b[4].strip()
                    if text:
                        # Fazla satır sonlarını temizle
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
    Grafik, tablo, şema veya matematiksel formül içeren bir sayfayı yüksek kaliteli PNG görseline dönüştürür.
    Vision (görsel yorumlama) yeteneğine sahip LLM'ler bu görsel dosyasını inceleyebilir.

    Parametreler:
        file_path: PDF dosya yolu.
        page_number: Görsele dönüştürülecek sayfa numarası (1-indeksli).
        dpi: Çözünürlük (varsayılan: 150 - metin ve diyagramlar için ideal denge).
    """
    if not os.path.exists(file_path):
        return {"hata": f"Dosya bulunamadı: {file_path}"}

    try:
        doc = fitz.open(file_path)
        if page_number < 1 or page_number > len(doc):
            return {"hata": f"Geçersiz sayfa numarası ({page_number}). Toplam sayfa: {len(doc)}"}

        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=dpi)
        
        filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_p{page_number}.png"
        output_path = os.path.join(CACHE_DIR, filename)
        pix.save(output_path)

        return {
            "durum": "Başarılı",
            "sayfa_no": page_number,
            "gorsel_dosya_yolu": os.path.abspath(output_path),
            "mesaj": f"Sayfa başarıyla PNG olarak kaydedildi. Vision yeteneğiniz ile bu görsel dosyasını doğrudan inceleyebilirsiniz."
        }
    except Exception as e:
        return {"hata": f"Görsel oluşturulurken hata: {str(e)}"}


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

    Parametreler:
        input_md_path: Kaynak Markdown dosyasının yolu (Örn: '\\\\wsl$\\Ubuntu\\home\\samet\\proje\\notlar.md' veya '/home/samet/notlar.md').
        output_pdf_path: Hedef PDF dosyasının kaydedileceği Windows yolu (Örn: 'C:/Users/samet/Desktop/Rapor.pdf').
        custom_css: Opsiyonel CSS tasarım şablonu (boş bırakılırsa modern GitHub makale stili uygulanır).
    """
    import markdown
    import tempfile

    # WSL Linux formatındaki yolları otomatik olarak Windows ağ yoluna çevir
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

    # Hedef dizini otomatik oluştur
    out_dir = os.path.dirname(os.path.abspath(clean_output))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # Tarayıcıyı bul
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



if __name__ == "__main__":
    mcp.run(transport="stdio")
