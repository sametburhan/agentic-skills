# Yerel Veritabanı (SQLite) İnceleme Aracı Kullanım Kılavuzu

Bu araç (`Database-Tools`), modelinizin yerel SQLite veritabanı dosyalarını (`.db`, `.sqlite`, `.sqlite3`) açıp incelemesini, tablo yapılarını öğrenmesini ve SQL sorguları çalıştırabilmesini sağlar.

---

## 1. Neden Faydalıdır?

Web projeleri, masaüstü yazılımları veya veri bilimi çalışmalarında SQLite sıklıkla kullanılır. Model:
- Veritabanında hangi tabloların ve sütunların olduğunu anında görür.
- Yeni bir özellik eklerken var olan sütun tipleriyle uyumlu SQL veya ORM kodu (SQLAlchemy, Prisma vb.) yazar.
- Test verileri ekleyebilir veya mevcut verileri doğrulayabilir.

---

## 2. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Amaç | Örnek Parametreler |
|---|---|---|
| `get_database_schema` | Veritabanındaki tüm tabloları, sütunları, veri tiplerini ve kayıt sayılarını dökümler. | `db_path`: `"app.db"` |
| `execute_sql_query` | SQL sorgusu çalıştırır (SELECT için satırları, INSERT/UPDATE için etkilenen satır sayısını döner). | `db_path`: `"app.db"`, `query`: `"SELECT * FROM users LIMIT 5"` |

---

## 3. Örnek Kullanım

1. Kullanıcı: *"Bu projedeki `data.db` dosyasını incele, 'siparisler' tablosunda kaç kayıt var?"*
2. Model: `get_database_schema(db_path="data.db")` çağrısını yaparak tüm şemayı analiz eder.
3. Model: `execute_sql_query(db_path="data.db", query="SELECT status, COUNT(*) FROM siparisler GROUP BY status")` ile istatistik çıkarır ve yanıtlar.
