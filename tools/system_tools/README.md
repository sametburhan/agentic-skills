# Sistem & Terminal Yönetim Aracı Kullanım Kılavuzu

Bu araç (`System-Dev-Tools`), LM Studio içerisindeki yerel yapay zeka modelinize Windows ortamında doğrudan terminal erişimi, PATH üzerindeki yazılım geliştirme araçlarına erişim ve web projelerini Chrome'da önizleme yeteneği kazandırır.

---

## 1. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Açıklama | Örnek Parametreler |
|---|---|---|
| `run_powershell` | PowerShell komutları çalıştırır (`python`, `pip`, `npm`, `git` vb. tüm CLI araçları). | `command`: `"npm run dev"`, `cwd`: `"C:/projeler/web-app"` |
| `run_wsl` | WSL (Ubuntu vb.) içinde doğrudan yerel Linux/Bash komutları çalıştırır (`gcc`, `apt`, `make`, `docker` vb.). | `command`: `"gcc -o app main.c"`, `distro`: `"Ubuntu"` |
| `get_wsl_status` | Sistemdeki WSL dağıtımlarını ve durumlarını listeler. | *(Parametresiz)* |
| `open_in_chrome` | Sistemdeki Google Chrome tarayıcısında belirtilen adresi yeni bir sekmede açar. | `url`: `"http://localhost:5173"` |
| `check_localhost_service` | Belirtilen yerel portun (localhost) açık ve dinlemede olup olmadığını test eder. | `port`: `3000` |
| `get_system_environment_info` | Python, Pip, Node, NPM ve Git versiyonlarını tek raporda listeler. | *(Parametresiz)* |
| `python_run_code` | Python kodunu sistem yorumlayıcısı veya seçilen venv ile çalıştırır. | `code`: `"print('ok')"`, `venv_path`: `".venv"` |
| `python_run_file` | Bir `.py` dosyasını ayrı argümanlarla çalıştırır. | `file_path`: `"scripts/check.py"`, `args`: `["--json"]` |
| `python_create_venv` | Boş bir hedef dizinde yeni Python sanal ortamı oluşturur. | `venv_path`: `".venv"`, `cwd`: `"C:/projeler/api"` |
| `python_install_packages` | Doğrulanmış paket belirtimlerini pip ile kurar. | `packages`: `["fastapi>=0.115", "uvicorn"]`, `venv_path`: `".venv"` |
| `python_install_requirements` | Requirements dosyasını sistem veya venv Python'una kurar. | `requirements_path`: `"requirements.txt"`, `venv_path`: `".venv"` |
| `python_environment_info` | Yorumlayıcı, sürüm, platform, venv ve pip bilgilerini yapılandırılmış döndürür. | `venv_path`: `".venv"` |
| `get_current_datetime` | Güncel yerel veya IANA saat dilimindeki zamanı, UTC karşılığını ve Unix timestamp'i döndürür. | `timezone_name`: `"Europe/Istanbul"` |
| `convert_datetime` | ISO 8601 tarih/saat değerini başka bir saat dilimine dönüştürür. | `datetime_value`: `"2026-10-14T12:00:00Z"`, `target_timezone`: `"Europe/Istanbul"` |
| `calculate_datetime` | Bir tarihe süre ekler; negatif değerlerle çıkarma yapar. | `days`: `7`, `hours`: `-2` |
| `datetime_difference` | İki tarih/saat arasındaki saniye, saat ve gün farkını hesaplar. | `start_datetime`, `end_datetime` |

---

## 2. Tipik İş Akışları

### A. Proje Bağımlılıklarını Yükleme ve Geliştirme Sunucusunu Başlatma
Modeliniz bir projeyi derlemek veya paket yüklemek istediğinde:
```text
Kullanıcı: "Mevcut dizinde bir Vite projesi oluştur ve bağımlılıklarını kur."
Ajan Çağrısı: run_powershell(command="npm create vite@latest frontend -- --template react-ts; cd frontend; npm install")
```

