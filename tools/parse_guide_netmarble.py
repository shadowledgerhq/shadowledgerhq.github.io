"""Transforme les pages du guide officiel Netmarble (dumps texte de crawl_guide_netmarble.py)
en data/db/rates.json (pages « Rate » : tableaux de probabilités) et data/db/game_rules.json
(pages de règles). Les pages « Rewards » (récompenses de modes, très volumineuses) sont ignorées.
Usage : python3 tools/parse_guide_netmarble.py DOSSIER_DUMPS [AAAA-MM-JJ]"""
import json, re, sys
from pathlib import Path

D = Path(sys.argv[1])
DATE = sys.argv[2] if len(sys.argv) > 2 else "2026-11-16"
RACINE = Path(__file__).resolve().parent.parent
URL = "https://guide.netmarble.com/sololv/{}"
PREF = "Solo Leveling:ARISE_"
NAV = {"[Solo Leveling] Guide", "Fachtna’s Essential ARISE Guide", "⭐Must Read for New Hunters",
       "🦎 Content & Key Rewards Overview", "🦎Growth Guide by Total Power",
       "🦎Combat Styles & Classes Overview", "🦎How to Set Up Artifacts", "🦎Currencies Overview"}
FR = {
 "Battle Class": "Classe de combat", "Achievements": "Succès", "Special Commissions": "Commissions spéciales",
 "Options": "Options", "Sung Jinwoo": "Sung Jinwoo", "Change Job": "Changement de classe", "Skill": "Compétence",
 "Collection": "Collection", "Hunters": "Chasseurs", "Weapons": "Armes", "Artifacts": "Artefacts",
 "Army of Shadows": "Armée des ombres", "Manage Presets": "Gérer les préréglages", "Story": "Histoire",
 "Gates": "Portails", "Dispatch Mining Teams": "Envoi d'équipes de minage", "Draw": "Invocation", "Shop": "Boutique",
 "Monarch Milestones": "Jalons des Monarques", "Missions": "Missions", "Craft": "Fabrication", "Fuse": "Fusion",
 "Codex": "Codex", "Tutorial": "Didacticiel", "Unstable Dungeon": "Donjon instable",
 "Battlefield of Time Mode": "Champ de bataille du temps", "Battlefield of Trials": "Champ de bataille des épreuves",
 "Power of Calamity": "Pouvoir du fléau", "Mailbox": "Boîte aux lettres", "Event": "Événement",
 "Hunter Pass": "Passe de chasseur", "Inventory": "Inventaire", "Hunter Archive": "Archives des chasseurs",
 "Armory": "Armurerie", "Hunter Preview": "Aperçu des chasseurs", "Rankings": "Classements",
 "Blessing Stones": "Pierres de bénédiction", "Activity support fund": "Fonds de soutien d'activité",
 "Special Summons": "Invocations spéciales", "Jewel": "Gemmes", "Bonds": "Liens",
 "Battlefield of Chaos": "Champ de bataille du chaos", "Workshop of Brilliant Light": "Atelier de la lumière éclatante",
 "Core": "Noyau", "Remnant Power": "Pouvoir résiduel", "The Simulation Gate": "Portail de simulation",
 "Challenge Medals": "Médailles de défi", "Skill Research": "Recherche de compétence",
 "The Architect's Test": "Épreuve du Concepteur", "Shadow Enforcer": "Exécuteur des ombres",
 "Training Room": "Salle d'entraînement", "The Overseer's Forbidden Library": "Bibliothèque interdite du Surveillant",
 "Hunter Co-Op Training": "Entraînement coopératif de chasseurs", "Edge of Illusion and Dreams": "Orée de l'illusion et des rêves",
 "New Hunter Protocol": "Protocole du nouveau chasseur", "Mind Rift": "Faille mentale", "Successors": "Successeurs",
 "Seasonal Cards": "Cartes de saison", "Hall of the Monarchs": "Salle des Monarques", "Figures": "Statues",
 "Deep Containment Zone": "Zone de confinement profond", "Profile": "Profil",
 "Chest Rate": "Taux des coffres", "Draw Rate": "Taux d'invocation", "Fuse Rate": "Taux de fusion",
 "Capsule Rate": "Taux des capsules", "Dice Rate": "Taux des dés", "Artifact Rates": "Taux des artefacts",
 "Artifact Enchantment Rate": "Taux d'enchantement des artefacts", "Core Rate": "Taux des noyaux",
 "World Drop Rate": "Taux de butin mondial", "Amplification Rate": "Taux d'amplification",
 "Figure Rates": "Taux des statues", "Seasonal Card Rates": "Taux des cartes de saison",
}
FR.update({"Content & Key Rewards Overview": "Contenus et récompenses clés", "Growth Guide by Total Power": "Guide de progression par puissance totale",
 "Combat Styles & Classes Overview": "Styles de combat et classes", "How to Set Up Artifacts": "Configurer les artefacts",
 "Currencies Overview": "Aperçu des monnaies", "Must Read for New Hunters": "À lire pour les nouveaux chasseurs","Guild : Overview": "Guilde : aperçu", "Guild: Guild Lobby": "Guilde : hall de guilde",
 "Guild: Guild Content": "Guilde : contenus de guilde", "Guild: Guild Boss": "Guilde : boss de guilde",
 "Guild: Guild Rank": "Guilde : rang de guilde", "Guild Achievement": "Succès de guilde"})

