# Akıllı PDF Okuma Aracı Kullanım Kılavuzu

Bu araç (`Smart-PDF-Tools`), yüzlerce sayfadan oluşan büyük PDF dokümanlarını (kitaplar, şartnameler, teknik raporlar, akademik makaleler) **tamamen hafif, hızlı ve yapılandırılmış JSON/metin formatında** modele iletmek üzere tasarlanmıştır.

---

## ⚡ Kritik Bilgi: PDF'ler Nasıl Okunur? (Görsel vs. JSON)

> **Önemli Not:** Araç sayfaları varsayılan olarak **asla görsel (piksel) olarak işlemez**. 
> Sayfaları görsel olarak işlemek çok ağır bir GPU ve VRAM yükü getirir. 
> 
> Bu araç, PDF içeriğini doğrudan ayrıştırarak **yapılandırılmış JSON ve düz metin** formatında döner. Görsel alma aracı (`render_pdf_page_to_image`) yalnızca metin olarak okunması imkansız bir el çizimi veya özel bir akış şeması olduğunda çağrılabilecek **tamamen opsiyonel** bir araçtır.

---

## 1. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Dönüş Formatı | Amaç |
|---|---|---|
| `get_pdf_info_and_toc` | **JSON Dict** | Toplam sayfa sayısı, başlık, yazar ve İçindekiler Tablosunu (TOC) listeler. |
| `search_pdf` | **JSON Listesi** | Dokümanda kelime araması yapar. Eşleşen sayfa no ve metin kesitlerini döner. |
| `extract_pdf_pages_as_json` | **Yapılandırılmış JSON** | **(En Güçlü Araç)** Sayfadaki başlıkları, paragrafları ve **veri tablolarını 2D liste/JSON nesnesi** olarak çıkarır. |
| `read_pdf_page_range` | **Markdown Metin** | İlgili sayfa aralığını hafif Markdown formatında okur. |
| `render_pdf_page_to_image` | *PNG Dosya Yolu* | *(Yalnızca Gerekirse)* Karmaşık bir şema veya diyagramı görsel olarak incelemek için opsiyonel araç. |

---

## 2. `extract_pdf_pages_as_json` Çıktı Formatı

Bu fonksiyon PDF'i piksellerle uğraşmadan doğrudan saf ve yapılandırılmış JSON'a döker:

```json
{
  "dosya": "finans_raporu.pdf",
  "sayfa_araligi": "12-12",
  "toplam_sayfa": 150,
  "sayfalar": [
    {
      "sayfa_no": 12,
      "tablolar": [
        [
          ["Çeyrek", "Gelir (M$)", "Kar (M$)"],
          ["Q1", "120.5", "34.2"],
          ["Q2", "145.0", "41.8"]
        ]
      ],
      "metin_bloklari": [
        "12.1. İkinci Çeyrek Mali Analiz Özeti",
        "Bu çeyrekte operasyonel verimlilik artışı sayesinde net kar marjı %28.8 seviyesine ulaşmıştır."
      ]
    }
  ]
}
```

### Neden Bu Yaklaşım Çok Avantajlıdır?
1. **Sıfır GPU VRAM Harcaması:** Görüntü işleme yapılmaz, sadece CPU üzerinde milisaniyeler içinde metin ve tablo matrisi çıkarılır.
2. **Tablolar Bozulmaz:** PDF'lerde metin olarak kopyalandığında darmadağın olan tablolar, gerçek 2D satır-sütun matrisi olarak JSON içinde korunur.
3. **Minimum Token Kullanımı:** Modelin bağlam penceresi görsel token'ları ile dolmaz; yalnızca saf bilgiye odaklanır.

---

## 3. Tavsiye Edilen Çalışma Akışı

1. **Keşif:** `get_pdf_info_and_toc(file_path="manual.pdf")` -> TOC incelenir.
2. **Arama:** `search_pdf(file_path="manual.pdf", query="güvenlik politikası")` -> İlgili sayfalar bulunur.
3. **JSON Olarak Çıkarma:** `extract_pdf_pages_as_json(file_path="manual.pdf", start_page=14, end_page=16)` -> Sayfadaki tablo ve metinler JSON olarak okunur.
