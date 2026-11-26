"""Rendu d'une vidéo Shadow Ledger (schémas seulement, sans voix) à partir de video.json.

Usage : python rendu_video.py <video.json> <racine_depot> <fr|en> <sortie.mp4> [--images dossier] [--vertical]
Gabarit : docs/GABARIT_VIDEO.md. Aucune image de tiers : tout est dessiné.
"""
import io, json, os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 30
VERT = False  # format vertical 1080 × 1920 (TikTok, Shorts, Reels) : zone sûre = rien dans les 20 % du bas ni le bord droit
BG = (11, 13, 23); PANEL = (22, 24, 40); LINE = (48, 50, 72)  # charte RESEAUX.md §1
TXT = (237, 235, 255); MUTED = (146, 146, 176); WARN = (248, 113, 113)
SJW = (124, 92, 255); HUN = (79, 209, 255); TAG = (245, 158, 11); OK = (74, 222, 128)
F_INTER = "/usr/share/fonts/opentype/inter/Inter-{}.otf"
F_CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-{}.ttc"
_cache = {}
_logo = {}


def logo_layers(svg, size):
    """Hexagone et « S » du logo, rendus séparément (fond transparent) avec rsvg-convert."""
    k = (svg, size)
    if k not in _logo:
        src = open(svg, encoding="utf-8").read()
        src = re.sub(r'<rect width="512" height="512"[^>]*/>', "", src)
        hexa = re.sub(r"<path[^>]*/>|<rect x=[^>]*/>", "", src)
        lettre = re.sub(r"<polygon[^>]*/>", "", src)
        out = []
        for part in (hexa, lettre):
            png = subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size)], input=part.encode(),
                                 capture_output=True, check=True).stdout
            out.append(Image.open(io.BytesIO(png)).convert("RGBA"))
        _logo[k] = out
    return _logo[k]



def font(size, weight="Regular", cjk=False):
    k = (size, weight, cjk)
    if k not in _cache:
        if cjk:
            _cache[k] = ImageFont.truetype(F_CJK.format("Bold" if weight in ("Bold", "SemiBold") else "Regular"), size, index=1)  # 1 = KR
        else:
            _cache[k] = ImageFont.truetype(F_INTER.format(weight), size)
    return _cache[k]


def has_cjk(s):
    return any(ord(c) > 0x2E80 for c in s)


def tf(s, size, weight="Regular"):
    """Police adaptée au texte (CJK si besoin)."""
    return font(size, weight, cjk=has_cjk(s))


def L(v, lang):
    return v.get(lang, v.get("fr", "")) if isinstance(v, dict) else v


def wrap(d, text, f, maxw):
    lines, cur = [], ""
    for w in text.split(" "):
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------- éléments communs ----------
def base(video, scene, lang, t):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    # bandeau essai
    b = L(video["badge"], lang)
    f = font(22, "SemiBold")
    tw = d.textlength(b, font=f)
    bx = 60 if VERT else W - tw - 80
    by = 100 if VERT else 36
    d.rounded_rectangle((bx, by, bx + tw + 40, by + 44), 10, outline=WARN, width=2)
    d.text((bx + 20, by + 9), b, font=f, fill=WARN)
    d.text((60, 44), "SHADOW LEDGER", font=font(24, "Bold"), fill=MUTED)
    if scene["type"] not in ("intro", "titre", "outro"):
        title = L(scene["title"], lang)
        if VERT:
            ft = tf(title, 52, "Bold")
            for i, ln in enumerate(wrap(d, title, ft, W - 200)):
                d.text((60, 180 + 64 * i), ln, font=ft, fill=TXT)
        else:
            d.text((60, 110), title, font=tf(title, 56, "Bold"), fill=TXT)
    # sources (vertical : sous le titre, hors de la zone du bas)
    if scene.get("sources") and VERT:
        s = ("Sources : " if lang == "fr" else "Sources: ") + " · ".join(scene["sources"])
        for i, ln in enumerate(wrap(d, s, font(18), W - 200)[:2]):
            d.text((60, 330 + 24 * i), ln, font=font(18), fill=MUTED)
    elif scene.get("sources"):
        s = ("Sources : " if lang == "fr" else "Sources: ") + " · ".join(scene["sources"])
        d.text((60, H - 205), s, font=font(18), fill=MUTED)
    # narration (sous-titres, en attendant la voix)
    cur = None
    for seg in scene.get("narration", []):
        if t >= seg["t"]:
            cur = seg
    if cur:
        txt = L(cur, lang)
        f = tf(txt, 36, "Regular")
        maxw = W - 260 if VERT else W - 240
        lines = wrap(d, txt, f, maxw)
        bas = int(H * 0.8) - 30 if VERT else H - 12
        y0 = bas - 48 * len(lines)
        d.rectangle((0, y0 - 24, W, bas + 18 if VERT else H), fill=(6, 8, 12))
        cx = (W - 100) / 2 if VERT else W / 2
        for i, ln in enumerate(lines):
            lw = d.textlength(ln, font=f)
            d.text((cx - lw / 2, y0 + 48 * i), ln, font=f, fill=TXT)
    return im, d


