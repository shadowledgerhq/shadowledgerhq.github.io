"""Lit les modèles Fandom des sets d'artefacts (JSON de l'API MediaWiki) et écrit data/db/artifact_sets.json.
Usage : python3 -I tools/parse_fandom_artifacts.py <dossier contenant t_Complete.json t_Armor.json t_Jewelry.json> <sortie.json>"""
import json, re, sys, os

SRC = "https://solo-leveling-arise.fandom.com/wiki/Artifacts"

def clean(s):
    s = re.sub(r"\{\{(?:Text Color|Color)\|[^|}]*\|([^{}]*)\}\}", r"\1", s)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"<br\s*/?>", " ", s)
    s = re.sub(r"'''", "", s)
    return re.sub(r"\s+", " ", s).strip()

def slug(n):
    return re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "")).strip("-")

def parse(kind, path):
    d = json.load(open(path))
    page = list(d["query"]["pages"].values())[0]["revisions"][0]
    text, ts = page["slots"]["main"]["*"], page["timestamp"]
    out = []
    for blk in re.split(r"\n\|-\s*<!--[^>]*-->", text)[1:]:
        m = re.search(r"link=\]\]\s*<br>\s*(.+?)\n", blk) or re.search(r"<br>\s*([^\n]+?)\n", blk)
        name = clean(m.group(1)) if m else None
        files = re.findall(r"\[\[File:([^|\]]+)", blk)
        bonuses = {}
        for n, t in re.findall(r"'''(\d) Set Effect'''<br>(.*?)(?=\n\|-|\n\|'''|\Z)", blk, re.S):
            bonuses[n] = clean(t)
        pm = re.match(r"(.*?)\s*\((.+)\)\s*$", name or "")
        nick = None
        if pm: name, nick = pm.group(1).strip(), pm.group(2).strip()
        out.append({"id": slug(name), "name": {"fr": "", "en": name, "ko": ""}, "kind": kind,
                    "rarity": None, "nickname_en": nick,
                    "pieces": [{"slot": None, "name": {"fr": "", "en": f.rsplit('.',1)[0]}, "icon": None} for f in files],
                    "bonuses": {k: {"en": v, "fr": ""} for k, v in bonuses.items()},
                    "main_stat_options": None, "icon": None,
                    "source": SRC + " (modèle Template:Artifact_%s_Sets)" % kind.capitalize(),
                    "wiki_revision": ts, "verified_at": "2026-11-13", "game_version": None,
                    "notes": "Texte EN du wiki Fandom (CC BY-SA), non vérifié en jeu ; FR à traduire depuis le jeu."})
    return out

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    res = []
    for k, f in (("complete", "t_Complete.json"), ("armor", "t_Armor.json"), ("jewelry", "t_Jewelry.json")):
        res += parse(k, os.path.join(src, f))
    json.dump(res, open(dst, "w"), ensure_ascii=False, indent=2)
    for r in res: print(r["kind"], r["id"], list(r["bonuses"]), len(r["pieces"]))
