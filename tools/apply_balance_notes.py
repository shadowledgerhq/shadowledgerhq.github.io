"""Dépouille les notices d'équilibrage Netmarble (data/db/netmarble_notes.json) :
- ajoute `balance_history[]` (texte brut EN de chaque changement) aux entrées hunters / weapons / blessings /
  sjw_skills / artifact_sets / shadows rapprochées par le nom EN ;
- crée une entrée `data/db/patches.json` « équilibrage » par notice ;
- bénédictions : applique les nouvelles valeurs (Rare/Héroïque/Légendaire/Transcendante) seulement si les anciennes
  valeurs de la notice égalent celles de la base (sinon : signalé, rien modifié).
Usage : python3 tools/apply_balance_notes.py [--ecrire] [--depuis AAAA-MM-JJ]   (sans --ecrire : simulation + rapport ;
--depuis : ne traite que les notices de cette date ou après, pour ne pas écraser les vérifications manuelles des anciennes)"""
import json, re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent / "data" / "db"
ECRIRE = "--ecrire" in sys.argv
L = lambda f: json.loads((R / f"{f}.json").read_text(encoding="utf-8"))
notes = [e for e in L("netmarble_notes") if re.search(r"Balance Adjust", e["name"]["en"], re.I)]
if "--depuis" in sys.argv:
    _d = sys.argv[sys.argv.index("--depuis") + 1]; notes = [e for e in notes if e["date"] >= _d]
notes.sort(key=lambda e: (e["date"], e["id"]))
norm = lambda s: re.sub(r"[^a-z0-9]", "", re.sub(r"^(ssr|sr|r)\s+", "", s.strip().lower()).replace("’", "").replace("'", ""))
CAT = [("hunter", "hunters"), ("blessing", "blessings"), ("rune", "sjw_skills"), ("weapon", "weapons"),
       ("artifact", "artifact_sets"), ("shadow", "shadows")]
db = {c: L(c) for _, c in CAT}
idx = {c: {} for c in db}
for c, items in db.items():
    for e in items:
        if e.get("kind") == "rules": continue
        for n in {e["name"].get("en", ""), e["name"].get("fr", "")}:
            if n: idx[c].setdefault(norm(n), e)
ALIAS = {"artifact_sets": {"kamishsobsession": "set-of-kamishs-obession"}, "weapons": {"vulkansrage": "vulcans-rage", "somaasura": "soma-and-asura"},
         "sjw_skills": {"phantomstrike": "phantom-strike", "daggerrush": "dagger-rush"}}
for c, m in ALIAS.items():
    par_id = {e["id"]: e for e in db[c]}
    for k, i in m.items():
        if i in par_id: idx[c][k] = par_id[i]
def cat_de(titre):
    t = titre.lower()
    for k, c in CAT:
        if k in t: return c
    return None
def sections(texte):
    """[(catégorie, entité, texte brut)]"""
    out, cat, bloc_cat = [], None, ""
    texte = re.sub(r"\n{3,}", "\n\n", re.sub(r"[ \t\u00a0]+\n", "\n", texte))
    parts = re.split(r"\n(?=\s*📌)", texte)
    for p in parts:
        m = re.match(r"\s*📌\s*(.*)", p)
        if not m: continue
        titre = m.group(1).split("\n")[0]
        if titre.strip().startswith("Notes"): continue
        c = cat_de(titre); corps = p[p.index("\n"):] if "\n" in p else ""
        ent = re.split(r"\n\s*▶", corps)
        if len(ent) > 1 and c != "blessings":
            for e in ent[1:]:
                nom, _, rest = e.partition("\n"); out.append((c, nom.strip(), rest.strip(), titre))
        else:  # tableau « Nom / (description) / texte » : noms connus de la catégorie seulement
            lignes = corps.split("\n"); debuts = []
            for i, l in enumerate(lignes):
                if c and l.strip() and norm(l) in idx[c] and i + 2 < len(lignes) and not lignes[i + 1].strip() and lignes[i + 2].strip().startswith("("):
                    debuts.append(i)
            for k, i in enumerate(debuts):
                fin = debuts[k + 1] if k + 1 < len(debuts) else len(lignes)
                out.append((c, lignes[i].strip(), "\n".join(lignes[i + 1:fin]).strip(), titre))
            if not debuts:
                out.append((c, "", corps.strip(), titre))
    return out
