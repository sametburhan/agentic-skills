# Web Arama, Sayfa Gözlemleme ve WebSocket Araçları

Bu modül, yerel LLM'lere güncel web araması, sayfa içeriği gözlemleme ve genel amaçlı WebSocket iletişimi sağlar.

## Araçlar

| Araç | Amaç |
|---|---|
| `web_search` | `ddgs` üzerinden arama yapar; servis başarısızsa DuckDuckGo HTML sonucuna geri döner. |
| `fetch_web_page_text` | Statik HTML'i indirir, gereksiz etiketleri temizler ve başlıkla birlikte bağlam-dostu metin döndürür. |
| `observe_web_page` | Başlık, metin ve ilk 50 bağlantıyı yapılandırılmış olarak döndürür. JavaScript gerekiyorsa kurulu Chrome/Edge'i headless çalıştırır; başarısız olursa statik HTTP'ye döner. |
| `research_web` | İlk 20 arama sonucunu en fazla 8 paralel işçiyle okuyup kaynak, başlık, özet, temiz metin ve hata raporunu tek çağrıda döndürür. |
| `websocket_connect` | Özel başlık ve alt protokol desteğiyle kalıcı `ws://` veya `wss://` bağlantısı açar. |
| `websocket_send` | Bağlantıya metin veya Base64 kodlu ikili mesaj gönderir. |
| `websocket_receive` | Sıradaki metin ya da ikili mesajı zaman aşımı kontrolüyle alır. |
| `websocket_ping` | Ping gönderip pong yanıtını doğrular. |
| `websocket_close` | Bağlantıyı kapatıp bellek içi bağlantı havuzundan çıkarır. |
| `websocket_list_connections` | Sunucunun belleğinde tuttuğu bağlantıları listeler. |
| `websocket_request` | Bağlan-gönder-al-kapat akışını tek çağrıda yürütür. |

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

websocket_request(
  url="wss://echo.example.com/socket",
  message="{\"type\":\"ping\"}",
  headers={"Authorization": "Bearer ..."},
  receive_count=1,
  timeout_seconds=10
)
```

Kalıcı bağlantı için önce `websocket_connect` çağrılır ve dönen `connection_id`, sonraki `websocket_send`, `websocket_receive`, `websocket_ping` ve `websocket_close` çağrılarında kullanılır. İkili mesajlar MCP'nin JSON taşımasına uygun olması için Base64 olarak alınır ve gönderilir. En fazla 32 eşzamanlı bağlantı ve bağlantı başına en fazla 16 MiB mesaj sınırı vardır.

Bağlantılar yalnızca çalışan MCP sunucusunun belleğinde yaşar; istemci veya sunucu yeniden başlatılırsa yeniden bağlanmak gerekir. Yetkilendirme başlıkları araç çıktısına yazılmaz. Yine de sırları sohbet metnine koymak yerine mümkün olduğunda ortam değişkeni veya istemcinin gizli değer yönetimini kullanın.

`observe_web_page` bir tarayıcı bulamazsa hata vermek yerine `static-http` moduna geçer ve `render_uyarisi` alanında nedeni bildirir. Form doldurma, oturum açma ve tıklama gibi etkileşimli tarayıcı otomasyonu bu ilk aşamanın kapsamı dışındadır.

`research_web` hız için JavaScript tarayıcısı açmaz. Dinamik bir sayfanın statik HTML'i yetersizse ilgili URL daha sonra `observe_web_page(render_javascript=true)` ile derinlemesine incelenebilir.
