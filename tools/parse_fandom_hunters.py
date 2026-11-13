"""Lit les pages de chasseurs du wiki Fandom (API MediaWiki) et écrit data/db/hunters.json.
Usage : python3 -I tools/parse_fandom_hunters.py <sortie.json>"""
import json, re, sys, urllib.parse, urllib.request

API = "https://solo-leveling-arise.fandom.com/api.php"
WIKI = "https://solo-leveling-arise.fandom.com/wiki/"

def get(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"})))

def clean(s):
    s = re.sub(r"\{\{Res\|[^{}]*\}\}", "", s)
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|([^{}]*)\}\}", r"\1", s)
    s = re.sub(r"\{\{(?:SSR|SR|R|Class)\|?([^{}|]*)[^{}]*\}\}", lambda m: m.group(0) if False else (m.group(1) or ""), s)
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|", "", s)  # modèles mal fermés sur le wiki
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = s.replace("{{", "").replace("}}", "")
    s = re.sub(r"\[\[File:[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<div[^>]*>|</div>", " ", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def slug(n):
    return re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "")).strip("-")

def params(text):
    d = {}
    for m in re.finditer(r"^\|\s*([a-z0-9_]+)\s*=(.*?)(?=^\|\s*[a-z0-9_]+\s*=|^\}\}|\Z)", text, re.S | re.M | re.I):
        d.setdefault(m.group(1).lower(), m.group(2).strip())
    return d

def first(pat, s, g=1):
    m = re.search(pat, s)
    return m.group(g) if m else None

def num(v):
    m = re.match(r"\s*([\d][\d,\.]*)", v or "")
    return m.group(1) if m else None

def nums(s):
    m = re.search(r"Data\|([\d.,]+)(?:-([\d.,]+))?", s or "")
    return m.groups() if m else None

def skill(kind, p, k):
    name = p.get(k + "_name")
    if not name: return None
    body = p.get(k if k != "basic" else "basic_attacks") or p.get(k + "_attack") or ""
    cd = first(r"Cooldown: \{\{[^|]*\|[^|]*\|([\d.]+)", body)
    mp = first(r"MP Consumption: \{\{[^|]*\|[^|]*\|([\d.\-]+)", body)
    return {"type": kind, "name": {"fr": "", "en": clean(name), "ko": ""}, "text": {"fr": "", "en": clean(p.get(k + "_des", ""))},
            "cooldown": float(cd) if cd else None, "mp_cost": mp,
            "effects": [], "effects_text_en": clean(body), "values_by_level": {}}

titles = [m["title"] for m in get({"action": "query", "list": "categorymembers", "cmtitle": "Category:Characters", "cmlimit": 500})["query"]["categorymembers"]]
out = []
for i in range(0, len(titles), 20):
    q = get({"action": "query", "prop": "revisions", "rvprop": "content|timestamp|ids", "rvslots": "main", "titles": "|".join(titles[i:i+20])})
    for pg in q["query"]["pages"].values():
        r = pg.get("revisions", [{}])[0]
        txt = r.get("slots", {}).get("main", {}).get("*", "")
        if not re.search(r"Hunter[_ ]Infobox2", txt): continue
        txt = re.sub(r"^\|\s*\|", "|", txt, flags=re.M)
        txt = re.sub(r"\|((?:basic|core|skill1|skill2|support|qte|ultimate)(?:_name|_des|_attacks?|_mod)?|passive|a[1-5]|total_power[12]|hp[12]|attack[12]|defense[12])=", r"\n|\1=", txt)
        p = params(txt)
        name = clean(p.get("title1", pg["title"]))
        type_en = (first(r"\{\{Class\|([^}|]*)", p.get("type", "")) or clean(p.get("type", "")).split(" ")[0] or "").lower().strip() or None
        role = {"elemental stacker": "stacker", "elemental buster": "buster", "supporter": "supporter"}.get(type_en)
        element = (first(r"\|\s*([A-Za-z]+) Element", p.get("element", "")) or clean(p.get("element", ""))).lower() or None
        rarity = (first(r"\{\{(S?S?R|SR|R)\b", p.get("rarity", "")) or "").lower() or None
        sk = [skill(k, p, key) for k, key in (("basic_attack", "basic"), ("core_attack", "core"), ("skill_1", "skill1"), ("skill_2", "skill2"), ("support", "support"), ("qte", "qte"), ("ultimate", "ultimate"))]
        out.append({"id": slug(name), "name": {"fr": "", "en": name, "ko": ""}, "rarity": rarity, "role": role, "type_en": type_en,
                    "element": element, "class": clean(p.get("role", "")) or None, "weapon_type": None,
                    "exclusive_weapon": clean(p.get("exclusive_weapon", "")) or None,
                    "release_date_en": clean(p.get("release_date", "")) or None,
                    "skills": [s for s in sk if s], "passives": [{"tier": 0, "text": {"fr": "", "en": clean(p["passive"])}}] if p.get("passive") else [],
                    "base_stats": {"lv1": {"hp": num(p.get("hp1")), "attack": num(p.get("attack1")), "defense": num(p.get("defense1")), "total_power": num(p.get("total_power1"))},
                                   "max": {"hp": num(p.get("hp2")), "attack": num(p.get("attack2")), "defense": num(p.get("defense2")), "total_power": num(p.get("total_power2"))}},
                    "advancement": [{"tier": n, "text": {"fr": "", "en": clean(p[f"a{n}"])}} for n in range(1, 6) if p.get(f"a{n}")],
                    "icon": None, "source": WIKI + urllib.parse.quote(pg["title"].replace(" ", "_")), "wiki_revid": r.get("revid"),
                    "wiki_timestamp": r.get("timestamp"), "verified_at": "2026-11-13", "game_version": None,
                    "notes": "Texte EN du wiki Fandom (CC BY-SA), non vérifié en jeu ; page possiblement antérieure aux rééquilibrages récents (cf. patches.json). Nom FR et icône à compléter. Noms de compétences copiés tels quels (certains en français sur le wiki)."})
out.sort(key=lambda h: h["id"])
succ = [h for h in out if h["type_en"] == "successor"]
hun = [h for h in out if h["type_en"] != "successor"]
for h in succ: h["role"] = None
json.dump(hun, open(sys.argv[1], "w"), ensure_ascii=False, indent=2)
json.dump(succ, open(sys.argv[1].replace("hunters.json", "successors.json"), "w"), ensure_ascii=False, indent=2)
print(len(hun), "chasseurs,", len(succ), "successeurs ;", sum(1 for h in hun if not h["advancement"]), "sans avancement ;", sum(1 for h in hun if not h["skills"]), "sans compétences")
print("role:", {r: sum(1 for h in hun if h["role"] == r) for r in (None, "stacker", "supporter", "buster")})
print("sans rareté:", [h["id"] for h in hun if not h["rarity"]], "| sans élément:", [h["id"] for h in hun if not h["element"]])
