# ==========================================
#   Discord Music Bot
#   Created & Maintained by Bikio
#   GitHub: https://github.com/bikiogirl
# ==========================================
import os, sqlite3, calendar, datetime as dt
from zoneinfo import ZoneInfo
import discord
from discord import app_commands
from discord.ext import tasks
from dotenv import load_dotenv
import report
print("done!")

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
TZ = ZoneInfo(os.getenv("TIMEZONE", "Europe/Athens"))
BUMP_BOTS = {int(x) for x in os.getenv("BUMP_BOT_IDS", "302050872383242240").split(",") if x.strip()}
def ids(name): return {int(x) for x in os.getenv(name, "").split(",") if x.strip()}
MESSAGE_CHANNELS = ids("MESSAGE_CHANNEL_IDS")  # empty = count all channels
IGNORED_VOICE = ids("IGNORED_VOICE_IDS")       # voice channels that do not count (e.g. AFK)
COUNT_ROLES = ids("COUNT_ROLE_IDS")  # empty = everyone counts

def counts(member):
    if not COUNT_ROLES or member.id in staff_ids(member.guild.id):
        return True
    return any(r.id in COUNT_ROLES for r in member.roles)

BUMP_WORDS = ("bump done", "👍")  # words that indicate a successful bump

db = sqlite3.connect("activity.db")
db.executescript("""
CREATE TABLE IF NOT EXISTS activity(guild_id INT, user_id INT, day TEXT,
  messages INT DEFAULT 0, voice REAL DEFAULT 0, bumps INT DEFAULT 0, PRIMARY KEY(guild_id,user_id,day));
CREATE TABLE IF NOT EXISTS staff(guild_id INT, user_id INT, PRIMARY KEY(guild_id,user_id));
CREATE TABLE IF NOT EXISTS members(guild_id INT, day TEXT, count INT, PRIMARY KEY(guild_id,day));
""")
intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.messages = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
voice_start: dict = {}


def now(): return dt.datetime.now(TZ)

def add(gid, uid, day, col, amount):
    db.execute(f"INSERT INTO activity(guild_id,user_id,day,{col}) VALUES(?,?,?,?) "
               f"ON CONFLICT(guild_id,user_id,day) DO UPDATE SET {col}={col}+excluded.{col}",
               (gid, uid, day, amount))
    db.commit()

def snapshot(guild):
    db.execute("INSERT OR REPLACE INTO members VALUES(?,?,?)",
               (guild.id, now().date().isoformat(), guild.member_count))
    db.commit()

# ---------- Voice ----------
def active(member, ch):
    return ch is not None and ch != member.guild.afk_channel and ch.id not in IGNORED_VOICE

def close_session(gid, uid):
    start = voice_start.pop((gid, uid), None)
    if not start: return
    end, cur = now(), start
    while cur < end:  # split by day
        midnight = cur.replace(hour=0, minute=0, second=0, microsecond=0) + dt.timedelta(days=1)
        seg = min(end, midnight)
        add(gid, uid, cur.date().isoformat(), "voice", (seg - cur).total_seconds())
        cur = seg

@client.event
async def on_voice_state_update(member, before, after):
    if member.bot: return
    b, a = active(member, before.channel), active(member, after.channel)
    if b and not a: close_session(member.guild.id, member.id)
    elif a and not b and counts(member): voice_start[(member.guild.id, member.id)] = now()

# ---------- Messages & Bumps ----------
@client.event
async def on_message(msg):
    if not msg.guild: return
    day = now().date().isoformat()
    if msg.author.bot:
        if msg.author.id in BUMP_BOTS:
            text = " ".join((e.description or "") for e in msg.embeds).lower() + (msg.content or "").lower()
            meta = getattr(msg, "interaction_metadata", None)
            user = meta.user if meta else (msg.interaction.user if msg.interaction else None)
            if user and any(w in text for w in BUMP_WORDS):
                add(msg.guild.id, user.id, day, "bumps", 1)
        return
    cid = getattr(msg.channel, "parent_id", None) or msg.channel.id  # threads count under their parent channel
    if MESSAGE_CHANNELS and cid not in MESSAGE_CHANNELS: return
    if not counts(msg.author): return
    add(msg.guild.id, msg.author.id, day, "messages", 1)

@client.event
async def on_member_join(m): snapshot(m.guild)
@client.event
async def on_member_remove(m): snapshot(m.guild)

@tasks.loop(hours=1)
async def hourly():
    for g in client.guilds: snapshot(g)

