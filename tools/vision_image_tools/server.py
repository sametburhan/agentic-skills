"""
Yerel Görsel & Mockup İnceleme MCP Sunucusu (Vision Image Tools)
Bu sunucu, kullanıcının bilgisayarındaki herhangi bir tasarım görselini (UI mockup, ekran alıntısı,
mimari şema, logo vb.) inceler, yerel Vision LLM'lerin VRAM sınırlarını aşmayacak şekilde optimize eder
ve modelin görseli piksel bazlı yorumlamasını sağlar.
"""

import os
from typing import Dict, Any
from PIL import Image
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Vision-Image-Tools")

CACHE_DIR = os.path.join(os.getcwd(), ".vision_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


@mcp.tool()
def inspect_local_image(image_path: str, max_dimension: int = 1280) -> Dict[str, Any]:
    """
    Yerel bir görsel dosyasını (PNG, JPG, WEBP, BMP) doğrular ve Vision modelinin güvenle inceleyebilmesi
    için gerekirse boyutlandırarak optimize eder (VRAM taşmasını önler).

    Parametreler:
        image_path: İncelenecek görselin tam veya göreceli dosya yolu.
        max_dimension: Görselin maksimum genişlik/yükseklik boyutu (varsayılan: 1280 piksel - Vision modelleri için ideal denge).
    """
    if not os.path.exists(image_path):
        return {"hata": f"Görsel dosyası bulunamadı: {image_path}"}

    try:
        with Image.open(image_path) as img:
            orig_width, orig_height = img.size
            img_format = img.format
            mode = img.mode

            # Boyutlandırma gereksinimi kontrolü
            needs_downscale = max(orig_width, orig_height) > max_dimension

            if needs_downscale:
                ratio = min(max_dimension / orig_width, max_dimension / orig_height)
                new_width = int(orig_width * ratio)
                new_height = int(orig_height * ratio)

                # Aspect ratio koruyarak yüksek kaliteli yeniden boyutlandırma
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                base_name = os.path.splitext(os.path.basename(image_path))[0]
                output_filename = f"{base_name}_opt_{new_width}x{new_height}.png"
                output_path = os.path.join(CACHE_DIR, output_filename)
                
                # RGB'ye çevirip PNG olarak kaydet (RGBA ise şeffaflığı korur)
                if mode in ("RGBA", "LA") or (mode == "P" and "transparency" in img.info):
                    resized_img.save(output_path, "PNG")
                else:
                    resized_img.convert("RGB").save(output_path, "PNG")

                return {
                    "durum": "Optimize Edildi",
                    "orijinal_boyut": f"{orig_width}x{orig_height} ({img_format})",
                    "optimize_boyut": f"{new_width}x{new_height}",
                    "gorsel_dosya_yolu": os.path.abspath(output_path),
                    "mesaj": f"Görsel yerel GPU VRAM'inizi korumak için {new_width}x{new_height} boyutuna optimize edildi. Vision yeteneğiniz ile bu dosyayı inceleyebilirsiniz."
                }
            else:
                return {
                    "durum": "Doğrudan Hazır",
                    "boyut": f"{orig_width}x{orig_height} ({img_format})",
                    "gorsel_dosya_yolu": os.path.abspath(image_path),
                    "mesaj": "Görsel boyutu yerel model için ideal. Vision yeteneğiniz ile doğrudan inceleyebilirsiniz."
                }

    except Exception as e:
        return {"hata": f"Görsel işlenirken hata oluştu: {str(e)}"}


@mcp.tool()
def get_image_metadata(image_path: str) -> Dict[str, Any]:
    """
    Bir görsel dosyasının dosya boyutu, çözünürlüğü ve renk formatı gibi temel meta verilerini döner.
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
                "renk_modu": img.mode,
                "boyut_kb": file_size_kb
            }
    except Exception as e:
        return {"hata": f"Meta veri okunurken hata: {str(e)}"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
