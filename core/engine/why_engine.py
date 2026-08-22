from . import memory_graph

def find_cause(user_text):
    if "چرا" in user_text:
        # حذف "چرا" و برداشتن کلمهٔ اول (اسم اصلی)
        rest = user_text.replace("چرا", "").strip()
        subject = rest.split()[0] if rest else rest  # اولین کلمه
        cause_text = memory_graph.query_cause_graph(subject)
        if cause_text:
            return cause_text
        # اگر با اولین کلمه پیدا نشد، با کل عبارت (برای اطمینان)
        cause_text = memory_graph.query_cause_graph(rest)
        if cause_text:
            return cause_text
        return "علت در حافظه یافت نشد، نیاز به استدلال داریم."
    return ""
