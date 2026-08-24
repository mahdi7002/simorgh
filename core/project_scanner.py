import json
from pathlib import Path

EXCLUDE_DIRS = {"venv", "node_modules", ".git", "__pycache__", ".cache", "site-packages", "models"}
PROJECT_MARKERS = {".git", "main.py", "manage.py", "package.json", "requirements.txt", "app.py"}
DOC_EXTS = {".txt", ".md", ".pdf"}
MAX_DEPTH_FROM_HOME = 3  # فقط تا ۳ سطح زیر خانه رو به‌عنوان ریشه پروژه در نظر بگیر

def has_marker(d: Path) -> bool:
    try:
        names = {p.name for p in d.iterdir()}
    except (PermissionError, OSError):
        return False
    return bool(names & PROJECT_MARKERS)

def scan():
    home = Path.home()
    projects = []
    project_paths = set()
    standalone_docs = []

    def walk(d: Path, depth: int):
        if any(part in EXCLUDE_DIRS for part in d.parts):
            return
        if has_marker(d):
            projects.append(str(d))
            project_paths.add(str(d))
            return  # دیگه داخل این پروژه دنبال پروژهٔ تودرتو نگرد
        if depth >= MAX_DEPTH_FROM_HOME:
            return
        try:
            for child in d.iterdir():
                if child.is_dir():
                    walk(child, depth + 1)
        except (PermissionError, OSError):
            pass

    for top in home.iterdir():
        if top.is_dir() and top.name not in EXCLUDE_DIRS:
            walk(top, 1)

    def inside_project(f: Path) -> bool:
        fs = str(f)
        return any(fs.startswith(p + "/") for p in project_paths)

    for ext in DOC_EXTS:
        for f in home.rglob(f"*{ext}"):
            if any(part in EXCLUDE_DIRS for part in f.parts):
                continue
            if inside_project(f):
                continue
            standalone_docs.append(str(f))

    catalog = {"projects": sorted(projects), "standalone_docs": standalone_docs}
    out_path = Path.home() / "simorgh" / "catalog.json"
    out_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"پروژه‌های واقعی پیداشده: {len(projects)}")
    print(f"اسناد مستقل (قبل از حذف تکراری): {len(standalone_docs)}")

if __name__ == "__main__":
    scan()
