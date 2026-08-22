import requests

def query_llm(prompt):
    resp = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={"messages": [{"role": "system", "content": "تو یک دستیار مفید و مختصر هستی."},
                           {"role": "user", "content": prompt}],
              "max_tokens": 80, "temperature": 0.3},
        timeout=60
    )
    return resp.json()["choices"][0]["message"]["content"]
