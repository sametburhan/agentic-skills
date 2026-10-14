# Web Arama ve Sayfa Gözlemleme Araçları

Bu modül, yerel LLM'lere API anahtarı gerektirmeden güncel web araması ve sayfa içeriği gözlemleme yeteneği sağlar.

## Araçlar

| Araç | Amaç |
|---|---|
| `web_search` | `ddgs` üzerinden arama yapar; servis başarısızsa DuckDuckGo HTML sonucuna geri döner. |
| `fetch_web_page_text` | Statik HTML'i indirir, gereksiz etiketleri temizler ve başlıkla birlikte bağlam-dostu metin döndürür. |
| `observe_web_page` | Başlık, metin ve ilk 50 bağlantıyı yapılandırılmış olarak döndürür. JavaScript gerekiyorsa kurulu Chrome/Edge'i headless çalıştırır; başarısız olursa statik HTTP'ye döner. |
| `research_web` | İlk 20 arama sonucunu en fazla 8 paralel işçiyle okuyup kaynak, başlık, özet, temiz metin ve hata raporunu tek çağrıda döndürür. |

## Örnekler

```text
web_search(query="Python 3.13 release notes", max_results=5)

fetch_web_page_text(
  url="https://docs.python.org/3/whatsnew/3.13.html",
  max_characters=8000
)

observe_web_page(
  url="https://example.com",
  max_characters=12000,
  render_javascript=true,
  timeout_seconds=30
)

research_web(
  query="yerel LLM ajan araçları",
  max_pages=20,
  max_characters_per_page=4000,
  concurrency=5,
  timeout_seconds=15
)
```

`observe_web_page` bir tarayıcı bulamazsa hata vermek yerine `static-http` moduna geçer ve `render_uyarisi` alanında nedeni bildirir. Form doldurma, oturum açma ve tıklama gibi etkileşimli tarayıcı otomasyonu bu ilk aşamanın kapsamı dışındadır.

`research_web` hız için JavaScript tarayıcısı açmaz. Dinamik bir sayfanın statik HTML'i yetersizse ilgili URL daha sonra `observe_web_page(render_javascript=true)` ile derinlemesine incelenebilir.
