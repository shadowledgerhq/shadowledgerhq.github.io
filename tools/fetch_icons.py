"""Télécharge les icônes (images de api.slagate.com/cdn référencées par GET /api/references, accord d'Alexis du 13/11/2026),
les convertit en PNG 128x128 (fond transparent, proportions conservées) dans data/icons/<categorie>/<id>.png
et renseigne le champ `icon` des fichiers data/db/*.json. Cadence : 1 requête toutes les 0,5 s, reprise possible.
Usage : python3 -I tools/fetch_icons.py <references.json>"""
import io, json, os, re, sys, time, urllib.request
from PIL import Image

d = json.load(open(sys.argv[1]))["data"]
UA = "ShadowLedger-DB/1.0"
norm = lambda s: re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip().lower()
def load(f): return json.load(open(f"data/db/{f}.json"))
def save(f, x): json.dump(x, open(f"data/db/{f}.json", "w"), ensure_ascii=False, indent=2)
last = [0.0]

def fetch(url, dest):
    if os.path.exists(dest): return "déjà"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    wait = 0.5 - (time.time() - last[0])
    if wait > 0: time.sleep(wait)
    last[0] = time.time()
    for attempt in range(3):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read()
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            im.thumbnail((128, 128), Image.LANCZOS)
            out = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
            out.paste(im, ((128 - im.width) // 2, (128 - im.height) // 2))
            out.save(dest, "PNG", optimize=True)
            return "ok"
        except Exception as e:
            err = str(e)[:60]; time.sleep(2 * (attempt + 1))
    return "échec " + err

stats = {}
def run(cat, entries, api_list, key="nom", idf=lambda o: o["id"], apikey=None):
    idx = {norm(a[key]): a for a in api_list if a.get("image")}
    ok = miss = 0; fails = []
    for o in entries:
        fr = o["name"]["fr"] if "name" in o else None
        a = idx.get(norm(fr)) if fr else None
        if not a: miss += 1; continue
        path = f"data/icons/{cat}/{idf(o)}.png"
        r = fetch(a["image"], path)
        if r.startswith("échec"): fails.append((idf(o), r)); continue
        o["icon"] = path; ok += 1
    stats[cat] = (ok, miss, fails)

H = load("hunters"); run("hunters", H, d["chasseurs"]); save("hunters", H)
Wl = load("weapons"); run("weapons", Wl, d["armes"]); save("weapons", Wl)
C = load("cores"); run("cores", C, d["noyaux"]); save("cores", C)
Sh = load("shadows"); run("shadows", Sh, d["ombres"]); save("shadows", Sh)
B = load("blessings"); run("blessings", B, d["pierresBenediction"]); save("blessings", B)
Rl = load("sjw_skills"); run("sjw_skills", [r for r in Rl if r["kind"] == "rune"], d["competences"]); save("sjw_skills", Rl)
# pièces d'artefacts
A = load("artifact_sets"); idx = {(norm(a["set_name"]), norm(a["nom"])): a for a in d["artefacts"]}
ok = miss = 0; fails = []
for s in A:
    first = None
    for p in s["pieces"]:
        a = idx.get((norm(s["name"]["fr"]), norm(p["name"]["fr"])))
        if not a or not p.get("slot"): miss += 1; continue
        path = f"data/icons/artifact_pieces/{s['id']}--{p['slot']}.png"
        r = fetch(a["image"], path)
        if r.startswith("échec"): fails.append((path, r)); continue
        p["icon"] = path; ok += 1; first = first or path
    if first: s["icon"] = first
stats["artifact_pieces"] = (ok, miss, fails)
save("artifact_sets", A)
for k, (ok, miss, fails) in stats.items(): print(f"{k}: {ok} icônes, {miss} sans correspondance, {len(fails)} échecs {fails[:3]}")
