"""SPEC_ETAPE1 v26 : RESULT du BOT en japonais, `Phase1` sans espace, comparaison sans accents/casse/espaces."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ocr_ecrans as O
from donnees import charger_config

CFG = charger_config()

# Texte OCR synthétique de docs/essais/composition/bot_results_sans_sjw_ja.png
JA = """RESULT
突撃の暗殺者タール
突撃の暗殺者タール
Phase1 00:04.734
Phase2 00:15.212
Phase3 00:29.224
進行時間 00:29
もう一度プレイ 出る 戦闘オプション
aaaaaaaaaaaa 00:29.224"""


def test_v26_result_bot_japonais():
    assert O.detecter(JA, CFG) == "bot"
    e = O.lire_bot(JA, CFG)
    assert e["phases"] == [4.734, 15.212, 29.224] and e["chrono"] == 29.224 and e["play_time"] == 29
    assert e["stage"] == "突撃の暗殺者タール"


def test_v26_lecture_29_224_sur():
    l = O.lectures_depuis_texte(JA, {"video_id": "x", "channel_id": "c", "published_at": "2026-11-16T00:00:00Z", "title": "BOT", "mode_guess": ["bot"]}, CFG, "video-complete", t=12)
    assert len(l) == 1 and l[0]["score"] == 29.224 and l[0]["confidence"] == "sur" and l[0]["exact"]
    assert l[0]["stage"] == "突撃の暗殺者タール"


def test_v26_phase1_sans_espace_et_casse_toutes_langues():
    en = "Results\nBaruka\nPHASE 1 00:09.281\nphase2 00:14.986\nPhase 3 00:19.926\nPlay Time 00:19\nThenaX 00:19.926"
    assert O.detecter(en, CFG) == "bot" and O.lire_bot(en, CFG)["stage"] == "Baruka"
    assert O.detecter(en.replace("PHASE 1", "Phase1"), CFG) == "bot"
    assert O.detecter(en.replace("Play Time", "play  time"), CFG) == "bot"
    assert O.detecter(JA.replace("Phase1", "Phase 1").replace("進行時間", "進行 時間"), CFG) == "bot"


def test_v26_pas_de_faux_positif():
    assert O.detecter("Phase1 boss 12 joueurs", CFG) is None       # pas de chronos
    assert O.detecter("RESULT\nPhase1 00:04.734\nPhase2 00:15.212", CFG) is None   # pas de temps de jeu


def test_v26_boutons_ignores():
    e = O.lire_bot(JA, CFG)
    assert "もう一度" not in str(e["stage"]) and "出る" not in str(e["stage"])


def test_v26_zone_armes_sjw_vide_sur_les_2_captures():
    import pc
    d = Path(__file__).resolve().parents[2] / "docs" / "essais" / "composition"
    assert pc.zone_armes_bot(d / "bot_results_sans_sjw_ja.png", CFG) is True
    assert pc.zone_armes_bot(d / "bot_results_ja.png", CFG) is False
    meta = {"video_id": "x", "channel_id": "c", "published_at": "2026-11-16T00:00:00Z", "title": "BOT", "mode_guess": ["bot"]}
    l = O.lectures_depuis_texte(JA, meta, CFG, "video-complete", t=12, zones={"armes_sjw_vides": True})
    assert l[0]["detail"]["armes_sjw_vides"] is True
    l = O.lectures_depuis_texte(JA, meta, CFG, "video-complete", t=12)
    assert "armes_sjw_vides" not in l[0]["detail"]          # inconnu : jamais une preuve


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("OK")
