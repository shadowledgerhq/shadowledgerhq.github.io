"""Export Excel (brouillon) : lecture des classements, onglets, lignes non sûres en gris."""
import sys, tempfile, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import export_excel


def test_lignes_et_fichier():
    runs = [{"rank": None, "player": "B", "score": {"total": 5, "runs": [5], "unit": "rage_count"}, "confidence": "a_verifier", "video_id": "v2", "notes": "x"},
            {"rank": 1, "player": "A", "score": {"total": 332, "runs": [167, 165], "unit": "rage_count"}, "confidence": "sur", "video_id": "v1",
             "published_at": "2026-11-13T11:14:16+01:00", "score_source": "record", "notes": ""}]
    lignes = export_excel.lignes_mode(runs)
    assert [l[1] for l in lignes] == ["A", "B"] and lignes[0][3] == "167 + 165" and lignes[1][3] == "" and lignes[0][6].endswith("v1") and lignes[0][5] == "2026-11-13 11:14"
    try:
        import openpyxl
    except ImportError:
        return
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "data" / "runs" / "2026-11-12"
        d.mkdir(parents=True)
        (d / "gb.json").write_text(json.dumps(runs), encoding="utf-8")
        f = export_excel.exporter("2026-11-12", racine=tmp)
        wb = openpyxl.load_workbook(f)
        assert wb.sheetnames[0] == "Shadow Ledger" and {"POC", "BOT", "GB", "HOTM"} <= set(wb.sheetnames)       # HOTM : onglet vide s'il n'y a rien
        assert wb["GB"]["C6"].value == "A" and wb["GB"]["B6"].value.endswith("1") and wb["HOTM"]["B7"].value.startswith("Aucune donnée")


def test_ordre_des_lignes_non_classees():
    bot = [{"player": n, "score": {"total": t, "runs": [t], "unit": "seconds"}, "confidence": "a_verifier"} for n, t in (("A", 29.0), ("B", 19.9), ("C", 23.2))]
    assert [l[1] for l in export_excel.lignes_mode(bot)] == ["B", "C", "A"]                # BOT : temps le plus court d'abord
    gb = [{"player": n, "score": {"total": t, "runs": [t], "unit": "rage_count"}, "confidence": "a_verifier"} for n, t in (("A", 165), ("B", 189))]
    assert [l[1] for l in export_excel.lignes_mode(gb)] == ["B", "A"]                       # GB : Rage Count le plus haut d'abord
    mixte = bot + [{"player": "Z", "rank": 1, "score": {"total": 99.0, "runs": [99.0], "unit": "seconds"}, "confidence": "sur"}]
    assert export_excel.lignes_mode(mixte)[0][1] == "Z"                                      # un classé passe toujours devant


if __name__ == "__main__":
    test_lignes_et_fichier()
    test_ordre_des_lignes_non_classees()
    print("ok")
