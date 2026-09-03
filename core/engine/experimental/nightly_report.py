import sqlite3, json, os, datetime
DB_PATH = os.path.join(os.path.dirname(__file__), "../../data/simorgh.db")

def generate_report():
    conn = sqlite3.connect(DB_PATH)
    today = datetime.date.today().isoformat()
    cmds = conn.execute("SELECT COUNT(*) FROM terminal_history WHERE date(timestamp)=?", (today,)).fetchone()[0]
    errors = conn.execute("SELECT COUNT(*) FROM terminal_history WHERE date(timestamp)=? AND command LIKE '%not found%'", (today,)).fetchone()[0]
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    cmds_y = conn.execute("SELECT COUNT(*) FROM terminal_history WHERE date(timestamp)=?", (yesterday,)).fetchone()[0]
    report = {
        "date": today,
        "total_commands": cmds,
        "error_commands": errors,
        "commands_yesterday": cmds_y,
        "trend": "up" if cmds > cmds_y else "down"
    }
    conn.close()
    path = os.path.join(os.path.dirname(__file__), "../../data/reports", f"report_{today}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Nightly report saved: {path}")

if __name__ == "__main__":
    generate_report()
