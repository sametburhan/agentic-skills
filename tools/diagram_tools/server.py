"""
Mermaid Diyagram ve Markdown to PNG MCP Sunucusu (Diagram & Visualizer Tools)
Bu sunucu; Mermaid formatında yazılmış akış şemalarını, mimari diyagramları ve
Markdown (.md) dokümanlarını doğrudan yüksek çözünürlüklü PNG görsellerine dönüştürür.
"""

import os
import re
import base64
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
import fitz  # PyMuPDF
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Diagram-Visualizer-Tools")

CACHE_DIR = os.path.join(os.getcwd(), ".diagram_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


def _resolve_wsl_path(path_str: str) -> str:
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
    Mermaid formatındaki akış şeması, mimari diyagram veya sıra diyagramını yüksek kaliteli PNG görseline dönüştürür.
    Doğrudan ham Mermaid kodu (örn: 'flowchart TD; A-->B') veya içinde mermaid kodu olan bir dosya yolu verilebilir.

    Parametreler:
        mermaid_code_or_file: Ham mermaid kod stringi veya .mmd / .md dosya yolu (WSL yolları dahil).
        output_png_path: Çıktı PNG dosyasının kaydedileceği yol (Örn: 'C:/Users/samet/Desktop/diyagram.png').
        theme: Görsel teması ('default', 'neutral', 'dark', 'forest').
        scale: Çözünürlük çarpanı (varsayılan: 2 - keskin ve net metinler için).
    """
    input_str = mermaid_code_or_file.strip()
    clean_output = _resolve_wsl_path(output_png_path)

    # Dosya yolu mu yoksa ham kod mu kontrol et
    resolved_input_path = _resolve_wsl_path(input_str)
    mermaid_code = input_str

    if os.path.exists(resolved_input_path) and os.path.isfile(resolved_input_path):
        try:
            with open(resolved_input_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Markdown içindeyse ```mermaid ... ``` bloğunu ayıkla
            match = re.search(r"```mermaid\s*\n(.*?)\n```", content, re.DOTALL)
            if match:
                mermaid_code = match.group(1).strip()
            else:
                mermaid_code = content.strip()
        except Exception as e:
            return {"hata": f"Dosya okunurken hata oluştu: {str(e)}"}

    # Hedef dizini otomatik oluştur
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
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
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
    her birini ayrı ayrı PNG dosyası olarak belirtilen dizine kaydeder (diagram_1.png, diagram_2.png vb.).

    Parametreler:
        input_md_path: İncelenecek Markdown dosyasının yolu (WSL veya Windows).
        output_directory: PNG görsellerinin kaydedileceği klasör (Örn: 'C:/Users/samet/Desktop/diyagramlar').
    """
    clean_md = _resolve_wsl_path(input_md_path)
    clean_out_dir = _resolve_wsl_path(output_directory)

    if not os.path.exists(clean_md):
        return {"hata": f"Markdown dosyası bulunamadı: {clean_md}"}

    os.makedirs(clean_out_dir, exist_ok=True)

    try:
        with open(clean_md, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        diagrams = re.findall(r"```mermaid\s*\n(.*?)\n```", content, re.DOTALL)
        if not diagrams:
            return {"mesaj": "Belirtilen Markdown dosyasında herhangi bir ```mermaid bloğu bulunamadı."}

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
    Bir Markdown dosyasını önce derleyip ardından belirtilen sayfasını yüksek kaliteli PNG görseli olarak kaydeder.
    README, rapor veya dokümantasyon sayfalarının doğrudan görsel önizlemesini almak için kullanılır.

    Parametreler:
        input_md_path: Kaynak Markdown dosyası (WSL veya Windows yolu).
        output_png_path: Kaydedilecek PNG dosyasının yolu.
        page_number: Dönüştürülecek sayfa numarası (varsayılan: 1).
        dpi: Çözünürlük (varsayılan: 150 dpi).
    """
    from tools.pdf_tools.server import convert_markdown_to_pdf

    clean_md = _resolve_wsl_path(input_md_path)
    clean_out_png = _resolve_wsl_path(output_png_path)

    temp_pdf = os.path.join(CACHE_DIR, f"temp_{os.getpid()}.pdf")

    try:
        # Önce PDF'e çevir
        pdf_res = convert_markdown_to_pdf(clean_md, temp_pdf)
        if "hata" in pdf_res:
            return pdf_res

        # PDF'in sayfasını PNG olarak kaydet
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
            "mesaj": f"Markdown sayfası başarıyla PNG olarak kaydedildi ({pix.width}x{pix.height} piksel)."
        }

    except Exception as e:
        return {"hata": f"Markdown PNG'ye dönüştürülürken hata: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
