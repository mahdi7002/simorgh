import re

ARCHETYPES = {
    "حافظ": {"keywords": ["عشق", "شراب", "شعر", "دل"], "tone": "شاعرانه و رندانه"},
    "مولانا": {"keywords": ["نی", "سماع", "شمس", "عشق"], "tone": "عارفانه و شورانگیز"},
    "ابن سینا": {"keywords": ["علم", "منطق", "درمان", "عقل"], "tone": "حکیمانه و دقیق"},
    "سهروردی": {"keywords": ["نور", "اشراق", "حکمت", "خیال"], "tone": "اشراقی و نورانی"},
    "رابعه": {"keywords": ["عشق", "خدا", "خلوت", "سوز"], "tone": "عاشقانه و زاهدانه"},
    "بیرونی": {"keywords": ["زمین", "نجوم", "هندسه", "طبیعت"], "tone": "دانشورانه و مشاهده‌گر"}
}

def detect_archetype(text):
    scores = {}
    for archetype, data in ARCHETYPES.items():
        score = sum(1 for kw in data["keywords"] if kw in text)
        if score > 0:
            scores[archetype] = score
    if scores:
        return max(scores, key=scores.get)
    return "حافظ"

def get_archetype_tone(archetype):
    return ARCHETYPES.get(archetype, ARCHETYPES["حافظ"])["tone"]
