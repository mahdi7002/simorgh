import random
try:
    from app.knowledge.poetry_lookup import lookup
except Exception:
    lookup = None
TRIG = ("از کیست", "سروده کیست", "کدام شاعر", "شاعرش", "کی گفته", "مال کیست")

class PoetAgent:
    """شاعر سیمرغ - بدون نیاز به پایگاه داده"""
    def __init__(self, memory_agent=None, knowledge_agent=None):
        self.memory = memory_agent
        self.knowledge = knowledge_agent

    def generate_response(self, user_input, emotion):
        if lookup and any(t in user_input for t in TRIG):
            q = user_input
            for t in TRIG:
                q = q.replace(t, " ")
            r = lookup(q)
            if r["status"] == "answer":
                return f"«{r['verse']}»\n— {r['poet']}"
            if r["status"] in ("ambiguous", "uncertain") and r["candidates"]:
                return "مطمئن نیستم؛ احتمالاً از: " + "، ".join(r["candidates"][:3])
            return "این بیت را در مجموعه‌ی شعرم پیدا نکردم."
        templates = {
            "love": [
                "دل در گرو عشق تو، هر ذره‌ام غزل‌خوان شد 🌹",
                "عشق، تنها کلید دروازه‌های ناپیدای وجود است.",
                "هر تپش قلب، زمزمهٔ نام توست."
            ],
            "sadness": [
                "در اعماق اندوه، گوهری خفته است به نام «خویشتن».",
                "باران که می‌بارد، آسمان هم گریه می‌کند… اما فردا آفتاب است.",
                "غم، سایه‌ای است که ردّ پای نور را نشان می‌دهد."
            ],
            "joy": [
                "شادی، همان پرنده‌ای است که در قفس نمی‌خواند؛ رهایش کن! 🕊️",
                "لبخندت، رنگین‌کمانی است بر پهنهٔ هستی.",
                "امروز، جشنی است در هر سلول تنم."
            ],
            "hope": [
                "نور، حتی از باریک‌ترین شکاف‌ها می‌تابد.",
                "فردا، هنوز ننوشته‌ترین صفحهٔ کتاب زندگی‌ست.",
                "تو همان امیدی که جهان به آن محتاج است."
            ],
            "fear": [
                "ترس، گرگی است که تنها به خیال تو زنده است.",
                "شجاعت، نبودن ترس نیست؛ رقصیدن با آن است.",
                "هراسی نیست، این تنها باد است که از کوه می‌آید."
            ],
            "surprise": [
                "چه شگفت! جهان پر از نشانه‌های پنهان است.",
                "هر لحظه، تولد دوباره‌ای است در راز هستی.",
                "در چشمانت حیرتی می‌بینم که کائنات را می‌ماند."
            ],
            "neutral": [
                "هر سخن، بذری است در خاک ذهن؛ بیا بکاریم...",
                "سیمرغ، همواره در جستجوی بلندای قاف است.",
                "حرفی بزن، تا واژه‌ها برقصند."
            ]
        }
        lines = templates.get(emotion, templates["neutral"])
        return random.choice(lines)
