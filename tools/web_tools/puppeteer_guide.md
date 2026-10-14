# Eski Puppeteer Yapılandırmalarından Geçiş

Bu proje artık `@modelcontextprotocol/server-puppeteer` paketine veya ayrı bir Node.js MCP sunucusuna bağlı değildir. Eski `puppeteer` girdisi `mcp_config.json` dosyasından kaldırılmıştır.

## Yerine kullanılan araçlar

- `observe_web_page`: JavaScript gerekiyorsa bilgisayardaki Chrome veya Edge'i headless modda çalıştırır; sayfanın başlığını, temiz metnini ve bağlantılarını döndürür.
- `research_web`: Bir sorgunun ilk 20 sonucunu sınırlı paralellikle indirerek tek çağrıda kaynaklı araştırma verisi üretir.
- `fetch_web_page_text`: JavaScript gerektirmeyen sayfalar için daha hızlı ve hafif metin çıkarımı yapar.
- `open_in_chrome`: Bir URL'yi kullanıcıya göstermek üzere varsayılan tarayıcıda açar.

## Kapsam

Yeni araçlar bilgi toplama ve içerik gözlemleme için tasarlanmıştır. Form doldurma, oturum açma, butona tıklama ve ekran görüntüsü tabanlı etkileşimli tarayıcı otomasyonu bu ilk aşamanın kapsamı dışındadır.

JavaScript-render edilmiş içerik örneği:

```text
observe_web_page(
  url="https://example.com/app",
  max_characters=12000,
  render_javascript=true,
  timeout_seconds=30
)
```

Toplu araştırma örneği:

```text
research_web(
  query="aranacak konu",
  max_pages=20,
  max_characters_per_page=4000,
  concurrency=5,
  timeout_seconds=15
)
```
