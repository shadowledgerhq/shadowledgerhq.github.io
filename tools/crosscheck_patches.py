"""Recoupe la base (wiki, antérieur) avec le patch du 22/10/2026 (notes Netmarble) et les plafonds de niveau.
Ajoute `patch_adjustments` aux fiches concernées ; met à jour les valeurs de chef d'ombre au rang General (valeurs annoncées par Netmarble).
Usage : python3 -I tools/crosscheck_patches.py"""
import json, re
N = "https://forum.netmarble.com/slv_en/view/32/109983"
P = "2026-10-22"
def load(f): return json.load(open(f"data/db/{f}.json"))
def save(f, x): json.dump(x, open(f"data/db/{f}.json", "w"), ensure_ascii=False, indent=2)
rep = []

# --- chasseurs et armes : (id, résumé, jetons à retrouver dans la fiche si le wiki est déjà à jour)
H = [("elena-renault", "T5 : nouvel effet Insatiable Hunger (Burst +40 %, équipe Water Buster)", ["Insatiable Hunger"]),
 ("yoo-soohyun", "T1 : Core Attack +200 % pendant 12 s (avant 6 s), Madness cooldown 6 s (avant 12 s) ; T2 : +12 % Fire par allié Fire ; T3 : Superstar (ATQ +60 %, crit +30 %, 16 s) ; T4 : ATQ +10 % par allié Fire", ["Superstar"]),
 ("cha-hae-in-the-pure-sword-princess", "Base 175→220 % ; T3 15→60 % et 170→200 % ; T4 7→8 % (GB : par allié, sans limite) ; T5 : Will of the Sword (nouveau), 60→100 %", ["220%", "Will of the Sword"]),
 ("seorin", "Frozen Drift : Overdrive 20→60 s ; T3 : Black Tea? (nouveau) ; T5 : Subzero cumul 10→20", ["Black Tea"]),
 ("meilin-fisher", "Help! Berry! : nouvel effet SJW +16 % ; durées 30→32 s ; Basic 16→32 s ; T3 cumul 50→64 ; T4 PV 8→32 % ; T5 24→64 s", ["64 second"]),
 ("choi-jong-in", "Fire Barrage : baisse de DEF 15→70 %, 15→25 s", [r"Decreases? (?:the target's )?Defense by 70%"]),
 ("baek-yoonho", "White Flame Storm Kick : baisse de DEF 20→70 %, 12→25 s", [r"Decreases? (?:the target's )?Defense by 70%"]),
 ("emma-laurent", "Roaring Flames : Fire 15→20 % ; +30 % de dégâts sur cible [Break]", [r"Flame.s Wrath\].{0,300}30%"]),
 ("liu-zhigang", "Veiled Intent : portée fortement augmentée", None), ("agnes-rivera", "Il Bacio della Morte : portée fortement augmentée", None),
 ("lee-joohee-pilgrim-of-the-labyrinth", "Radiant Burst : portée fortement augmentée", None), ("diana-lopez", "Chicxulub : portée fortement augmentée", None)]
Hs = load("hunters"); byid = {h["id"]: h for h in Hs}
for hid, txt, tok in H:
    h = byid.get(hid)
    if not h: rep.append(f"chasseur introuvable : {hid}"); continue
    blob = json.dumps({k: h[k] for k in ("skills", "passives", "advancement")}, ensure_ascii=False)
    refl = None if tok is None else all(re.search(t, blob) for t in tok)
    h.setdefault("patch_adjustments", []).append({"patch": P, "source": N, "summary": txt, "wiki_reflects_patch": refl,
        "note": "Valeurs après patch = celles de l'avis Netmarble ; si wiki_reflects_patch est false/null, le texte de la fiche peut être antérieur au patch."})
    rep.append(f"{hid}: wiki à jour={refl} (page du {h['wiki_timestamp'][:10]})")
save("hunters", Hs)
W = load("weapons"); wid = {w["id"]: w for w in W}
for wid_, txt, tok in [("melody-of-iron-and-blood", "Seorin (arme exclusive, base T5) : PV de l'utilisateur 12→30 %", ["30%"]),
                       ("hook-line-and-sinker", "Meilin Fisher (arme exclusive, base T5) : nouvel effet [Up!] ; durée Side Whip 12→32 s ; bonus max 16 %", ["32 second"])]:
    w = wid.get(wid_)
    if not w: rep.append(f"arme introuvable : {wid_}"); continue
    blob = json.dumps(w["passive"], ensure_ascii=False)
    refl = all(re.search(t, blob) for t in tok)
    w.setdefault("patch_adjustments", []).append({"patch": P, "source": N, "summary": txt, "wiki_reflects_patch": refl})
    rep.append(f"{wid_}: wiki à jour={refl}")
