# Kapsamlı Git MCP Aracı Kullanım Kılavuzu

Git entegrasyonu, yerel modelinizin kod projelerinizdeki değişiklikleri takip etmesini, commit mesajları üretmesini, branch oluşturmasını ve diff incelemesi yapmasını sağlar.

Bu amaçla resmi ve açık kaynaklı **Git MCP Sunucusu** (`@modelcontextprotocol/server-git`) kullanılır.

---

## 1. Kurulum ve Çalıştırma

Git MCP sunucusu doğrudan `npx` aracılığıyla çalıştırılır. Çalıştırılırken hedef Git deposunun yolu (repository path) argüman olarak verilir:

```bash
npx -y @modelcontextprotocol/server-git C:/Users/samet/Desktop/projeniz
```

*(Birden fazla proje için veya dinamik dizin geçişleri için `run_powershell` aracımızla birlikte hibrit olarak da kullanılabilir).*

---

## 2. Sunulan Git Araçları (Tools)

| Fonksiyon Adı | Açıklama |
|---|---|
| `git_status` | Değiştirilen, silinen ve henüz izlenmeyen (untracked) dosyaları listeler. |
| `git_diff_unstaged` | Stage edilmemiş (çalışma alanındaki) satır bazlı kod değişikliklerini (diff) gösterir. |
| `git_diff_staged` | `git add` ile stage edilmiş, commit edilmeye hazır değişiklikleri gösterir. |
| `git_add` | Belirtilen dosyaları veya tüm değişiklikleri staging alanına ekler. |
| `git_commit` | Açıklayıcı bir mesaj ile yeni bir commit oluşturur. |
| `git_log` | Son commit geçmişini, yazar ve mesaj detaylarıyla listeler. |
| `git_create_branch` | Yeni bir Git dalı (branch) oluşturur. |
| `git_checkout` | Farklı bir dala veya commit'e geçiş yapar. |

---

## 3. Hibrit Model: Git MCP + PowerShell Terminali

Bazı durumlarda Git MCP'nin sağladığı standart fonksiyonların ötesine geçmeniz gerekebilir:
- `git push origin main` (Uzak sunucuya gönderme / SSH anahtarları)
- `git pull --rebase`
- `git stash pop`
- `git merge feature-branch`

Bu tür özel veya etkileşimli operasyonlar için modeliniz `system_tools` içindeki `run_powershell` aracını kullanarak doğrudan terminal Git komutunu da tetikleyebilir:
```text
run_powershell(command="git push origin main", cwd="C:/Users/samet/Desktop/projem")
```

---

## 4. Model İçin Örnek Promptlar

- *"Mevcut depodaki değişiklikleri kontrol et (`git_status`), mantıklı gruplara bölerek conventional commit formatında commit'le."*
- *"Son 5 commit'i incele ve sürüm notu (changelog) taslağı oluştur."*
- *"`refactor/login-page` adında yeni bir branch aç ve oraya geç."*
