import io
from PIL import Image, ImageDraw, ImageFont, ImageColor

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]

def labels(d):
    k, s, e = d["kind"], d["start"], d["end"]
    if k == "week": return f"{s:%d/%m} – {e:%d/%m/%Y}", "This week", "the previous week", "Week"
    if k == "month": return f"{MONTHS[s.month-1]} {s.year}", f"{MONTHS[s.month-1]}", "the previous month", MONTHS[s.month-1]
    return str(s.year), str(s.year), "the previous year", str(s.year)

def tot(users, staff):
    z = lambda: [0, 0.0, 0]
    st, mb, al = z(), z(), z()
    for uid, (m, v, b) in users.items():
        for t in ([st] if uid in staff else [mb]) + [al]:
            t[0] += m; t[1] += v; t[2] += b
    return st, mb, al

def h(sec): return f"{sec/3600:.2f}h"

def delta(c, p, unit="", hours=False):
    d = (c - p) / 3600 if hours else c - p
    icon = "📈" if d > 0 else "📉" if d < 0 else "➖"
    sign = "+" if d > 0 else "-" if d < 0 else ""
    val = f"{abs(d):.2f}" if hours else f"{abs(int(d)):,}"
    return f"(`{icon} {sign}{val}{unit}`)"

def trend(c, p, verbs):
    r = c / p if p else (2 if c else 1)
    return verbs[0] if r > 1.1 else verbs[2] if r < 0.9 else verbs[1]

def score(t): return t[0] + t[1] / 3600 * 10 + t[2]

UP = ("increased", "stayed stable", "decreased")