def tag_estime(d, x, y, lang):
    s = "ESTIMATION" if lang == "fr" else "ESTIMATE"
    f = font(18, "Bold"); w = d.textlength(s, font=f)
    d.rounded_rectangle((x, y, x + w + 20, y + 30), 6, fill=(60, 45, 10))
    d.text((x + 10, y + 4), s, font=f, fill=TAG)


# ---------- types de scènes ----------
def s_intro(video, sc, lang, t, ctx):
    """Intro 2 s : hexagone qui se trace (0-0,6 s), « S » (0,6-1,2 s), nom + bandeau du mode (1,2-2 s)."""
    im = Image.new("RGB", (W, H), BG)
    hexa, lettre = logo_layers(video["logo"], 420)
    cx, cy = W // 2 - 210, (560 if VERT else 170)
    a = ease(t / 0.6)
    mask = Image.new("L", hexa.size, 0)
    ImageDraw.Draw(mask).pieslice((-200, -200, 620, 620), -90, -90 + 360 * a, fill=255)
    hm = hexa.copy(); hm.putalpha(Image.composite(hexa.getchannel("A"), mask, mask))
    im.paste(hm, (cx, cy), hm)
    b = ease((t - 0.6) / 0.4)
    if b > 0:
        lm = lettre.copy(); lm.putalpha(lettre.getchannel("A").point(lambda v: int(v * b)))
        im.paste(lm, (cx, cy + int(20 * (1 - b))), lm)
    d = ImageDraw.Draw(im)
    c = ease((t - 1.2) / 0.4)
    if c > 0:
        col = lambda rgb: tuple(int(v * c + BG[i] * (1 - c)) for i, v in enumerate(rgb))
        f = font(84, "Bold"); s = "SHADOW LEDGER"; w = d.textlength(s, font=f)
        d.text(((W - w) / 2, cy + 470), s, font=f, fill=col(TXT))
        s = L(sc["subtitle"], lang); f = font(36, "SemiBold"); w = d.textlength(s, font=f)
        d.rounded_rectangle(((W - w) / 2 - 24, cy + 600, (W + w) / 2 + 24, cy + 660), 10, fill=col(SJW))
        d.text(((W - w) / 2, cy + 608), s, font=f, fill=col(TXT))
    return im


def s_titre(video, sc, lang, t, ctx):
    im, d = base(video, sc, lang, t)
    for txt, y, size, col in ((L(sc["title"], lang), 360, 80, TXT), (L(sc["subtitle"], lang), 470, 44, MUTED)):
        f = font(size, "SemiBold"); w = d.textlength(txt, font=f)
        d.text(((W - w) / 2, y), txt, font=f, fill=col)
    return im


