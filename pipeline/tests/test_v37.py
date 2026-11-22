"""SPEC_ETAPE1 v37 : actualités probables (tri 1), ordre du PC, décision du tri 3 sur l'image, libellés inconnus."""
import sys
import tempfile
import pytest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import libelles_inconnus
import ocr_ecrans
import ordre_pc
import pc
import tri1
from donnees import Donnees, charger_config
from test_tri34 import GB_RESULTS, HUD_228, OutilsImages, meta
from test_v29 import SEM

CONFIG = charger_config()


@pytest.fixture(autouse=True)
def _racine_temporaire(tmp_path, monkeypatch):
    """`libelles_inconnus.garder` écrit sous `pc.RACINE` : jamais dans le vrai dépôt (docs/essais/ocr/libelles_inconnus)."""
    monkeypatch.setattr(pc, "RACINE", tmp_path)
FORUM = "forum.netmarble.com\nOFFICIAL CHANNELS\nEnter Redeem Code\nNotices\nNew SSR Hunter & Exclusive Weapon Added\n11/19 Update Content Preview"
BATALHA = "Categoria de Batalha\nPoder Total 3,301,661\nHabilidade de Luta Max. 14,016,128\nPoder Total 2,462,079\nPoder Total 2,457,762"
T_LKN = "🚨 SOLO LEVELING ARISE BEYOND – IMPORTANT LAST UPDATE! 🔥 NEW SSR WEAPONS, THALIA & GUILD BOSS UPDATE!"
T_TJN = "RESUMO DA ATUALIZAÇÃO! Buffs, Novos Recursos, Banners e Códigos Grátis | Solo Leveling: ARISE"
T_LO3 = "THALIA VAI QUEBRAR O META? Resumo da Live + Armas do Kamish e Novos codes | Solo Leveling: Arise"


def video(vid, titre, duree="PT8M42S", modes=("gb",)):
    return {**meta(vid, modes, titre), "duration": duree}


def lecture(vid, score, source="titre"):
    return {"video_id": vid, "mode": "gb", "score": score, "score_source": source, "detail": {}, "notes": []}


def test_marquage_titre_sans_score_seulement():
    marque = lambda titre, lectures=(): tri1.titre_hors_sujet_probable(video("v", titre), list(lectures), CONFIG)
    assert marque(T_LKN) and marque(T_TJN) and marque(T_LO3)
    assert not marque("Guild Boss Update 165 RC", [lecture("v", 165)])              # score dans le titre : pas marqué
    assert not marque("Guild Boss Update 165 RC", [lecture("v", 165, "sous-titres")])
    assert marque("Guild Boss Update", [lecture("v", None)])
    assert marque("Guild Boss Update", [lecture("autre", 165)])                       # le score d'une AUTRE vidéo ne compte pas
    assert not marque("Updated build") and not marque("lively stream")             # mot entier
    assert marque("무과금 업데이트 정리") and marque("アップデート情報") and marque("PATCH NOTES 11/19") and marque("Atualização da semana")
    e = {"status": "en_cours"}
    assert tri1.marquer_hors_sujet(e, video("v", T_TJN), [], CONFIG) and e["hors_sujet_probable"] and tri1.NOTE_HORS_SUJET in e["notes"]
    e["pc"] = {"ecran_jeu": True}                                                  # un écran de jeu vu : démarqué
    assert tri1.marquer_hors_sujet(e, video("v", T_TJN), [], CONFIG) and "hors_sujet_probable" not in e and "notes" not in e


def monde(tmp):
    d = Donnees(Path(tmp))
    vids = {"lKnkiCvMwSM": video("lKnkiCvMwSM", T_LKN), "TjnPwCk_VSc": video("TjnPwCk_VSc", T_TJN, "PT25M14S"),
            "Lo3sHrW18Vg": video("Lo3sHrW18Vg", T_LO3, "PT17M49S"), "normale": video("normale", "Eden GB run"),
            "longue": video("longue", "Stream guild boss", "PT3H"), "longue_score": video("longue_score", "Stream 165 RC", "PT3H")}
    d.ecrire(f"runs/{SEM}/_videos.json", vids)
    d.ecrire(f"runs/{SEM}/_lectures.json", [lecture("longue_score", 165)])
    proc = {v: {"week": SEM, "channel_id": "UC" + v, "published_at": "2026-11-14T10:00:00Z", "status": "en_cours", "pc_needed": True,
                "modes": ["gb"]} for v in vids}
    d.ecrire("processed.json", proc)
    return d, vids, proc


