"""
Kod Tabanı ve Dosya Yönetimi MCP Sunucusu (Codebase & Filesystem Tools)
Bu sunucu, yerel LLM'in herhangi bir dildeki (Python, C++, HTML, CSS, JavaScript, Rust vb.)
kod tabanını kolayca incelemesini, arama yapmasını, yeni dosyalar oluşturmasını,
dosyaları silmesini ve büyük dosyaları baştan yazmadan cerrahi olarak düzenlemesini (search & replace) sağlar.
"""

import os
import re
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Codebase-Dev-Tools")

DEFAULT_IGNORE_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv",
    "__pycache__", ".pytest_cache", "build", "dist", ".pdf_cache",
    ".idea", ".vscode", "target", "bin", "obj"
}


@mcp.tool()
def read_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    """
    Belirtilen kaynak kod dosyasını (C++, Python, HTML, CSS, JS vb.) okur.
    Büyük dosyalarda context window'u korumak için satır aralığı (start_line, end_line) belirtilebilir. (1-indeksli)

    Parametreler:
        file_path: Dosya yolu.
        start_line: Okunacak ilk satır (opsiyonel, 1'den başlar).
        end_line: Okunacak son satır (opsiyonel).
    """
    if not os.path.exists(file_path):
        return f"HATA: Dosya bulunamadı: {file_path}"
    if os.path.isdir(file_path):
        return f"HATA: '{file_path}' bir dizindir, dosya değildir. 'list_codebase_tree' kullanın."

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if start_line is not None or end_line is not None:
            s = max(1, start_line if start_line is not None else 1)
            e = min(total_lines, end_line if end_line is not None else total_lines)
            selected = lines[s - 1:e]
            content = "".join([f"{idx:4d} | {line}" for idx, line in enumerate(selected, start=s)])
            return f"--- [{file_path} (Satır {s}-{e} / Toplam {total_lines})] ---\n\n{content}"
        else:
            # Tüm dosya
            if total_lines > 500:
                snippet = "".join([f"{idx:4d} | {line}" for idx, line in enumerate(lines[:500], start=1)])
                return f"--- [{file_path} (İlk 500 satır gösteriliyor, Toplam: {total_lines})] ---\n\n{snippet}\n\n... [Dosya çok uzun olduğu için kesildi. Devamı için start_line=501 ile çağırın] ..."
            else:
                return "".join([f"{idx:4d} | {line}" for idx, line in enumerate(lines, start=1)])

    except Exception as e:
        return f"HATA: Dosya okunurken sorun oluştu: {str(e)}"