def s_outro(video, sc, lang, t, ctx):
    """Outro 5 s (RESEAUX.md §4) : support de l'écran de fin YouTube."""
    im, d = base(video, sc, lang, t)
    hexa, lettre = logo_layers(video["logo"], 380)
    if VERT:  # 3 s, texte en haut (zone sûre), pas d'écran de fin YouTube
        for layer in (hexa, lettre):
            im.paste(layer, ((W - 380) // 2 - 50, 300), layer)
        y = 720
        for txt, size, col, wt in (("SHADOW LEDGER", 64, TXT, "Bold"), (L(sc["subtitle"], lang), 34, TXT, "SemiBold"), (L(sc["credits"], lang), 26, MUTED, "Regular")):
            f = tf(txt, size, wt)
            for ln in wrap(d, txt, f, W - 260):
                d.text(((W - 100 - d.textlength(ln, font=f)) / 2, y), ln, font=f, fill=col)
                y += int(size * 1.35)
            y += 30
        return im
    for layer in (hexa, lettre):
        im.paste(layer, (170, 200), layer)
    d.text((170, 600), "SHADOW LEDGER", font=font(56, "Bold"), fill=TXT)
    for k in range(2):  # emplacements vides pour l'écran de fin (vidéo suivante, abonnement)
        x = 900 + 480 * k
        d.rounded_rectangle((x, 230, x + 420, 466), 16, outline=LINE, width=3)
    s = L(sc["subtitle"], lang); f = font(36, "SemiBold"); w = d.textlength(s, font=f)
    d.text(((W - w) / 2, 730), s, font=f, fill=TXT)
    c = L(sc["credits"], lang); f = tf(c, 26); w = d.textlength(c, font=f)
    d.text(((W - w) / 2, 800), c, font=f, fill=MUTED)
    return im


def s_classement(video, sc, lang, t, ctx):
    im, d = base(video, sc, lang, t)
    x0, y0, rh = 160, 230, 92
    heads = ["#", "Joueur" if lang == "fr" else "Player", "Chrono" if lang == "fr" else "Time", "Origine" if lang == "fr" else "Source", ""]
    xs = [x0, x0 + 90, x0 + 640, x0 + 900, x0 + 1360]
    for x, h in zip(xs, heads):
        d.text((x, y0), h, font=font(26, "SemiBold"), fill=MUTED)
    for i, r in enumerate(sc["rows"]):
        a = ease((t - 0.4 - 0.35 * i) / 0.5)
        if a <= 0:
            continue
        y = y0 + 55 + rh * i + 20 * (1 - a)
        d.rounded_rectangle((x0 - 30, y - 12, W - 160, y + rh - 26), 12, fill=PANEL)
        d.text((xs[0], y), str(i + 1), font=font(40, "Bold"), fill=TXT)
        d.text((xs[1], y - 4), r["player"], font=tf(r["player"], 40, "Bold"), fill=TXT)
        d.text((xs[2], y), r["time"] + " s", font=font(40, "Bold"), fill=SJW)
        d.text((xs[3], y + 8), L(r["note"], lang), font=font(28), fill=MUTED)
        s = "à vérifier" if lang == "fr" else "to check"
        d.rounded_rectangle((xs[4], y + 2, xs[4] + 170, y + 46), 8, outline=WARN, width=2)
        d.text((xs[4] + 18, y + 8), s, font=font(26, "SemiBold"), fill=WARN)
    if t > 3:
        d.text((x0, y0 + 55 + rh * 5 + 10), L(sc["footnote"], lang), font=font(30, "SemiBold"), fill=OK)
    return im


def s_phases(video, sc, lang, t, ctx):
    im, d = base(video, sc, lang, t)
    x0, x1, vmax = 420, 1760, 20.0
    X = lambda v: x0 + (x1 - x0) * v / vmax
    cols = [(64, 54, 110), (98, 70, 170), (140, 110, 235)]
    for k in range(0, 21, 2):
        d.line((X(k), 260, X(k), 640), fill=LINE, width=1)
        d.text((X(k) - 10, 650), str(k), font=font(24), fill=MUTED)
    for i, r in enumerate(sc["rows"]):
        y = 300 + 170 * i
        d.text((80, y + 10), r["player"], font=tf(r["player"], 40, "Bold"), fill=TXT)
        d.text((80, y + 70), L(r["note"], lang), font=font(20), fill=MUTED)
        prev = 0.0
        grow = ease((t - 0.5 - 0.6 * i) / 1.5) * vmax
        for p, end in enumerate(r["phases"]):
            e = min(end, grow)
            if e > prev:
                d.rectangle((X(prev), y, X(e), y + 90), fill=cols[p])
                if e == end:
                    dur = f"{end - prev:.3f}".replace(".", "," if lang == "fr" else ".")
                    lab = ("Phase " if lang == "fr" else "Phase ") + f"{p + 1} · {dur} s"
                    d.text((X(prev) + 14, y + 28), lab, font=font(26, "SemiBold"), fill=TXT)
            prev = end
    if t > 5 and len(sc["rows"]) >= 2:
        a, b = sc["rows"]
        g = (b["phases"][1] - b["phases"][0]) - (a["phases"][1] - a["phases"][0])
        s = (f"Écart en phase 2 : {g:.3f} s".replace(".", ",") if lang == "fr" else f"Phase 2 gap: {g:.3f} s")
        d.text((X(a["phases"][0]), 700), s, font=font(34, "Bold"), fill=TAG)
    return im


def charger_events(root, row):
    """Événements d'une run avec t_game ; t_game manquant = interpolé sur t_run (estimé)."""
    data = json.load(open(os.path.join(root, row["file"]), encoding="utf-8"))
    ev = data["runs"][-1]["events"]
    known = [(e["t_run"], e["t_game"]) for e in ev if e.get("t_game") is not None]
    out = []
    for e in ev:
        tg, est = e.get("t_game"), False
        if tg is None and known:
            est = True
            before = [k for k in known if k[0] <= e["t_run"]]
            after = [k for k in known if k[0] >= e["t_run"]]
            if before and after and after[0][0] > before[-1][0]:
                (r0, g0), (r1, g1) = before[-1], after[0]
                tg = g0 + (g1 - g0) * (e["t_run"] - r0) / (r1 - r0)
            elif before:
                tg = before[-1][1] + (e["t_run"] - before[-1][0])
            else:
                tg = max(0.0, after[0][1] - (after[0][0] - e["t_run"]))
        if tg is None:
            continue
        kind = "sjw" if e["hunter"] == "sjw" else ("tag" if e["slot"] == "tag" else "hun")
        lab = {"sjw_skill_1": "S1", "sjw_skill_2": "S2", "sjw_ultimate": "ULT", "skill_1": "S1", "skill_2": "S2", "ultimate": "ULT", "core": "N", "tag": ""}.get(e["slot"], "")
        out.append({"tg": tg, "kind": kind, "lab": lab, "est": est})
    return out


def marker(d, x, y, kind, est, r=16):
    col = {"sjw": SJW, "hun": HUN, "tag": TAG}[kind]
    if kind == "sjw":
        pts = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
    elif kind == "tag":
        pts = [(x, y - r), (x + r, y + r * 0.8), (x - r, y + r * 0.8)]
    else:
        pts = None
    if pts:
        d.polygon(pts, fill=None if est else col, outline=col, width=3)
    else:
        d.ellipse((x - r, y - r, x + r, y + r), fill=None if est else col, outline=col, width=3)


def s_timeline(video, sc, lang, t, ctx):
    im, d = base(video, sc, lang, t)
    vmax = float(sc["axis_max"])
    if VERT:
        x0, x1, top, rh = 80, W - 150, 470, 240
    else:
        x0, x1, top, rh = 470, 1820, 250, 165
    X = lambda v: x0 + (x1 - x0) * v / vmax
    rows = sc["rows"]
    yb = top + rh * len(rows)
    for k in range(0, int(vmax) + 1, 2):
        d.line((X(k), top - 10, X(k), yb - 30), fill=LINE, width=1)
        d.text((X(k) - 10, yb - 20), f"{k}", font=font(22), fill=MUTED)
    for pm in sc.get("phase_marks", []):
        for yy in range(top - 10, yb - 30, 18):
            d.line((X(pm), yy, X(pm), yy + 9), fill=MUTED, width=2)
        s = (f"fin phase {sc['phase_marks'].index(pm) + 1}" if lang == "fr" else f"end of phase {sc['phase_marks'].index(pm) + 1}")
        d.text((X(pm) + 6, top - 40), s, font=font(20), fill=MUTED)
    play = min(vmax, max(0.0, (t - 0.5) * vmax / (sc["duration"] - 1.5)))
    for i, r in enumerate(rows):
        y = top + rh * i
        d.rounded_rectangle((40, y, x1 + 40, y + rh - 30), 12, fill=PANEL)
        if VERT:
            d.text((70, y + 12), r["player"], font=tf(r["player"], 34, "Bold"), fill=TXT)
            d.text((70 + d.textlength(r["player"], font=tf(r["player"], 34, "Bold")) + 20, y + 24), L(r["sub"], lang), font=font(20), fill=MUTED)
            ym = y + 130
        else:
            d.text((70, y + 22), r["player"], font=tf(r["player"], 36, "Bold"), fill=TXT)
            d.text((70, y + 78), L(r["sub"], lang), font=font(20), fill=MUTED)
            ym = y + (rh - 30) / 2
        d.line((x0, ym, x1, ym), fill=LINE, width=2)
        evs = ctx["events"][i]
        for e in evs:
            if e["tg"] <= play:
                yy = ym + {"sjw": -34, "hun": 0, "tag": 34}[e["kind"]]
                marker(d, X(e["tg"]), yy, e["kind"], e["est"])
                if e["lab"]:
                    d.text((X(e["tg"]) + 20, yy - 13), e["lab"], font=font(20, "SemiBold"), fill=TXT)
    d.line((X(play), top - 10, X(play), yb - 30), fill=TXT, width=3)
    d.text((X(play) - 120, yb + 4), f"{play:5.2f} s", font=font(24, "Bold"), fill=TXT)
    # légende
    lg = L(sc["legend"], lang)
    lx, ly = 60, yb + (45 if VERT else 50)
    for kind, txt in zip(("sjw", "hun", "tag"), lg[:3]):
        marker(d, lx + 14, ly + 14, kind, False, r=12)
        d.text((lx + 36, ly), txt, font=font(24), fill=TXT)
        lx += 60 + d.textlength(txt, font=font(24))
    if VERT:
        lx, ly = 60, ly + 44
    marker(d, lx + 14, ly + 14, "hun", True, r=12)
    d.text((lx + 36, ly), lg[3], font=font(24), fill=TAG)
    return im


def s_points(video, sc, lang, t, ctx):
    im, d = base(video, sc, lang, t)
    pts = sc["points"]
    step = min(2.5, (sc["duration"] - 3) / len(pts))
    est = {int(s.split("[")[1].rstrip("]")) for s in sc.get("estimates", [])}
    y = 240
    for i, p in enumerate(pts):
        a = ease((t - 0.5 - step * i) / 0.5)
        if a <= 0:
            continue
        txt = L(p, lang)
        f = tf(txt, 36, "SemiBold")
        lines = wrap(d, txt, f, 1480)
        h = 40 + 46 * len(lines)
        xo = 40 * (1 - a)
        d.rounded_rectangle((140 + xo, y, 1780, y + h), 14, fill=PANEL)
        d.ellipse((165 + xo, y + h / 2 - 28, 221 + xo, y + h / 2 + 28), fill=SJW)
        n = str(i + 1); fn = font(32, "Bold")
        d.text((193 + xo - d.textlength(n, font=fn) / 2, y + h / 2 - 20), n, font=fn, fill=BG)
        for k, ln in enumerate(lines):
            d.text((260 + xo, y + 20 + 46 * k), ln, font=f, fill=TXT)
        if i in est:
            tag_estime(d, 1600, y + h / 2 - 15, lang)
        y += h + 22
    return im


def s_build(video, sc, lang, t, ctx):
    im, d = base(video, sc, lang, t)
    d.text((60, 185), L(sc["subtitle"], lang), font=font(30, "SemiBold"), fill=OK)
    cw = (W - 160) / len(sc["columns"])
    for c, col in enumerate(sc["columns"]):
        x = 60 + cw * c
        a = ease((t - 0.4 - 0.8 * c) / 0.6)
        if a <= 0:
            continue
        d.rounded_rectangle((x, 260, x + cw - 40, 800), 16, fill=PANEL)
        d.text((x + 30, 285), L(col["head"], lang), font=font(38, "Bold"), fill=SJW if c == 0 else HUN)
        y = 360
        for it in col["items"]:
            txt = L(it, lang)
            grey = ("non lu" in txt) or ("not read" in txt)
            f = font(30, "Regular")
            for ln in wrap(d, txt, f, cw - 110):
                d.text((x + 30, y), ln, font=f, fill=MUTED if grey else TXT)
                y += 40
            y += 20
    return im


SCENES = {"intro": s_intro, "titre": s_titre, "outro": s_outro, "classement": s_classement, "phases": s_phases,
          "timeline": s_timeline, "points": s_points, "build": s_build}
ANIM = {"intro": 2.1, "titre": 0.0, "classement": 3.5, "phases": 5.5, "points": None, "build": 2.0, "outro": 0.0, "timeline": None}


def render(video_path, root, lang, out, images=None, vertical=False):
    global W, H, VERT
    video = json.load(open(video_path, encoding="utf-8"))
    if vertical:  # clip vertical : scènes choisies dans video.json["vertical"], outro raccourcie
        W, H, VERT = 1080, 1920, True
        v = video["vertical"]
        scenes = [dict(s) for s in video["scenes"] if s["id"] in v["scenes"]]
        for s in scenes:
            if s["type"] == "outro":
                s["duration"] = v.get("outro_duration", 3)
        video["scenes"] = scenes
    for base_dir in (root, os.getcwd()):
        cand = os.path.join(base_dir, video.get("logo", ""))
        if video.get("logo") and os.path.exists(cand):
            video["logo"] = cand
            break
    tmp = tempfile.mkdtemp()
    parts = []
    for n, sc in enumerate(video["scenes"]):
        ctx = {}
        if sc["type"] == "timeline":
            ctx["events"] = [charger_events(root, r) for r in sc["rows"]]
        fn = SCENES[sc["type"]]
        dur = sc["duration"]
        nfr = int(round(dur * FPS))
        if images:  # images de contrôle : moment le plus chargé
            fn(video, sc, lang, dur - 0.6, ctx).save(os.path.join(images, f"{n:02d}-{sc['id']}-{lang}.jpg"), quality=90)
            continue
        part = os.path.join(tmp, f"{n:02d}.mp4"); tpart = part + ".tmp.mp4"
        fade = f"fade=t=in:st=0:d=0.3,fade=t=out:st={dur - 0.3}:d=0.3"
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
               "-r", str(FPS), "-i", "-", "-vf", fade, "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
               "-pix_fmt", "yuv420p", "-r", str(FPS), tpart]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        last, last_key = None, None
        for k in range(nfr):
            t = k / FPS
            # le texte change à chaque segment de narration : clé = (image animée ?, segment)
            seg = sum(1 for s in sc.get("narration", []) if t >= s["t"])
            limit = ANIM.get(sc["type"])
            key = None if (limit is None or t < limit) else ("fixe", seg)
            if key is not None and key == last_key:
                buf = last
            else:
                buf = fn(video, sc, lang, t, ctx).tobytes()
            last, last_key = buf, key
            p.stdin.write(buf)
        p.stdin.close()
        if p.wait() != 0:
            raise SystemExit(f"échec ffmpeg scène {sc['id']}")
        os.replace(tpart, part)
        parts.append(part)
    if images:
        return
    lst = os.path.join(tmp, "liste.txt")
    open(lst, "w").write("".join(f"file '{x}'\n" for x in parts))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    tout = out + ".tmp.mp4"
    # piste audio muette (YouTube accepte mieux une vidéo avec audio)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                    "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-shortest",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", tout], check=True)
    os.replace(tout, out)


if __name__ == "__main__":
    a = sys.argv[1:]
    img = a[a.index("--images") + 1] if "--images" in a else None
    if img:
        os.makedirs(img, exist_ok=True)
    render(a[0], a[1], a[2], a[3], img, vertical="--vertical" in a)
