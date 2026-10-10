"""
Otonom Plan & Görev Takipçisi MCP Sunucusu (Task Planner & Scratchpad)
Bu sunucu, yerel LLM'in çok adımlı karmaşık projelerde hedefinden sapmasını önlemek,
ilerlemeyi takip etmek ve adımları disiplinli bir şekilde tamamlamasını sağlamak için kullanılır.
"""

import os
import json
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Task-Planner-Tools")

PLAN_FILE = os.path.join(os.getcwd(), ".agent_plan.json")


def _load_plan() -> Dict[str, Any]:
    if os.path.exists(PLAN_FILE):
        try:
            with open(PLAN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"gorevler": []}
    return {"gorevler": []}


def _save_plan_file(data: Dict[str, Any]) -> None:
    with open(PLAN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@mcp.tool()
def create_plan(tasks: List[str]) -> str:
    """
    Çok adımlı bir görev için yeni bir iş planı oluşturur.
    (Örn: tasks=["1. Proje dosyalarını incele", "2. CSS flexbox hatalarını düzelt", "3. Projeyi derle ve test et"])

    Parametreler:
        tasks: Sıralı yapılacaklar listesi (string listesi).
    """
    if not tasks:
        return "HATA: En az bir görev tanımlanmalıdır."

    plan_items = []
    for idx, t in enumerate(tasks, start=1):
        plan_items.append({
            "id": idx,
            "gorev": t,
            "durum": "todo",  # todo, in_progress, completed, failed
            "not": ""
        })

    data = {"gorevler": plan_items}
    _save_plan_file(data)
    return f"BAŞARILI: {len(tasks)} adımlık yeni plan oluşturuldu. 'get_current_plan' ile durumu görebilirsiniz."


@mcp.tool()
def update_task_status(task_id: int, status: str, note: Optional[str] = None) -> str:
    """
    Belirli bir görevin durumunu günceller.

    Parametreler:
        task_id: Görevin sıra numarası (1, 2, 3...).
        status: Yeni durum ('todo', 'in_progress', 'completed', 'failed').
        note: Görevle ilgili opsiyonel açıklama veya sonuç notu.
    """
    valid_statuses = {"todo", "in_progress", "completed", "failed"}
    if status.lower() not in valid_statuses:
        return f"HATA: Geçersiz durum '{status}'. Geçerli durumlar: {', '.join(valid_statuses)}"

    data = _load_plan()
    tasks = data.get("gorevler", [])

    found = False
    for item in tasks:
        if item["id"] == task_id:
            item["durum"] = status.lower()
            if note:
                item["not"] = note
            found = True
            break

    if not found:
        return f"HATA: ID={task_id} olan bir görev bulunamadı."

    _save_plan_file(data)
    return f"BAŞARILI: Görev #{task_id} durumu '{status}' olarak güncellendi."


@mcp.tool()
def get_current_plan() -> str:
    """
    Mevcut planı, tamamlanan adımları, devam eden işleri ve kalan görevleri görsel bir kontrol listesi olarak döner.
    """
    data = _load_plan()
    tasks = data.get("gorevler", [])

    if not tasks:
        return "Aktif bir görev planı bulunmuyor. 'create_plan' ile yeni bir plan oluşturabilirsiniz."

    total = len(tasks)
    completed = sum(1 for t in tasks if t["durum"] == "completed")

    status_icons = {
        "todo": "[ ]",
        "in_progress": "[→]",
        "completed": "[✓]",
        "failed": "[✗]"
    }

    lines = [f"=== Ajan Görev Planı ({completed}/{total} Tamamlandı) ==="]
    for t in tasks:
        icon = status_icons.get(t["durum"], "[?]")
        note_str = f" (Not: {t['not']})" if t.get("not") else ""
        lines.append(f"{icon} #{t['id']}: {t['gorev']} [{t['durum']}]{note_str}")

    return "\n".join(lines)


@mcp.tool()
def clear_plan() -> str:
    """
    Mevcut planı temizler ve sıfırlar.
    """
    _save_plan_file({"gorevler": []})
    return "Mevcut plan sıfırlandı."


if __name__ == "__main__":
    mcp.run(transport="stdio")
