# Yerel LLM Otonom Geliştirici & Araştırma Ajanı (LM Studio + Modüler MCP)

Bu depo, **LM Studio** ortamında çalışan yerel açık kaynaklı ve görsel (vision) yetenekli dil modellerini tam donanımlı bir otonom ajana dönüştüren modüler araç setidir.

Yerel modellerin sınırlı bağlam penceresini (context window) korumak için tüm araçlar **bağımsız modüller** olarak tasarlanmıştır. İhtiyacınıza göre araçları tek tıkla açıp kapatabilirsiniz.

---

## 📁 Proje Yapısı

```text
c:\Users\samet\Desktop\agentic-skills\
│
├── README.md                      # Ana Kılavuz (Bu dosya)
├── SYSTEM_PROMPT.md               # LM Studio için optimize edilmiş kompakt Sistem İstemi
├── mcp_config.json                # LM Studio ve MCP istemcileri için modüler ayar dosyası
├── requirements.txt               # Gerekli Python kütüphaneleri
├── install_dependencies.bat       # Tek tıkla bağımlılık yükleme betiği
├── unified_server.py              # Tüm araçları tek çatıda toplayan Birleşik Sunucu
│
└── tools/
    ├── codebase_tools/            # Dosya oluşturma, silme, satır bazlı okuma, cerrahi düzenleme, kod arama
    │   ├── server.py
    │   └── README.md
    │
    ├── system_tools/              # Windows PowerShell, WSL (Linux Bash), PATH araçları ve Chrome sekmesi açma
    │   ├── server.py
    │   └── README.md
    │
    ├── memory_tools/              # Kalıcı proje hafızası (kuralları, tercihleri ve mimariyi hatırlama)
    │   ├── server.py
    │   └── README.md
    │
    ├── planner_tools/             # Otonom plan ve görev takipçisi (Adım adım yapılacaklar listesi)
    │   ├── server.py
    │   └── README.md
    │
    ├── api_tools/                 # REST API ve HTTP istemcisi (GET, POST, PUT, DELETE testleri)
    │   ├── server.py
    │   └── README.md
    │
    ├── vision_image_tools/        # Yerel UI mockup ve görselleri VRAM dostu optimize edip Vision'a sunma
    │   ├── server.py
    │   └── README.md
    │
    ├── database_tools/            # SQLite veritabanı şema analizi ve SQL sorgulama
    │   ├── server.py
    │   └── README.md
    │
    ├── pdf_tools/                 # 100+ sayfalık PDF'ler için TOC, arama, sayfa okuma ve Vision görseli alma
    │   ├── server.py
    │   └── README.md
    │
    ├── web_tools/                 # DDGS arama, temiz metin çıkarma ve Chrome/Edge headless sayfa gözlemi
    │   ├── search_server.py
    │   ├── README.md
    │   └── puppeteer_guide.md     # Eski Puppeteer yapılandırmaları için geçiş notları
    │
    ├── diagram_tools/             # Mermaid şemalarını ve Markdown sayfalarını PNG görsellerine dönüştürme
    │   ├── server.py
    │   └── README.md
    │
    ├── office_tools/              # Word (.docx) raporları ve PowerPoint (.pptx) sunumlarını yapılandırılmış okuma
    │   ├── server.py
    │   └── README.md
    │
    └── git_tools/                 # Yerel Git durum, diff, log, branch, add ve commit araçları
        ├── server.py
        └── README.md
```

---

## 🎯 Proje Bazlı Modüler Çalışma (Bağlam Penceresi Optimizasyonu)

Yerel 7B, 8B veya 14B modellerin bellek taşmasını önlemek için LM Studio ayarlarından projenizin türüne göre sadece ilgili sunucuları aktif bırakmanız önerilir:

### Profil A: Temel Kod Geliştirme (En Hafif Bağlam)
- `core-codebase` (Dosya okuma, yazma, arama, ağaç yapısı)
- `core-system` (PowerShell, WSL Linux terminali)
- `git` (Versiyon kontrolü)

### Profil B: Backend & API Geliştirme
- `core-codebase` + `core-system`
- `api-client` (FastAPI / Express endpoint testleri)
- `web-search` (`websocket_*` araçlarıyla `ws://` ve `wss://` servis testi)
- `sqlite-database` (Veritabanı tabloları ve SQL sorguları)
- `task-planner` (Çok adımlı görevleri unutmamak için)

### Profil C: Frontend & UI Tasarım
- `core-codebase` + `core-system`
- `vision-images` (Tasarım mockup'larını modele gösterme)
- `web-search` (`observe_web_page` ile statik veya JavaScript-render edilmiş sayfa inceleme)

### Profil D: Araştırma, Dokümantasyon & Ofis
- `office-tools` (Word raporları ve PowerPoint sunumlarını JSON okuma)
- `smart-pdf` (Uzun PDF kitap ve makale analizi)
- `web-search` (`research_web` ile ilk 20 sonucu toplu araştırma ve kaynaklı içerik okuma)
- `project-memory` (Öğrenilen bilgileri kalıcı kaydetme)

---

## ⚙️ Kurulum ve LM Studio Entegrasyonu

### 1. Adım: Python Bağımlılıklarını Kurun
Çalışma dizinindeki `install_dependencies.bat` dosyasını çift tıklayarak çalıştırın:
```powershell
python -m pip install -r requirements.txt
```

Betik kendi proje dizinine otomatik geçer, MCP yapılandırmasındaki `python` komutuyla aynı yorumlayıcıyı tercih eder ve kurulum hatasında başarı mesajı göstermez. Otomatik kullanım için `install_dependencies.bat --no-pause` çalıştırılabilir.

### 2. Adım: LM Studio'ya MCP Sunucularını Tanıtın
1. LM Studio uygulamasını açın ve **Settings (Ayarlar) / Developer -> MCP Servers** bölümüne gidin.
2. [mcp_config.json](file:///c:/Users/samet/Desktop/agentic-skills/mcp_config.json) dosyasını içe aktarın veya sunucuları ekleyin.
3. Çalışacağınız projeye göre yukarıdaki profillerden birini seçerek ilgili sunucuların yanındaki anahtarları açık tutun.

> `all-in-one-suite` kullanıyorsanız aynı modüler sunucuları ayrıca açmayın; araç isimleri yinelenir.
> Yapılandırma değişikliğinden sonra MCP istemcisini yeniden başlatın.

---

## 📖 Ayrıntılı Kılavuzlar

- [Ofis Belgeleri (DOCX & PPTX) Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/office_tools/README.md)
- [Kod Tabanı & Dosya Yönetimi Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/codebase_tools/README.md)
- [Sistem, PowerShell & WSL Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/system_tools/README.md)
- [Kalıcı Proje Hafızası Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/memory_tools/README.md)
- [Otonom Görev Planlayıcı Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/planner_tools/README.md)
- [REST API İstemcisi Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/api_tools/README.md)
- [Vision Görsel İnceleme Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/vision_image_tools/README.md)
- [SQLite Veritabanı Aracı Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/database_tools/README.md)
- [Akıllı PDF & Vision Aracı Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/pdf_tools/README.md)
- [Web Arama & İçerik Çekme Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/web_tools/README.md)
- [Eski Puppeteer Yapılandırmaları İçin Geçiş Notları](file:///c:/Users/samet/Desktop/agentic-skills/tools/web_tools/puppeteer_guide.md)
- [Mermaid & Markdown to PNG Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/diagram_tools/README.md)
- [Git MCP Aracı Kılavuzu](file:///c:/Users/samet/Desktop/agentic-skills/tools/git_tools/README.md)
