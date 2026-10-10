# Mermaid Diyagram ve Markdown to PNG Aracı Kullanım Kılavuzu

Bu araç (`Diagram-Visualizer-Tools`), özellikle yazılım mimarisi, akış şemaları ve teknik raporlarda sıklıkla kullanılan **Mermaid diyagram kodlarını** ve **Markdown (.md) sayfalarını** doğrudan yüksek kaliteli **PNG görsellerine** dönüştürür.

---

## 1. Neden Bu Araca İhtiyaç Var?

- Yazılım mimarisi şemaları (flowchart, sequenceDiagram, erDiagram, classDiagram) sıklıkla Markdown içinde kod olarak tutulur.
- Bu şemaları sunumlarda, sosyal medyada, dokümanlarda veya üçüncü parti sistemlerde görsel (PNG) olarak kullanmak için manuel ekran görüntüsü almak zahmetlidir.
- Bu araç ile model:
  1. İster ham Mermaid kodunu,
  2. İsterse WSL ya da Windows'taki bir `.md` dosyasının içindeki diyagramları tek komutla PNG olarak çıkartıp kaydeder.

---

## 2. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Amaç | Örnek Parametreler |
|---|---|---|
| `render_mermaid_to_png` | Tek bir Mermaid diyagramını (koddan veya dosyadan) PNG'ye dönüştürür. | `mermaid_code_or_file`: `"flowchart TD; A-->B"`, `output_png_path`: `"diyagram.png"`, `theme`: `"default"` |
| `extract_and_render_all_mermaid_diagrams` | Bir `.md` dosyasındaki **tüm** ```mermaid bloklarını tespit edip ayrı ayrı PNG yapar. | `input_md_path`: `"/home/samet/README.md"`, `output_directory`: `"C:/Users/samet/Desktop/semalar"` |
| `convert_markdown_to_png` | Tüm Markdown doküman sayfasını şık bir görsel (PNG) olarak kaydeder. | `input_md_path`: `"notlar.md"`, `output_png_path`: `"sayfa1.png"` |

---

## 3. Örnek Kullanım Senaryoları

### Senaryo A: Ham Koddan Anında PNG Üretme
```python
render_mermaid_to_png(
    mermaid_code_or_file="""
    sequenceDiagram
        Kullanici->>Sunucu: Giris Yap(kullanici, sifre)
        Sunucu-->>Veritabani: Kullaniciyi Dogrula
        Veritabani-->>Sunucu: Basarili
        Sunucu-->>Kullanici: JWT Token
    """,
    output_png_path="C:/Users/samet/Desktop/auth_flow.png",
    theme="neutral"
)
```

### Senaryo B: WSL İçindeki Bir Markdown Dosyasındaki Şemaları Ayıklama
Kullanıcı: *"WSL'deki `mimari.md` dosyasındaki akış şemalarını Masaüstüme PNG olarak çıkart."*
```python
extract_and_render_all_mermaid_diagrams(
    input_md_path="\\\\wsl$\\Ubuntu\\home\\samet\\mimari.md",
    output_directory="C:/Users/samet/Desktop/Mimariler"
)
```
Araç `diagram_1.png`, `diagram_2.png` olarak tüm şemaları belirtilen klasöre kaydeder.
