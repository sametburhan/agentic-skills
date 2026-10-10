# REST API & HTTP İstemci Aracı Kullanım Kılavuzu

Bu araç (`API-Client-Tools`), modelinizin yerel bilgisayarınızda veya uzak sunucularda çalışan web servislerini doğrudan test etmesini sağlar (Ajan için hafif bir Postman / cURL alternatifidir).

---

## 1. Neden PowerShell Curl Yerine Bu Araç?

PowerShell üzerinden `curl` veya `Invoke-RestMethod` ile JSON göndermek tırnak işaretleri ve Windows kaçış karakterleri yüzünden modeller için zordur. Bu araç doğrudan yapılandırılmış bir JSON nesnesi alarak isteği hatasız iletir.

---

## 2. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Amaç | Parametreler |
|---|---|---|
| `http_request` | GET, POST, PUT, DELETE veya PATCH istekleri gönderir. Durum kodunu, yanıt süresini ve yanıt gövdesini döner. | `method`, `url`, `headers`, `json_body`, `params`, `timeout` |

---

## 3. Örnek Kullanım Senaryoları

### Senaryo A: Yerel FastAPI Endpoint'ini Test Etme
```python
http_request(
    method="GET",
    url="http://localhost:8000/api/health"
)
```

### Senaryo B: POST İsteği ile JSON Veri Gönderme
```python
http_request(
    method="POST",
    url="http://localhost:8000/api/users",
    headers={"Authorization": "Bearer token123"},
    json_body={"username": "test_user", "email": "test@example.com"}
)
```
Model dönen HTTP 200 veya 422 hata kodunu anında inceleyerek backend kodunu kendi kendine düzeltebilir.
