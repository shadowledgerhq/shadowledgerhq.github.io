"""Archive des notes officielles Netmarble (forum EN, boards 13 Developer Notes, 14 Updates, 32 Notices)
-> data/db/netmarble_notes.json. Entrée : dossier de dumps texte <board>_<id>.txt (1re ligne titre, 2e date).
Usage : python3 tools/build_notes_netmarble.py DOSSIER [AAAA-MM-JJ]"""
import json, re, sys, datetime
from pathlib import Path
D = Path(sys.argv[1]); DATE = sys.argv[2] if len(sys.argv) > 2 else "2026-11-16"
RACINE = Path(__file__).resolve().parent.parent
BOARDS = {"13": "Developer Notes", "14": "Updates", "32": "Notices"}
out = []
for f in sorted(D.glob("*_*.txt")):
    board, id_ = f.stem.split("_")
    if board not in BOARDS: continue
    t = f.read_text(encoding="utf-8").split("\n")
    titre, date = t[0].strip(), t[1].strip()
    corps = "\n".join(t[2:])
    i = corps.find("All Rights Reserved.")
    i = i + len("All Rights Reserved.") if i >= 0 else 0
    j = corps.find("We require consent", i)
    corps = corps[i:j] if j > i else corps[i:]
    corps = re.sub(r"[ \t]+\n", "\n", corps)
    corps = re.sub(r"\n{3,}", "\n\n", corps).strip()
    try: iso = datetime.datetime.strptime(date, "%b %d, %Y").date().isoformat()
    except ValueError: iso = None
    out.append({"id": f"{board}-{id_}", "kind": "note", "board": BOARDS[board], "date": iso,
        "name": {"fr": "", "en": titre}, "icon": None,
        "source": f"https://forum.netmarble.com/slv_en/view/{board}/{id_}", "verified_at": DATE,
        "game_version": None, "text_en": corps,
        "notes": "Texte intégral lu au navigateur (EN). Les tableaux et images des notes peuvent être incomplets."})
out.sort(key=lambda e: (e["date"] or "", e["id"]))
p = RACINE / "data" / "db" / "netmarble_notes.json"
p.write_text("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in out) + "\n]\n", encoding="utf-8")
print(len(out), p.stat().st_size // 1024, "Ko")
