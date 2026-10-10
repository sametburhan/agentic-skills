# Kod Tabanı ve Dosya Yönetim Aracı Kullanım Kılavuzu

Bu araç seti (`Codebase-Dev-Tools`), LM Studio'daki yerel modelinize tam teşekküllü bir yazılım geliştirici gibi herhangi bir dildeki (**HTML, CSS, JavaScript, TypeScript, C++, Python, Rust, Go, SQL vb.**) projeleri inceleme, anlama, dosya oluşturma, silme ve mevcut kodları cerrahi hassasiyetle düzenleme yeteneği kazandırır.

---

## 1. Neden Terminal Komutları Yerine Bu Özel Araçlar Kullanılmalıdır?

PowerShell üzerinden `echo "kod" > dosya.py` veya `Set-Content` ile kod yazmak:
- Çift tırnaklar, ters bölü (`\`), süslü parantez (`{}`) ve çok satırlı stringlerde **kaçış karakteri (escaping) hatalarına** yol açar.
- 1000 satırlık bir C++ dosyasında 2 satırlık bir hata düzeltmek için tüm dosyayı baştan yazdırmak hem dakikalar sürer hem de modelin bağlam penceresini (context window) tüketir.

Bu araç seti ile:
1. **`write_file`**: Hiçbir karakter bozulması olmadan doğrudan dosyayı diske yazar.
2. **`edit_file_snippet`**: Sadece değişecek fonksiyonu veya bloğu bulup değiştirir (Search & Replace).
3. **`read_file`**: İstenen satır aralığını satır numaralarıyla okur (örn: 45-80 arası satırlar).

---

## 2. Sunulan Araçlar (Tools)

| Fonksiyon Adı | Amaç | Örnek Parametreler |
|---|---|---|
| `list_codebase_tree` | Projenin dizin ve dosya hiyerarşisini listeler (`node_modules`, `.git`, `venv` otomatik elenir). | `directory_path`: `"./src"`, `max_depth`: `3` |
| `search_code` | Kod dosyalarında fonksiyon/sınıf/değişken araması yapar. Satır no ve dosya yolunu döner. | `query`: `"calculate_total"`, `file_extensions`: `[".cpp", ".h"]` |
| `read_file` | Dosyayı okur. Büyük dosyalarda istenirse satır aralığı verilebilir. | `file_path`: `"main.cpp"`, `start_line`: `10`, `end_line`: `60` |
| `write_file` | Sıfırdan dosya oluşturur veya üzerine yazar. | `file_path`: `"index.html"`, `content`: `"<!DOCTYPE html>..."` |
| `edit_file_snippet` | Dosyadaki hedef kod bloğunu yeni kodla günceller (Cerrahi Search & Replace). | `file_path`: `"styles.css"`, `target_snippet`: `"color: red;"`, `replacement_snippet`: `"color: #3b82f6;"` |
| `delete_file` | İstenmeyen bir dosyayı diskten siler. | `file_path`: `"temp.log"` |

---

## 3. Tipik Kod İnceleme ve Düzenleme İş Akışı

Modelinize büyük veya yabancı bir proje teslim ettiğinizde otonom olarak şu sırayı izler:

1. **Projeyi Keşfetme:**
   `list_codebase_tree(directory_path="C:/projeler/oyun-motoru")`
   *(Projenin klasör yapısını, dosya adlarını ve mimarisini anlar).*

2. **İlgili Kodu Bulma:**
   `search_code(query="class Player", file_extensions=[".cpp", ".h"])`
   *(Oyuncu sınıfının `include/Player.h` dosyasında 45. satırda tanımlandığını bulur).*

3. **Hedefli Okuma:**
   `read_file(file_path="include/Player.h", start_line=40, end_line=90)`
   *(Sadece ilgili 50 satırı okuyarak bellek tasarrufu yapar).*

4. **Hata Düzeltme / Özellik Ekleme:**
   `edit_file_snippet(file_path="include/Player.h", target_snippet="int health = 100;", replacement_snippet="int health = 100;\n    int mana = 50;")`
   *(Dosyanın geri kalanına dokunmadan sadece değişkeni ekler).*

---

## 4. LM Studio İçin Örnek Promptlar

- *"Mevcut dizindeki C++ projesinin dosya yapısını incele ve `main.cpp` dosyasında belleği serbest bırakmayan yerleri kontrol et."*
- *"Bir `index.html` ve buna bağlı modern bir `style.css` dosyası oluştur, ardından `open_in_chrome` ile tarayıcıda aç."*
- *"`services/auth.py` dosyasındaki şifre doğrulama fonksiyonunu bcrypt kullanacak şekilde güncelle."*
