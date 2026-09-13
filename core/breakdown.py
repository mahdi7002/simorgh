import json
from collections import Counter
from pathlib import Path

from core.paths import ROOT
catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
docs = catalog.get("standalone_docs_unique", catalog["standalone_docs"])
home = str(Path.home())

counter = Counter()
for d in docs:
    rel = d[len(home)+1:] if d.startswith(home) else d
    top = rel.split("/")[0]
    counter[top] += 1

for name, count in counter.most_common(25):
    print(f"{count:5d}  {name}")
