import sqlite3, json, os, requests, time
from tqdm import tqdm
import sys
sys.path.insert(0, '.')

LIMIT = 5000  # تعداد مقالات
DB_PATH = "data/simorgh.db"
API_URL = "https://fa.wikipedia.org/w/api.php"

def fetch_articles(limit):
    titles = []
    params = {
        "action": "query",
        "format": "json",
        "list": "allpages",
        "aplimit": min(limit, 500),
        "apnamespace": 0
    }
    while len(titles) < limit:
        resp = requests.get(API_URL, params=params).json()
        for page in resp["query"]["allpages"]:
            titles.append(page["title"])
            if len(titles) >= limit:
                break
        if "continue" in resp:
            params["apcontinue"] = resp["continue"]["apcontinue"]
        else:
            break
    return titles

def fetch_extracts(titles, batch_size=50):
    conn = sqlite3.connect(DB_PATH)
    for i in tqdm(range(0, len(titles), batch_size), desc="دانلود مقالات"):
        batch = titles[i:i+batch_size]
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts",
            "exintro": 1,
            "explaintext": 1,
            "titles": "|".join(batch)
        }
        resp = requests.get(API_URL, params=params).json()
        pages = resp.get("query", {}).get("pages", {})
        for page_id, data in pages.items():
            title = data.get("title", "")
            extract = data.get("extract", "")
            if extract:
                conn.execute("INSERT OR IGNORE INTO nodes (type, name, properties) VALUES ('article', ?, ?)",
                             (title, json.dumps({"source": "wikipedia"})))
                conn.execute("INSERT OR IGNORE INTO memory_fts (node_id, content) VALUES ((SELECT id FROM nodes WHERE name=?), ?)",
                             (title, extract))
        time.sleep(0.5)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    print(f"دریافت {LIMIT} عنوان مقاله...")
    titles = fetch_articles(LIMIT)
    print(f"دانلود خلاصهٔ مقالات...")
    fetch_extracts(titles)
    print(f"✔ {LIMIT} مقاله به پایگاه دانش اضافه شد.")
