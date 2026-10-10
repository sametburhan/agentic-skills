# Kalıcı Proje Hafızası (Persistent Memory) Kullanım Kılavuzu

Bu araç (`Persistent-Memory-Tools`), yerel dil modelinizin oturumlar arasında mimari kuralları, kullanıcı tercihlerini ve proje standartlarını kalıcı olarak hatırlamasını sağlar.

---

## 1. Neden İhtiyaç Duyulur?

Yerel LLM'lerde sohbet penceresi sıfırlandığında model projenin kurallarını unutur. Her seferinde:
*"Python 3.11 kullanıyoruz, type hint zorunlu, testler pytest ile yazılmalı"* demek yerine, model bunu bir kez hafızaya kaydeder ve gelecekteki tüm sohbetlerde hatırlar.

Hafıza verileri yerel olarak `.agent_memory.json` dosyasında saklanır.

---

## 2. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Amaç | Örnek Parametreler |
|---|---|---|
| `save_memory` | Anahtar-değer çifti ve kategori ile kalıcı bilgi kaydeder. | `key`: `"api_port"`, `value`: `"8000"`, `category`: `"ayarlar"` |
| `read_memory` | Belirli bir anahtara ait bilgiyi çeker. | `key`: `"kod_stili"` |
| `list_memories` | Kayıtlı tüm hafızayı veya kategoriye göre listeler. | `category`: `"mimari"` *(opsiyonel)* |
| `delete_memory` | Artık geçerli olmayan bir bilgiyi hafızadan siler. | `key`: `"gecici_ip"` |

---

## 3. Örnek Kullanım

- Kullanıcı: *"Bu projede veritabanı olarak SQLite kullanacağız ve modeller `src/models/` altında toplanacak. Bunu aklında tut."*
- Model çağrısı:
  ```python
  save_memory(
      key="veritabani_yapisi",
      value="Veritabanı: SQLite. Modeller: src/models/ dizininde yer almalı.",
      category="mimari"
  )
  ```
- Sonraki oturumda model: `read_memory(key="veritabani_yapisi")` çağırarak kuralı hatırlar.