@client.event
async def on_ready():
    await tree.sync()
    for g in client.guilds:
        snapshot(g)
        for vc in g.voice_channels:
            if vc == g.afk_channel or vc.id in IGNORED_VOICE: continue
            for m in vc.members:
                if not m.bot and counts(m): voice_start.setdefault((g.id, m.id), now())
    if not hourly.is_running(): hourly.start()
    print("Ready:", client.user)

# ---------- Staff selection ----------
def staff_ids(gid): return {r[0] for r in db.execute("SELECT user_id FROM staff WHERE guild_id=?", (gid,))}

staff_group = app_commands.Group(name="staff", description="Choose who counts as Staff",
                                 default_permissions=discord.Permissions(manage_guild=True))

@staff_group.command(name="add", description="Add a staff member")
@app_commands.describe(user="The user")
async def staff_add(i: discord.Interaction, user: discord.Member):
    db.execute("INSERT OR IGNORE INTO staff(guild_id,user_id) VALUES(?,?)", (i.guild_id, user.id))
    db.commit()
    await i.response.send_message(f"✅ {user.mention} was added to the Staff Team.", ephemeral=True)

@staff_group.command(name="remove", description="Remove a staff member from the count")
async def staff_remove(i: discord.Interaction, user: discord.Member):
    db.execute("DELETE FROM staff WHERE guild_id=? AND user_id=?", (i.guild_id, user.id)); db.commit()
    await i.response.send_message(f"🗑️ {user.mention} was removed.", ephemeral=True)

@staff_group.command(name="list", description="List the staff members that are counted")
async def staff_list(i: discord.Interaction):
    lines = [f"• <@{u}>" for u in staff_ids(i.guild_id)]
    await i.response.send_message("**Staff Team:**\n" + ("\n".join(lines) or "—"), ephemeral=True)

tree.add_command(staff_group)

# ---------- Report ----------
def span(kind, d):
    if kind == "week":
        s = d - dt.timedelta(days=d.weekday()); return s, s + dt.timedelta(days=6)
    if kind == "month":
        return d.replace(day=1), d.replace(day=calendar.monthrange(d.year, d.month)[1])
    return d.replace(month=1, day=1), d.replace(month=12, day=31)

def aggregate(gid, s, e):
    rows = db.execute("SELECT user_id,SUM(messages),SUM(voice),SUM(bumps) FROM activity "
                      "WHERE guild_id=? AND day BETWEEN ? AND ? GROUP BY user_id",
                      (gid, s.isoformat(), e.isoformat()))
    return {u: (m or 0, v or 0, b or 0) for u, m, v, b in rows}

def members_at(gid, day, fallback):
    r = db.execute("SELECT count FROM members WHERE guild_id=? AND day<=? ORDER BY day DESC LIMIT 1",
                   (gid, day.isoformat())).fetchone()
    return r[0] if r else fallback

@tree.command(name="report", description="Activity report")
@app_commands.describe(period="Period", previous="Show the previous (completed) period")
@app_commands.choices(period=[app_commands.Choice(name="Week", value="week"),
                              app_commands.Choice(name="Month", value="month"),
                              app_commands.Choice(name="Year", value="year")])
async def report_cmd(i: discord.Interaction, period: app_commands.Choice[str], previous: bool = False):
    await i.response.defer()
    g, kind = i.guild, period.value
    for uid in list(voice_start):  # update everyone currently in voice
        if uid[0] == g.id:
            close_session(*uid); voice_start[uid] = now()
    today = now().date()
    s, e = span(kind, today)
    if previous: s, e = span(kind, s - dt.timedelta(days=1))
    ps, pe = span(kind, s - dt.timedelta(days=1))
    cur, prv = aggregate(g.id, s, e), aggregate(g.id, ps, pe)
    names = {}
    for uid in set(cur) | set(prv) | staff_ids(g.id):
        m = g.get_member(uid); names[uid] = m.display_name if m else str(uid)
    data = dict(kind=kind, start=s, end=e, cur=cur, prev=prv, staff=staff_ids(g.id), names=names,
                members_now=members_at(g.id, min(e, today), g.member_count),
                members_prev=members_at(g.id, pe, g.member_count))
    img = report.build_image(data)
    await i.followup.send(file=discord.File(img, "report.png"))
    for chunk in report.build_text(data):
        await i.followup.send(embed=discord.Embed(description=chunk, color=0x5865F2))

client.run(TOKEN)
