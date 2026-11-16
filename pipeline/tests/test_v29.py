"""SPEC v29 : ordre de traitement du PC (top 10), ligne « Top 10 couvert », critère de gel n° 3, blocs triés par horodatage."""
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ordre_pc
import rapport_pc
from donnees import Donnees

SEM = "2026-11-12"


def ligne(v, total, conf, unite):
    return {"video_id": v, "video_ids": [v], "score": {"total": total, "runs": [total], "unit": unite}, "confidence": conf}


def monde(tmp):
    d = Donnees(Path(tmp))
    gb = [ligne(f"s{i}", 100 - i, "sur", "rage_count") for i in range(10)]                 # 10e `sûr` = 91
    gb += [ligne("g_haut", 95, "a_verifier", "rage_count"), ligne("g_bas", 50, "a_verifier", "rage_count"),
           ligne("g_haut2", 99, "a_verifier", "rage_count")]
    bot = [ligne(f"t{i}", 20 + i, "sur", "seconds") for i in range(10)]                    # 10e `sûr` = 29 s
    bot += [ligne("b_court", 25, "a_verifier", "seconds"), ligne("b_long", 40, "a_verifier", "seconds")]
    poc = [ligne("p1", 5, "sur", "damage"), ligne("p_prov", 1, "a_verifier", "damage")]    # < 10 `sûr` : tout est candidat
    for nom, lignes in (("gb", gb), ("bot", bot), ("poc", poc)):
        d.ecrire(f"runs/{SEM}/{nom}.json", lignes)
    return d


def test_ordre_candidates_puis_les_autres():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        ids = ["g_bas", "b_long", "sans_score", "g_haut", "p_prov", "b_court", "g_haut2"]
        ordre, cand = ordre_pc.ordonner(d, SEM, ids)
        assert cand == {"sans_score", "g_haut", "p_prov", "b_court", "g_haut2"}
        assert ordre[-2:] == ["g_bas", "b_long"] or set(ordre[-2:]) == {"g_bas", "b_long"}
        assert ordre.index("g_haut2") < ordre.index("g_haut")                  # 99 avant 95 (score décroissant)
        assert ordre.index("g_haut2") < ordre.index("sans_score") and ordre[4] == "sans_score" or ordre.index("sans_score") > ordre.index("g_haut")
        assert ordre.index("sans_score") > ordre.index("b_court")              # sans score provisoire : après les scorés du groupe


def test_bot_temps_croissant_et_dixieme_sur():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        info = ordre_pc.analyser(d, SEM)
        assert info["b_court"][0] is True and info["b_long"][0] is False          # 25 s < 29 s : candidate ; 40 s : non
        assert info["g_haut"][0] is True and info["g_bas"][0] is False
        assert info["p_prov"][0] is True                                           # mode à moins de 10 `sûr`


def test_ligne_top10_et_comptage():
    with tempfile.TemporaryDirectory() as tmp:
        d = monde(tmp)
        proc = {v: {"week": SEM, "status": "en_cours", "pc_needed": True} for v in ("g_bas", "g_haut", "inconnue")}
        proc["fait"] = {"week": SEM, "status": "en_cours", "pc_needed": True, "pc": {"tri4": "fait"}}
        assert ordre_pc.candidates_restantes(d, SEM, proc) == 2                    # g_haut + inconnue
        assert ordre_pc.ligne_top10(0) == "- Top 10 couvert : oui (0 vidéo candidate au top 10 restante)"
        assert ordre_pc.ligne_top10(2) == "- Top 10 couvert : non (2 vidéos candidates au top 10 restantes)"


def _instant(h, m):
    return datetime(2026, 11, 16, h, m, tzinfo=timezone.utc)


def test_blocs_tries_par_horodatage_et_gel3():
    with tempfile.TemporaryDirectory() as tmp:
        d = Donnees(Path(tmp))
        couvert = ["- Top 10 couvert : oui (0 vidéo candidate au top 10 restante)", "- Erreurs bloquantes : anti-bot YouTube (passage incomplet : anti-bot)"]
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(19, 31), ["- Top 10 couvert : non (3 vidéos candidates au top 10 restantes)", "- Erreurs bloquantes : aucune"])
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(21, 36), couvert)
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(19, 4), ["- x"])                 # écrit en dernier mais plus ancien
        texte = (d.data / rapport_pc.chemin(SEM)).read_text(encoding="utf-8")
        assert [m for m in __import__("re").findall(r"passage-pc pc-daily (\S+)", texte)] == [_instant(19, 4).isoformat(), _instant(19, 31).isoformat(), _instant(21, 36).isoformat()]
        assert len(rapport_pc.blocs(texte)) == 3 and rapport_pc.dernier_bloc(d, SEM)[-1].startswith("- Erreurs bloquantes : anti-bot")
        # un passage qui réécrit son bloc remplace le sien
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(21, 36), couvert + ["- relu"])
        assert len(rapport_pc.blocs((d.data / rapport_pc.chemin(SEM)).read_text(encoding="utf-8"))) == 3
        # critère 3 : courant couvert (anti-bot seul) + précédent (21:36) couvert -> atteint ; précédent non couvert -> 1/2
        assert rapport_pc.critere_gel3(d, SEM, "pc-daily", _instant(22, 40), 0, ["anti-bot YouTube (x)"]).startswith("2/2")
        assert rapport_pc.critere_gel3(d, SEM, "pc-daily", _instant(22, 40), 1, []).startswith("0/2")
        assert rapport_pc.critere_gel3(d, SEM, "pc-daily", _instant(22, 40), 0, ["git : x"]).startswith("0/2")
        assert rapport_pc.critere_gel3(d, SEM, "pc-daily", _instant(20, 0), 0, []).startswith("1/2")      # le précédent (19:31) n'est pas couvert