def build_text(d):
    period, label, prevlabel, short = labels(d)
    sc, mc, ac = tot(d["cur"], d["staff"]); sp, mp, ap = tot(d["prev"], d["staff"])
    names, cur, prev, staff = d["names"], d["cur"], d["prev"], d["staff"]
    z = (0, 0.0, 0)
    ratio = ac[0] / ap[0] if ap[0] else 2
    big = "an impressive increase" if ratio >= 2 else "an increase" if ratio > 1.1 else "a decrease" if ratio < 0.9 else "stable activity"
    mv = trend(ac[0], ap[0], UP)
    vv = trend(ac[1], ap[1], UP)
    out = [f"**📊 Overall Activity**\n{label} showed {big} in server activity compared to {prevlabel}. "
           f"Messages {mv}, while Voice Channel presence {vv}.\n\n"
           f"• Messages: `{ac[0]:,}` {delta(ac[0], ap[0])}\n• Voice Calls: `{h(ac[1])}` {delta(ac[1], ap[1], 'h', True)}\n"
           f"• Bumps: `{ac[2]:,}` {delta(ac[2], ap[2])}\n• Total Members: `{d['members_now']}` {delta(d['members_now'], d['members_prev'])}"]

    sl = sorted(((u, cur.get(u, z)) for u in staff), key=lambda x: -x[1][0])
    sb = max(sl, key=lambda x: x[1][2], default=None)
    t = [f"**🛡️ Staff Team Activity**\nThe Staff Team's message activity {trend(sc[0], sp[0], UP)}, "
         f"and its Voice Channel participation {trend(sc[1], sp[1], UP)}.\n",
         f"• Staff Messages: `{sc[0]:,}` {delta(sc[0], sp[0])}",
         f"• Voice Call Time: `{h(sc[1])}` {delta(sc[1], sp[1], 'h', True)}"]
    if sl and sl[0][1][0]: t.append(f"• Top Staff Chatter: {names[sl[0][0]]} — `{sl[0][1][0]:,}` messages")
    if sb and sb[1][2]: t.append(f"• Bump Leader: {names[sb[0]]} — `{sb[1][2]}` bumps {delta(sb[1][2], prev.get(sb[0], z)[2])}")
    out.append("\n".join(t))

    out.append(f"**👥 Members Activity**\nMember chat activity {trend(mc[0], mp[0], UP)}, "
               f"and Voice Channel presence {trend(mc[1], mp[1], UP)}.\n\n• Member Messages: `{mc[0]:,}` {delta(mc[0], mp[0])}\n"
               f"• Member Voice Time: `{h(mc[1])}` {delta(mc[1], mp[1], 'h', True)}")

    def line(u):
        c, p = cur.get(u, z), prev.get(u, z)
        return (f"• {names[u]}: `{c[0]:,}` messages {delta(c[0], p[0])}, `{h(c[1])}` Voice {delta(c[1], p[1], 'h', True)} "
                f"and `{c[2]}` bumps {delta(c[2], p[2])}")
    rising = sorted([u for u in staff if score(cur.get(u, z)) > score(prev.get(u, z))],
                    key=lambda u: -(score(cur.get(u, z)) - score(prev.get(u, z))))[:4]
    if rising: out.append("**⭐ Rising Stars**\n" + "\n".join(line(u) for u in rising))

    drops = sorted([u for u in staff if cur.get(u, z)[0] < prev.get(u, z)[0]],
                   key=lambda u: cur.get(u, z)[0] - prev.get(u, z)[0])[:3]
    idle = [names[u] for u in staff if score(cur.get(u, z)) == 0]
    dl = [f"• {names[u]}: Messages dropped from `{prev[u][0]:,}` to `{cur.get(u, z)[0]:,}` "
          f"{delta(cur.get(u, z)[0], prev[u][0])}" for u in drops if cur.get(u, z)[0] > 0]
    if idle: dl.append(f"• {' & '.join(idle)}: `0` activity in messages, Voice and bumps.")
    if dl: out.append("**📉 Biggest Drops**\n" + "\n".join(dl))

    hl = [f"• Chat: Total messages went from `{ap[0]:,}` to `{ac[0]:,}`.",
          f"• Voice: Total Voice activity went from `{ap[1]/3600:.0f}h` to `{ac[1]/3600:.0f}h`."]
    allr = max((u for u in staff if all(cur.get(u, z))), key=lambda u: score(cur[u]), default=None)
    if allr:
        c = cur[allr]; hl.append(f"• Top All-Rounder: {names[allr]} — `{c[0]:,}` messages, `{h(c[1])}` Voice, `{c[2]}` bumps.")
    for u in staff:
        if score(prev.get(u, z)) == 0 and score(cur.get(u, z)) > 0:
            c = cur[u]; hl.append(f"• New Entry: {names[u]} with `{c[0]:,}` messages and `{c[2]}` bumps."); break
    out.append("**✨ Highlights**\n" + "\n".join(hl))

    out.append(f"**📝 {short} in a Nutshell**\n{label} closed with {big} in server activity. "
               f"Messages reached `{ac[0]:,}` and Voice Channel presence reached `{ac[1]/3600:.0f}` hours.")
    # split into messages < 4000 characters
    chunks, buf = [], ""
    for s in out:
        if len(buf) + len(s) > 3800: chunks.append(buf); buf = ""
        buf += s + "\n\n"
    return chunks + [buf]

# ---------------- Image ----------------
BG, MUTED, TXT = "#0e1120", "#8b92b8", "#f2f4ff"
GREEN, RED = "#3ddc97", "#ff5c7a"
EMOJI_FONT_PATHS = ["fonts/NotoColorEmoji.ttf", "NotoColorEmoji.ttf",
                    "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
                    "/usr/share/fonts/noto/NotoColorEmoji.ttf", "C:/Windows/Fonts/seguiemj.ttf"]
_emoji_font = None

def font(size, bold=False):
    names = (["fonts/bold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf"] if bold
             else ["fonts/regular.ttf", "DejaVuSans.ttf", "arial.ttf", "Arial.ttf"])
    for n in names:
        try: return ImageFont.truetype(n, size)
        except OSError: pass
    return ImageFont.load_default()