### B. Localhost Kontrolü ve Chrome Sekmesinde Açma
Model yerel bir sunucuyu arka planda başlattıktan sonra portun açılıp açılmadığını kontrol eder ve ardından Chrome'da kullanıcıya sunar:
1. `check_localhost_service(port=5173)` -> "Port AKTİF"
2. `open_in_chrome(url="http://localhost:5173")` -> Chrome'da yeni sekme açılır.

### C. Python Sanal Ortamı ve Bağımlılıklar

```text
python_create_venv(venv_path=".venv", cwd="C:/projeler/api")
python_install_requirements(
  requirements_path="requirements.txt",
  cwd="C:/projeler/api",
  venv_path=".venv"
)
python_run_file(
  file_path="app.py",
  cwd="C:/projeler/api",
  venv_path=".venv",
  args=["--check"]
)
```

Her çağrı bağımsız bir süreçtir; `Activate.ps1` durumu çağrılar arasında taşınmaz. Bunun yerine `venv_path` verilerek doğru yorumlayıcı doğrudan seçilir. `python_install_packages` paketleri shell üzerinden birleştirmez ve pip seçeneği gibi görünen `-` ile başlayan girdileri reddeder.

### D. Git Komutları
- Git branch kontrolü: `run_powershell(command="git status")`

### E. WSL (Linux) Ortamında Çalışma
Model Linux'a özgü araçları çalıştırmak istediğinde:
- Linux derleyicisi kullanma: `run_wsl(command="g++ -O3 -o program main.cpp", distro="Ubuntu")`
- Linux paket kontrolü: `run_wsl(command="dpkg -l | grep python")`
- Linux servisleri: `run_wsl(command="docker ps")`
- WSL dosya sistemine erişim: `\\wsl$\Ubuntu\home\kullanici\...` veya `\\wsl.localhost\Ubuntu\...` yolu doğrudan `read_file` ve `write_file` araçlarıyla kullanılabilir.

### F. Güncel Zaman ve Tarih Hesapları

```text
get_current_datetime(timezone_name="Europe/Istanbul")

convert_datetime(
  datetime_value="2026-10-14T12:00:00Z",
  target_timezone="Europe/Istanbul"
)

calculate_datetime(
  datetime_value="2026-10-14T15:00:00+03:00",
  timezone_name="Europe/Istanbul",
  days=7
)
```

Saat dilimi verilmemiş ISO 8601 değerleri `source_timezone` veya `timezone_name` ile yorumlanır. `local`, `UTC` ve `Europe/Istanbul` gibi IANA saat dilimleri desteklenir.

---

## 3. LM Studio'da Model İçin Örnek Promptlar

Modelinize bu araçları etkin şekilde kullandırmak için sistem talimatına (System Prompt) veya sohbet sırasında şu örnekleri verebilirsiniz:

- *"Bilgisayarımdaki Python ve Node.js sürümlerini kontrol et ve bir sorun olup olmadığını söyle."*
- *"C:/Users/.../my-app dizininde `npm run build` komutunu çalıştır ve çıktısını analiz et."*
- *"Localhost 3000 portunu dinle, aktifse Chrome'da aç."*

---

## 4. Güvenlik ve Hata Yönetimi İpuçları

1. **Zaman Aşımı (Timeout):** Uzun süren derleme veya indirme işlemlerinde varsayılan 60 saniyelik süre yetersiz gelebilir. `timeout_seconds=180` parametresi ile süre artırılabilir.
2. **Kritik Komutlar:** Modelin kaza eseri `Remove-Item` veya `del /s` gibi yıkıcı komutlar çalıştırmaması için modelin System Prompt'una dosya silme işlemlerinden önce kullanıcı onayı istemesi hatırlatılmalıdır.
3. **UTF-8 Karakter Desteği:** Araç, Windows PowerShell çıktısını otomatik olarak UTF-8 olarak kodlar; böylece Türkçe karakterler veya özel semboller bozulmadan modele iletilir.
4. **Python Çıktı Sınırı:** `python_run_code` ve `python_run_file`, aşırı bağlam tüketimini önlemek için stdout ve stderr alanlarını ayrı ayrı 100.000 karakterle sınırlar.
