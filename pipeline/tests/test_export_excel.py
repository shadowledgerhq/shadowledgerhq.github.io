"""Export Excel (SPEC §5.6, v21) : formats BOT/POC/GB, détail des runs, dégâts, séparation « À vérifier », Top 10, page de garde, Rejetées."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_excel as ex


def run(mode, joueur, total, unite, confiance="sur", rang=None, **kw):
    r = {"mode": mode, "player": joueur, "score": {"total": total, "runs": kw.pop("runs", [total]), "unit": unite}, "confidence": confiance,
         "rank": rang, "video_id": "v_" + joueur, "video_ids": kw.pop("video_ids", ["v_" + joueur]), "published_at": "2026-11-13T11:14:16+01:00",
         "notes": kw.pop("notes", "")}
    r.update(kw)
    return r


def test_formats():
    assert ex.temps(19.926) == "00:19.926" and ex.temps(19.0) == "00:19.000" and ex.temps(125.5) == "02:05.500"
    assert ex.entier(131449789393717) == "131 449 789 393 717" and ex.arrondi(7.9e12) == "7,90 T"
    assert ex.notes_propres("a; boss non contrôlé; b") == "a; b"
    poc = run("poc", "P", 3, "damage", runs=[2, 1], runs_detail=[{"team": 1}, {"team": 2}])
    assert ex.detail_runs(poc) == "Éq. 1 : 2 · Éq. 2 : 1"
    gb = run("gb", "G", 156, "rage_count", runs_detail=[{"team": None, "damage": 7907273299084, "damage_exact": True}])
    assert ex.detail_runs(gb) == "G? : 156" and ex.degats_gb(gb) == (7907273299084, True)
    gb2 = run("gb", "H", 332, "rage_count", runs=[167, 165], runs_detail=[{"team": 1, "damage": 17.28e12, "damage_exact": False}, {"team": 2, "damage": 15.55e12, "damage_exact": True}])
    assert ex.detail_runs(gb2) == "G1 : 167 · G2 : 165" and ex.degats_gb(gb2)[1] is False
    assert ex.detail_runs(run("bot", "B", 19.9, "seconds")) == ""
    assert ex.joueur(run("bot", "B", 19.9, "seconds", player_ingame="Pseudo")) == "B (Pseudo)" and ex.joueur(run("poc", "B", 1, "damage", player_ingame="x")) == "B"


def test_ordre_et_lignes():
    bot = [run("bot", n, t, "seconds", "a_verifier") for n, t in (("A", 29.0), ("B", 19.9), ("C", 23.2))]
    assert [l["Joueur"] for l in ex.lignes_mode(bot, "bot")] == ["B", "C", "A"]
    gb = [run("gb", n, t, "rage_count", "a_verifier") for n, t in (("A", 165), ("B", 189))]
    mixte = bot + [run("bot", "Z", 99.0, "seconds", rang=1)]
    assert ex.lignes_mode(mixte, "bot")[0]["Joueur"] == "Z" and [l["Joueur"] for l in ex.lignes_mode(gb, "gb")] == ["B", "A"]
    deux = [run("gb", "A", 10, "rage_count", "a_verifier", video_ids=["x", "y"])]
    assert ex.colonnes_mode("gb", 2) == ["Rang", "Joueur", "Score", "Détail des runs", "Dégâts", "Statut", "Publiée (Paris)", "Vidéo", "Vidéo 2", "Notes"]
    assert ex.lignes_mode(deux, "gb")[0]["Vidéo 2"].endswith("/watch?v=y") and ex.lignes_mode(deux, "gb", gele=True)[0]["Statut"] == "Non vérifié"


def test_fichier():
    try:
        import openpyxl
    except ImportError:
        return
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "data" / "runs" / "2026-11-12"
        d.mkdir(parents=True)
        poc = [run("poc", f"J{i}", (20 - i) * 10**12, "damage", rang=i + 1, runs=[(20 - i) * 10**12]) for i in range(12)] + [run("poc", "Prov", 5 * 10**12, "damage", "a_verifier")]
        (d / "poc.json").write_text(json.dumps(poc), encoding="utf-8")
        (d / "bot.json").write_text(json.dumps([run("bot", "B", 19.926, "seconds", "a_verifier", player_ingame="Pseudo", notes="x; boss non contrôlé")]), encoding="utf-8")
        (d / "hotm-gate-inconnue.json").write_text(json.dumps([run("hotm", "H", 5, "points")]), encoding="utf-8")
        (d / "_meta.json").write_text(json.dumps({"week": "2026-11-12", "frozen": False}), encoding="utf-8")
        r = Path(tmp) / "data" / "rejected"
        r.mkdir()
        (r / "2026-11-12.json").write_text(json.dumps([{"video_id": "abc", "channel_id": "UC1", "title": "Titre", "reason": "live", "detail": "d"}]), encoding="utf-8")
        wb = openpyxl.load_workbook(ex.exporter("2026-11-12", racine=tmp))
        assert wb.sheetnames == ["Shadow Ledger", "POC", "BOT", "GB", "HOTM", "Rejetées"]
        poc_ws = wb["POC"]
        assert poc_ws["D6"].value == 20 * 10**12 and poc_ws["D6"].number_format == "#,##0" and poc_ws["E6"].value.startswith("Éq. ?")      # entier complet
        valeurs = [poc_ws.cell(k, 2).value for k in range(6, 22)]
        assert "À vérifier" in valeurs and valeurs.index("À vérifier") == 12                    # séparation après les 12 classés
        assert poc_ws["B6"].fill.fgColor.rgb.endswith(ex.TOP10) and not poc_ws["B16"].fill.fgColor.rgb.endswith(ex.TOP10)   # Top 10 marqué (10 lignes)
        bot_ws = wb["BOT"]
        assert bot_ws["C7"].value == "B (Pseudo)" and bot_ws["D7"].number_format == "mm:ss.000" and "boss non contrôlé" not in bot_ws["I7"].value
        assert wb["HOTM"]["B7"].value.startswith("Aucune run") and wb["Rejetées"]["B6"].value == "Titre" and wb["Rejetées"]["B6"].hyperlink.target.endswith("abc")
        garde = [str(c.value) for row in wb["Shadow Ledger"].iter_rows() for c in row if c.value]
        assert any("ESSAI — non publié" in t for t in garde) and any("Provisoire" in t for t in garde) and any(ex.CREDIT == t for t in garde)
        assert any(t.startswith("BOT : ") for t in garde)


if __name__ == "__main__":
    test_formats()
    test_ordre_et_lignes()
    test_fichier()
    print("ok")
