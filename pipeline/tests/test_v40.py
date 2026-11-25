"""SPEC v40 : POC refonte — écran de palier (lecture par ancres sur les captures réelles), contrôles, vote, texte, classement."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import classement as C
import ocr_ecrans
import pc
import poc_palier as P
import tri1

RACINE = Path(__file__).resolve().parents[2]
CAPT = RACINE / "docs/essais/ocr/libelles_inconnus"
CONFIG = json.loads((RACINE / "pipeline/config/etape1.json").read_text(encoding="utf-8"))
OUTILS_OK = bool(shutil.which("tesseract") and shutil.which("ffmpeg"))
META = {"video_id": "v1", "channel_id": "c1", "channel_title": "Joueur", "published_at": "2026-11-21T10:00:00Z", "mode_guess": ["poc"]}


def lire_capture(nom):
    tmp = tempfile.mkdtemp()
    png = f"{tmp}/x.png"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(CAPT / f"{nom}.jpg"), png], check=True)
    try:
        texte = (CAPT / f"{nom}.txt").read_text(encoding="utf-8")
        return P.lire(pc.Outils(CONFIG["pc"]), png, texte)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --- détection ----------------------------------------------------------------------------------

@pytest.mark.parametrize("nom", ["3y8yRhcSq4Y_530", "3y8yRhcSq4Y_536", "9BrduWR4aSY_354", "PJqW-zrX8qM_695", "cNIuOYknYg8_153", "wWySgU0_sIQ_547"])
def test_detection_des_captures_de_palier(nom):
    texte = (CAPT / f"{nom}.txt").read_text(encoding="utf-8")
    assert ocr_ecrans.detecter(texte) == "poc_palier"


def test_gb_results_pas_confondu():
    texte = (CAPT / "CnFBmHEzZww_502.txt").read_text(encoding="utf-8")
    assert ocr_ecrans.detecter(texte) == "gb_results_partiel"


# --- contrôles (SPEC §3) ---------------------------------------------------------------------------

def valeurs(**kw):
    base = dict(tier=17, team=1, rank_score=17_000_000, goal_progress=100.0, team_pct=[39.02, 60.98], player=6_177_875_929_148, successor=0,
                successeur_present=True, hunters=[3_718_164_023_571, 2_254_996_020_308, 473_923_978_322], total_contribution=12_624_959_951_349)
    base.update(kw)
    return base


def test_controles_cas_9brdu():
    ok, notes = P.controles(valeurs())
    assert ok and not notes


def test_controle_a_b_c_en_echec():
    assert not P.controles(valeurs(rank_score=17_000_200))[0]                      # (a)
    assert P.controles(valeurs(rank_score=17_000_090))[0]                          # (a) tolérance 100
    assert not P.controles(valeurs(team_pct=[39.02, 60.80]))[0]                    # (b)
    assert P.controles(valeurs(team_pct=[39.02, 60.94]))[0]                        # (b) tolérance 0,05
    assert not P.controles(valeurs(total_contribution=12_624_959_951_350))[0]      # (c)
    assert not P.controles(valeurs(rank_score=None))[0]
    ok, notes = P.controles(valeurs(via_expansion=True))
    assert not ok and any("chiffres de tête" in n for n in notes)


def test_controle_c_sans_successeur():
    e = valeurs(successeur_present=False, successor=None, tier=5, rank_score=4_487_518, goal_progress=48.75, team_pct=[48.75, 0.0],
                player=418_938_604, hunters=[1_514_880_684, 840_578_462, 665_090_055], total_contribution=3_439_487_805)
    assert P.controles(e)[0]


# --- lecture sur les captures réelles ------------------------------------------------------------------

@pytest.mark.skipif(not OUTILS_OK, reason="tesseract et ffmpeg requis")
def test_9brdu_354_sur():
    e = lire_capture("9BrduWR4aSY_354")
    assert (e["tier"], e["team"], e["rank_score"], e["goal_progress"], e["team_pct"]) == (17, 1, 17_000_000, 100.0, [39.02, 60.98])
    assert e["total_contribution"] == 12_624_959_951_349 and e["successor"] == 0 and e["play_time"] == "01:57"
    assert P.controles(e)[0]


@pytest.mark.skipif(not OUTILS_OK, reason="tesseract et ffmpeg requis")
def test_pjqw_695_sur():
    e = lire_capture("PJqW-zrX8qM_695")
    assert (e["tier"], e["team"], e["rank_score"], e["goal_progress"], e["team_pct"]) == (16, 2, 15_962_022, 96.2, [65.94, 30.26])
    assert e["total_contribution"] == 6_359_680_894_418 and P.controles(e)[0]


@pytest.mark.skipif(not OUTILS_OK, reason="tesseract et ffmpeg requis")
def test_3y8y_536_palier_5():
    e = lire_capture("3y8yRhcSq4Y_536")
    assert (e["tier"], e["team"], e["goal_progress"], e["team_pct"][0]) == (5, 1, 48.75, 48.75)
    assert abs(e["rank_score"] - 4_487_518) <= 100 and e["total_contribution"] == 3_439_487_805 and P.controles(e)[0]


@pytest.mark.skipif(not OUTILS_OK, reason="tesseract et ffmpeg requis")
def test_ecran_assombri_jamais_une_valeur_fausse_sure():
    e = lire_capture("3y8yRhcSq4Y_530")          # fenêtre de récompense : contributions illisibles
    ok, _ = P.controles(e)
    if ok:      # si les contrôles passent, les valeurs sont exactes
        assert e["total_contribution"] == 3_439_487_805 and e["player"] == 418_938_604


# --- lecture de classement et vote ------------------------------------------------------------------

def ecran(rank=17_000_000, total=12_624_959_951_349, tier=17, team=1, ok=True, t=100):
    e = valeurs(tier=tier, team=team, rank_score=rank, total_contribution=total)
    if not ok:
        e["total_contribution"] = total + 1
    return e


def lecs(*specs):
    out = []
    for spec in specs:
        out.append(ocr_ecrans.lectures_depuis_texte(
            (CAPT / "9BrduWR4aSY_354.txt").read_text(encoding="utf-8"), META, CONFIG, "video-complete", spec.get("t", 100), {"palier": ecran(**spec)})[0])
    return out


def test_lecture_sans_score_si_controle_en_echec():
    l = lecs({"ok": False})[0]
    assert l["detail"]["sans_score"] and l["confidence"] == "a_verifier" and any(n.startswith("contrôle POC palier") for n in l["notes"])


def test_vote_deux_images_pour_sur():
    une = ocr_ecrans.dedoublonner_lectures(lecs({"t": 100}))
    assert une[0]["confidence"] == "a_verifier" and "palier : lu sur une seule image" in " ".join(une[0]["notes"])
    deux = ocr_ecrans.dedoublonner_lectures(lecs({"t": 100}, {"t": 101}))
    assert len(deux) == 1 and deux[0]["confidence"] == "sur" and deux[0]["exact"] and deux[0]["detail"]["par_t"] == [100, 101]
    idem = ocr_ecrans.dedoublonner_lectures(deux + lecs({"t": 101}))          # relecture : idempotent
    assert len(idem) == 1 and idem[0]["detail"]["par_t"] == [100, 101]


def test_vote_rank_score_different_pas_sur():
    r = ocr_ecrans.dedoublonner_lectures(lecs({"t": 100, "rank": 17_000_000}, {"t": 101, "rank": 17_000_050}))
    assert len(r) == 1 and r[0]["confidence"] == "a_verifier"


# --- texte (SPEC §4) --------------------------------------------------------------------------------------

def texte(titre):
    l, _ = tri1.lectures_texte(META, [("titre", titre)], CONFIG)
    return l[0] if l else None


def test_texte_palier_borne_basse():
    l = texte("TIER 17 POC 100% WITH WATER TEAM RUN")
    assert l["score"] == 16_000_000 and l["confidence"] == "a_verifier" and not l["exact"] and "palier du titre : rang prudent" in l["notes"]
    assert texte("Power of Calamity T12 Team 1")["score"] == 11_000_000
    assert texte("POC palier 3 guide")["score"] == 2_000_000


def test_texte_clear_et_rank_score():
    assert texte("Tier 5 clear")["score"] == 5_000_000
    assert texte("POC Rank Score 15,962,022")["score"] == 15_962_022
    assert "palier du titre : clear" in texte("Tier 5 clear")["notes"]


def test_texte_degats_ne_sont_plus_un_score():
    assert texte("PoC 19R 80T 12,000,000,000,000 damage") is None
    l = texte("Tier 5 clear 12,624,959,951,349 damage")
    assert l["score"] == 5_000_000 and "dégâts du texte : information" in l["notes"]


def test_texte_avant_la_refonte_inchange():
    meta = {**META, "published_at": "2026-11-12T10:00:00Z"}
    l, _ = tri1.lectures_texte(meta, [("titre", "POC 12,624,959,951,349")], CONFIG)
    assert l and l[0]["score"] == 12_624_959_951_349


# --- classement (SPEC §2) -----------------------------------------------------------------------------------

def run_ecran(chaine, video, tier, team, rank, total, sur=True, t=100):
    return {"video_id": video, "channel_id": chaine, "channel_title": chaine, "published_at": "2026-11-21T10:00:00Z", "mode": "poc", "lang": "en",
            "team": team, "score": rank, "exact": sur, "confidence": "sur" if sur else "a_verifier", "score_source": "video-complete", "t": t,
            "stage": None, "notes": [], "_cle": "poc", "_refonte": True, "element": None, "element_source": None,
            "detail": {"v40": True, "v40_sur": sur, "tier": tier, "total_contribution": total, "goal_progress": 50.0, "team_pct": [30.0, 20.0],
                       "play_time": "02:00"}}


def test_ligne_meilleur_rank_score_et_runs_detail_du_palier():
    runs = [run_ecran("c1", "v1", 5, 1, 4_487_518, 3_439_487_805), run_ecran("c1", "v1", 17, 1, 16_390_200, 5_000_000_000),
            run_ecran("c1", "v1", 17, 2, 17_000_000, 12_000_000_000)]
    l = C.ligne_poc_refonte(runs, CONFIG, "2026-11-19")
    assert l["score"]["total"] == 17_000_000 and l["score"]["unit"] == "rank_score" and l["confidence"] == "sur"
    assert [r["team"] for r in l["runs_detail"]] == [1, 2] and all(r["tier"] == 17 for r in l["runs_detail"])
    assert l["score"]["runs"] == [5_000_000_000, 12_000_000_000]            # information, jamais additionné


def test_ligne_score_plus_haut_non_confirme():
    runs = [run_ecran("c1", "v1", 5, 1, 4_487_518, 3_439_487_805), run_ecran("c1", "v2", 17, 1, 17_000_000, 12_000_000_000, sur=False)]
    l = C.ligne_poc_refonte(runs, CONFIG, "2026-11-19")
    assert l["score"]["total"] == 4_487_518 and "score plus haut non confirmé : 17000000 (v2)" in l["notes"]


def test_ex_aequo_meme_rang():
    lignes = [C.ligne_poc_refonte([run_ecran(c, f"v{c}", 17, 1, rank, 1)], CONFIG, "2026-11-19")
              for c, rank in (("a", 17_000_000), ("b", 17_000_000), ("c", 15_000_000))]
    out = C.ordonner(lignes, "poc")
    assert [l["rank"] for l in out] == [1, 1, 3]


def test_texte_seul_ne_classe_pas():
    r = run_ecran("c1", "v1", None, None, 4_000_000, None)
    r["detail"] = {"poc_texte": "palier", "palier": 5}
    r["confidence"], r["score_source"] = "a_verifier", "titre"
    l = C.ligne_poc_refonte([r], CONFIG, "2026-11-19")
    assert l["confidence"] == "a_verifier" and l["score"]["total"] == 4_000_000 and l["rank"] is None
