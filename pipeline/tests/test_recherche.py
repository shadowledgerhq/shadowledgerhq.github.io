import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semaine import bornes, dans_creneau, debut_semaine, id_semaine
from youtube import ApiYouTube, QuotaDepasse, recherche

U = timezone.utc


def test_semaine_hiver_ete():
    # Hiver : jeudi 01:00 Paris = jeudi 00:00Z.
    assert debut_semaine(datetime(2026, 11, 13, 10, tzinfo=U)) == datetime(2026, 11, 12, 0, tzinfo=U)
    assert id_semaine(datetime(2026, 11, 12, 0, 30, tzinfo=U)) == "2026-11-12"   # 01:30 Paris
    assert id_semaine(datetime(2026, 11, 11, 23, 59, tzinfo=U)) == "2026-11-05"  # 00:59 Paris
    # Été : jeudi 01:00 Paris = mercredi 23:00Z.
    assert debut_semaine(datetime(2026, 7, 3, tzinfo=U)) == datetime(2026, 7, 1, 23, 0, tzinfo=U)
    assert bornes("2026-11-12") == (datetime(2026, 11, 12, 0, tzinfo=U), datetime(2026, 11, 19, 0, tzinfo=U))
    # Semaine du passage à l'heure d'hiver (25/10/2026) : 7 jours + 1 h en UTC.
    d, f = bornes("2026-10-22")
    assert d == datetime(2026, 10, 21, 23, tzinfo=U) and f == datetime(2026, 10, 29, 0, tzinfo=U)
    assert dans_creneau(datetime(2026, 11, 13, 19, 5, tzinfo=U), "20:00", "23:59")
    assert not dans_creneau(datetime(2026, 11, 13, 18, 5, tzinfo=U), "20:00", "23:59")


CONFIG = {"quota_max_units": 400, "pages_max_par_requete": 2,
          "queries": {"poc": ["q1", "q2"], "bot": ["q3", "q4", "q5"]},
          "mode_keywords": {"hotm": ["hotm"]}}


def faux_http(url):
    p = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
    res = url.split("/v3/")[1].split("?")[0]
    if res == "playlistItems":
        return {"items": [
            {"contentDetails": {"videoId": "ch1", "videoPublishedAt": "2026-11-13T10:00:00Z"}},
            {"contentDetails": {"videoId": "old", "videoPublishedAt": "2026-11-01T10:00:00Z"}}],
            "nextPageToken": "x"}
    if res == "search":
        items = [{"id": {"videoId": v}, "snippet": {"publishedAt": "2026-11-13T09:00:00Z"}}
                 for v in ("v1", "live1", "rediff", "vu")]
        return {"items": items, "nextPageToken": "p2" if "pageToken" not in p else None}
    if res == "videos":
        out = []
        for v in p["id"].split(","):
            sn = {"channelId": "UC" + v, "channelTitle": v, "title": f"{v} HOTM",
                  "publishedAt": "2026-11-13T09:00:00Z", "liveBroadcastContent": "none"}
            it = {"id": v, "snippet": sn, "contentDetails": {"duration": "PT1M"}}
            if v == "live1":
                sn["liveBroadcastContent"] = "live"
            if v == "rediff":
                it["liveStreamingDetails"] = {"actualStartTime": "2026-11-13T08:00:00Z"}
            out.append(it)
        return {"items": out}
    raise AssertionError(res)


def test_recherche():
    api = ApiYouTube("cle", CONFIG["quota_max_units"], http=faux_http)
    debut, fin = bornes("2026-11-12")
    r = recherche(api, debut, fin, CONFIG, [{"channel_id": "UCc", "uploads_playlist": "UUc"}], {"vu"})
    assert set(r["videos"]) == {"ch1", "v1"}
    assert r["videos"]["v1"]["mode_guess"] == ["hotm", "poc"]
    assert [(x["meta"]["video_id"], x["reason"]) for x in r["rejets"]] == [("rediff", "live")]
    # Plafond 400 - réserve 100 : 2 pages de recherche (1 + 200 + 100 > 300) ; la suite s'arrête, les détails passent.
    assert r["arret_quota"] and api.units == 1 + 200 + 1


def test_plafond():
    api = ApiYouTube("cle", 1, http=faux_http)
    api.appel("videos", id="a")
    try:
        api.appel("videos", id="b")
        assert False
    except QuotaDepasse:
        pass


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_"):
            f()
    print("OK")
