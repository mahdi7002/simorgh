import re

GOAL_PATTERNS = [
    (r"(روشن|خاموش)\s+(شدن|کردن)\s*(تلویزیون|لامپ|کولر)", "device_control"),
    (r"چرا\s+(.+)", "why_question"),
    (r"دستور\s+(پخت|آشپزی)\s+(.+)", "recipe_request"),
    (r"یادآوری\s+(.+)", "reminder"),
    (r"چی\s+بپزم", "meal_suggestion"),
    (r"مشاوره\s+(تربیتی|درسی)", "consultation"),
    (r"چطور\s+(.+)", "how_to"),
]

def extract_goal(text):
    for pattern, intent in GOAL_PATTERNS:
        m = re.search(pattern, text)
        if m:
            return {"intent": intent, "description": text}
    return {"intent": "general", "description": text}