def nombres(s):
    return [float(x.replace(",", ".")) for x in re.findall(r"(\d+(?:[.,]\d+)?)", s)]
def appliquer_pierre(e, texte, rapport, n):
    """Cherche des lignes « a b / c / d e / f » (4 groupes, chaque groupe = 1 valeur ou ancienne+nouvelle)."""
    vec = (e.get("values_by_level") or {}).get("values_by_rarity_rare_heroic_legendary_transcendent")
    if not vec: return False
    modif = False
    for lg in texte.split("\n"):
        for m in re.finditer(r"((?:\d+(?:\.\d+)?%?(?: \d+(?:\.\d+)?%?)?)(?: / (?:\d+(?:\.\d+)?%?(?: \d+(?:\.\d+)?%?)?)){3})", lg):
            groupes = [g.strip() for g in m.group(1).split(" / ")]
            anc, nouv = [], []
            for g in groupes:
                v = nombres(g)
                if len(v) == 2: anc.append(v[0]); nouv.append(v[1])
                elif len(v) == 1: anc.append(v[0]); nouv.append(v[0])
                else: break
            if len(anc) != 4 or anc == nouv: continue
            for k, ligne in enumerate(vec):
                if [float(x) for x in ligne] == anc:
                    vec[k] = [int(x) if x == int(x) else x for x in nouv]; modif = True
                    e.setdefault("values_balance_applied", []).append({"date": n["date"], "url": n["source"], "line": k, "from": anc, "to": nouv})
                    rapport.append(f"  appliqué {e['id']} ligne {k}: {anc} → {nouv}"); break
            else: rapport.append(f"  NON appliqué {e['id']} : anciennes valeurs {anc} ≠ base {vec}")
    return modif
STOP = {"increases", "damage", "duration", "second", "user", "attack", "when", "with", "every", "that", "this", "effect", "stacking", "times", "after", "target", "their", "from"}
PAIR = re.compile(r"(?<![\d.\-])(\d+(?:\.\d+)?)(%?)\s+(\d+(?:\.\d+)?)(%| second\(s\)| seconds?| times?)?(?![\d.\-])")
def paires(txt):
    out = []; prec = []
    for lg in txt.split("\n"):
        if not lg.strip(): continue
        ctx = " ".join(prec[-2:]) + " " + lg; prec.append(lg)
        if lg.strip().startswith(("Tier", "(", "Lv", "Category")) or "/" in lg: continue
        for m in PAIR.finditer(lg):
            a, ua, b, ub = m.group(1), m.group(2), m.group(3), (m.group(4) or "")
            if a == b: continue
            u = ub if ub else ua
            if ua and not ub: u = ua
            out.append({"line": " ".join(lg.split())[:140], "old": a, "new": b, "unit": u.strip(),
                        "ctx": {w.lower() for w in re.findall(r"[A-Za-z]{4,}", ctx)} - STOP})
    return out
def motif(v, u):
    u = (" " + u) if u not in ("", "%") else u
    return re.compile(r"(?<![\d.\-])" + re.escape(v) + re.escape(u) + r"(?![\d.\-])")
