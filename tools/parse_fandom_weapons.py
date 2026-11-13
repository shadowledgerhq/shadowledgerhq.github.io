"""Lit les pages d'armes du wiki Fandom (Category:Weapons) et écrit data/db/weapons.json.
Usage : python3 -I tools/parse_fandom_weapons.py <hunters.json> <sortie.json>"""
import json, re, sys, urllib.parse, urllib.request
API = "https://solo-leveling-arise.fandom.com/api.php"
WIKI = "https://solo-leveling-arise.fandom.com/wiki/"

def get(params):
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json"})
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "curl/8"})))

def clean(s):
    s = re.sub(r"\{\{Res\|[^{}]*\}\}", "", s or "")
    s = re.sub(r"\{\{(?:Text[_ ]Color|Color)\|[^|}]*\|([^{}]*)\}\}", r"\1", s)
    s = re.sub(r"\[\[File:[^\]]*\]\]", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<div[^>]*>|</div>", " ", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def slug(n): return re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "")).strip("-")

def params(text):
    d = {}
    for m in re.finditer(r"^\|\s*([A-Za-z0-9_]+)\s*=(.*?)(?=^\|\s*[A-Za-z0-9_]+\s*=|^\}\}|\Z)", text, re.S | re.M):
        d.setdefault(m.group(1).lower(), m.group(2).strip())
    return d

def tmpl(txt, name):
    m = re.search(r"\{\{\s*" + name + r"[^|{}]*\n(.*?)^\}\}", txt, re.S | re.M)
    return params(m.group(1)) if m else {}

def tag(v):  # {{Fire}} / {{SSR}} / {{Player}}
    m = re.search(r"\{\{\s*([A-Za-z ]+?)\s*(?:\||\}\})", v or "")
    return m.group(1).strip().lower() if m else (clean(v).lower() or None)

hunters = {h["id"]: h for h in json.load(open(sys.argv[1]))}
titles = [m["title"] for m in get({"action": "query", "list": "categorymembers", "cmtitle": "Category:Weapons", "cmlimit": 500})["query"]["categorymembers"]]
out = []
for i in range(0, len(titles), 20):
    q = get({"action": "query", "prop": "revisions", "rvprop": "content|timestamp|ids", "rvslots": "main", "titles": "|".join(titles[i:i+20])})
    for pg in q["query"]["pages"].values():
        r = pg.get("revisions", [{}])[0]
        txt = r.get("slots", {}).get("main", {}).get("*", "")
        if not re.search(r"\{\{\s*Weapon\b", txt): continue
        info = tmpl(txt, "Weapon")
        name = clean(info.get("title1", pg["title"]))
        kind = tag(info.get("type")) or ""
        _m = re.search(r"\[\[([^\]|]+)", info.get("exclusive_hunter", ""))
        eh = (_m.group(1).strip() if _m else clean(info.get("exclusive_hunter", "").split("}}")[0])) or None
        w = {"id": slug(name), "name": {"fr": "", "en": name, "ko": ""}, "rarity": (re.search(r"\b(SSR|SR|R)\b", info.get("rarity", "")) or re.search(r"Category:(SSR|SR|R) Weapons", txt) or [None, None])[1].lower() if (re.search(r"\b(SSR|SR|R)\b", info.get("rarity", "")) or re.search(r"Category:(SSR|SR|R) Weapons", txt)) else None,
             "kind": "sung_jinwoo" if (kind == "player" or "Category:Sung Jinwoo Weapons" in txt) else ("hunter" if (kind.startswith("hunter") or "Category:Hunter Weapons" in txt) else None),
             "hunter_id": None, "exclusive_hunter_en": eh, "element": ((re.search(r"\b(Fire|Water|Wind|Light|Dark)\b", info.get("element", "")) or [None, None])[1] or "").lower() or None,
             "weapon_type": None, "base_stats": {}, "passive": [], "skills": [], "effects": [],
             "icon": None, "source": WIKI + urllib.parse.quote(pg["title"].replace(" ", "_")), "wiki_revid": r.get("revid"),
             "wiki_timestamp": r.get("timestamp"), "verified_at": "2026-11-13", "game_version": None,
             "notes": "Texte EN du wiki Fandom (CC BY-SA), non vérifié en jeu ; possiblement antérieur aux rééquilibrages récents. Nom FR et icône à compléter."}
        if eh:
            w["hunter_id"] = next((hid for hid, h in hunters.items() if h["name"]["en"].lower() == eh.lower()), None)
        sk = tmpl(txt, "Sung Jinwoo Weapon Skills")
        if sk:
            w["weapon_type"] = clean(sk.get("type", "")) or None
            for k, label in (("basic", "basic_attack"), ("core", "core_attack"), ("skill", "skill")):
                if sk.get(k):
                    w["skills"].append({"type": label, "name": {"fr": "", "en": clean(sk.get("skill_name", "")) if k == "skill" else "", "ko": ""},
                                        "text": {"fr": "", "en": clean(sk.get(k + "_des", sk.get("skill_des", "") if k == "skill" else ""))},
                                        "effects_text_en": clean(sk[k]), "effects": [], "values_by_level": {}})
        pa = tmpl(txt, "Sung Jinwoo Weapon Passive")
        for n in range(0, 6):
            if pa.get(f"a{n}"): w["passive"].append({"tier": n, "text": {"fr": "", "en": clean(pa[f"a{n}"])}})
        hs = tmpl(txt, "Hunter Weapon Stats")
        if hs:
            w["base_stats"] = {"stat_type": clean(hs.get("stat_type", "")) or None}
            for n in (1, 2):
                if hs.get(f"passive{n}"): w["passive"].append({"tier": n, "text": {"fr": "", "en": clean(hs[f"passive{n}"])}})
        out.append(w)
out.sort(key=lambda w: (w["kind"] or "", w["id"]))
json.dump(out, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
import collections
print(len(out), collections.Counter(w["kind"] for w in out), collections.Counter(w["rarity"] for w in out))
print("hunter sans id:", [(w["id"], (w["exclusive_hunter_en"] or "")[:30]) for w in out if w["kind"] == "hunter" and w["exclusive_hunter_en"] and not w["hunter_id"]])
print("sans kind:", [w["id"] for w in out if not w["kind"]])
print("sans passif:", [w["id"] for w in out if not w["passive"]])