def emoji_image(ch, size):
    global _emoji_font
    if _emoji_font is None:
        _emoji_font = False
        for p in EMOJI_FONT_PATHS:
            try: _emoji_font = ImageFont.truetype(p, 109); break
            except OSError: pass
    if not _emoji_font: return None
    try:
        im = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((10, 10), ch, font=_emoji_font, embedded_color=True)
        box = im.getbbox()
        if not box: return None
        im = im.crop(box); r = size / max(im.size)
        return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    except Exception:
        return None

def lum(c):
    r, g, b = ImageColor.getrgb(c); return 0.299 * r + 0.587 * g + 0.114 * b

def build_image(d):
    period, _, _, _ = labels(d)
    sc, mc, ac = tot(d["cur"], d["staff"]); sp, mp, ap = tot(d["prev"], d["staff"])
    z = (0, 0.0, 0)
    rows = sorted(((u, d["cur"].get(u, z)) for u in d["staff"]), key=lambda x: -x[1][0])
    W, RH, G = 1000, 54, 6
    H = 40 + 100 + 24 + 34 + 3 * (RH + G) + 22 + max(len(rows), 1) * (RH + G) + 60
    im = Image.new("RGB", (W, H), BG); dr = ImageDraw.Draw(im)
    T = lambda xy, s, f, c=TXT, a="la": dr.text(xy, str(s), font=f, fill=c, anchor=a)
    kind = {"week": "Weekly", "month": "Monthly", "year": "Yearly"}[d["kind"]]

    # Header
    dr.rounded_rectangle((40, 40, W - 40, 140), 22, fill="#181c33")
    dr.rounded_rectangle((40, 40, 54, 140), 7, fill="#5865F2")
    T((84, 62), f"{kind} Activity Report", font(32, True)); T((84, 106), period, font(20), MUTED)
    diff = d["members_now"] - d["members_prev"]
    T((W - 70, 56), "MEMBERS", font(15, True), MUTED, "ra")
    T((W - 70, 74), f"{d['members_now']:,}", font(34, True), TXT, "ra")
    if diff: T((W - 70, 126), f"{'▲' if diff > 0 else '▼'} {abs(diff)}", font(15, True), GREEN if diff > 0 else RED, "rm")

    X_NAME, COLS = 96, (690, 820, 950)
    y = 164
    for x, lab in zip(COLS, ("MESSAGES", "VOICE", "BUMPS")): T((x, y + 8), lab, font(14, True), MUTED, "ra")
    y += 34

    def row(y, label, vals, color, emoji=None):
        dark = lum(color) < 150
        tc, sc_ = ("#ffffff", "#e6e6f0") if dark else ("#10131f", "#2a2d3d")
        dr.rounded_rectangle((40, y, W - 40, y + RH), 14, fill=color,
                             outline="#4a4f70" if lum(color) < 45 else None, width=2)
        xi = X_NAME - 8
        if emoji:
            e = emoji_image(emoji, 30)
            if e: im.paste(e, (58, y + (RH - e.height) // 2), e)
            else: dr.ellipse((62, y + RH // 2 - 7, 76, y + RH // 2 + 7), fill=tc)
        T((X_NAME, y + RH // 2), label[:22], font(21, True), tc, "lm")
        for x, v in zip(COLS, vals): T((x, y + RH // 2), v, font(21, True), tc, "rm")

    fmt = lambda t: (f"{t[0]:,}", f"{t[1]/3600:.2f}h", f"{t[2]:,}")
    row(y, "ALL", fmt(ac), "#2b3050", "📊"); y += RH + G
    row(y, "Staff Team", fmt(sc), "#8b4a1c", "🛡️"); y += RH + G
    row(y, "Members", fmt(mc), "#1f8a85", "👥"); y += RH + G + 22
    for u, (m, v, b) in rows:
        row(y, d["names"][u], fmt((m, v, b)), "#3a3f5c"); y += RH + G
    if not rows: T((W // 2, y + 24), "No staff selected (use /staff add)", font(18), MUTED, "mm")
    T((W // 2, H - 30), f"Generated • {d['end']:%d/%m/%Y}", font(14), MUTED, "mm")
    buf = io.BytesIO(); im.save(buf, "PNG"); buf.seek(0)
    return buf