def test_ordre_pc_hors_sujet_en_dernier_et_hors_top10():
    with tempfile.TemporaryDirectory() as tmp:
        d, vids, proc = monde(tmp)
        tri1.marquer_hors_sujet_semaine(proc, vids, d.lectures(SEM), SEM, CONFIG)
        assert {v for v, p in proc.items() if p.get("hors_sujet_probable")} == {"lKnkiCvMwSM", "TjnPwCk_VSc", "Lo3sHrW18Vg"}
        ids = ["lKnkiCvMwSM", "TjnPwCk_VSc", "longue", "Lo3sHrW18Vg", "longue_score", "normale"]
        ordre, cand = ordre_pc.ordonner(d, SEM, ids, proc)
        assert ordre[:2] == ["longue_score", "normale"] and set(ordre[2:]) == {"lKnkiCvMwSM", "TjnPwCk_VSc", "longue", "Lo3sHrW18Vg"}
        assert cand == {"longue_score", "normale"}                                  # ni hors sujet ni longue sans score
        assert ordre_pc.candidates_restantes(d, SEM, proc) == 2                      # « Top 10 couvert » (et gel n° 3) ne les comptent pas
        proc["normale"]["status"] = proc["longue_score"]["status"] = "termine"
        assert ordre_pc.candidates_restantes(d, SEM, proc) == 0 and "Top 10 couvert : oui" in ordre_pc.ligne_top10(0)
        proc["TjnPwCk_VSc"]["pc"] = {"ecran_jeu": True}                              # écran vu : redevient candidate
        assert ordre_pc.candidates_restantes(d, SEM, proc) == 1


def test_ecran_de_jeu_et_pages_web():
    assert ocr_ecrans.page_web(FORUM) and not ocr_ecrans.ecran_de_jeu(FORUM, CONFIG)
    assert ocr_ecrans.ecran_de_jeu(GB_RESULTS, CONFIG) and ocr_ecrans.ecran_de_jeu(HUD_228, CONFIG)
    assert ocr_ecrans.ecran_de_jeu("FormTeam\nPlayer Mode", CONFIG)                    # composition
    assert not ocr_ecrans.ecran_de_jeu("", CONFIG) and not ocr_ecrans.ecran_de_jeu("My Page https://forum.netmarble.com", CONFIG)


def test_libelles_inconnus_jamais_une_page_web():
    assert not libelles_inconnus.ressemble_score(FORUM + "\n12,345,678,901\n12,345,678,902\n12,345,678,903")
    assert not libelles_inconnus.a_garder(FORUM + "\n00:21.042", None, [])
    assert libelles_inconnus.ressemble_score("12,345,678,901\n12,345,678,902\n12,345,678,903")


def lancer_tri3(vid, titre, textes, duree="PT8M42S"):
    o = OutilsImages({vid: textes})
    etat = {}
    lect, avert, reporte = pc.traiter_images(vid, video(vid, titre, duree), o, CONFIG, [], etat, "2026-11-22")
    return o, etat, lect, avert, reporte


def test_tri3_actualites_rejetees_sans_tri4():
    ecrans = {t: FORUM for t in list(range(0, 10, 2)) + list(range(452, 522, 2))}
    for vid, titre, duree in (("lKnkiCvMwSM", T_LKN, "PT8M42S"), ("TjnPwCk_VSc", T_TJN, "PT25M14S"), ("Lo3sHrW18Vg", T_LO3, "PT17M49S")):
        o, etat, lect, avert, reporte = lancer_tri3(vid, titre, ecrans, duree)
        assert etat["rejet"] == "actualites" and etat["tri3"] == "fait" and etat["tri4"] == "inutile" and not reporte and lect == []
        assert not any(a[0] == "img" and a[2][0][2] == CONFIG["pc"]["images"]["tri4_pas_s"] for a in o.appels)      # aucun tri 4


def test_tri3_ecran_vu_traitement_normal_et_demarquage():
    o, etat, lect, avert, reporte = lancer_tri3("TjnPwCk_VSc", T_TJN, {0: FORUM, 2: HUD_228, 4: FORUM}, "PT25M14S")
    assert etat.get("ecran_jeu") is True and "rejet" not in etat
    e = {"status": "en_cours", "pc": etat}
    assert not tri1.marquer_hors_sujet(e, video("TjnPwCk_VSc", T_TJN), lect, CONFIG) or "hors_sujet_probable" not in e


def test_titre_avec_score_pas_de_decision_sur_l_image():
    lecs = [lecture("g", 165)]
    o = OutilsImages({"g": {t: FORUM for t in range(0, 10, 2)}})
    etat = {}
    pc.traiter_images("g", video("g", "Guild Boss Update 165 RC"), o, CONFIG, lecs, etat, "2026-11-22")
    assert "rejet" not in etat                                                     # score dans le titre : jamais rejetée sur l'image


