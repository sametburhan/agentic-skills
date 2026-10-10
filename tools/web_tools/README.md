# Web Arama ve İçerik Araçları Kullanım Kılavuzu

Bu dizindeki araçlar, yerel LLM modelinize güncel internet bilgisine erişme, arama motorlarında araştırma yapma ve web sayfalarının metin içeriğini bağlam dostu bir şekilde okuma yeteneği kazandırır.

---

## 1. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Amaç | API Key Gerekir mi? |
|---|---|---|
| `web_search` | DuckDuckGo motorunu kullanarak internette arama yapar. Başlık, URL ve kısa özet döner. | **Hayır (Ücretsiz & Limitsiz)** |
| `fetch_web_page_text` | Hedef URL'nin HTML içeriğini indirir; reklam, script ve CSS kodlarını ayıklayarak temiz metni getirir. | **Hayır** |

---

## 2. Tipik Kullanım Senaryosu

1. **Arama Yapma:**
   ```text
   Kullanıcı: "Python 3.12 ile gelen yeni TypeVar özelliklerini araştır."
   Ajan Çağrısı: web_search(query="Python 3.12 TypeVar changes documentation", max_results=3)
   ```
2. **Hedef Dokümantasyonu Derinlemesine Okuma:**
   ```text
   Ajan Çağrısı: fetch_web_page_text(url="https://docs.python.org/3/whatsnew/3.12.html", max_characters=4000)
   ```
3. **Yanıtlama:** Model elde ettiği güncel ve filtrelenmiş verileri sentezleyerek kullanıcıya yanıt verir.

---

## 3. Web Arama (Hafif) vs. Puppeteer (Gelişmiş) Ne Zaman Kullanılır?

| İhtiyaç | Önerilen Araç | Nedeni |
|---|---|---|
| Hızlı bilgi sorgulama, dokümantasyon okuma | `web_search` + `fetch_web_page_text` | Çok hafiftir, RAM harcamaz, saniyeler içinde temiz metin döner. |
| Butonlara tıklama, form doldurma, oturum açma | `@modelcontextprotocol/server-puppeteer` | Sayfadaki JavaScript kodlarını gerçek Chromium motorunda çalıştırır. |
| Web sitesinin ekran görüntüsünü alıp tasarıma bakma | `puppeteer_screenshot` (Puppeteer) | Modelinizin Vision özelliği ile arayüz hatalarını ve CSS tasarımını görmesini sağlar. |

Puppeteer'ın kurulumu ve kullanımı için [puppeteer_guide.md](file:///c:/Users/samet/Desktop/agentic-skills/tools/web_tools/puppeteer_guide.md) dosyasını inceleyin.
