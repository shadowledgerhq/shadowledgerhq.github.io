"""SPEC_ETAPE1 v46 (écran coréen) : lecture par ancres de Pj6QzXQ81jQ_170 (1280×720) avec un faux OCR calé sur les positions de la capture,
contrôle (d) reste + Goal Progress = 100 %, détection tolérante (espaces, 총/충, 여/어). tesseract kor réel : à confirmer sur le PC."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import poc_palier
import ocr_ecrans

# (texte, x, y, largeur, hauteur) de la capture Pj6QzXQ81jQ_170.jpg
VALEURS = [("재앙의 권좌 19단계 1팀", 52, 86, 190, 20), ("6,825,874,526,264", 214, 182, 120, 16), ("1,737,769,011,489", 210, 278, 120, 16),
           ("1,977,042,172,398", 208, 378, 120, 16), ("1,925,229,149,652", 208, 430, 120, 16), ("805,532,671,254", 214, 485, 110, 16),
           ("13,271,447,531,057", 58, 614, 240, 32), ("18,163,097", 433, 560, 140, 32), ("16.30%", 685, 560, 100, 32),
           ("16.30%", 517, 648, 45, 18), ("0.00%", 712, 648, 45, 18), ("83.70%", 862, 648, 50, 18)]
MOTS = [("플레이어", 52, 131, 62, 18), ("기여도", 118, 131, 40, 18), ("계승자", 52, 228, 48, 18), ("기여도", 105, 228, 40, 18),
        ("헌터", 52, 326, 34, 18), ("기여도", 90, 326, 40, 18), ("총", 52, 577, 14, 18), ("기여도", 70, 577, 40, 18),
        ("랭킹", 426, 523, 40, 16), ("점수", 470, 523, 30, 16), ("달성률", 677, 523, 46, 16), ("1팀", 481, 648, 30, 18), ("2팀", 674, 648, 30, 18),
        ("2팀", 1067, 678, 30, 18), ("도전", 1100, 678, 30, 18), ("다시하기", 966, 678, 55, 18), ("진행", 1124, 44, 30, 16), ("시간", 1158, 44, 30, 16)]


class Faux:
    def __init__(self, valeurs=VALEURS, mots=MOTS):
        self.valeurs, self.mots, self.langues = valeurs, mots, []

    def dimensions(self, png):
        return (1280, 720)

    def boites(self, png, langues="eng", timeout=90):
        return list(self.mots) if "kor" in langues else []       # le tesseract anglais ne lit pas le coréen

    def recadrer_px(self, png, x, y, largeur, hauteur, echelle=3, seuil=None, normaliser=False):
        return f"zone:{x}:{y}:{largeur}:{hauteur}"

    def ocr(self, petit, langues=None, psm=6, timeout=120, extra=None):
        self.langues.append(langues)
        _, x, y, w, h = petit.split(":")
        x, y, w, h = float(x), float(y), float(w), float(h)
        return "\n".join(t for t, vx, vy, vw, vh in self.valeurs if x <= vx + vw / 2 <= x + w and y <= vy + vh / 2 <= y + h)


def test_lecture_coreen_complete():
    e = poc_palier.lire(Faux(), "x.png")
    assert (e["tier"], e["team"]) == (19, 1)
    assert e["rank_score"] == 18_163_097 and e["goal_progress"] == 16.30 and e["team_pct"] == [16.30, 0.0]
    assert e["total_contribution"] == 13_271_447_531_057 and e["player"] == 6_825_874_526_264 and e["successor"] == 1_737_769_011_489
    assert e["hunters"] == [1_977_042_172_398, 1_925_229_149_652, 805_532_671_254] and e["reste"] == 83.70
    ok, notes = poc_palier.controles(e)
    assert ok, notes


def test_langue_ocr_coreen():
    f = Faux()
    poc_palier.lire(f, "x.png")
    assert set(f.langues) == {"kor+eng"}


def test_controle_d():
    e = poc_palier.lire(Faux(), "x.png")
    ok, _ = poc_palier.controles({**e, "reste": 80.0})
    assert not ok and any("d : reste" in n for n in poc_palier.controles({**e, "reste": 80.0})[1])
    assert poc_palier.controles({**e, "reste": None})[0]          # reste non lu : pas de contrôle (d)
    assert poc_palier.controles({**e, "reste": 83.74})[0]         # ± 0,05


def test_detection_tolerante():
    assert poc_palier.detecter("충 기 어 도 18,163,097 플레이어 기 여 도")
    assert poc_palier.detecter("랭 킹 점수 달 성 률")
    assert ocr_ecrans.detecter("RESULT 재 앙 의 권 좌 19단계 1팀 다 시 하기 2 팀 도전 나가기") == "poc_palier"
    assert not poc_palier.detecter("다시하기 나가기 진행 시간 02:00")


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("OK")
