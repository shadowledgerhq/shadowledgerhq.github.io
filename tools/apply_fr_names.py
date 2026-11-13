"""Ajoute les noms FR depuis GET https://api.slagate.com/api/references (route publique, autorisée par Alexis le 13/11/2026).
Associations EN->FR : tables ci-dessous (traductions littérales) ; le reste reste vide.
Usage : python3 -I tools/apply_fr_names.py <references.json>"""
import json, re, sys
d = json.load(open(sys.argv[1]))["data"]
SRC = "https://api.slagate.com/api/references (route GET publique ; accord d'Alexis 13/11/2026 : routes GET publiques seulement)"
slug = lambda n: re.sub(r"[^a-z0-9]+", "-", n.lower().replace("'", "").replace("’", "")).strip("-")
def load(f): return json.load(open(f"data/db/{f}.json"))
def save(f, x): json.dump(x, open(f"data/db/{f}.json", "w"), ensure_ascii=False, indent=2)
def setfr(o, fr, note=None):
    o["name"]["fr"] = fr; o["name_fr_source"] = SRC
    if note: o["notes"] += " " + note
rep = {}

# noyaux : 18/18
CORES = {"ferocious-protectors-desire":"Désir du Protecteur féroce","ferocious-protectors-armor":"Armure du Protecteur féroce","ferocious-protectors-claw":"Griffe du Protecteur Féroce",
 "arrogant-rulers-reflection":"Réfléxion du Dominateur arrogant","arrogant-rulers-will":"Volonté du Dominateur arrogant","arrogant-rulers-gaze":"Regard du Dominateur arrogant",
 "hunger-of-the-crimson-apex":"Appétit du Prédateur écarlate","desires-of-the-crimson-apex":"Désirs du Prédateur écarlate","punishment-of-the-crimson-apex":"Châtiment du Prédateur écarlate",
 "eyes-of-the-watcher":"Yeux du Veilleur","limbs-of-the-watcher":"Membres du Veilleur","teeth-of-the-watcher":"Dents du Veilleur",
 "nameless-demons-deception":"Tromperie du Démon Anonyme","nameless-demons-horn":"Corne du Démon Anonyme","nameless-demons-magisphere":"Magisphère du Démon Anonyme",
 "ancient-wraiths-obession":"Obsession du Spectre Antique","ancient-wraiths-right-hand":"Main droite du Spectre Antique","ancient-wraiths-mana-power":"Énergie de Mana du Spectre Antique"}
api = {c["nom"] for c in d["noyaux"]}
C = load("cores"); n = 0
for c in C:
    fr = CORES.get(c["id"])
    if fr and fr in api: setfr(c, fr); n += 1
save("cores", C); rep["noyaux"] = f"{n}/{len(C)}"

# sets d'artefacts
SETS = {"the-architects-blue-poison":"Poison bleu du Concepteur","surturs-flame":"Flammes de Surtur","glorious-arrogance":"Arrogance glorieuse","noble-flesh":"Chair noble","kamishs-obession":"Obsession de Kamish",
 "chaotic-infamy":"Infamie chaotique","chaotic-desire":"Désir chaotique","chaotic-wish":"Vœu chaotique","burning-curse":"Malédiction ardente","burning-blessing":"Bénédiction ardente","burning-greed":"Avarice ardente",
 "iron-will":"Volonté de fer","crimson-knights-set":"Belliciste","high-ranking-demons-set":"Destructeur","dragon-knights-set":"Fondation solide","black-lions-set":"Armé","almighty-kargalgans-set":"Mort en un coup",
 "holy-set":"Noble sacrifice","clerics-set":"Ange en blanc","palace-guards-set":"Gardien","new-hunters-set":"Analyse imparable","hard-leather-set":"Ténacité",
 "destructive-instinct":"Instinct destructeur","shining-star":"Etoile étincelante","viridescent-set":"Concentration de puissance de feu","aquamarine-set":"Connexion exceptionnelle","peridot-set":"Bénédiction de sylphe",
 "beast-set":"Expert","obsidian-set":"Capacité exceptionnelle","skeleton-set":"Berserker","behemoth-set":"Exécuteur","red-eyed-set":"Champion de la bataille"}
SL = ["helmet","chestplate","gloves","boots","necklace","bracelet","ring","earrings"]
CAT = {"Casque":"helmet","Armure":"chestplate","Gants":"gloves","Bottes":"boots","Collier":"necklace","Bracelet":"bracelet","Bague":"ring","Boucles":"earrings"}
pieces = {}
for a in d["artefacts"]: pieces.setdefault(a["set_name"], {})[CAT[a["categorie"]]] = a["nom"]
A = load("artifact_sets"); n = 0; np_ = 0
for s in A:
    key = s["id"].replace("set-of-", "")
    fr = SETS.get(key)
    if not fr or fr not in pieces: continue
    setfr(s, fr, "Nom FR : association par traduction littérale du nom/surnom du wiki, à confirmer." if s["kind"] != "complete" else None); n += 1
    slots = SL if s["kind"] == "complete" else (SL[:4] if s["kind"] == "armor" else SL[4:])
    if len(s["pieces"]) == len(slots):
        for p, sl in zip(s["pieces"], slots):
            p["slot"] = sl
            if sl in pieces[fr]: p["name"]["fr"] = pieces[fr][sl]; np_ += 1
save("artifact_sets", A); rep["sets"] = f"{n}/{len(A)} (pièces FR : {np_})"

