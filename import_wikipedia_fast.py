import sqlite3, json, os, requests, time

LIMIT = 5000
DB_PATH = "data/simorgh.db"
API_URL = "https://fa.wikipedia.org/w/api.php"

def fetch_articles(limit):
    titles = []
    params = {"action": "query", "format": "json", "list": "allpages", "aplimit": 500, "apnamespace": 0}
    while len(titles) < limit:
        try:
            resp = requests.get(API_URL, params=params, timeout=30).json()
            for page in resp["query"]["allpages"]:
                titles.append(page["title"])
                if len(titles) >= limit:
                    break
            if "continue" in resp:
                params["apcontinue"] = resp["continue"]["apcontinue"]
            else:
                break
        except Exception as e:
            print(f"⚠ خطا در دریافت فهرست: {e} — تلاش مجدد در ۵ ثانیه")
            time.sleep(5)
    return titles

def fetch_extracts(titles):
    conn = sqlite3.connect(DB_PATH)
    done = 0
    for i in range(0, len(titles), 50):
        batch = titles[i:i+50]
        params = {"action": "query", "format": "json", "prop": "extracts", "exintro": 1, "explaintext": 1, "titles": "|".join(batch)}
        try:
            resp = requests.get(API_URL, params=params, timeout=30).json()
            pages = resp.get("query", {}).get("pages", {})
            for page_id, data in pages.items():
                title = data.get("title", "")
                extract = data.get("extract", "")
                if extract:
                    conn.execute("INSERT OR IGNORE INTO nodes (type, name, properties) VALUES ('article', ?, ?)",
                                 (title, json.dumps({"source": "wikipedia"})))
                    conn.execute("INSERT OR IGNORE INTO memory_fts (node_id, content) VALUES ((SELECT id FROM nodes WHERE name=?), ?)",
                                 (title, extract))
                    done += 1
            if i % 500 == 0:
                print(f"   پیشرفت: {done} مقاله از {LIMIT}")
        except Exception as e:
            print(f"⚠ خطا در دریافت مقالات {i}-{i+50}: {e} — رد شدن از این دسته")
        time.sleep(0.8)
    conn.commit()
    conn.close()
    print(f"✔ {done} مقاله با موفقیت ذخیره شد.")

if __name__ == "__main__":
    print(f"دریافت {LIMIT} عنوان مقاله...")
    titles = fetch_articles(LIMIT)
    print(f"دانلود خلاصهٔ {len(titles)} مقاله...")
    fetch_extracts(titles)
