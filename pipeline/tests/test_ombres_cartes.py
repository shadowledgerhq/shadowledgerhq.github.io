"""v33 : ombres reconnues par leur carte (`data/icons/shadows_cartes/`, fournie par la discussion 9) sur les captures réelles POC / BOT."""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest

pytest.importorskip("cv2")
from PIL import Image

import builds
import portraits

RACINE = Path(__file__).resolve().parents[2]
CFG = builds.charger_config()


def _lancer(mode, capture, obs=None, dossier=RACINE / "data/icons"):
    obs = obs if obs is not None else {"shadows": [], "notes": []}
    obs.setdefault("notes", [])
    img = Image.open(RACINE / f"docs/essais/composition/{capture}.png").convert("RGB")
    builds._ombres_par_bibliotheque(obs, {"personnages": [img]}, CFG["zones"][mode], SimpleNamespace(dossier=dossier), CFG)
    return obs


def test_poc_beste_et_greed_reconnus_position_3_inconnue():
    obs = _lancer("poc", "poc_personnages_ja")
    assert [(o["position"], o["id"]) for o in obs["shadows"]] == [(1, "beste"), (2, "greed")]
    assert any("shadow_2 reconnu par sa carte, icône lue : aucune" in n for n in obs["notes"])


def test_bot_beste_et_greed_reconnus():
    obs = _lancer("bot", "bot_personnages_ja")
    assert [(o["position"], o["id"]) for o in obs["shadows"]] == [(1, "beste"), (2, "greed")]


def test_la_carte_l_emporte_sur_l_icone_peu_fiable():
    """15/11 : position 2 lue `brute` (0,62) à tort ; la carte (118 correspondances) donne greed et la note garde l'icône lue."""
    obs = _lancer("poc", "poc_personnages_ja", {"shadows": [{"position": 1, "id": "beste"}, {"position": 2, "id": "brute"}, {"position": 3, "id": None}]})
    assert [o["id"] for o in obs["shadows"]] == ["beste", "greed", None]
    assert any("icône lue : brute" in n for n in obs["notes"])


def test_bibliotheque_absente_ou_vide_ne_change_rien(tmp_path):
    obs = _lancer("poc", "poc_personnages_ja", {"shadows": [{"position": 2, "id": "brute"}]}, dossier=tmp_path)
    assert obs["shadows"] == [{"position": 2, "id": "brute"}] and obs["notes"] == []
    (tmp_path / portraits.DOSSIER_OMBRES).mkdir()
    assert _lancer("poc", "poc_personnages_ja", {"shadows": []}, dossier=tmp_path)["shadows"] == []


def test_les_cartes_de_la_base_sont_des_ombres_connues():
    import json
    ids = {s["id"] for s in json.loads((RACINE / "data/db/shadows.json").read_text(encoding="utf-8")) if isinstance(s, dict)}
    assert {f.stem for f in (RACINE / "data/icons/shadows_cartes").glob("*.png")} <= ids
