"""28/11 : HOTM arrêté (décision d'Alexis) : aucune requête, vidéos HOTM seules rejetées `mode_arrete`, pas de classement ni d'onglet."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import youtube
from donnees import charger_config

CFG = charger_config()


def test_config_sans_hotm():
    assert "hotm" not in CFG["modes_actifs"] and "hotm" not in CFG["modes_classement"]
    assert youtube.modes_actifs(CFG) == {"poc", "bot", "gb"}


def test_filtrer_modes():
    assert youtube.filtrer_modes_actifs({"hotm"}, CFG) == (set(), True)                       # HOTM seul : rejet
    assert youtube.filtrer_modes_actifs({"hotm", "gb"}, CFG) == ({"gb"}, False)                # mélange : HOTM retiré, vidéo gardée
    assert youtube.filtrer_modes_actifs(set(), CFG) == (set(), False)                          # aucun indice : comme avant
    assert youtube.filtrer_modes_actifs({"hotm"}, {"queries": {"hotm": [], "gb": []}}) == ({"hotm"}, False)   # sans la clé : tout actif (réactivation)


def test_requetes_hotm_non_lancees():
    from datetime import datetime, timezone
    qs = []

    class Api:
        def appel(self, ressource, **kw):
            if ressource == "search":
                qs.append(kw.get("q"))
            return {"items": []}
    d0, d1 = datetime(2026, 11, 26, tzinfo=timezone.utc), datetime(2026, 12, 3, tzinfo=timezone.utc)
    youtube.recherche(Api(), d0, d1, CFG, [], set())
    assert qs and not any(("monarchs" in q.lower() or "hotm" in q.lower()) for q in qs)


if __name__ == "__main__":
    test_config_sans_hotm(); test_filtrer_modes(); test_requetes_hotm_non_lancees(); print("OK")
