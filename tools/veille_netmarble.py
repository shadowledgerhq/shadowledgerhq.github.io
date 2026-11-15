"""Veille des notes officielles Netmarble (forum EN) : « Developer Notes » (13) et « Updates » (14).
Compare avec data/veille/netmarble.json, écrit les nouveautés dans data/veille/a_traiter.md. Gratuit (Playwright, pas d'API payante).
Usage : python3 tools/veille_netmarble.py   (pip install playwright ; playwright install chromium ; ou CHROMIUM_PATH)
Sortie : code 0 ; imprime NOUVEAU: <titre> <url> pour chaque nouvelle note."""
import json, os, re, sys, datetime
from playwright.sync_api import sync_playwright
BASE = "https://forum.netmarble.com/slv_en"
BOARDS = {"13": "Developer Notes", "14": "Updates"}
ETAT, RAPPORT = "data/veille/netmarble.json", "data/veille/a_traiter.md"
def lire(page, b):
    page.goto(f"{BASE}/list/{b}/1", wait_until="networkidle", timeout=90000)
    out = []
    for li in page.query_selector_all("li"):
        a = li.query_selector(f'a[href*="/slv_en/view/{b}/"]')
        if not a: continue
        txt = " ".join(li.inner_text().split())
        m = re.search(r"([A-Z][a-z]{2} \d{1,2}, \d{4})", txt)
        date = datetime.datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat() if m else None
        out.append({"id": a.get_attribute("href").rstrip("/").split("/")[-1], "board": b, "url": "https://forum.netmarble.com" + a.get_attribute("href"),
                    "titre": " ".join(a.inner_text().split()), "date": date})
    seen, res = set(), []
    for x in out:
        if x["id"] not in seen: seen.add(x["id"]); res.append(x)
    return res
def main():
    kw = {"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--no-sandbox"], **kw); page = br.new_page()
        lus = [x for b in BOARDS for x in lire(page, b)]; br.close()
    if not lus: print("ERREUR : aucune note lue (page changée ?)"); sys.exit(1)
    connus = json.load(open(ETAT, encoding="utf-8")) if os.path.exists(ETAT) else {"notes": {}}
    premiere = not connus["notes"]
    nouvelles = [x for x in lus if x["id"] not in connus["notes"]]
    now = datetime.date.today().isoformat()
    for x in lus: connus["notes"].setdefault(x["id"], {**x, "vu_le": now})
    connus["derniere_verification"] = now
    json.dump(connus, open(ETAT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if nouvelles and not premiere:
        L = open(RAPPORT, encoding="utf-8").read() if os.path.exists(RAPPORT) else ""
        add = "".join(f"- {now} · **{BOARDS[x['board']]}** · {x['date']} · [{x['titre']}]({x['url']}) — à traiter (discussion 9)\n" for x in nouvelles)
        head = "# Veille Netmarble : notes à traiter\nLigne supprimée une fois la note intégrée à `patches.json`.\n\n"
        open(RAPPORT, "w", encoding="utf-8").write(head + add + L.replace(head, ""))
        for x in nouvelles: print("NOUVEAU:", x["titre"], x["url"])
    else: print("Rien de nouveau." if not premiere else f"Première lecture : {len(lus)} notes enregistrées.")
main()
