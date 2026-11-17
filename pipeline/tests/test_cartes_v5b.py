"""Cartes (suite SPEC v5) : puissances rémanentes du BOT, recadrages en grand, apprentissage automatique dès qu'un nom est lu."""
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pytest

pytest.importorskip("cv2")
from PIL import Image

import builds as B
import ecrans_hors_compo as H
import icones
from test_etape2 import CFG, DB, REGLES_TOUT, build, ctx, obs_hunters

RACINE = B.RACINE
DOSSIER = RACINE / "docs/essais/builds/v0tuXJNxudk_ocr"


# --- puissances rémanentes (BOT) ---------------------------------------------------------------------------------------------

def _image_avec_carte(ident):
    """Capture BOT noire où la zone `successor` montre la carte `ident` (plumbing de la bibliothèque sans capture 1080p disponible)."""
    base = Image.new("RGB", (1920, 1080), "black")
    z = CFG["zones"]["bot"]["personnages"]["successor"]["successor"]
    carte = Image.open(RACINE / f"data/icons/remnant_powers_cartes/{ident}.png").convert("RGB")
    x0, y0, x1, y1 = round(z[0] * 1920), round(z[1] * 1080), round(z[2] * 1920), round(z[3] * 1080)
    base.paste(carte.resize((x1 - x0, y1 - y0)), (x0, y0))
    return base


def _remanente(img, obs):
    B._remanente_par_bibliotheque(obs, {"personnages": [img]}, CFG["zones"]["bot"], SimpleNamespace(dossier=RACINE / "data/icons"), CFG, DB)
    return obs


def test_remanente_reconnue_par_sa_carte():
    obs = _remanente(_image_avec_carte("rockpasa"), {"successor": {"id": "myro"}, "unmatched": [{"element": "successor", "owner": "successor", "slot": None}], "notes": []})
    assert obs["successor"]["id"] == "rockpasa" and obs["unmatched"] == []
    assert any("successor reconnu par sa carte" in n for n in obs["notes"])
    for ident in ("baran", "legia", "yogmund"):
        assert _remanente(_image_avec_carte(ident), {"notes": [], "unmatched": []})["successor"]["id"] == ident


def test_remanente_capture_720p_sans_faux_positif():
    img = Image.open(RACINE / "docs/essais/composition/bot_personnages_ja.png").convert("RGB")
    obs = _remanente(img, {"successor": {"id": None}, "notes": [], "unmatched": []})
    assert (obs["successor"] or {}).get("id") in (None, "rockpasa")      # blond en manteau rouge = Rockpasa (base) ; jamais une autre


def test_icone_d_un_successeur_de_sjw_ecartee_au_bot():
    obs = _remanente(Image.new("RGB", (1920, 1080)), {"successor": {"id": "myro"}, "notes": [], "unmatched": []})
    assert obs["successor"]["id"] is None


def test_build_bot_puissance_remanente_sans_id_inconnu():
    o = obs_hunters(3)
    o["successor"] = {"id": "rockpasa", "level": None}
    b = build(ctx("bot", team=None), o, REGLES_TOUT)
    assert b["successor"]["category"] == "remnant_powers" and not any("id inconnu" in e for e in b["erreurs"])


# --- recadrages en grand -------------------------------------------------------------------------------------------------------

def test_recadrage_non_reconnu_en_grand_et_carte_entiere_pour_les_chasseurs(tmp_path):
    grand = Image.new("RGB", (900, 1300), "gray")
    carte = Image.new("RGB", (500, 900), "white")
    b = {"run_id": "poc-x", "run_index": 1, "unmatched": [{"element": "weapons", "owner": "hunter_1", "slot": None},
                                                            {"element": "hunters", "owner": "hunter_2", "slot": None}]}
    obs = {"_crops": {("hunter_1", "weapons", None): grand, ("hunter_2", "hunters", None): Image.new("RGB", (50, 50))}, "_cartes_pleines": {2: carte}}
    chemin = tmp_path / "data/builds/s/poc/poc-x-1.json"
    B.ecrire_crops(b, obs, tmp_path, chemin)
    tailles = [Image.open(tmp_path / u["crop"]).size for u in b["unmatched"]]
    assert max(tailles[0]) == 480 and max(tailles[1]) == 480 and tailles[1][1] > tailles[1][0]      # carte entière (portrait), pas la zone du visage 50 px


def test_crops_config_480():
    assert CFG["crops"]["taille"] == 480


# --- apprentissage automatique dès qu'un nom est lu ------------------------------------------------------------------------------

def test_nom_ocr_lu_remplace_l_icone_et_apprend_la_carte():
    db = B.charger_db(RACINE)
    texte = (DOSSIER / "v0tuXJNxudk_hors-compo_16_stats.txt").read_text(encoding="utf-8")
    compo = Image.open(DOSSIER / "v0tuXJNxudk_compo_personnages_0.jpg").convert("RGB")
    # la carte 2 avait été lue par l'icône comme un AUTRE chasseur : le nom écrit + le portrait tranchent
    obs = {"hunters": [{"position": 1, "id": None, "weapon": {}, "artifacts": [], "cores": []},
                       {"position": 2, "id": "esil-radiru", "weapon": {}, "artifacts": [], "cores": []},
                       {"position": 3, "id": None, "weapon": {}, "artifacts": [], "cores": []}], "notes": []}
    H.integrer(obs, [("stats", texte), ("stats_position", "[2]")], db, CFG)
    h2 = next(h for h in obs["hunters"] if h["position"] == 2)
    assert h2["id"] == "christopher-reed" and h2["via_portrait"] is True
    assert any("nom écrit ≠ icône lue : esil-radiru" in n for n in obs["notes"])
    with tempfile.TemporaryDirectory() as tmp:
        banque = icones.Banque(tmp)
        B.apprendre_cartes(obs, {"personnages": [compo]}, CFG, banque, "poc")
        assert (banque.dossier / "hunters_cartes" / "christopher-reed.png").exists()
        assert not (banque.dossier / "hunters_cartes" / "esil-radiru.png").exists()
        avant = (banque.dossier / "hunters_cartes" / "christopher-reed.png").read_bytes()
        B.apprendre_cartes(obs, {"personnages": [compo.resize((800, 450))]}, CFG, banque, "poc")      # jamais écrasée
        assert (banque.dossier / "hunters_cartes" / "christopher-reed.png").read_bytes() == avant


def test_meme_chasseur_lu_par_l_icone_ailleurs_est_retire():
    db = B.charger_db(RACINE)
    texte = (DOSSIER / "v0tuXJNxudk_hors-compo_16_stats.txt").read_text(encoding="utf-8")
    obs = {"hunters": [{"position": 1, "id": "christopher-reed", "weapon": {}, "artifacts": [], "cores": []},
                       {"position": 2, "id": None, "weapon": {}, "artifacts": [], "cores": []}], "notes": []}
    H.integrer(obs, [("stats", texte), ("stats_position", "[2]")], db, CFG)
    par = {h["position"]: h for h in obs["hunters"]}
    assert par[2]["id"] == "christopher-reed" and par[1]["id"] is None and len(obs["hunters"]) == 2
