# Office Belgeleri (DOCX & PPTX) Okuma Aracı Kullanım Kılavuzu

Bu araç (`Office-Document-Tools`), yerel dil modelinizin Microsoft Word raporlarını (`.docx`) ve Microsoft PowerPoint sunumlarını (`.pptx`) hafif ve yapılandırılmış bir **JSON/metin** formatında doğrudan açıp okumasını, arama yapmasını ve özet çıkarmasını sağlar.

---

## 1. Neden Bu Araçlara İhtiyaç Var?

- Birçok proje şartnamesi, iş analizi ve teknik rapor `.docx` formatında teslim edilir.
- Proje sunumları, toplantı slaytları ve mimari özetler `.pptx` formatında paylaşılır.
- Bu dosyalar ikili (binary zip/xml) formatta olduğu için standart metin editörleri tarafından okunamaz.
- Bu araç sayesinde model:
  1. **Word Belgelerindeki:** Başlık hiyerarşisini (H1, H2), paragrafları ve tabloları bozulmadan okur.
  2. **PowerPoint Sunumlarındaki:** Slayt başlıklarını, madde işaretlerini, sunum tablolarını ve en önemlisi **Konuşmacı Notlarını (Speaker Notes)** analiz eder.

---

## 2. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Dosya Türü | Amaç | Örnek Parametreler |
|---|---|---|---|
| `read_docx` | Word (.docx) | Başlıkları, paragrafları ve tabloları JSON olarak okur. | `file_path`: `"Rapor.docx"` |
| `search_docx` | Word (.docx) | Belgede kelime araması yapar. | `file_path`: `"Rapor.docx"`, `query`: `"bütçe"` |
| `get_pptx_outline` | PowerPoint (.pptx) | Sunumun slayt sayısını ve başlık listesini döner (İçindekiler). | `file_path`: `"Sunum.pptx"` |
| `read_pptx` | PowerPoint (.pptx) | Belirtilen slayt aralığını, maddeleri ve konuşmacı notlarını okur. | `file_path`: `"Sunum.pptx"`, `start_slide`: `1`, `end_slide`: `10` |
| `search_pptx` | PowerPoint (.pptx) | Sunumda kelime araması yapar ve eşleşen slayt numaralarını döner. | `file_path`: `"Sunum.pptx"`, `query`: `"Q3 hedefleri"` |

---

## 3. Örnek Kullanım Senaryoları

### Senaryo A: 50 Sayfalık Bir Word Raporunu İnceleme
1. Model `search_docx(file_path="C:/Users/samet/Desktop/proje_raporu.docx", query="risk analizi")` çağrısı yaparak ilgili paragrafları anında bulur.
2. Ya da `read_docx(file_path="proje_raporu.docx")` ile tüm tablo ve başlıkları JSON matrisi olarak okur.

### Senaryo B: PowerPoint Sunumunu Özetleme
1. Model önce `get_pptx_outline(file_path="pazarlama.pptx")` ile tüm slayt başlıklarını görür.
2. Ardından `read_pptx(file_path="pazarlama.pptx", start_slide=1, end_slide=5)` ile ilk 5 slaydın içeriğini ve konuşmacı notlarını okuyup özet çıkarır.

---

## 4. Dönen Çıktı Formatı (JSON Örneği)

### `read_docx` Çıktı Örneği:
```json
{
  "dosya": "Proje_Raporu.docx",
  "toplam_paragraf": 42,
  "toplam_tablo": 2,
  "icerik": [
    {"stil": "Heading 1", "metin": "1. Giriş ve Amaç"},
    {"stil": "Normal", "metin": "Bu proje yerel LLM mimarisini geliştirmek için hazırlanmıştır."}
  ],
  "tablolar": [
    {
      "tablo_no": 1,
      "satirlar": [
        ["Modül Adı", "Bellek Tüketimi", "Durum"],
        ["PDF Okuyucu", "12 MB", "Aktif"],
        ["Office Tools", "8 MB", "Aktif"]
      ]
    }
  ]
}
```

### `read_pptx` Çıktı Örneği:
```json
{
  "dosya": "Yillik_Plan.pptx",
  "okunan_aralik": "1-3",
  "toplam_slayt": 24,
  "slaytlar": [
    {
      "slayt_no": 1,
      "baslik": "2026 Teknoloji Vizyonu",
      "maddeler": [
        "Ajanik iş akışlarının yaygınlaşması",
        "Yerel açık kaynak modellerin entegrasyonu"
      ],
      "tablolar": [],
      "konusmaci_notlari": "Burada dinleyicilere yerel VRAM avantajlarından bahsetmeyi unutma."
    }
  ]
}
```

---

## 5. WSL ve Windows Yol Uyumluluğu

Her iki araç da hem Windows dosya yollarını hem de WSL Linux yollarını otomatik algılar:
- Windows: `C:/Users/samet/Desktop/Rapor.docx`
- WSL: `/home/samet/projects/Rapor.docx` (Arka planda `\\wsl$\Ubuntu\home\samet\projects\Rapor.docx` olarak çözümlenir).
