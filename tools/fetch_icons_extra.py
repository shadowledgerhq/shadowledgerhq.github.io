"""Complète la base avec les successeurs (nom FR + icône) et les 9 compétences QTE de Sung Jin Woo (nom FR, élément, icône)
depuis GET https://api.slagate.com/api/references (route publique, accord d'Alexis du 13/11/2026, icônes autorisées).
Usage : python3 -I tools/fetch_icons_extra.py <references.json>"""
import io, json, os, re, sys, time, unicodedata, urllib.request
from PIL import Image
d = json.load(open(sys.argv[1]))["data"]
SRC = "https://api.slagate.com/api/references (route GET publique ; accord d'Alexis 13/11/2026)"
slug = lambda n: re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode().lower().replace("'", "").replace("’", "")).strip("-")
EL = {"feu": "fire", "eau": "water", "vent": "wind", "lumière": "light", "ténèbres": "dark", "neutre": "neutral", "bris": "break"}
def load(f): return json.load(open(f"data/db/{f}.json"))
def save(f, x): json.dump(x, open(f"data/db/{f}.json", "w"), ensure_ascii=False, indent=2)
last = [0.0]
def fetch(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if os.path.exists(dest): return True
    time.sleep(max(0, 0.5 - (time.time() - last[0]))); last[0] = time.time()
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "ShadowLedger-DB/1.0"}), timeout=30).read()
    im = Image.open(io.BytesIO(raw)).convert("RGBA"); im.thumbnail((128, 128), Image.LANCZOS)
    out = Image.new("RGBA", (128, 128), (0, 0, 0, 0)); out.paste(im, ((128 - im.width) // 2, (128 - im.height) // 2)); out.save(dest, "PNG", optimize=True)
    return True
# successeurs
MAP = {"myro": "Myro", "velvet": "Velvet", "the-monarch-of-shadows": "Monarque des Ombres"}
api = {p["nom"]: p for p in d["passifsDeBoss"] if p["type"] == "successeur"}
S = load("successors"); n = 0
for s in S:
    p = api.get(MAP.get(s["id"]))
    if not p: continue
    s["name"]["fr"] = p["nom"]; s["name_fr_source"] = SRC
    path = f"data/icons/successors/{s['id']}.png"
    if p.get("image") and fetch(p["image"], path): s["icon"] = path
    n += 1
save("successors", S)
# compétences QTE de SJW
R = load("sjw_skills"); have = {r["id"] for r in R}; q = 0
for c in d["qte"]:
    i = "qte--" + slug(c["nom"])
    if i in have: continue
    path = f"data/icons/sjw_skills/{i}.png"
    fetch(c["image"], path)
    els = [EL.get(c[k].lower(), c[k]) for k in ("element", "element2", "element3") if c.get(k)]
    R.append({"id": i, "kind": "skill", "name": {"fr": c["nom"], "en": "", "ko": ""}, "rarity": None, "type": "qte", "runes": [], "element": els[0] if els else None,
              "tags": els, "cooldown": None, "effects": [], "values_by_level": {}, "icon": path, "source": SRC, "name_fr_source": SRC,
              "verified_at": "2026-11-14", "game_version": None,
              "notes": "Compétence QTE de Sung Jin Woo (liste « qte » de l'API slagate). Nom EN, effets et valeurs à saisir ; `tags` = éléments/effets listés par l'API (ex. neutral, break)."})
    q += 1
save("sjw_skills", R)
print("successeurs :", n, "| QTE ajoutées :", q)