def test_video_longue_sans_score_tri3_seul_ou_hors_limite():
    ecrans = {t: FORUM for t in range(0, 10, 2)}
    _, etat, _, _, _ = lancer_tri3("longue", "Stream guild boss", ecrans, "PT3H")
    assert etat["rejet"] == "actualites"
    o = OutilsImages({"longue": {2: HUD_228}})
    etat = {}
    _, avert, _ = pc.traiter_images("longue", video("longue", "Stream guild boss", "PT3H"), o, CONFIG, [], etat, "2026-11-22")
    assert etat["tri3"] == "fait" and etat["tri4"] == "inutile" and etat["ecran_jeu"] is True and "tri 4 non fait" in avert
    _, avert, _ = pc.traiter_images("tropl", video("tropl", "Stream", "PT9H"), OutilsImages({}), CONFIG, [], {}, "2026-11-22")
    assert "hors limite" in avert                                                  # au-delà de decision_max_minutes : comme avant


def test_rejeter_actualites_ecrit_rejected_et_processed():
    with tempfile.TemporaryDirectory() as tmp:
        d, vids, proc = monde(tmp)
        reste = pc.rejeter_actualites(d, SEM, "lKnkiCvMwSM", proc, [lecture("lKnkiCvMwSM", 5, "miniature"), lecture("normale", 3)], "2026-11-22")
        (r,) = d.rejected(SEM)
        assert r["video_id"] == "lKnkiCvMwSM" and r["reason"] == "actualites" and r["detail"] == "actualités : aucun écran de jeu" and r["last_tri"] == 3
        assert proc["lKnkiCvMwSM"]["status"] == "rejete" and not proc["lKnkiCvMwSM"]["pc_needed"] and [l["video_id"] for l in reste] == ["normale"]


def test_baruka_trois_phases_sans_a_verifier():
    doc = CONFIG["bot"]["phases_par_boss"]["_doc"]
    assert "À VÉRIFIER" not in doc and CONFIG["bot"]["phases_par_boss"]["baruka"] == 3


# ---- v37.1 : garde contre le rejet à tort
SCORE_INCONNU = "결과\n12,345,678,901\n12,345,678,902\n12,345,678,903"


def test_v371_classement_de_puissance_n_est_pas_un_ecran_de_jeu():
    assert not ocr_ecrans.ecran_de_jeu(BATALHA, CONFIG) and not libelles_inconnus.ressemble_score(BATALHA)
    assert ocr_ecrans.ecran_de_jeu("Total Power\nFormTeam", CONFIG)                      # fiche / composition : écran de jeu
    # TjnPwCk_VSc : seuls ces écrans de puissance au début et à la fin -> rejetée
    o, etat, lect, avert, reporte = lancer_tri3("TjnPwCk_VSc", T_TJN, {t: BATALHA for t in list(range(0, 10, 2)) + list(range(1480, 1520, 2))}, "PT25M14S")
    assert etat["rejet"] == "actualites" and etat["decision_tri3"]["video_min"] == 25.2 and "telechargement_s" in etat["decision_tri3"]


def test_v371_ecran_de_score_non_reconnu_pas_de_rejet_note_et_tri4():
    o, etat, lect, avert, reporte = lancer_tri3("uptd", "Guild Boss Update", {0: FORUM, 2: SCORE_INCONNU, 4: FORUM}, "PT8M")
    assert "rejet" not in etat and etat["ecran_score_non_reconnu"] is True and "ecran_jeu" not in etat
    assert etat["tri3"] == "fait" and etat.get("tri4") != "inutile"                         # passe au tri 4
    e = {"status": "en_cours", "pc": etat}
    tri1.marquer_hors_sujet(e, video("uptd", "Guild Boss Update"), lect, CONFIG)
    assert e["hors_sujet_probable"] is True and tri1.NOTE_ECRAN_SCORE in e["notes"] and tri1.NOTE_HORS_SUJET in e["notes"]
    # toujours en dernier dans l'ordre du PC
    with tempfile.TemporaryDirectory() as tmp:
        d, vids, proc = monde(tmp)
        proc["normale"]["status"] = "en_cours"
        proc["lKnkiCvMwSM"].update(e)
        assert ordre_pc.ordonner(d, SEM, ["lKnkiCvMwSM", "normale"], proc)[0] == ["normale", "lKnkiCvMwSM"]
    # le forum seul (page web) n'est jamais un écran de score : rejetée
    _, etat2, _, _, _ = lancer_tri3("uptd2", "Guild Boss Update", {0: FORUM, 2: FORUM + "\n12,345,678,901\n12,345,678,902\n12,345,678,903"}, "PT8M")
    assert etat2["rejet"] == "actualites"


def test_v371_video_longue_ecran_de_score_non_reconnu_tri3_seul():
    _, etat, _, avert, _ = lancer_tri3("longue", "Stream guild boss", {0: SCORE_INCONNU}, "PT3H")
    assert "rejet" not in etat and etat["ecran_score_non_reconnu"] and etat["tri4"] == "inutile" and "tri 4 non fait" in avert


def test_v371_entete_du_rapport_donne_la_duree_de_telechargement():
    l = pc.entete_etat(True, 1, 0, 0, [], decisions=[("TjnPwCk_VSc", {"video_min": 25.2, "telechargement_s": 130})])
    assert any("TjnPwCk_VSc 25.2 min → 130 s" in x for x in l)