# plafonds de niveau (notes Netmarble)
for w in W: w["max_level"] = {"value": 130, "source": "https://forum.netmarble.com/slv_en/view/14/107225", "patch": "2026-07-02"}
save("weapons", W)

# --- chefs d'ombre : valeurs au rang General annoncées par le patch
SH = {"iron": ("Defense", None, 18, "effet supplémentaire (rang General) : DEF de toute l'équipe +18 % ; l'effet PV max +12 % du wiki est conservé"), "tank": ("Max HP", None, 18, "effet supplémentaire (rang General) : PV max de toute l'équipe +18 % ; l'effet DEF +12 % du wiki est conservé"),
      "blades": ("Attack", 7, 18, None), "bigrock": ("Basic Skill damage", 12, 24, None), "skull": ("Mana Power", 12, 24, None),
      "tusk": ("Core Attack skill damage", 40, 60, None), "kaisel": ("Ultimate Skill damage", 9, 24, None), "jima": ("Attack", 5, 13, None), "beru": ("Attack and Critical Hit damage", 5, 10, None)}
S = load("shadows"); sid = {s["id"]: s for s in S}
for k, (stat, before, after, extra) in SH.items():
    s = sid[k]; g = s["leader_skill_by_rank"].get("general")
    m = re.search(r"by ([\d.]+)%", g["text"]) if g else None
    wiki_val = float(m.group(1)) if m else None
    s.setdefault("patch_adjustments", []).append({"patch": P, "source": N, "rank": "general", "stat": stat, "before_netmarble": before, "after": after,
        "wiki_general_value": wiki_val, "wiki_matches_before": (wiki_val == before) if before is not None else None, "additional_effect": before is None,
        "summary": extra or f"{stat} de l'équipe {before}→{after} % (rang General)"})
    if g and before is not None: g["value_after_patch_22_10"] = after
    rep.append(f"ombre {k}: wiki general={wiki_val} annoncé avant={before} après={after}")
    s["max_level"] = {"value": 195, "source": "https://forum.netmarble.com/slv_en/view/14/107225", "patch": "2026-07-02", "note": "niveau max de l'armée d'ombres (Netmarble)"}
for s in S:
    s["max_level"] = {"value": 195, "source": "https://forum.netmarble.com/slv_en/view/14/107225", "patch": "2026-07-02"}
save("shadows", S)
# --- noyaux : plafond 25 (17/09)
C = load("cores")
for c in C: c["max_level"] = {"value": 25, "source": "https://forum.netmarble.com/slv_en/view/14/109279", "patch": "2026-09-17", "note": "20 selon le wiki, avant le patch"}
save("cores", C)
# --- pierres : écart entre valeurs du wiki (rareté max) et texte FR de l'API
B = load("blessings"); diff = []
for b in B:
    vals = b["values_by_level"].get("values_by_rarity_rare_heroic_legendary_transcendent")
    fr = b["text"]["fr"]
    if not vals or not fr: continue
    nums = {float(x.replace(",", ".")) for x in re.findall(r"(\d+(?:[.,]\d+)?)", fr)}
    maxv = [v[-1] for v in vals]
    ok = all(m in nums for m in maxv)
    b["value_check"] = {"wiki_max_values": maxv, "all_found_in_api_text": ok, "note": "comparaison automatique wiki (Transcendent) ↔ texte FR de l'API ; false = valeur du wiki possiblement périmée ou texte reformulé"}
    if not ok: diff.append(b["id"])
save("blessings", B)
# --- sets : aucune valeur détaillée dans les patchs
A = load("artifact_sets")
for s in A:
    s["patch_adjustments_unknown"] = {"patches": ["2026-06-11?", "2026-07-02", "2026-07-30", "2026-09-17", "2026-10-22"],
        "note": "Netmarble annonce des rééquilibrages de sets (6/4, 7/2, 7/30, 9/17, 10/22) sans donner les valeurs : texte du wiki (mai 2026) possiblement périmé."}
save("artifact_sets", A)
print("\n".join(rep)); print("pierres dont une valeur wiki est absente du texte API :", len(diff), diff)
