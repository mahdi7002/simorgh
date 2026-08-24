import requests
from . import knowledge_retriever

def query_llm(prompt):
    # ۱. جستجو در پایگاه دانش داخلی
    articles = knowledge_retriever.search_knowledge(prompt, limit=2)
    context = ""
    if articles:
        context = "دانش داخلی:\n" + "\n".join([f"- {a['title']}: {a['content'][:400]}" for a in articles])
        context += "\n\nبر اساس دانش داخلی و درک خود، به پرسش زیر پاسخ بده:\n"
    
    full_prompt = context + prompt if context else prompt
    
    resp = requests.post(
        "http://localhost:8080/v1/chat/completions",
        json={
            "messages": [
                {"role": "system", "content": "تو یک دستیار هوشمند با دسترسی به پایگاه دانش فارسی هستی. از اطلاعات داده‌شده استفاده کن."},
                {"role": "user", "content": full_prompt}
            ],
            "max_tokens": 150,
            "temperature": 0.3
        },
        timeout=60
    )
    return resp.json()["choices"][0]["message"]["content"]