@mcp.tool()
def write_file(file_path: str, content: str, overwrite: bool = True) -> str:
    """
    Sıfırdan dosya oluşturur veya mevcut dosyanın üzerine yazar.
    HTML, CSS, C++, Python ve diğer tüm kaynak kod dosyalarını tırnak veya karakter bozulması olmadan güvenle kaydeder.

    Parametreler:
        file_path: Oluşturulacak/yazılacak dosyanın tam veya göreceli yolu.
        content: Dosyaya yazılacak ham kaynak kod içeriği.
        overwrite: Dosya zaten varsa üzerine yazılsın mı? (varsayılan: True).
    """
    try:
        dir_name = os.path.dirname(file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        if os.path.exists(file_path) and not overwrite:
            return f"HATA: '{file_path}' zaten mevcut ve 'overwrite=False' seçilmiş."

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"BAŞARILI: '{file_path}' dosyası başarıyla yazıldı ({len(content)} karakter)."
    except Exception as e:
        return f"HATA: Dosya yazılırken sorun oluştu: {str(e)}"


@mcp.tool()
def edit_file_snippet(file_path: str, target_snippet: str, replacement_snippet: str) -> str:
    """
    Mevcut bir kaynak kod dosyasında belirli bir kod bloğunu veya fonksiyonu cerrahi olarak değiştirir (Search & Replace).
    Tüm 1000 satırlık dosyayı baştan yazmak yerine sadece değişmesi gereken satırları güncellemek için idealdir.

    Parametreler:
        file_path: Düzenlenecek dosya yolu.
        target_snippet: Değiştirilecek mevcut kod parçası (dosyadakiyle birebir eşleşmelidir).
        replacement_snippet: Yeni eklenecek kod parçası.
    """
    if not os.path.exists(file_path):
        return f"HATA: Dosya bulunamadı: {file_path}"

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if target_snippet not in content:
            return f"HATA: Değiştirilmek istenen 'target_snippet' dosya içerisinde tam olarak bulunamadı. Lütfen 'read_file' ile dosyadaki mevcut satırları kontrol edin."

        occurrence_count = content.count(target_snippet)
        if occurrence_count > 1:
            return f"UYARI: Değiştirilmek istenen blok dosyada {occurrence_count} kez geçiyor. Yanlış yeri değiştirmemek için lütfen etrafındaki birkaç satırı da dahil ederek daha belirgin bir hedef blok seçin."

        new_content = content.replace(target_snippet, replacement_snippet, 1)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        return f"BAŞARILI: '{file_path}' dosyasındaki hedef kod parçası başarıyla güncellendi."
    except Exception as e:
        return f"HATA: Düzenleme sırasında sorun oluştu: {str(e)}"


@mcp.tool()
def delete_file(file_path: str) -> str:
    """
    Belirtilen bir dosyayı diskten siler.
    """
    if not os.path.exists(file_path):
        return f"HATA: Dosya bulunamadı: {file_path}"
    if os.path.isdir(file_path):
        return f"HATA: '{file_path}' bir klasördür. Bu araç yalnızca dosya silmek içindir."

    try:
        os.remove(file_path)
        return f"BAŞARILI: '{file_path}' dosyası başarıyla silindi."
    except Exception as e:
        return f"HATA: Dosya silinirken sorun oluştu: {str(e)}"


@mcp.tool()
def list_codebase_tree(directory_path: str = ".", max_depth: int = 3) -> str:
    """
    Bir kod projesinin dizin ve dosya hiyerarşisini (ağaç yapısını) çıkarır.
    'node_modules', '.git', 'venv' gibi gürültü oluşturan klasörleri otomatik olarak atlar.

    Parametreler:
        directory_path: İncelenecek proje kök dizini (varsayılan: geçerli dizin).
        max_depth: Maksimum derinlik seviyesi (varsayılan: 3).
    """
    if not os.path.exists(directory_path):
        return f"HATA: Dizin bulunamadı: {directory_path}"

    root_abs = os.path.abspath(directory_path)
    tree_lines = [f"[DIR] {os.path.basename(root_abs) or root_abs}/"]

    def build_tree(current_dir: str, depth: int, prefix: str):
        if depth > max_depth:
            return

        try:
            entries = sorted(os.listdir(current_dir))
        except PermissionError:
            return

        # Filtreleme
        dirs = [e for e in entries if os.path.isdir(os.path.join(current_dir, e)) and e not in DEFAULT_IGNORE_DIRS]
        files = [e for e in entries if os.path.isfile(os.path.join(current_dir, e))]

        total_items = len(dirs) + len(files)
        counter = 0

        for d in dirs:
            counter += 1
            is_last = (counter == total_items)
            branch = "`-- " if is_last else "|-- "
            tree_lines.append(f"{prefix}{branch}[DIR] {d}/")
            next_prefix = prefix + ("    " if is_last else "|   ")
            build_tree(os.path.join(current_dir, d), depth + 1, next_prefix)

        for f in files:
            counter += 1
            is_last = (counter == total_items)
            branch = "`-- " if is_last else "|-- "
            tree_lines.append(f"{prefix}{branch}[FILE] {f}")

    build_tree(root_abs, 1, "")
    return "\n".join(tree_lines)


@mcp.tool()
def search_code(
    query: str,
    directory_path: str = ".",
    file_extensions: Optional[List[str]] = None,
    max_matches: int = 10
) -> List[Dict[str, Any]]:
    """
    Kod tabanındaki dosyalarda fonksiyon, sınıf, değişken veya anahtar kelime araması yapar.
    Örn: C++, Python, HTML, CSS dosyalarında arama yaparak dosya yolu, satır numarası ve kod satırını listeler.

    Parametreler:
        query: Aranacak metin veya kelime.
        directory_path: Aranacak dizin (varsayılan: .).
        file_extensions: Aranacak uzantı filtresi (Örn: ['.cpp', '.h'] veya ['.html', '.css', '.py']). Boş bırakılırsa tüm kod dosyaları taranır.
        max_matches: Getirilecek maksimum eşleşme sayısı (varsayılan: 10).
    """
    if not os.path.exists(directory_path):
        return [{"hata": f"Dizin bulunamadı: {directory_path}"}]

    clean_exts = [e.lower() if e.startswith(".") else f".{e.lower()}" for e in file_extensions] if file_extensions else None
    matches = []

    for root, dirs, files in os.walk(directory_path):
        # Gürültülü klasörleri atla
        dirs[:] = [d for d in dirs if d not in DEFAULT_IGNORE_DIRS]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if clean_exts and ext not in clean_exts:
                continue

            file_path = os.path.join(root, file)
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, start=1):
                        if query.lower() in line.lower():
                            matches.append({
                                "dosya": os.path.relpath(file_path, directory_path),
                                "satir_no": line_idx,
                                "kod": line.strip()
                            })
                            if len(matches) >= max_matches:
                                return matches
            except Exception:
                continue

    return matches if matches else [{"mesaj": f"'{query}' ifadesi eşleşen dosyalarda bulunamadı."}]


if __name__ == "__main__":
    mcp.run(transport="stdio")
