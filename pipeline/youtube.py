"""Recherche YouTube de l'étape 1 (docs/SPEC_ETAPE1.md §1). Bibliothèque standard uniquement.

La clé API vient de la variable d'environnement YOUTUBE_API_KEY (secret GitHub), jamais du code.
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request

from semaine import iso_utc, parse_iso

URL = "https://www.googleapis.com/youtube/v3/"
COUTS = {"search": 100, "playlistItems": 1, "videos": 1, "channels": 1}
RESERVE_DETAILS = 100  # unités gardées pour playlists et détails quand les recherches s'arrêtent


class QuotaDepasse(Exception):
    pass


class ApiYouTube:
    def __init__(self, cle, max_units, http=None):
        self.cle, self.max_units, self.units = cle, max_units, 0
        self._http = http or self._http_reel

    @staticmethod
    def _http_reel(url):
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def appel(self, ressource, limite=None, **params):
        cout = COUTS[ressource]
        if self.units + cout > (limite if limite is not None else self.max_units):
            raise QuotaDepasse(f"plafond du passage atteint ({self.units} unités)")
        params = {k: v for k, v in params.items() if v is not None}
        url = URL + ressource + "?" + urllib.parse.urlencode({**params, "key": self.cle})
        self.units += cout
        try:
            return self._http(url)
        except urllib.error.HTTPError as e:
            corps = e.read().decode("utf-8", "replace")
            if "quotaExceeded" in corps or "dailyLimitExceeded" in corps:
                raise QuotaDepasse("quotaExceeded (API)") from None
            raise RuntimeError(f"API {ressource} HTTP {e.code}: {corps[:200]}") from None


def deviner_modes(texte, config):
    """Indices de mode d'après les mots-clés de config.mode_keywords."""
    texte = (texte or "").lower()
    modes = set()
    sans_chiffre = set(config.get("mode_keywords", {}).get("_sans_chiffre", []))  # v7 : « gb » jamais après un chiffre
    for mode, mots in config.get("mode_keywords", {}).items():
        if mode.startswith("_"):
            continue
        for mot in mots:
            # v3 : mot-clé latin = mot entier (« bot » n'est pas dans « robot »), même collé à du CJK
            motif = rf"(?<![a-z0-9]){re.escape(mot)}(?![a-z0-9])" if mot.isascii() else re.escape(mot)
            if mot in sans_chiffre:  # exclut 12GB, 128 GB, 8\u00a0GB (gigaoctets)
                motif = r"(?<!\d)(?<!\d )(?<!\d\u00a0)(?<!\d\u202f)" + motif
            if re.search(motif, texte):
                modes.add(mode)
                break
    return modes


def _miniature(snippet):
    t = snippet.get("thumbnails", {})
    for cle in ("maxres", "high", "medium", "default"):
        if cle in t:
            return t[cle]["url"]
    return None


def recherche(api, debut, fin, config, channels, deja_vus):
    """Retourne {"videos": {id: meta}, "rejets": [...], "arret_quota": str|None, "erreurs": [...]}.
    `deja_vus` : ids présents dans processed.json ou rejected (jamais réanalysés)."""
    trouves, erreurs, arret = {}, [], None

    # 1. Chaînes suivies : playlist d'uploads.
    for ch in channels:
        jeton = None
        try:
            while True:
                r = api.appel("playlistItems", part="snippet,contentDetails",
                              playlistId=ch["uploads_playlist"], maxResults=50, pageToken=jeton)
                dernier = None
                for it in r.get("items", []):
                    pub = it.get("contentDetails", {}).get("videoPublishedAt")
                    if not pub:
                        continue  # vidéo privée ou supprimée
                    dernier = parse_iso(pub)
                    if debut <= dernier < fin:
                        trouves.setdefault(it["contentDetails"]["videoId"], set())
                jeton = r.get("nextPageToken")
                if not jeton or dernier is None or dernier < debut:
                    break
        except QuotaDepasse as e:
            arret = str(e)
            break
        except Exception as e:  # une chaîne en erreur n'arrête pas le passage
            erreurs.append(f"chaîne {ch.get('channel_id')} : {e}")

    # 2. Recherche par requêtes.
    limite_recherche = config["quota_max_units"] - RESERVE_DETAILS
    for mode, requetes in config["queries"].items():
        if arret:
            break
        for q in requetes:
            jeton = None
            try:
                for _ in range(config.get("pages_max_par_requete", 2)):
                    r = api.appel("search", limite=limite_recherche, part="snippet", type="video",
                                  order="date", publishedAfter=iso_utc(debut),
                                  publishedBefore=iso_utc(fin), maxResults=50, q=q,
                                  pageToken=jeton)
                    items = r.get("items", [])
                    for it in items:
                        trouves.setdefault(it["id"]["videoId"], set()).add(mode)
                    jeton = r.get("nextPageToken")
                    if not jeton or not items or parse_iso(items[-1]["snippet"]["publishedAt"]) < debut:
                        break
            except QuotaDepasse as e:
                arret = str(e)
                break
            except Exception as e:
                erreurs.append(f"requête « {q} » : {e}")

    # 3. Détails des vidéos nouvelles.
    nouveaux = [v for v in trouves if v not in deja_vus]
    videos, rejets = {}, []
    for i in range(0, len(nouveaux), 50):
        lot = nouveaux[i:i + 50]
        try:
            r = api.appel("videos", part="snippet,contentDetails,liveStreamingDetails",
                          id=",".join(lot), maxResults=50)
        except Exception as e:
            erreurs.append(f"détails ({len(lot)} vidéos) : {e}")
            if isinstance(e, QuotaDepasse):
                arret = arret or str(e)
                break
            continue
        for it in r.get("items", []):
            sn = it["snippet"]
            vid = it["id"]
            if sn.get("liveBroadcastContent", "none") != "none":
                continue  # live en cours ou à venir : revu au prochain passage
            modes = trouves[vid] | deviner_modes(sn.get("title", "") + "\n" + sn.get("description", ""), config)
            meta = {
                "video_id": vid,
                "channel_id": sn["channelId"],
                "channel_title": sn.get("channelTitle", ""),
                "title": sn.get("title", ""),
                "description": sn.get("description", ""),
                "published_at": sn["publishedAt"],
                "lang": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage"),
                "duration": it.get("contentDetails", {}).get("duration"),
                "thumbnail": _miniature(sn),
                "mode_guess": sorted(modes),
            }
            pub = parse_iso(sn["publishedAt"])
            raison = None
            if it.get("liveStreamingDetails", {}).get("actualStartTime"):
                raison = "live"
            elif not (debut <= pub < fin):
                raison = "hors_fenetre"
            if raison:
                rejets.append({"meta": meta, "reason": raison, "detail": ""})
            else:
                videos[vid] = meta
    return {"videos": videos, "rejets": rejets, "arret_quota": arret, "erreurs": erreurs}
