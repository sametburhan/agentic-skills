# Yerel Görsel & Mockup İnceleme (Vision Image) Kullanım Kılavuzu

Bu araç (`Vision-Image-Tools`), kullanıcının masaüstündeki veya proje klasöründeki herhangi bir UI tasarımını, çizimi veya hata ekran görüntüsünü modelinize gösterip kodlatmanız için hazırlanmıştır.

---

## 1. Neden VRAM Optimizasyonu Gereklidir?

Yerel Vision modelleri (örneğin Qwen-VL veya Llama-Vision), 4K veya yüksek çözünürlüklü (3000x2000px) görseller verildiğinde:
- Çok yüksek sayıda görüntü token'ı (image patches) üretir.
- GPU VRAM sınırını tüketerek LM Studio'nun çökmesine (Out-of-Memory) neden olabilir.

Bu araç, 1280 pikselden büyük görselleri oranını (aspect ratio) bozmadan otomatik olarak akıllıca ölçeklendirir ve `.vision_cache/` içine güvenli bir kopya kaydeder.

---

## 2. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Amaç | Örnek Parametreler |
|---|---|---|
| `inspect_local_image` | Görseli doğrular, gerekirse VRAM dostu boyuta çeker ve dosya yolunu döner. | `image_path`: `"mockup.png"`, `max_dimension`: `1280` |
| `get_image_metadata` | Çözünürlük ve dosya formatı gibi bilgileri okur. | `image_path`: `"logo.png"` |

---

## 3. Örnek Kullanım Senaryosu (Mockup'tan Koda)

1. Kullanıcı: *"Masaüstümdeki `design.png` dosyasına bak ve oradaki kart bileşenini React + CSS olarak kodla."*
2. Model çağrısı: `inspect_local_image(image_path="C:/Users/samet/Desktop/design.png")`
3. Model optimize edilen görseli yerleşik **Vision** katmanında inceler:
   - *"Görselde sol üstte 48px yuvarlak bir profil resmi, sağda bir başlık ve altta 2 adet aksiyon butonu var."*
4. Model `write_file` ile React bileşenini üretir.
