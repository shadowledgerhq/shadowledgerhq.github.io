"""Lit les pages d'ombres du wiki Fandom (Category:Army of Shadows) et écrit data/db/shadows.json.
Usage : python3 -I tools/parse_fandom_shadows.py <sortie.json>"""
import json, re, sys, urllib.parse, urllib.request
API = "https://solo-leveling-arise.fandom.com/api.php"
WIKI = "https://solo-leveling-arise.fandom.com/wiki/"

def get(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"})))

def clean(s):
    s = re.sub(r"\{\{Res\|[^{}]*\}\}", "", s or "")
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|([^{}]*)\}\}", r"\1", s)
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|", "", s)
    s = re.sub(r"\[\[File:[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s).replace("{{", "").replace("}}", "")
    s = re.sub(r"<div[^>]*>|</div>", " ", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def slug(n): return re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "")).strip("-")

def params(text):
    d = {}
    for m in re.finditer(r"^\|\s*([A-Za-z0-9_]+)\s*=(.*?)(?=^\|\s*[A-Za-z0-9_]+\s*=|\Z)", text, re.S | re.M):
        d.setdefault(m.group(1).lower(), m.group(2).strip())
    return d

def tmpl(txt, name):
    m = re.search(r"\{\{\s*" + name + r"\s*\n(.*?)(?:^\}\}|\}\}[ \t]*(?=\n[ \t]*\n|\n==|\Z))", txt, re.S | re.M)
    return params(re.sub(r"^\|\s*\|", "|", m.group(1), flags=re.M)) if m else {}

titles = [m["title"] for m in get({"action": "query", "list": "categorymembers", "cmtitle": "Category:Army of Shadows", "cmlimit": 500})["query"]["categorymembers"] if m["title"] != "Army of Shadows"]
q = get({"action": "query", "prop": "revisions", "rvprop": "content|timestamp|ids", "rvslots": "main", "titles": "|".join(titles)})
RANKS = ["common", "elite", "knight", "elite_knight", "general"]
out = []
for pg in q["query"]["pages"].values():
    r = pg["revisions"][0]; txt = r["slots"]["main"]["*"]
    name = clean(pg["title"])
    promo = tmpl(txt, "Shadow Promotion")
    sk = tmpl(txt, "Shadow Skills")
    arm = tmpl(txt, "Shadow Armament")
    nick = re.search(r"'''([^']+)'''\.", txt)
    obtain = re.search(r"==\s*Obtaining and Promotion\s*==\s*(.*?)(?=\n\{\{Shadow Promotion|\n==)", txt, re.S)
    leader = {}
    for rk in RANKS:
        v = promo.get(rk + "_authority")
        if v:
            n = re.search(r"Data\|([\d.]+)", v)
            leader[rk] = {"text": clean(v), "value": float(n.group(1)) if n else None}
    skills = []
    for i in range(1, 10):
        if sk.get(f"skill{i}") or sk.get(f"skill{i}_des"):
            skills.append({"slot": i, "name": {"fr": "", "en": clean(sk.get(f"skill{i}_name", "")), "ko": ""},
                           "text": {"fr": "", "en": clean(sk.get(f"skill{i}_des", ""))},
                           "effects_text_en": clean(sk.get(f"skill{i}", "")), "effects": [], "values_by_level": {}})
    out.append({"id": slug(name), "name": {"fr": "", "en": name, "ko": ""}, "rarity": None,
                "nickname_en": nick.group(1) if nick else None,
                "obtaining_en": clean(obtain.group(1)) if obtain else None,
                "leader_skill_by_rank": leader, "skills": skills,
                "passives": [], "armament_en": {k: clean(v) for k, v in arm.items()} or None,
                "values_by_level": {}, "icon": None, "source": WIKI + urllib.parse.quote(pg["title"].replace(" ", "_")),
                "wiki_revid": r.get("revid"), "wiki_timestamp": r.get("timestamp"), "verified_at": "2026-11-13", "game_version": None,
                "notes": "Texte EN du wiki Fandom (CC BY-SA), non vérifié en jeu. Les chefs d'ombre ont été rééquilibrés le 22/10/2026 (cf. patches.json) : valeurs du wiki possiblement antérieures. Nom FR et icône à compléter."})
out.sort(key=lambda s: s["id"])
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
for s in out: print(s["id"], len(s["skills"]), list(s["leader_skill_by_rank"]).__len__(), s["wiki_timestamp"][:10], bool(s["armament_en"]))
print(sum(1 for s in out if "{{" in json.dumps(s)), "avec restes de modèle")
