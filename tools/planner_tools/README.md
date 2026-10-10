# Otonom Plan & Görev Takipçisi (Task Planner) Kullanım Kılavuzu

Bu araç (`Task-Planner-Tools`), yerel yapay zeka modelinizin uzun ve çok adımlı mühendislik görevlerinde odağını kaybetmeden, adım adım ilerlemesini ve her aşamada ne yaptığını size şeffaf bir şekilde raporlamasını sağlar.

---

## 1. Neden Kritik Bir Araçtır?

Özellikle yerel açık kaynaklı modeller (7B, 8B, 14B), tek bir promptta birden fazla karmaşık görev verildiğinde:
- Ortadaki adımları atlayabilir.
- Hangi adımda kaldığını unutup aynı komutu tekrar tekrar çalıştırabilir.

Bu araç ile model, göreve başlamadan önce kendine bir **yapılacaklar listesi (todo checklist)** oluşturur ve her adımı bitirdikçe işaretler. Durum `.agent_plan.json` dosyasında saklanır.

---

## 2. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Amaç | Örnek Parametreler |
|---|---|---|
| `create_plan` | Yeni bir çok adımlı görev planı başlatır. | `tasks`: `["1. Dosyaları listele", "2. Kodu yaz", "3. Test et"]` |
| `update_task_status` | Görevin durumunu günceller (`todo`, `in_progress`, `completed`, `failed`). | `task_id`: `2`, `status`: `"completed"`, `note`: `"Hata çözüldü"` |
| `get_current_plan` | Mevcut planı ve tamamlanma oranını görüntüler. | *(Parametresiz)* |
| `clear_plan` | Mevcut planı sıfırlar. | *(Parametresiz)* |

---

## 3. Örnek Ajan İş Akışı

1. **Kullanıcı:** *"Bu backend projesine JWT authentication ekle, testlerini yaz ve derle."*
2. **Model Planı Başlatır:**
   ```python
   create_plan(tasks=[
       "1. Mevcut auth.py dosyasını incele",
       "2. JWT token üretme fonksiyonunu ekle",
       "3. Endpoint'e login koruması ekle",
       "4. Pytest testlerini yaz ve çalıştır"
   ])
   ```
3. **Model Adım Adım İlerler:**
   - 1. adımı yapar -> `update_task_status(task_id=1, status="completed")`
   - 2. adımı yapar -> `update_task_status(task_id=2, status="in_progress")`
4. Kullanıcı istediği an *"Şu an hangi aşamadasın?"* dediğinde model `get_current_plan()` çıktısını paylaşır:
   ```text
   === Ajan Görev Planı (2/4 Tamamlandı) ===
   [✓] #1: Mevcut auth.py dosyasını incele [completed]
   [✓] #2: JWT token üretme fonksiyonunu ekle [completed]
   [→] #3: Endpoint'e login koruması ekle [in_progress]
   [ ] #4: Pytest testlerini yaz ve çalıştır [todo]
   ```