def test_blocs_existants_dans_le_mauvais_ordre_sont_remis_dans_l_ordre():
    with tempfile.TemporaryDirectory() as tmp:
        d = Donnees(Path(tmp))
        m1, m2 = rapport_pc.marqueur("pc-daily", _instant(20, 31)), rapport_pc.marqueur("pc-daily", _instant(20, 4))
        d.ecrire(rapport_pc.chemin(SEM), rapport_pc.ENTETE.format(week=SEM) + f"\n{m1}\n## a\n\n- 20:31\n\n{m2}\n## b\n\n- 20:04\n")
        assert rapport_pc.blocs((d.data / rapport_pc.chemin(SEM)).read_text(encoding="utf-8"))[-1].endswith("- 20:31")
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(22, 0), ["- 22:00"])
        t = (d.data / rapport_pc.chemin(SEM)).read_text(encoding="utf-8")
        assert t.index("- 20:04") < t.index("- 20:31") < t.index("- 22:00")


DOSSIER_OCR = Path(__file__).resolve().parents[2] / "docs" / "essais" / "ocr" / "libelles_inconnus"


def test_pt_br_results_reconnu_sans_accents_sur_la_capture_reelle():
    import ocr_ecrans
    texte = (DOSSIER_OCR / "T5dR6iJAn-Y_227.txt").read_text(encoding="utf-8")        # « Pontuagao », « Cacador », « Res tado » (OCR)
    assert ocr_ecrans.langue_results(texte) == "pt" and ocr_ecrans.detecter(texte) == "gb_results_partiel"
    assert ocr_ecrans.detecter("Pontuacao do Jogador\n7.907.273.299.084") is None       # un seul libellé ne suffit pas


def test_ecrans_exclus_jamais_un_ecran_de_score_ni_collectes():
    import libelles_inconnus
    import ocr_ecrans
    exclus = ["HWebrRc_l0o_0", "HWebrRc_l0o_4", "HWebrRc_l0o_10", "MJ2iz5TFmvM_300", "MJ2iz5TFmvM_390", "PiklPqHaKtE_1013",
              "trinzgj3FV4_261", "trinzgj3FV4_267", "uTe6xbn1bc8_0", "uTe6xbn1bc8_4", "vYtRCpFtSOk_421"]
    for nom in exclus:
        texte = (DOSSIER_OCR / f"{nom}.txt").read_text(encoding="utf-8")
        assert ocr_ecrans.ecran_exclu(texte), nom
        assert ocr_ecrans.detecter(texte) is None and not ocr_ecrans.candidat_bot(texte) and not libelles_inconnus.ressemble_score(texte), nom
        assert not libelles_inconnus.a_garder(texte, None, []), nom
    # un vrai écran n'est pas exclu
    assert not ocr_ecrans.ecran_exclu((DOSSIER_OCR / "T5dR6iJAn-Y_227.txt").read_text(encoding="utf-8"))
    # le « Record » de l'écran de composition BOT ne devient jamais un score
    assert ocr_ecrans.detecter("FormTeam Player Mode\nRecord 00:31.271\nPhase1 00:05.000 Phase2 00:12.000\nPlay Time 00:31") is None


def test_gel3_relances_et_passages_refuses_ne_comptent_pas():
    with tempfile.TemporaryDirectory() as tmp:
        d = Donnees(Path(tmp))
        couvert = ["- Top 10 couvert : oui (0 vidéo candidate au top 10 restante)", "- Erreurs bloquantes : aucune"]
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(10, 0), couvert)
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(12, 0), ["- Top 10 couvert : non (2 vidéos candidates au top 10 restantes)", "- Type : relance automatique (x)"])
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(13, 0), ["- Passage complet : non", "- Erreurs bloquantes : passage refusé : un autre passage PC tourne déjà"])
        # la relance non couverte et le passage refusé ne remettent rien à zéro : 10:00 couvert + courant couvert = 2/2
        assert rapport_pc.critere_gel3(d, SEM, "pc-daily", _instant(20, 0), 0, []).startswith("2/2")
        # un passage planifié non couvert remet à 0/2
        rapport_pc.ecrire_bloc(d, SEM, "pc-daily", _instant(14, 0), ["- Top 10 couvert : non (1 vidéo candidate au top 10 restante)", "- Erreurs bloquantes : aucune"])
        assert rapport_pc.critere_gel3(d, SEM, "pc-daily", _instant(20, 0), 0, []).startswith("1/2")
        # le passage courant est une relance : il ne compte pas (seulement les précédents planifiés)
        assert rapport_pc.critere_gel3(d, SEM, "pc-daily", _instant(20, 0), 0, [], relance=True).startswith("0/2")


def test_manual_sans_titre_result_jamais_un_ecran_de_score_bot():
    import libelles_inconnus
    import ocr_ecrans
    t = (DOSSIER_OCR / "uTe6xbn1bc8_32.txt").read_text(encoding="utf-8")               # HUD de combat du BOT (MANUAL, NEW Phase 2 00:21.042)
    assert ocr_ecrans.manual_sans_titre(t) and ocr_ecrans.detecter(t) is None and not ocr_ecrans.candidat_bot(t)
    assert not libelles_inconnus.ressemble_score(t) and not libelles_inconnus.a_garder(t, None, [])
    assert not ocr_ecrans.manual_sans_titre("RESULT MANUAL\nPhase1 00:05.000 Phase2 00:12.000 Play Time 00:31")   # titre RESULT : pas exclu
    # le HUD du GB (MANUAL aussi) reste reconnu par ses libellés
    hud = (DOSSIER_OCR.parent / "Oj_-5x6700s_tri3_212.txt").read_text(encoding="utf-8")
    assert "manual" in hud.lower()
