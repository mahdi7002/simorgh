#!/usr/bin/env python3
import sys, io
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
API = "http://localhost:8000"

def ask_question(text):
    with console.status("[bold green]در حال اندیشیدن..."):
        resp = requests.post(f"{API}/ask", json={"text": text})
        if resp.status_code != 200:
            console.print("[red]خطا در ارتباط با سیمرغ[/]")
            return
        data = resp.json()
        console.print(Panel(data.get("response", "پاسخی دریافت نشد"), title="[bold cyan]پاسخ سیمرغ[/]", border_style="cyan"))

def show_status():
    r = requests.get(f"{API}/status").json()
    table = Table(title="وضعیت سیستم")
    table.add_column("بخش", style="cyan")
    table.add_column("وضعیت", style="green")
    for k,v in r.items():
        table.add_row(k, "✅" if v else "❌")
    console.print(table)

def main():
    console.print("🦅 [bold gold]سیمرغ[/] — فرمانده خط محلی\n", justify="center")
    print("دستورها: ۱ (پرسش) | ۲ (وضعیت) | خروج (پایان)")
    while True:
        try:
            cmd = input("\n> ").strip()
            if cmd == "خروج":
                break
            elif cmd == "۱":
                q = input("پرسش خود را وارد کنید: ").strip()
                if q:
                    ask_question(q)
            elif cmd == "۲":
                show_status()
            else:
                console.print("[red]فرمان نامعتبر[/]")
        except (KeyboardInterrupt, EOFError):
            break
    console.print("\nاز کویر تا بی‌نهایت — سیمرغ همواره با توست.", style="bold green")

if __name__ == "__main__":
    main()
