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
    assert [l[1] for l in lignes] == ["A", "B"] and lignes[0][3] == "167 + 165" and lignes[0][6].endswith("v1") and lignes[0][5] == "2026-11-13 11:14"
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
        assert wb["GB"]["B6"].value == "A" and wb["GB"]["A6"].value.endswith("1") and wb["HOTM"]["A7"].value.startswith("Aucune donnée")


if __name__ == "__main__":
    test_lignes_et_fichier()
    print("ok")
