import sqlite3, json, os
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def discover_from_events(window_minutes=5, min_occurrences=3):
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT a.entity_name, a.event_type, b.entity_name, b.event_type, COUNT(*)
        FROM events a
        JOIN events b ON a.id < b.id
        WHERE (julianday(b.timestamp) - julianday(a.timestamp)) * 1440 BETWEEN 1 AND ?
        AND a.entity_name != b.entity_name
        GROUP BY a.entity_name, a.event_type, b.entity_name, b.event_type
        HAVING COUNT(*) >= ?
    """
    rows = conn.execute(query, (window_minutes, min_occurrences)).fetchall()
    proposals = []
    for r in rows:
        proposals.append({
            "source": f"{r[0]}_{r[1]}",
            "target": f"{r[2]}_{r[3]}",
            "relation": "causes",
            "confidence": min(0.9, 0.4 + r[4] * 0.1),
            "explanation": f"کشف خودکار: {r[0]} ({r[1]}) → {r[2]} ({r[3]}) | {r[4]} بار تکرار"
        })
    conn.close()
    return proposals

def apply_discoveries(proposals):
    """
    اصل ۱۶ منشور: دقیقاً مثلِ apply_proposals در reflection.py — سیمرغ
    هرگز رابطه‌ی علّیِ کشف‌شده را بدونِ تأییدِ انسان به حافظه‌ی گراف
    اضافه نمی‌کند. این تابع فقط پیشنهادها را چاپ/برمی‌گرداند؛ اعمالِ
    واقعی باید توسط یک انسان و به‌صورتِ صریح انجام شود.
    """
    print(f"[گاورننس] {len(proposals)} رابطه‌ی علّیِ کشف‌شده — طبق اصل ۱۶ "
          "منشور، اعمال نمی‌شود. برای بررسی و اعمالِ دستی، proposals را ببین.")
    return 0
