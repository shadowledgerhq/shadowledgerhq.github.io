"""Complète blessings.json et sjw_skills.json depuis GET https://api.slagate.com/api/references (route publique, accord d'Alexis 13/11/2026).
Usage : python3 -I tools/apply_fr_names2.py <references.json>"""
import json, re, sys
d = json.load(open(sys.argv[1]))["data"]
SRC = "https://api.slagate.com/api/references (route GET publique ; accord d'Alexis 13/11/2026)"
slug = lambda n: re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "").replace("’", "")).strip("-")
EL = {"Feu": "fire", "Eau": "water", "Vent": "wind", "Lumière": "light", "Ténèbres": "dark"}
def load(f): return json.load(open(f"data/db/{f}.json"))
def save(f, x): json.dump(x, open(f"data/db/{f}.json", "w"), ensure_ascii=False, indent=2)
clean = lambda s: re.sub(r"\s+", " ", s or "").strip()

# --- pierres
EXTRA = {"Crushing Attack": "Attaque dévastatrice", "Sandbag": "Économie des forces", "Title: Conqueror of Adversity": "Titre : Vaillant dans l'adversité",
         "Title: Wolf Assassin": "Titre : Massacreur de lycans", "Bloodlust": "Hostilité", "Irreversible Road": "Sans retour", "Ravenous Instinct": "Instinct primaire"}
api = {p["nom"]: p for p in d["pierresBenediction"]}
B = load("blessings"); used = set(); mism = []
for b in B:
    if not b["name"]["fr"] and b["name"]["en"] in EXTRA: b["name"]["fr"] = EXTRA[b["name"]["en"]]; b["notes"] += " Nom FR rapproché par la phrase d'ambiance et la mécanique (concordantes)."
    p = api.get(b["name"]["fr"])
    if not p: continue
    used.add(p["nom"]); b["name_fr_source"] = SRC
    b["text"]["fr"] = clean(p["description"]); b["api_type"] = p["type"]
    cat = {"booster": "empowerment", "survie": "survival"}.get(p["type"])
    if cat != b["category"]: mism.append(b["id"])
    b["notes"] += " Texte FR (API slagate) : la valeur affichée est celle de la rareté max ; l'API peut être plus récente que le wiki (ex. Irreversible Road : 36 % FR contre 24 % wiki)."
NEWEN = {"Acrobate": "Acrobat", "Ricochet": "Ricochet", "Toucher de l'Exécuteur": "Finisher Touch"}  # noms EN cités dans la note des développeurs du 11/06/2026
n_new = 0
for nom, p in api.items():
    if nom in used: continue
    en = NEWEN.get(nom, "")
    B.append({"id": slug(en or nom), "name": {"fr": nom, "en": en, "ko": ""}, "category": {"booster": "empowerment", "survie": "survival"}.get(p["type"]), "api_type": p["type"], "rarity": None,
              "text": {"fr": clean(p["description"]), "en": ""}, "flavor_en": "", "effects": [], "conditions": [], "values_by_level": {}, "icon": None,
              "source": SRC, "name_fr_source": SRC, "verified_at": "2026-11-13", "game_version": None,
              "notes": "Absente du wiki Fandom. Nom FR et texte FR de l'API slagate ; texte FR = valeur de la rareté max." + (" Nom EN : note Netmarble du 11/06/2026 (Developer Notes)." if en else " Nom EN officiel à confirmer.")})
    n_new += 1
save("blessings", B)

# --- runes / compétences
comp = {slug(c["i18n"]["en"]["nom"]): c for c in d["competences"] if c.get("i18n", {}).get("en")}
R = load("sjw_skills"); have = set(); k = 0
for r in R:
    if r["kind"] != "rune": continue
    c = comp.get(slug(r["name"]["en"]))
    if c:
        have.add(slug(r["name"]["en"])); r["name"]["ko"] = c["i18n"].get("ko", {}).get("nom", ""); r["name"]["ja"] = c["i18n"].get("ja", {}).get("nom", "")
        if not r["element"] and EL.get(c.get("element")): r["element"] = EL[c["element"]]
        k += 1
new = 0
for sl, c in comp.items():
    if sl in have: continue
    R.append({"id": "rune--" + sl, "kind": "rune", "parent_skill": None, "name": {"fr": c["nom"], "en": c["i18n"]["en"]["nom"], "ko": c["i18n"].get("ko", {}).get("nom", ""), "ja": c["i18n"].get("ja", {}).get("nom", "")},
              "rarity": ["rare", "heroic", "legendary", "transcendent"], "type": None, "element": EL.get(c.get("element")), "cooldown": None, "mp_cost": None,
              "text": {"fr": "", "en": ""}, "effects": [], "effects_text_en": "", "values_by_level": {}, "icon": None, "source": SRC, "name_fr_source": SRC,
              "verified_at": "2026-11-13", "game_version": None, "notes": "Absente du wiki Fandom (page de juin). Noms FR/EN/KO/JA de l'API slagate ; compétence parente, effets et valeurs : à saisir (notes Netmarble ou jeu)."})
    new += 1
save("sjw_skills", R)
print("pierres : nouvelles", n_new, "| catégories incohérentes:", mism, "| total", len(B))
print("runes : KO/JA ajoutés", k, "| nouvelles entrées", new, "| total", len(R))
