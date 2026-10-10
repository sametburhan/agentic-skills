# Puppeteer ile Web Gezintisi, Ekran Görüntüsü ve Vision Entegrasyonu

Puppeteer MCP Sunucusu (`@modelcontextprotocol/server-puppeteer`), açık kaynaklı headless Chromium tarayıcısını yapay zeka modelinizin kontrolüne verir. Bu araç; web sitelerinde gezinme, butonlara tıklama, form doldurma ve **en önemlisi web sitelerinin ekran görüntüsünü alıp vision modelinize gönderme** işlevlerini yerine getirir.

---

## 1. Kurulum ve Çalıştırma

Puppeteer sunucusu Node.js ve npx üzerinden tek komutla çalışır:
```bash
npx -y @modelcontextprotocol/server-puppeteer
```
*(LM Studio `mcp_config.json` içerisine eklendiğinde arka planda otomatik başlatılır.)*

---

## 2. Puppeteer Tarafından Sağlanan Araçlar

1. **`puppeteer_navigate`**:
   - Belirtilen web sitesine veya yerel geliştirme adresine gider (`https://example.com` veya `http://localhost:3000`).
2. **`puppeteer_screenshot`**:
   - Tarayıcının mevcut durumunun veya belirli bir HTML elementinin ekran görüntüsünü alır.
   - Ekran görüntüsü base64 / PNG formatında modelinize iletilir. Vision özellikli modeliniz doğrudan görseli inceler.
3. **`puppeteer_click`**:
   - CSS seçicisi (selector) ile belirtilen butona veya bağlantıya tıklar (örn: `button#submit`, `a.nav-link`).
4. **`puppeteer_fill`**:
   - Giriş kutularına (input fields) metin yazar (örn: `input[name='search']`, `"yapay zeka"`).
5. **`puppeteer_evaluate`**:
   - Sayfa bağlamında özel JavaScript kodu çalıştırır.

---

## 3. Vision Modeli ile Localhost Test Döngüsü (Örnek Senaryo)

Modeliniz yerel bilgisayarınızda bir web arayüzü geliştirdiğinde görsel kalite kontrolü yapabilir:

1. **Geliştirme Sunucusunu Başlatma:** Model `run_powershell` ile `npm run dev` komutunu çalıştırır.
2. **Siteye Gitme:** `puppeteer_navigate(url="http://localhost:5173")` çağrılır.
3. **Ekran Görüntüsü Alma:** `puppeteer_screenshot(name="dashboard_preview", width=1280, height=800)` çağrılır.
4. **Vision ile İnceleme:** Model elde edilen görseli analiz eder:
   - *"Header bileşeni mobil görünümde taşma yapıyor."*
   - *"Buton rengi kontrast testini geçmiyor."*
5. **Kod Düzeltme & Tekrar Test:** Model CSS kodunu düzeltir ve tekrar ekran görüntüsü alarak düzeldiğini onaylar.
6. **Kullanıcıya Gösterme:** Onaylandıktan sonra `open_in_chrome(url="http://localhost:5173")` ile sizin tarayıcınızda açar!
