"""Results POC coréen (Pj6QzXQ81jQ) : reconnu comme écran de palier POC, jamais comme Results GB."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ocr_ecrans

TEXTE = """RESULT 재앙의 권좌 19단계 2팀 진행 시간 02:00 플레이어 기여도 7,312,091,136,981 계승자 기여도 헌터 기여도
총 기여도 15,492,044,402,685 신기록 달성! 랭킹 점수 18,354,520 달성률 35.45% 다시하기 1팀 도전 나가기"""


def test_poc_coreen_pas_gb():
    assert ocr_ecrans.detecter(TEXTE) == "poc_palier"


if __name__ == "__main__":
    test_poc_coreen_pas_gb(); print("OK")