def slug(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower().replace("’", "").replace("'", "")).strip("-")

def blocs(texte, garder_vides):
    out, tab, titre_tab = [], None, None
    for l in texte.split("\n"):
        brut = l.rstrip()
        if "\t" in brut:
            cells = [c.strip() for c in brut.split("\t")]
            if not garder_vides:
                cells = [c for c in cells if c]
            if not any(cells):
                continue
            if tab is None:
                tab = {"header": cells, "rows": []}
                out.append(tab)
            else:
                tab["rows"].append(cells)
        else:
            s = brut.strip()
            if s:
                tab = None
                out.append(s)
    return out

rates, rules = [], []
for f in sorted(D.glob("*.txt"), key=lambda p: int(p.stem)):
    n = int(f.stem)
    lignes = f.read_text(encoding="utf-8").split("\n")
    titre = lignes[0]
    if not titre.startswith(PREF):
        continue
    en = titre[len(PREF):].strip()
    if n == 1 or re.search(r"\(\d\)$", en) or ("Reward" in en and not 233 <= n <= 240):
        continue  # menu, tableaux de récompenses de modes
    est_taux = "Rate" in en
    b = blocs("\n".join(lignes[1:]), est_taux)
    b = [x for x in b if not (isinstance(x, str) and x in NAV)]
    if not est_taux and b and isinstance(b[0], str) and b[0] == en:
        b = b[1:]
    e = {"id": slug(en), "kind": "rates" if est_taux else "rules",
         "name": {"fr": FR.get(en.lstrip("🦎⭐ "), ""), "en": en.lstrip("🦎⭐ ")},
         "guide_page": n, "blocks": b, "icon": None, "source": URL.format(n),
         "verified_at": DATE, "game_version": None,
         "notes": "Guide officiel Netmarble (EN seul), écrit sur la version test : peut être périmé. Valeurs arrondies."}
    if 233 <= n <= 240:
        e["notes"] = "Guide communautaire « Fachtna's Essential ARISE Guide » hébergé sur le guide officiel Netmarble (conseils, pas des règles officielles)."
    (rates if est_taux else rules).append(e)

for nom, liste in (("rates", rates), ("game_rules", rules)):
    p = RACINE / "data" / "db" / f"{nom}.json"
    p.write_text("[\n" + ",\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in liste) + "\n]\n", encoding="utf-8")
    print(nom, len(liste), p.stat().st_size // 1024, "Ko")