def appliquer_nombres(e, h, rapport):
    ch = []
    for pr in paires(h["text_en"]):
        blob = json.dumps({k: v for k, v in e.items() if k not in ("balance_history", "values_balance_applied", "balance_changes", "notes")}, ensure_ascii=False)
        mo, mn = motif(pr["old"], pr["unit"]), motif(pr["new"], pr["unit"])
        co, cn = len(mo.findall(blob)), len(mn.findall(blob))
        pr = dict(pr, date=h["date"], url=h["url"]); ctx = pr["ctx"]
        if co == 0 and cn >= 1: pr["status"] = "deja_applique"
        elif co == 1 and cn == 0 and sum(1 for w in ctx if w in blob[max(0, mo.search(blob).start() - 200):mo.search(blob).end() + 200].lower()) >= 2:
            def rem(o):
                if isinstance(o, str):
                    return mo.sub(pr["new"] + ((" " + pr["unit"]) if pr["unit"] not in ("", "%") else pr["unit"]), o, count=1)
                if isinstance(o, list): return [rem(x) for x in o]
                if isinstance(o, dict): return {k: (v if k in ("balance_history", "values_balance_applied", "balance_changes", "notes") else rem(v)) for k, v in o.items()}
                return o
            for k in list(e):
                if k not in ("balance_history", "values_balance_applied", "balance_changes", "notes"): e[k] = rem(e[k])
            pr["status"] = "applique"; rapport.append(f"  texte {e['id']}: {pr['old']}→{pr['new']}{pr['unit']} ({h['date']})")
        else: pr["status"] = "a_verifier"
        pr.pop("ctx", None); ch.append(pr)
    return ch
rap, non_trouves, patches = [], [], []
for n in notes:
    ch = []
    for c, nom, txt, titre in sections(n["text_en"]):
        cible = idx[c].get(norm(nom)) if c and nom else None
        if cible is None and c and nom and len(norm(nom)) > 6:
            ks = [k for k in idx[c] if norm(nom) in k or k in norm(nom)]
            ids = {idx[c][k]["id"] for k in ks}
            if len(ids) == 1: cible = idx[c][ks[0]]
        entry = {"date": n["date"], "url": n["source"], "section": titre.strip(), "text_en": txt}
        if cible is not None:
            if not any(h["url"] == entry["url"] and h["text_en"] == txt for h in cible.setdefault("balance_history", [])):
                cible["balance_history"].append(entry)
            if c == "blessings": appliquer_pierre(cible, txt, rap, n)
            elif c in ("hunters", "weapons", "sjw_skills", "shadows", "artifact_sets"):
                pc = appliquer_nombres(cible, entry, rap)
                cible["balance_changes"] = [x for x in cible.get("balance_changes", []) if x["url"] != entry["url"] or x["line"] not in {y["line"] for y in pc}] + pc
            ch.append({"category": c, "id": cible["id"], "change": " ".join(txt.split())[:160]})
        else:
            if c and nom: non_trouves.append(f"{n['date']} {c} {nom}")
            ch.append({"category": c or "general", "id": re.sub(r"[^a-z0-9]+", "-", (nom or titre).lower()).strip("-")[:40] or "x",
                       "change": " ".join(txt.split())[:160]})
    patches.append({"id": f"equilibrage-{n['date']}-{n['id'].split('-')[1]}", "kind": "balance", "version": None, "date": n["date"],
        "name": {"fr": f"Notice d'équilibrage du {n['date']}", "en": n["name"]["en"]}, "url": n["source"], "source": n["source"],
        "verified_at": "2026-11-16", "game_version": None,
        "notes": "Résumé automatique (début du texte de chaque changement) ; texte intégral dans netmarble_notes.json et `balance_history` des entrées concernées.",
        "changes": ch})
print(len(notes), "notices ;", sum(len(p["changes"]) for p in patches), "changements ;", len(non_trouves), "entités non rapprochées")
print("\n".join(rap)); print("NON RAPPROCHÉS (extrait) :", non_trouves[:40])
if ECRIRE:
    for c, items in db.items():
        (R / f"{c}.json").write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    p = L("patches"); p = [x for x in p if x.get("kind") != "balance"] + patches
    (R / "patches.json").write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("écrit.")