# runes de SJW (nom EN exact dans i18n)
en2fr = {slug(c["i18n"]["en"]["nom"]): c["nom"] for c in d["competences"] if c.get("i18n", {}).get("en")}
R = load("sjw_skills"); n = m = 0
for r in R:
    if r["kind"] != "rune": continue
    m += 1
    fr = en2fr.get(slug(r["name"]["en"]))
    if fr: setfr(r, fr); n += 1
save("sjw_skills", R); rep["runes"] = f"{n}/{m}"

# pierres de bénédiction (traductions littérales sûres)
BL = {"Lightning Speed":"Vitesse de l'éclair","First Strike Barrage":"Barrage initial","Irresistible Force":"Force irrésistible","Desire":"Désir","Intuit":"Intuition","We Are One":"Nous ne faisons qu'un",
 "Swift Strike":"Frappe véloce","Assassin's Proficiency":"Maîtrise de l'assassinat","Fatal Strike":"Frappe fatale","Weakness Detection":"Détection de faiblesse","Swiftness":"Rapidité","Double-edged Sword":"Épée à double tranchant",
 "Boss Slayer":"Chasseur de boss","Chains of Blood":"Chaînes ensanglantées","Title: Demon Slayer":"Titre : Chasseur de démons","Pulverize":"Pulvérisation","Sharp Perception":"Perception affûtée","Reawakening":"Ré-éveil",
 "Mana Rampage":"Carnage de mana","Monarch's Domain":"Domaine du monarque","Speed":"Vitesse","Advanced Dagger Technique":"Technique avancée de la dague","Swift Restoration":"Récupération rapide",
 "Best Defense is a Good Offense":"Attaquer pour mieux défendre","Aggressive Defense":"Défense agressive","Solidify":"Solidification","Mana Powered Shield":"Bouclier d'énergie de mana","Natural Disaster":"Catastrophe naturelle",
 "Penalty Quest: Survival":"Mission de la sanction : Survie","Life":"Vie","HP Extraction":"Extraction de PV","Camouflage":"Camouflage","Daily Quest Completion":"Accomplissement de quête journalière",
 "Kasaka's Steel Scales":"Écailles d'acier de Kasaka","Tenacity":"Ténacité","Kandiaru's Blessing":"Bénédiction de Kandiaru","Master Marksman":"Maître tireur de précision","Do or Die":"Marche ou crève",
 "Supercharge":"Surcharge de puissance","Iron Stance":"Posture de fer","Architect's Plan":"Plan du Concepteur","Spring of Life":"Source de vie","Devour":"Dévoration"}
apib = {p["nom"] for p in d["pierresBenediction"]}
B = load("blessings"); n = 0
for b in B:
    fr = BL.get(b["name"]["en"])
    if fr and fr in apib: setfr(b, fr); n += 1
save("blessings", B); rep["pierres"] = f"{n}/{len(B)}"

# ombres
SH = {"greed":"Avarice","beru":"Beru","beste":"Beste","bigrock":"Bigrock","brute":"Brute","cerbie":"Cerbie","tusk":"Croc","skull":"Crâne","igris":"Igrit","iron":"Iron","jima":"Jima","kaisel":"Kaisel","blades":"Lames","tank":"Tank","uros":"Uros"}
apis = {o["nom"] for o in d["ombres"]}
Sh = load("shadows"); n = 0
for s in Sh:
    fr = SH.get(s["id"])
    if fr and fr in apis: setfr(s, fr); n += 1
save("shadows", Sh); rep["ombres"] = f"{n}/{len(Sh)}"

# armes de Sung Jin Woo
WP = {"Allon's Orb":"Orbe d'Allon","Demon King's Daggers":"Dagues du roi des démons","Demonic Plum Flower Sword":"Epée démoniaque : Fleur de prunier","Divine Quarterstaff":"Bâton de combat divin","Ennio's Roar":"Rugissement d'Ennio",
 "Fan of the Fire Demon":"Éventail du Démon de feu","Fores's Wish":"Vœu de Fores","Gold-tailed Fox":"Renard à queue dorée","Hero's Sword":"Épée du Héros","Juicy Grilled Skewer":"Brochette grillée juteuse",
 "Truth: Kasaka's Venom Fang":"Vérité : Crochet venimeux de Kasaka","Truth: Demon Knight's Spear":"Vérité : Lance de chevalier démoniaque","Moonlit Gale":"Bourrasque du clair de lune","Moonshadow":"Ombre sélène",
 "Phoenix Soul":"Âme de phénix","Radiru Clan's Double-edged Spear":"Lance à double lame du clan Radir","Shadow Scythe":"Faux de l'ombre","Skadi":"Skadi","Soma and Asura":"Soma et Asura","Spooky Pumpkin":"Citrouille effrayante",
 "The Huntsman":"Le traqueur","Thetis' Grimoire":"Grimoire de Thétis","Transfiguration Key":"Clé de Transfiguration","Vulcan's Rage":"Rage de Vulcan","Winchester Roke":"Winchester Roke","Zeke's Fragment":"Fragment de Zeke",
 "PhantomBlade":"Lame fantôme","Winter Fang":"Croc du Frimas","Stormbringer":"Porte-tempête"}
apiw = {a["nom"] for a in d["armes"]}
W = load("weapons"); n = 0
for w in W:
    fr = WP.get(w["name"]["en"])
    if fr and fr in apiw: setfr(w, fr); n += 1
save("weapons", W); rep["armes"] = f"{n}/{len(W)} (SJW)"
print(rep)
