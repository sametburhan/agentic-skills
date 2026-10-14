# Yerel Git MCP Araçları

Bu modül artık harici veya yayından kaldırılmış bir npm paketine ihtiyaç duymaz. Windows'taki mevcut `git.exe` doğrudan ve etkileşimsiz alt süreçlerle çalıştırılır.

## Kurulum

`git --version` komutu çalışmalı ve Git PATH üzerinde bulunmalıdır. MCP sunucusu:

```json
{
  "git": {
    "command": "python",
    "args": ["c:/Users/samet/Desktop/agentic-skills/tools/git_tools/server.py"],
    "env": {"PYTHONIOENCODING": "utf-8"}
  }
}
```

## Araçlar

| Araç | Açıklama |
|---|---|
| `git_status` | Dalı ve kısa çalışma ağacı durumunu gösterir. |
| `git_diff` | Stage edilmiş veya edilmemiş diff'i döndürür. |
| `git_log` | Son commitleri yapılandırılmış olarak listeler. |
| `git_branches` | Yerel ve uzak dalları listeler. |
| `git_add` | Seçilen dosyaları veya tüm değişiklikleri stage eder. |
| `git_commit` | Stage edilmiş değişiklikleri commit eder. |
| `git_create_branch` | Geçerli isim kontrolüyle yeni dal oluşturur. |
| `git_checkout` | Var olan bir dala güvenli biçimde geçer. |

Her çağrı `repository_path` alır; böylece aynı MCP sunucusu farklı depolar üzerinde çalışabilir. Push, pull, rebase ve merge gibi uzak veya daha riskli işlemler ilk aşamada kasıtlı olarak eklenmemiştir.
