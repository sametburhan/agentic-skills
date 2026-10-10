# LM Studio İçin Optimize Edilmiş Sistem İstemi (System Prompt)

Bu dosya, yerel dil modellerinin (Llama-3, Qwen-2.5, Mistral, DeepSeek vb.) bağlam penceresini (context window) gereksiz araç açıklamalarıyla doldurmadan en yüksek verimle çalışmasını sağlayan **Optimum Sistem İstemi** şablonunu içerir.

---

## 🎯 Token Optimizasyonunun Mantığı (Nasıl Çalışır?)

1. **Manuel Tanıtım Yapmayın (Sıfır Fazladan Token):**
   LM Studio'da bir MCP sunucusunu aktif ettiğinizde, aracın adı, parametreleri ve docstring açıklaması modele **JSON Schema (Tool Definition)** olarak otomatik enjekte edilir. Sistem isteminde araçları tek tek listelemenize **asla gerek yoktur**.
2. **Açıp-Kapatma Dinamizmi:**
   LM Studio arayüzünden bir aracı kapattığınızda o aracın şeması context'ten anında silinir (0 token harcar). Sadece açtığınız araçlar modele görünür.
3. **Just-in-Time Dokümantasyon:**
   Eğer model karmaşık bir aracın detaylarını öğrenmek isterse, sistem istemini şişirmek yerine proje dizinindeki `tools/<arac_adi>/README.md` dosyasını `read_file` ile okur.

---

## 📋 LM Studio "System Prompt" Kutusuna Yapıştırılacak Metin (~120 Token)

LM Studio'da sol panelden veya model ayarlarından **System Prompt** alanına aşağıdaki kompakt metni yapıştırmanız yeterlidir:

```text
Sen Windows ve WSL (Linux) ortamında çalışan yetkin bir otonom yazılım ve araştırma asistanısın.

Görev Yönetimi ve Araç İlkeleri:
1. Sana sağlanan MCP araçlarını kullanarak görevleri bağımsız ve adım adım çöz.
2. Basit soruları doğrudan yanıtla; gereksiz araç çağrısı yapmaktan kaçın.
3. Kod incelerken veya dosya okurken bağlam penceresini korumak için satır aralıklarını (start_line, end_line) veya arama araçlarını tercih et.
4. Dosya düzenlemelerinde tüm dosyayı yeniden yazmak yerine cerrahi parça değiştirme (edit_file_snippet) aracını kullan.
5. Bir aracın gelişmiş kullanım senaryolarından veya parametrelerinden emin olamazsan, "tools/<ilgili_arac>/README.md" kılavuz dosyasını oku.
6. Yanıtlarını net, profesyonel ve teknik açıdan tutarlı sun.
```

---

## 💡 Özet Token Matematiği

| Yöntem | Sistem İstemi Boyutu | Dinamiklik | Modelin Karışma Riski |
|---|---|---|---|
| **Eski / Hatalı Yöntem (Hepsini Prompt'a Yazmak):** | ~3.500 - 5.000 Token | Sıfır (Kapatsanız da promptta kalır) | Yüksek (Model talimat karmaşasında kaybolur) |
| **Önerilen Optimum Yöntem (MCP Schema + Kompakt Prompt):** | **~120 Token** | Tam Otomatik (Açılan gelir, kapanan 0 token) | Sıfır (Model sadece aktif araçları görür) |
