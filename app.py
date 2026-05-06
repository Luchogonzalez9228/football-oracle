# ================================================================
#  FOOTBALL ORACLE PRO v3.0 — Arquitectura Multi-API Robusta
#  5 fuentes | Monte Carlo 10,000 | Latam + Europa + Mundial
#  Fallback automatico | Sugerencias de apuesta | 45 dias
# ================================================================
#
#  FUENTES GRATUITAS:
#  1. football-data.org   — Europa + UCL + World Cup
#  2. api-sports.io       — Global (Latam, Asia, Africa)
#  3. the-odds-api.com    — Cuotas en vivo (500 req/mes gratis)
#  4. open-meteo.com      — Clima del estadio (sin key)
#  5. clubelo.com         — Elo ratings de selecciones (sin key)
# ================================================================

import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import math

# ── KEYS ─────────────────────────────────────────────────────────
FD_KEY    = "a2aef808a68d4cd6ba2ad97f9953ec81"   # football-data.org  → football-data.org/client/register
APISPORTS = "70cb24441a57cc0a28c2fd7dd3b76110"   # api-sports.io      → dashboard.api-sports.io
ODDS_KEY  = "f028e4d3689b54c609ce7137fc6a40ba"   # the-odds-api.com   → the-odds-api.com/#get-access
# open-meteo y clubelo no necesitan key
# ─────────────────────────────────────────────────────────────────

N_SIM      = 10_000
DAYS_AHEAD = 45   # ventana de busqueda de partidos

def _secret(k, f=""):
    try:    return st.secrets.get(k, f)
    except: return f

def get_fd_key():   return st.session_state.get("fd_key",   _secret("FD_KEY",   FD_KEY))
def get_as_key():   return st.session_state.get("as_key",   _secret("APISPORTS",APISPORTS))
def get_odds_key(): return st.session_state.get("odds_key", _secret("ODDS_KEY", ODDS_KEY))

# ================================================================
st.set_page_config(page_title="Football Oracle PRO", page_icon="⚽",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;700&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#07070f;color:#e2e2f0;}
.hero{background:linear-gradient(135deg,#0d0d1c,#180808);border:1px solid #252535;
  border-radius:18px;padding:32px 36px 24px;margin-bottom:28px;position:relative;overflow:hidden;}
.hero::after{content:'';position:absolute;top:-80px;right:-80px;width:300px;height:300px;
  background:radial-gradient(circle,rgba(244,98,42,.12),transparent 70%);}
.hero h1{font-family:'Bebas Neue',sans-serif;font-size:clamp(2rem,6vw,3.2rem);
  color:#f4622a;letter-spacing:3px;line-height:.95;}
.hero .sub{color:#606080;font-size:.82rem;margin-top:8px;}
.apis{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;}
.pill{background:#13131f;border:1px solid #252535;border-radius:99px;
  padding:3px 10px;font-size:.7rem;color:#7070a0;}
.pill.on{border-color:#3ecf8e44;color:#3ecf8e;background:rgba(62,207,142,.08);}
.pill.off{border-color:#f4622a33;color:#f4622a55;}
.sec{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#f4622a;
  letter-spacing:2px;border-bottom:1px solid #1e1e2e;padding-bottom:5px;margin:22px 0 14px;}
.kpi{background:#0f0f1c;border:1px solid #1e1e2e;border-radius:12px;
  padding:14px 16px;text-align:center;margin-bottom:6px;}
.kpi-val{font-family:'Bebas Neue',sans-serif;font-size:2rem;color:#f5c842;line-height:1.1;}
.kpi-lbl{font-size:.63rem;color:#404060;letter-spacing:2px;text-transform:uppercase;margin-top:2px;}
.pc{border-radius:12px;padding:15px 18px;margin-bottom:9px;
  display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.pc-high{background:#09150f;border:1px solid #3ecf8e33;}
.pc-med{background:#141108;border:1px solid #f5c84233;}
.pc-low{background:#150808;border:1px solid #f4622a33;}
.pc-mkt{font-size:.65rem;color:#404060;letter-spacing:2px;text-transform:uppercase;min-width:115px;}
.pc-pick{font-weight:600;font-size:.9rem;flex:1;}
.pc-det{font-size:.72rem;color:#505070;margin-top:2px;}
.badge{display:inline-block;border-radius:6px;padding:2px 9px;
  font-size:.68rem;font-weight:700;letter-spacing:.5px;margin-top:3px;}
.b-high{background:rgba(62,207,142,.15);color:#3ecf8e;}
.b-med{background:rgba(245,200,66,.12);color:#f5c842;}
.b-low{background:rgba(244,98,42,.15);color:#f4622a;}
/* Bet suggestion */
.bet-box{background:linear-gradient(135deg,#0f1a0f,#0a1208);
  border:2px solid #3ecf8e55;border-radius:14px;padding:20px 24px;margin:12px 0;}
.bet-box h3{font-family:'Bebas Neue',sans-serif;color:#3ecf8e;font-size:1.4rem;
  letter-spacing:2px;margin-bottom:10px;}
.bet-row{display:flex;justify-content:space-between;align-items:center;
  padding:6px 0;border-bottom:1px solid #1a2a1a;}
.bet-row:last-child{border-bottom:none;}
.bet-label{font-size:.82rem;color:#8080a0;}
.bet-val{font-family:'Bebas Neue',sans-serif;font-size:1.2rem;color:#f5c842;}
.stake-rec{background:#0a1f0a;border:1px solid #3ecf8e44;border-radius:8px;
  padding:10px 14px;margin-top:10px;font-size:.82rem;color:#80d080;}
.warning-bet{background:#1a0808;border:1px solid #f4622a44;border-radius:8px;
  padding:10px 14px;margin-top:10px;font-size:.8rem;color:#d08080;}
.prow{margin:7px 0;}
.prow-lbl{font-size:.78rem;color:#8080a0;margin-bottom:2px;}
.pbar{background:#151525;border-radius:99px;height:9px;overflow:hidden;}
.pfill{height:100%;border-radius:99px;}
.match{background:#0f0f1c;border:1px solid #1e1e2e;border-radius:14px;
  padding:20px;text-align:center;margin:14px 0;}
.tn{font-family:'Bebas Neue',sans-serif;font-size:1.7rem;color:#e2e2f0;}
.vs{font-family:'Bebas Neue',sans-serif;font-size:2.2rem;color:#f4622a;}
.src-tag{font-size:.65rem;background:#13131f;border:1px solid #1e1e2e;
  border-radius:4px;padding:1px 6px;color:#505070;}
.elo-box{background:#0f0f1c;border:1px solid #252535;border-radius:10px;
  padding:10px 16px;margin:8px 0;font-size:.82rem;}
.stButton>button{background:#f4622a!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-weight:700!important;
  padding:13px 20px!important;width:100%!important;font-size:.95rem!important;letter-spacing:1px!important;}
.stButton>button:hover{background:#c04a1e!important;}
#MainMenu,footer,header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ================================================================
#  LIGAS — DICCIONARIOS COMPLETOS
# ================================================================

# football-data.org competition codes
FD_COMPETITIONS = {
    # Europa
    "Premier League (ENG)":          "PL",
    "La Liga (ESP)":                  "PD",
    "Bundesliga (GER)":               "BL1",
    "Serie A (ITA)":                  "SA",
    "Ligue 1 (FRA)":                  "FL1",
    "Eredivisie (NED)":               "DED",
    "Primeira Liga (POR)":            "PPL",
    "Championship (ENG)":             "ELC",
    # Europa continental
    "UEFA Champions League":          "CL",
    "UEFA Europa League":             "EL",
    # Latinoamerica
    "Copa Libertadores":              "CLI",
    # Clasificatorias y selecciones
    "World Cup Qualifying (S.Amer)":  "WC",
    "FIFA World Cup 2026":            "WC",
    "Euro / Nations League":          "EC",
}

# api-sports.io league IDs — fuente primaria para Latam
AS_LEAGUES = {
    # Europa
    "Premier League (ENG)":          {"id": 39,  "season": 2024},
    "La Liga (ESP)":                  {"id": 140, "season": 2024},
    "Bundesliga (GER)":               {"id": 78,  "season": 2024},
    "Serie A (ITA)":                  {"id": 135, "season": 2024},
    "Ligue 1 (FRA)":                  {"id": 61,  "season": 2024},
    "Eredivisie (NED)":               {"id": 88,  "season": 2024},
    "Primeira Liga (POR)":            {"id": 94,  "season": 2024},
    "Championship (ENG)":             {"id": 40,  "season": 2024},
    # Europa continental
    "UEFA Champions League":          {"id": 2,   "season": 2024},
    "UEFA Europa League":             {"id": 3,   "season": 2024},
    "UEFA Europa Conference League":  {"id": 848, "season": 2024},
    # LATAM — cobertura completa en api-sports
    "Liga BetPlay (COL)":             {"id": 239, "season": 2025},
    "Liga Profesional (ARG)":         {"id": 128, "season": 2025},
    "Serie A Brasil (BRA)":           {"id": 71,  "season": 2025},
    "Liga MX (MEX)":                  {"id": 262, "season": 2025},
    "Primera Division (CHI)":         {"id": 265, "season": 2025},
    "Liga 1 (PER)":                   {"id": 268, "season": 2025},
    "Primera Division (URU)":         {"id": 278, "season": 2025},
    "Copa Libertadores":              {"id": 13,  "season": 2025},
    "Copa Sudamericana":              {"id": 11,  "season": 2025},
    # Clasificatorias Mundialistas
    "World Cup Qualifying (S.Amer)":  {"id": 29,  "season": 2025},
    "World Cup Qualifying (EUR)":     {"id": 32,  "season": 2025},
    "World Cup Qualifying (CONC)":    {"id": 31,  "season": 2025},
    "World Cup Qualifying (AFR)":     {"id": 30,  "season": 2025},
    "World Cup Qualifying (ASIA)":    {"id": 36,  "season": 2025},
    # Mundiales y torneos de selecciones
    "FIFA World Cup 2026":            {"id": 1,   "season": 2026},
    "Copa America":                   {"id": 9,   "season": 2024},
    "Euro / Nations League":          {"id": 5,   "season": 2024},
    "Africa Cup of Nations":          {"id": 6,   "season": 2025},
    "CONCACAF Gold Cup":              {"id": 20,  "season": 2025},
    # USA
    "MLS (USA)":                      {"id": 253, "season": 2025},
}

# Prioridad de fuente por liga: "fd" primero o "as" primero
# Latam y selecciones usan as primero; Europa usa fd primero
AS_PRIORITY_LEAGUES = {
    "Liga BetPlay (COL)", "Liga Profesional (ARG)", "Serie A Brasil (BRA)",
    "Liga MX (MEX)", "Primera Division (CHI)", "Liga 1 (PER)",
    "Primera Division (URU)", "Copa Libertadores", "Copa Sudamericana",
    "World Cup Qualifying (S.Amer)", "World Cup Qualifying (EUR)",
    "World Cup Qualifying (CONC)", "World Cup Qualifying (AFR)",
    "World Cup Qualifying (ASIA)", "FIFA World Cup 2026",
    "Copa America", "Africa Cup of Nations", "CONCACAF Gold Cup", "MLS (USA)",
}

ODDS_SPORT_MAP = {
    "Premier League (ENG)":   "soccer_england_league1",
    "La Liga (ESP)":           "soccer_spain_la_liga",
    "Bundesliga (GER)":        "soccer_germany_bundesliga",
    "Serie A (ITA)":           "soccer_italy_serie_a",
    "Ligue 1 (FRA)":           "soccer_france_ligue_one",
    "UEFA Champions League":   "soccer_uefa_champs_league",
    "UEFA Europa League":      "soccer_uefa_europa_league",
    "FIFA World Cup 2026":     "soccer_fifa_world_cup",
    "Liga BetPlay (COL)":      "soccer_colombia_primera_a",
    "Liga Profesional (ARG)":  "soccer_argentina_primera_division",
    "Serie A Brasil (BRA)":    "soccer_brazil_campeonato",
    "MLS (USA)":               "soccer_usa_mls",
}

STADIUM_COORDS = {
    "Premier League (ENG)":   (51.50, -0.12),
    "Championship (ENG)":     (51.50, -0.12),
    "La Liga (ESP)":           (40.45, -3.69),
    "Bundesliga (GER)":        (48.21, 11.62),
    "Serie A (ITA)":           (45.47,  9.12),
    "Ligue 1 (FRA)":           (48.85,  2.35),
    "Eredivisie (NED)":        (52.31,  4.94),
    "Primeira Liga (POR)":     (38.75, -9.18),
    "UEFA Champions League":   (51.50, -0.12),
    "UEFA Europa League":      (51.50, -0.12),
    "Liga BetPlay (COL)":      ( 4.71,-74.07),  # Bogota
    "Liga Profesional (ARG)":  (-34.6,-58.44),  # Buenos Aires
    "Serie A Brasil (BRA)":    (-23.5,-46.63),  # Sao Paulo
    "Liga MX (MEX)":           (19.43,-99.13),
    "Primera Division (CHI)":  (-33.4,-70.65),  # Santiago
    "Liga 1 (PER)":            (-12.0,-77.03),  # Lima
    "Primera Division (URU)":  (-34.9,-56.17),  # Montevideo
    "Copa Libertadores":       (-23.5,-46.63),
    "Copa Sudamericana":       (-23.5,-46.63),
    "World Cup Qualifying (S.Amer)": (-34.6,-58.44),
    "FIFA World Cup 2026":     (29.76,-95.37),  # Houston
    "Copa America":            (25.77,-80.19),  # Miami
    "MLS (USA)":               (34.05,-118.24),
}

# ================================================================
#  SOURCE 1: football-data.org
# ================================================================
FD_BASE = "https://api.football-data.org/v4"

def _fd_headers():
    return {"X-Auth-Token": get_fd_key()}

@st.cache_data(ttl=1800, show_spinner=False)
def fd_get_fixtures(comp_code):
    if not get_fd_key(): return []
    today  = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{FD_BASE}/competitions/{comp_code}/matches",
                         headers=_fd_headers(),
                         params={"dateFrom": today, "dateTo": future, "status": "SCHEDULED"},
                         timeout=12)
        if r.status_code != 200: return []
        result = []
        for m in r.json().get("matches", []):
            home    = m.get("homeTeam",{}).get("shortName") or m.get("homeTeam",{}).get("name","?")
            away    = m.get("awayTeam",{}).get("shortName") or m.get("awayTeam",{}).get("name","?")
            home_id = m.get("homeTeam",{}).get("id")
            away_id = m.get("awayTeam",{}).get("id")
            date_s  = m.get("utcDate","")[:10]
            result.append({"id":m.get("id"),"date":date_s,"home":home,"away":away,
                           "home_id":home_id,"away_id":away_id,"comp":comp_code,
                           "source":"football-data.org",
                           "home_id_fd":home_id,"away_id_fd":away_id,
                           "home_id_as":None,"away_id_as":None,
                           "display":f"📅 {date_s}  |  {home}  vs  {away}"})
        return result
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def fd_get_team_matches(team_id, limit=20):
    if not get_fd_key() or not team_id: return []
    try:
        r = requests.get(f"{FD_BASE}/teams/{team_id}/matches",
                         headers=_fd_headers(),
                         params={"status":"FINISHED","limit":limit}, timeout=12)
        if r.status_code != 200: return []
        return r.json().get("matches",[])
    except: return []

# ================================================================
#  SOURCE 2: api-sports.io
# ================================================================
AS_BASE = "https://v3.football.api-sports.io"

def _as_headers():
    return {"x-apisports-key": get_as_key()}

@st.cache_data(ttl=1800, show_spinner=False)
def as_get_fixtures(league_id, season):
    if not get_as_key(): return []
    today  = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    strategies = [
        {"league":league_id,"season":season,"from":today,"to":future},
        {"league":league_id,"season":season,"from":today,"to":future,"status":"NS"},
        {"league":league_id,"season":season},
    ]
    for params in strategies:
        try:
            r = requests.get(f"{AS_BASE}/fixtures", headers=_as_headers(),
                             params=params, timeout=12)
            data = r.json()
            errors = data.get("errors",{})
            if errors and errors not in ([],{}): continue
            items = data.get("response",[])
            if not items: continue
            result = []
            for f in items:
                fix   = f.get("fixture",{})
                teams = f.get("teams",{})
                st_s  = fix.get("status",{}).get("short","")
                if st_s in ("FT","AET","PEN","CANC","ABD","PST","WO"): continue
                home = teams.get("home",{}).get("name","?")
                away = teams.get("away",{}).get("name","?")
                home_id = teams.get("home",{}).get("id")
                away_id = teams.get("away",{}).get("id")
                date_s = fix.get("date","")[:10]
                result.append({"id":fix.get("id"),"date":date_s,"home":home,"away":away,
                               "home_id":home_id,"away_id":away_id,"season":season,
                               "source":"api-sports.io",
                               "home_id_as":home_id,"away_id_as":away_id,
                               "home_id_fd":None,"away_id_fd":None,
                               "display":f"📅 {date_s}  |  {home}  vs  {away}"})
            if result: return result
        except: continue
    return []

@st.cache_data(ttl=3600, show_spinner=False)
def as_get_stats(team_id, league_id, season):
    if not get_as_key() or not team_id: return {}
    for s in [season, season-1, season+1]:
        try:
            r = requests.get(f"{AS_BASE}/teams/statistics", headers=_as_headers(),
                             params={"team":team_id,"league":league_id,"season":s}, timeout=12)
            d = r.json().get("response",{})
            if d: return d
        except: continue
    return {}

@st.cache_data(ttl=3600, show_spinner=False)
def as_search_team(team_name):
    """Search team by name to get AS id — bridges FD <-> AS."""
    if not get_as_key(): return None
    try:
        r = requests.get(f"{AS_BASE}/teams", headers=_as_headers(),
                         params={"search": team_name[:10]}, timeout=10)
        teams = r.json().get("response",[])
        if teams:
            return teams[0].get("team",{}).get("id")
    except: pass
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def as_get_last_fixtures(team_id, season, n=15):
    if not get_as_key() or not team_id: return []
    for s in [season, season-1]:
        try:
            r = requests.get(f"{AS_BASE}/fixtures", headers=_as_headers(),
                             params={"team":team_id,"season":s,"status":"FT","last":n}, timeout=12)
            d = r.json().get("response",[])
            if d: return d
        except: continue
    return []

# ================================================================
#  SOURCE 3: the-odds-api.com
# ================================================================
ODDS_BASE = "https://api.the-odds-api.com/v4"

@st.cache_data(ttl=1800, show_spinner=False)
def get_odds(sport_key, home_team, away_team):
    if not get_odds_key() or not sport_key: return None
    try:
        r = requests.get(f"{ODDS_BASE}/sports/{sport_key}/odds",
                         params={"apiKey":get_odds_key(),"regions":"eu",
                                 "markets":"h2h,totals","oddsFormat":"decimal"}, timeout=12)
        if r.status_code != 200: return None
        ht = home_team.lower(); at = away_team.lower()
        for ev in r.json():
            ht2 = ev.get("home_team","").lower()
            at2 = ev.get("away_team","").lower()
            if (ht[:5] in ht2 or ht2[:5] in ht) and (at[:5] in at2 or at2[:5] in at):
                bk = (ev.get("bookmakers") or [{}])[0]
                res = {"home":home_team,"away":away_team,"bookmaker":bk.get("title","")}
                for mkt in bk.get("markets",[]):
                    if mkt["key"]=="h2h":
                        for o in mkt.get("outcomes",[]):
                            n = o["name"].lower()
                            if ht[:5] in n:  res["odd_home"]=o["price"]
                            elif "draw" in n: res["odd_draw"]=o["price"]
                            else:            res["odd_away"]=o["price"]
                    elif mkt["key"]=="totals":
                        for o in mkt.get("outcomes",[]):
                            if o["name"]=="Over":  res["odd_over25"]=o["price"]
                            elif o["name"]=="Under":res["odd_under25"]=o["price"]
                return res
        return None
    except: return None

# ================================================================
#  SOURCE 4: open-meteo (sin key)
# ================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def get_weather(lat=51.5, lon=-0.1):
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params={"latitude":lat,"longitude":lon,
                                 "current":"temperature_2m,precipitation,windspeed_10m,weathercode",
                                 "timezone":"auto"}, timeout=8)
        c = r.json().get("current",{})
        code = c.get("weathercode",0)
        cond = ("Despejado" if code<3 else "Nublado" if code<50
                else "Lluvioso" if code<80 else "Tormenta")
        return {"temp":c.get("temperature_2m","?"),"rain":c.get("precipitation",0),
                "wind":c.get("windspeed_10m",0),"cond":cond,"code":code}
    except: return None

# ================================================================
#  SOURCE 5: clubelo.com (ratings Elo de selecciones, sin key)
# ================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def get_elo(team_name):
    """Get Elo rating for national teams from clubelo.com."""
    slug = team_name.replace(" ","-").replace("'","")
    try:
        r = requests.get(f"http://api.clubelo.com/{slug}", timeout=8)
        if r.status_code == 200:
            lines = r.text.strip().split("\n")
            if len(lines) >= 2:
                parts = lines[-1].split(",")
                if len(parts) >= 5:
                    return {"team":team_name, "elo":float(parts[4]), "rank":parts[2]}
    except: pass
    return None

# ================================================================
#  SMART FIXTURE LOADER — Fallback automatico entre fuentes
# ================================================================
def load_fixtures_smart(league_name):
    """
    Carga partidos con fallback automatico entre football-data.org y api-sports.io.
    - Latam y selecciones: api-sports primero
    - Europa: football-data primero
    Siempre intenta la otra fuente si la primaria falla.
    """
    fd_ok = bool(get_fd_key())
    as_ok = bool(get_as_key())
    latam_first = league_name in AS_PRIORITY_LEAGUES

    fixtures = []
    source   = None

    if latam_first:
        # Try api-sports first
        if as_ok and league_name in AS_LEAGUES:
            lg = AS_LEAGUES[league_name]
            fixtures = as_get_fixtures(lg["id"], lg["season"])
            if fixtures: source = "api-sports.io"
        # Fallback football-data
        if not fixtures and fd_ok and league_name in FD_COMPETITIONS:
            fixtures = fd_get_fixtures(FD_COMPETITIONS[league_name])
            if fixtures: source = "football-data.org"
    else:
        # Try football-data first
        if fd_ok and league_name in FD_COMPETITIONS:
            fixtures = fd_get_fixtures(FD_COMPETITIONS[league_name])
            if fixtures: source = "football-data.org"
        # Fallback api-sports
        if not fixtures and as_ok and league_name in AS_LEAGUES:
            lg = AS_LEAGUES[league_name]
            fixtures = as_get_fixtures(lg["id"], lg["season"])
            if fixtures: source = "api-sports.io"

    return fixtures, source

# ================================================================
#  SMART STATS LOADER — Sincronizacion de IDs entre fuentes
# ================================================================
def load_team_stats_smart(match, league_name):
    """
    Carga estadisticas de ambas fuentes y las sincroniza.
    Usa busqueda por nombre para resolver IDs cuando no coinciden.
    """
    fd_ok = bool(get_fd_key())
    as_ok = bool(get_as_key())
    lg    = AS_LEAGUES.get(league_name, {})
    season= lg.get("season", 2024)
    league_id = lg.get("id")

    # IDs desde la fuente que cargo los fixtures
    home_id_as = match.get("home_id_as") or match.get("home_id")
    away_id_as = match.get("away_id_as") or match.get("away_id")
    home_id_fd = match.get("home_id_fd") or match.get("home_id")
    away_id_fd = match.get("away_id_fd") or match.get("away_id")

    # Si los IDs de AS son None (fixture vino de FD), buscar por nombre
    if as_ok and league_id:
        if not home_id_as:
            home_id_as = as_search_team(match["home"])
        if not away_id_as:
            away_id_as = as_search_team(match["away"])

    # Cargar historico desde FD
    fd_home = fd_get_team_matches(home_id_fd) if fd_ok and home_id_fd else []
    fd_away = fd_get_team_matches(away_id_fd) if fd_ok and away_id_fd else []

    # Cargar estadisticas desde AS
    as_home_raw = as_get_stats(home_id_as, league_id, season) if as_ok and home_id_as and league_id else {}
    as_away_raw = as_get_stats(away_id_as, league_id, season) if as_ok and away_id_as and league_id else {}

    # Cargar partidos recientes desde AS (para BTTS y clean sheets)
    as_home_fx = as_get_last_fixtures(home_id_as, season) if as_ok and home_id_as else []
    as_away_fx = as_get_last_fixtures(away_id_as, season) if as_ok and away_id_as else []

    return {
        "home": {"fd_matches":fd_home, "as_stats":as_home_raw,
                 "as_fixtures":as_home_fx, "name":match["home"],
                 "id_fd":home_id_fd, "id_as":home_id_as},
        "away": {"fd_matches":fd_away, "as_stats":as_away_raw,
                 "as_fixtures":as_away_fx, "name":match["away"],
                 "id_fd":away_id_fd, "id_as":away_id_as},
        "season": season, "league_id": league_id,
    }

# ================================================================
#  STATISTICAL ENGINE
# ================================================================
def safe_f(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def profile_from_fd(matches, team_id):
    gf, ga = [], []
    for m in matches:
        ht_id = m.get("homeTeam",{}).get("id")
        s = m.get("score",{}).get("fullTime",{})
        h = s.get("home"); a = s.get("away")
        if h is None or a is None: continue
        if ht_id == team_id: gf.append(h or 0); ga.append(a or 0)
        else:                gf.append(a or 0); ga.append(h or 0)
    if not gf: return None
    n = min(len(gf), 15)
    btts = sum(1 for x,y in zip(gf[-n:],ga[-n:]) if x>0 and y>0)
    cs   = sum(1 for y in ga[-n:] if y==0)
    return {"goals_for":round(np.mean(gf[-n:]),3),
            "goals_against":round(np.mean(ga[-n:]),3),
            "btts_pct": round(btts/n,2), "cs_pct":round(cs/n,2),
            "shots_on":4.5,"yellows":1.8,"reds":0.1,"fouls":12.0,"corners":5.2,
            "source":"football-data.org","n_games":len(gf)}

def profile_from_as_stats(stats, is_home=True):
    if not stats: return None
    v = "home" if is_home else "away"
    def g(path, d=0.0):
        try:
            x = stats
            for k in path: x = x[k]
            return safe_f(x, d)
        except: return d
    gf = g(["goals","for","average",v]) or g(["goals","for","average","total"]) or 0
    ga = g(["goals","against","average",v]) or g(["goals","against","average","total"]) or 0
    if gf==0 and ga==0: return None
    def card_avg(color):
        d = stats.get("cards",{}).get(color,{})
        vals = [safe_f(vv) for vv in d.values() if safe_f(vv)>0]
        return round(sum(vals)/len(vals),2) if vals else (1.8 if color=="yellow" else 0.1)
    played = safe_f(stats.get("fixtures",{}).get("played",{}).get("total",0))
    return {"goals_for":max(0.3,gf),"goals_against":max(0.3,ga),
            "shots_on":g(["shots","on","average"],4.5),
            "yellows":card_avg("yellow"),"reds":card_avg("red"),
            "fouls":g(["fouls","committed","average"],12.0),
            "corners":g(["corners","total","average"],5.2),
            "source":"api-sports.io","n_games":int(played)}

def enrich_from_as_fixtures(profile, fixtures, team_id):
    """Add BTTS and clean sheet % from recent fixture history."""
    if not fixtures or not profile: return profile
    gf_list, ga_list = [], []
    for f in fixtures:
        teams = f.get("teams",{}); score = f.get("goals",{})
        is_home = teams.get("home",{}).get("id") == team_id
        h = score.get("home",0) or 0; a = score.get("away",0) or 0
        gf_list.append(h if is_home else a)
        ga_list.append(a if is_home else h)
    if gf_list:
        n = len(gf_list)
        profile["btts_pct"] = round(sum(1 for x,y in zip(gf_list,ga_list) if x>0 and y>0)/n,2)
        profile["cs_pct"]   = round(sum(1 for y in ga_list if y==0)/n,2)
    return profile

def merge_profiles(fd_p, as_p):
    """Weighted merge of both sources. 60% FD historical, 40% AS season stats."""
    defaults = {"goals_for":1.3,"goals_against":1.1,"shots_on":4.5,
                "yellows":1.8,"reds":0.1,"fouls":12.0,"corners":5.2,
                "btts_pct":0.45,"cs_pct":0.25,
                "source":"Valores promedio de liga","n_games":0}
    if fd_p and as_p:
        merged = {k:v for k,v in defaults.items()}
        merged["goals_for"]     = round(fd_p["goals_for"]*0.55    + as_p["goals_for"]*0.45,    3)
        merged["goals_against"] = round(fd_p["goals_against"]*0.55 + as_p["goals_against"]*0.45,3)
        for k in ["shots_on","yellows","reds","fouls","corners"]:
            merged[k] = as_p.get(k, defaults[k])
        merged["btts_pct"] = fd_p.get("btts_pct", 0.45)
        merged["cs_pct"]   = fd_p.get("cs_pct",   0.25)
        merged["source"]   = "Fusion FD + AS (maxima precision)"
        merged["n_games"]  = fd_p.get("n_games",0)
        return merged
    p = fd_p or as_p
    if p:
        for k,v in defaults.items():
            if k not in p: p[k] = v
        return p
    return defaults

def weather_adjust(profile, w):
    if not w: return profile
    p = dict(profile)
    rain = w.get("rain",0); wind = w.get("wind",0)
    if rain > 2:
        p["goals_for"]  = round(p["goals_for"] *0.92, 3)
        p["shots_on"]   = round(p["shots_on"]  *0.90, 3)
        p["fouls"]      = round(p["fouls"]     *1.05, 3)
        p["corners"]    = round(p["corners"]   *1.03, 3)
    if wind > 30:
        p["corners"]  = round(p["corners"] *0.95, 3)
        p["shots_on"] = round(p["shots_on"]*0.96, 3)
    return p

def elo_adjust(lh, la, home_elo, away_elo):
    """Adjust expected goals based on Elo difference."""
    if not home_elo or not away_elo: return lh, la
    diff = home_elo["elo"] - away_elo["elo"]
    factor = 1 + (diff / 800)
    factor = max(0.75, min(factor, 1.40))
    return round(lh * factor, 3), round(la / factor, 3)

def run_mc(hp, ap, weather=None, home_elo=None, away_elo=None):
    hp = weather_adjust(hp, weather)
    ap = weather_adjust(ap, weather)
    league_avg = 1.35
    lh = max(0.3, hp["goals_for"] * (ap["goals_against"]/league_avg) * 1.12)
    la = max(0.3, ap["goals_for"] * (hp["goals_against"]/league_avg))
    lh, la = elo_adjust(lh, la, home_elo, away_elo)
    rng = np.random.default_rng(42)
    hg  = rng.poisson(lh, N_SIM); ag = rng.poisson(la, N_SIM)
    tot = hg + ag
    def p(n): return round(n/N_SIM*100, 1)
    hc  = rng.poisson(hp["corners"], N_SIM); ac = rng.poisson(ap["corners"],  N_SIM)
    hy  = rng.poisson(hp["yellows"], N_SIM); ay = rng.poisson(ap["yellows"],  N_SIM)
    hr  = rng.poisson(hp["reds"],    N_SIM); ar = rng.poisson(ap["reds"],     N_SIM)
    hf  = rng.poisson(hp["fouls"],   N_SIM); af = rng.poisson(ap["fouls"],    N_SIM)
    hs  = rng.poisson(hp["shots_on"],N_SIM); as_= rng.poisson(ap["shots_on"], N_SIM)
    scores={}
    for h,a in zip(hg,ag): k=f"{h}-{a}"; scores[k]=scores.get(k,0)+1
    return {"phw":p(np.sum(hg>ag)),"pd":p(np.sum(hg==ag)),"paw":p(np.sum(hg<ag)),
            "lh":round(lh,2),"la":round(la,2),
            "o25":p(np.sum(tot>2.5)),"u25":p(np.sum(tot<=2.5)),
            "btts":p(np.sum((hg>0)&(ag>0))),"no_btts":p(np.sum(~((hg>0)&(ag>0)))),
            "hc":round(np.mean(hc),2),"ac":round(np.mean(ac),2),"tc":round(np.mean(hc+ac),2),
            "co85":p(np.sum(hc+ac>8.5)),"cu85":p(np.sum(hc+ac<=8.5)),
            "hy":round(np.mean(hy),2),"ay":round(np.mean(ay),2),"ty":round(np.mean(hy+ay),2),
            "hr":round(np.mean(hr),2),"ar":round(np.mean(ar),2),"tr":round(np.mean(hr+ar),2),
            "hf":round(np.mean(hf),2),"af":round(np.mean(af),2),"tf":round(np.mean(hf+af),2),
            "hs":round(np.mean(hs),2),"as_":round(np.mean(as_),2),
            "top":[(s,p(c)) for s,c in sorted(scores.items(),key=lambda x:-x[1])[:9]],
            "lh_raw":lh,"la_raw":la}

# ================================================================
#  CONFIDENCE & PREDICTIONS
# ================================================================
def conf_info(c):
    if c>=80:   return("#3ecf8e","✅ ALTA",  "pc-high","b-high")
    elif c>=60: return("#f5c842","⚡ MEDIA", "pc-med", "b-med")
    else:       return("#f4622a","⚠️ BAJA",  "pc-low", "b-low")

def implied(odd):
    if not odd or odd<=0: return 0
    return round(100/odd,1)

def build_predictions(R, hn, an, odds=None):
    rows=[]
    # 1X2
    best=max([(R["phw"],f"Victoria {hn}"),(R["pd"],"Empate"),(R["paw"],f"Victoria {an}")],key=lambda x:x[0])
    c_adj=best[0]
    if odds:
        ok = odds.get("odd_home" if "Victoria "+hn==best[1] else
                      "odd_draw" if "Empate"==best[1] else "odd_away")
        if ok: c_adj=round(best[0]*0.65+implied(ok)*0.35,1)
    rows.append({"mkt":"Resultado 1X2","pick":best[1],"conf":c_adj,
                 "det":f"Local {R['phw']}% / Empate {R['pd']}% / Visita {R['paw']}%"})
    # O/U 2.5
    o,u=R["o25"],R["u25"]
    rows.append({"mkt":"Goles O/U 2.5",
                 "pick":"Mas de 2.5 goles" if o>=u else "Menos de 2.5 goles",
                 "conf":max(o,u),"det":f"Goles esperados: {round(R['lh']+R['la'],2)}"})
    # BTTS
    rows.append({"mkt":"Ambos Marcan BTTS",
                 "pick":"Si — Ambos anotan" if R["btts"]>=R["no_btts"] else "No — Alguno no anota",
                 "conf":max(R["btts"],R["no_btts"]),
                 "det":f"lambda local {R['lh']} / lambda visita {R['la']}"})
    # Corners
    co,cu=R["co85"],R["cu85"]
    rows.append({"mkt":"Corners O/U 8.5",
                 "pick":"Mas de 8.5 corners" if co>=cu else "Menos de 8.5 corners",
                 "conf":max(co,cu),"det":f"Total esperado: {R['tc']} corners"})
    # Doble oportunidad
    dc1=min(round(R["phw"]+R["pd"],1),99.0); dc2=min(round(R["paw"]+R["pd"],1),99.0)
    rows.append({"mkt":"Doble Oportunidad",
                 "pick":f"{hn} o Empate" if dc1>=dc2 else f"{an} o Empate",
                 "conf":max(dc1,dc2),"det":"Cubre dos resultados posibles"})
    # Tarjetas
    ty=R["ty"]; line=max(1,round(ty)-1)
    prob_y=min(95.0,max(5.0,round(50+(ty-line-0.5)*18,1)))
    rows.append({"mkt":f"Amarillas O {line}.5","pick":f"Mas de {line}.5 amarillas",
                 "conf":prob_y,"det":f"Total amarillas esperadas: {ty}"})
    # Marcador exacto
    top=R["top"][0]
    rows.append({"mkt":"Marcador Exacto","pick":f"Resultado {top[0]}",
                 "conf":top[1],"det":"Marcador mas frecuente en 10,000 simulaciones"})
    return sorted(rows,key=lambda x:-x["conf"])

# ================================================================
#  BET SUGGESTION ENGINE
# ================================================================
def kelly_criterion(prob, odd, bankroll=100, fraction=0.25):
    """Kelly fraction for optimal stake."""
    if not odd or odd <= 1: return 0
    q = 1 - prob/100
    b = odd - 1
    kelly = (b*(prob/100) - q) / b
    kelly = max(0, kelly) * fraction  # fractional Kelly (safer)
    return round(kelly * bankroll, 2)

def generate_bet_suggestion(preds, R, odds, hn, an, bankroll=100):
    """Generate a clear bet suggestion with stake recommendation."""
    # Filter only high-confidence predictions
    high_conf = [p for p in preds if p["conf"] >= 75]
    if not high_conf:
        return None

    best = high_conf[0]
    conf = best["conf"]
    pick = best["pick"]
    mkt  = best["mkt"]

    # Get corresponding odd
    odd_val = None
    if odds:
        if "Victoria " + hn in pick:   odd_val = odds.get("odd_home")
        elif "Empate"       in pick:    odd_val = odds.get("odd_draw")
        elif "Victoria " + an in pick:  odd_val = odds.get("odd_away")
        elif "Mas de 2.5"   in pick:    odd_val = odds.get("odd_over25")
        elif "Menos de 2.5" in pick:    odd_val = odds.get("odd_under25")

    # Kelly stake
    stake = kelly_criterion(conf, odd_val or 1.85, bankroll) if odd_val else None

    # Value bet check
    implied_prob = implied(odd_val) if odd_val else None
    value_bet    = (conf > implied_prob + 5) if implied_prob else None

    # Risk level
    if conf >= 85:   risk = ("BAJO",   "#3ecf8e")
    elif conf >= 75: risk = ("MEDIO",  "#f5c842")
    else:            risk = ("ALTO",   "#f4622a")

    # Build combo suggestion if 2+ high conf
    combo = None
    if len(high_conf) >= 2:
        combo_picks = [p["pick"] for p in high_conf[:2]]
        combo_conf  = round(high_conf[0]["conf"] * high_conf[1]["conf"] / 100, 1)
        combo = {"picks": combo_picks, "conf": combo_conf}

    return {
        "pick":      pick,
        "mkt":       mkt,
        "conf":      conf,
        "odd":       odd_val,
        "stake":     stake,
        "implied":   implied_prob,
        "value_bet": value_bet,
        "risk":      risk,
        "combo":     combo,
    }

def render_bet_suggestion(bet, hn, an, bankroll):
    if not bet: return
    color,_,_,_ = conf_info(bet["conf"])
    risk_lbl, risk_color = bet["risk"]
    value_html = ""
    if bet["value_bet"] is True:
        value_html = f'<div style="background:rgba(62,207,142,.15);border-radius:6px;padding:6px 12px;margin-top:6px;font-size:.8rem;color:#3ecf8e">💎 <b>VALUE BET DETECTADA</b> — Tu probabilidad ({bet["conf"]}%) supera la probabilidad implícita de la cuota ({bet["implied"]}%). Ventaja estadística.</div>'
    elif bet["value_bet"] is False:
        value_html = f'<div style="background:rgba(244,98,42,.1);border-radius:6px;padding:6px 12px;margin-top:6px;font-size:.8rem;color:#f4622a">⚠️ Sin ventaja de valor — La cuota ya descuenta esta probabilidad.</div>'

    odd_txt  = f"{bet['odd']:.2f}" if bet['odd'] else "N/D (sin cuota en vivo)"
    stake_txt= f"${bet['stake']:.2f} de ${bankroll}" if bet['stake'] else "Calcula segun cuota disponible"

    combo_html = ""
    if bet.get("combo"):
        combo_html = f"""
        <div style="margin-top:14px;padding:12px;background:#0a1a0a;border-radius:8px;border:1px solid #3ecf8e22">
          <div style="font-size:.72rem;color:#404060;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px">Combinada sugerida (2 selecciones)</div>
          <div style="font-size:.88rem;font-weight:600">{"  +  ".join(bet['combo']['picks'])}</div>
          <div style="font-size:.75rem;color:#505070;margin-top:3px">Confianza combinada: {bet['combo']['conf']}% — mayor cuota, mayor riesgo</div>
        </div>"""

    st.markdown(f"""
    <div class="bet-box">
      <h3>SUGERENCIA DE APUESTA</h3>
      <div class="bet-row">
        <span class="bet-label">Mercado recomendado</span>
        <span class="bet-val">{bet['mkt']}</span>
      </div>
      <div class="bet-row">
        <span class="bet-label">Seleccion</span>
        <span style="font-weight:700;font-size:.95rem;color:#e2e2f0">{bet['pick']}</span>
      </div>
      <div class="bet-row">
        <span class="bet-label">Confianza estadistica</span>
        <span style="font-family:'Bebas Neue',sans-serif;font-size:1.5rem;color:{color}">{bet['conf']}%</span>
      </div>
      <div class="bet-row">
        <span class="bet-label">Cuota de referencia</span>
        <span class="bet-val">{odd_txt}</span>
      </div>
      <div class="bet-row">
        <span class="bet-label">Nivel de riesgo</span>
        <span style="color:{risk_color};font-weight:700">{risk_lbl}</span>
      </div>
      <div class="bet-row">
        <span class="bet-label">Stake sugerido (Kelly x0.25)</span>
        <span style="color:#f5c842;font-weight:700">{stake_txt}</span>
      </div>
      {value_html}
      {combo_html}
      <div class="warning-bet">
        ⚠️ <b>Advertencia:</b> Las sugerencias son estadisticas, no garantias. 
        Nunca apuestes mas de lo que puedes perder. Juega con responsabilidad.
        El criterio de Kelly es orientativo — ajusta segun tu bankroll real.
      </div>
    </div>""", unsafe_allow_html=True)

# ================================================================
#  UI HELPERS
# ================================================================
def render_pred(pred):
    color,badge,pc_cls,b_cls = conf_info(pred["conf"])
    c=pred["conf"]; w=int(min(c,100))
    warn=""
    if c<60:
        warn=f'<div style="margin-top:8px;padding:5px 10px;background:rgba(244,98,42,.1);border-radius:6px;font-size:.75rem;color:#f4622a">⚠️ RIESGO ALTO ({c}%) — Evita apostar en este mercado.</div>'
    elif c<80:
        warn=f'<div style="margin-top:8px;padding:5px 10px;background:rgba(245,200,66,.08);border-radius:6px;font-size:.75rem;color:#f5c842">⚡ Confianza media ({c}%) — Analiza antes de apostar.</div>'
    st.markdown(f"""
    <div class="pc {pc_cls}">
      <div style="min-width:120px"><div class="pc-mkt">{pred['mkt']}</div></div>
      <div style="flex:1">
        <div class="pc-pick">{pred['pick']}</div>
        <div class="pc-det">{pred['det']}</div>
      </div>
      <div style="text-align:center;min-width:95px">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:1.9rem;color:{color};line-height:1">{c}%</div>
        <div style="background:#151525;border-radius:99px;height:6px;overflow:hidden;margin:4px 0">
          <div style="width:{w}%;height:100%;background:{color};border-radius:99px"></div>
        </div>
        <span class="badge {b_cls}">{badge}</span>
      </div>
    </div>{warn}""", unsafe_allow_html=True)

def prob_bar(label,val,color):
    st.markdown(f"""<div class="prow">
      <div class="prow-lbl">{label} — <b style="color:{color}">{val}%</b></div>
      <div class="pbar"><div class="pfill" style="width:{min(val,100)}%;background:{color}"></div></div>
    </div>""", unsafe_allow_html=True)

def kpi(val,label,col):
    col.markdown(f'<div class="kpi"><div class="kpi-val">{val}</div><div class="kpi-lbl">{label}</div></div>',unsafe_allow_html=True)

def sec(t): st.markdown(f'<div class="sec">{t}</div>',unsafe_allow_html=True)

def pill(name,active):
    cls="on" if active else "off"; icon="✅" if active else "○"
    return f'<span class="pill {cls}">{icon} {name}</span>'

# ================================================================
#  SIDEBAR
# ================================================================
with st.sidebar:
    st.markdown("## APIs")
    fd_k  = st.text_input("football-data.org Key", value=st.session_state.get("fd_key",""),  type="password", help="Registrate gratis en football-data.org")
    as_k  = st.text_input("api-sports.io Key",      value=st.session_state.get("as_key",""),  type="password", help="Tu key actual de api-sports.io")
    od_k  = st.text_input("the-odds-api Key",       value=st.session_state.get("odds_key",""),type="password", help="Gratis en the-odds-api.com")
    if fd_k:  st.session_state["fd_key"]   = fd_k
    if as_k:  st.session_state["as_key"]   = as_k
    if od_k:  st.session_state["odds_key"] = od_k

    st.markdown("---")
    bankroll = st.number_input("Bankroll para Kelly ($)", min_value=10, max_value=100000,
                                value=st.session_state.get("bankroll",100), step=10)
    st.session_state["bankroll"] = bankroll

    st.markdown("---")
    if st.button("Probar conexiones"):
        if get_fd_key():
            try:
                r=requests.get(f"{FD_BASE}/competitions",headers=_fd_headers(),timeout=8)
                st.success(f"football-data: HTTP {r.status_code}")
            except Exception as e: st.error(f"FD: {e}")
        if get_as_key():
            try:
                r=requests.get(f"{AS_BASE}/status",headers=_as_headers(),timeout=8)
                d=r.json().get("response",{})
                req=d.get("requests",{})
                st.success(f"api-sports: {req.get('current',0)}/{req.get('limit_day',100)} req hoy")
            except Exception as e: st.error(f"AS: {e}")
        if get_odds_key():
            try:
                r=requests.get(f"{ODDS_BASE}/sports",params={"apiKey":get_odds_key()},timeout=8)
                st.success(f"odds-api: HTTP {r.status_code}")
            except Exception as e: st.error(f"Odds: {e}")
        try:
            r=requests.get("https://api.open-meteo.com/v1/forecast",
                           params={"latitude":51.5,"longitude":-0.1,"current":"temperature_2m"},timeout=8)
            st.success(f"open-meteo: {r.json().get('current',{}).get('temperature_2m','?')}C")
        except: st.error("open-meteo: sin respuesta")
        try:
            r=requests.get("http://api.clubelo.com/Barcelona",timeout=8)
            st.success("clubelo.com: OK" if r.status_code==200 else f"clubelo: {r.status_code}")
        except: st.error("clubelo: sin respuesta")

    st.markdown("---")
    st.markdown("**Leyenda:**")
    st.markdown("✅ **ALTA** >= 80%")
    st.markdown("⚡ **MEDIA** 60-79%")
    st.markdown("⚠️ **BAJA** < 60%")
    st.markdown("💎 **VALUE BET** = Ventaja vs cuota")
    st.markdown("---")
    st.markdown("**Fuentes:**")
    fd_ok=bool(get_fd_key()); as_ok=bool(get_as_key()); od_ok=bool(get_odds_key())
    st.markdown(f"{'✅' if fd_ok else '○'} football-data.org")
    st.markdown(f"{'✅' if as_ok else '○'} api-sports.io")
    st.markdown(f"{'✅' if od_ok else '○'} the-odds-api.com")
    st.markdown("✅ open-meteo.com")
    st.markdown("✅ clubelo.com")

# ================================================================
#  MAIN
# ================================================================
st.markdown(f"""
<div class="hero">
  <h1>FOOTBALL ORACLE PRO</h1>
  <div class="sub">v3.0 · Multi-API · Latam + Europa + Mundial · Sugerencias de apuesta · 45 dias</div>
  <div class="apis">
    {pill("football-data.org", fd_ok)}
    {pill("api-sports.io",     as_ok)}
    {pill("the-odds-api",      od_ok)}
    {pill("open-meteo",        True)}
    {pill("clubelo.com",       True)}
  </div>
</div>
""", unsafe_allow_html=True)

if not fd_ok and not as_ok:
    st.warning("Necesitas al menos UNA key activa. Pegala en el sidebar (icono menu arriba).")
    with st.expander("Como obtener las keys gratis"):
        st.markdown("""
**1. football-data.org** (recomendado para Europa)
- Ve a: `football-data.org/client/register`
- Registrate gratis → key llega al correo en minutos
- Cubre: Premier League, La Liga, Bundesliga, Serie A, Ligue 1, UCL, Copa Libertadores

**2. api-sports.io** (ya la tienes — cubre Latam completo)
- Tu key actual funciona para Colombia, Argentina, Brasil, Mexico y mas

**3. the-odds-api.com** (cuotas en vivo — 500 req/mes gratis)
- Ve a: `the-odds-api.com/#get-access`
- Activa el Value Bet detector y el Kelly Criterion

**4. open-meteo.com + clubelo.com** — Ya funcionan, sin registro
        """)
    st.stop()

# ── STEP 1: Liga ──────────────────────────────────────────────────
sec("① ELIGE LA LIGA")

all_leagues = sorted(set(list(FD_COMPETITIONS.keys()) + list(AS_LEAGUES.keys())))

# Group display
latam = sorted([l for l in all_leagues if any(x in l for x in ["BetPlay","Profesional","Brasil","MX","CHI","PER","URU","Libertadores","Sudamericana","Copa America","CONC"])])
europa= sorted([l for l in all_leagues if l not in latam and "World Cup" not in l and "FIFA" not in l and "Africa" not in l and "CONCACAF" not in l])
global_= sorted([l for l in all_leagues if l not in latam and l not in europa])

col1, col2 = st.columns(2)
with col1:
    region = st.selectbox("Region", ["Europa", "Latinoamerica", "Mundial / Selecciones"], label_visibility="collapsed")
with col2:
    if region == "Europa":          league_list = europa
    elif region == "Latinoamerica": league_list = latam
    else:                           league_list = global_
    league_name = st.selectbox("Liga", league_list, label_visibility="collapsed")

# ── STEP 2: Partido ───────────────────────────────────────────────
sec("② ELIGE EL PARTIDO")
with st.spinner(f"Buscando partidos en los proximos {DAYS_AHEAD} dias..."):
    fixtures, source_used = load_fixtures_smart(league_name)

if not fixtures:
    st.warning(f"No se encontraron partidos para **{league_name}** en los proximos {DAYS_AHEAD} dias.")
    with st.expander("Info de depuracion"):
        lg = AS_LEAGUES.get(league_name,{})
        if as_ok and lg:
            try:
                today=datetime.now().strftime("%Y-%m-%d")
                future=(datetime.now()+timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
                r=requests.get(f"{AS_BASE}/fixtures",headers=_as_headers(),
                               params={"league":lg["id"],"season":lg["season"],"from":today,"to":future},timeout=12)
                d=r.json()
                st.code(f"HTTP {r.status_code}\nerrors: {d.get('errors')}\nresults: {d.get('results',0)}",language="json")
            except Exception as e: st.error(str(e))
    st.stop()

st.success(f"{len(fixtures)} partido(s) encontrados — fuente: **{source_used}**")
match_map = {f["display"]:f for f in fixtures}
sel = st.selectbox("Partido", list(match_map.keys()), label_visibility="collapsed")
M   = match_map[sel]

st.markdown(f"""
<div class="match">
  <span class="tn">{M['home']}</span>
  &nbsp;&nbsp;<span class="vs">VS</span>&nbsp;&nbsp;
  <span class="tn">{M['away']}</span>
  <br><span style="color:#404060;font-size:.82rem">📅 {M['date']}  ·  <span class="src-tag">{M.get('source','')}</span></span>
</div>
""", unsafe_allow_html=True)

# ── STEP 3: Analyze ───────────────────────────────────────────────
if st.button(f"ANALIZAR CON MONTE CARLO — 10,000 SIMULACIONES"):
    with st.spinner("Cargando datos de todas las fuentes y simulando..."):
        # Load stats with smart ID sync
        data = load_team_stats_smart(M, league_name)

        hp_fd = profile_from_fd(data["home"]["fd_matches"], M.get("home_id"))
        ap_fd = profile_from_fd(data["away"]["fd_matches"], M.get("away_id"))
        hp_as = profile_from_as_stats(data["home"]["as_stats"], is_home=True)
        ap_as = profile_from_as_stats(data["away"]["as_stats"], is_home=False)

        # Enrich with recent fixtures
        hp_fd = enrich_from_as_fixtures(hp_fd, data["home"]["as_fixtures"], data["home"]["id_as"]) if hp_fd else hp_fd
        ap_fd = enrich_from_as_fixtures(ap_fd, data["away"]["as_fixtures"], data["away"]["id_as"]) if ap_fd else ap_fd

        hp = merge_profiles(hp_fd, hp_as)
        ap = merge_profiles(ap_fd, ap_as)

        # Odds
        sport_key = ODDS_SPORT_MAP.get(league_name)
        odds = get_odds(sport_key, M["home"], M["away"]) if od_ok and sport_key else None

        # Weather
        coords = STADIUM_COORDS.get(league_name, (51.5,-0.1))
        weather = get_weather(coords[0], coords[1])

        # Elo (for national team matches)
        home_elo = get_elo(M["home"]); away_elo = get_elo(M["away"])

        # Monte Carlo
        R     = run_mc(hp, ap, weather, home_elo, away_elo)
        preds = build_predictions(R, M["home"], M["away"], odds)
        bet   = generate_bet_suggestion(preds, R, odds, M["home"], M["away"], st.session_state.get("bankroll",100))

    st.success("10,000 simulaciones completadas")

    # ── DATA QUALITY REPORT ───────────────────────────────────
    sec("CALIDAD DE DATOS")
    c1,c2,c3 = st.columns(3)
    with c1:
        games_h = int(hp.get("n_games",0))
        q_color = "#3ecf8e" if games_h>=10 else "#f5c842" if games_h>=5 else "#f4622a"
        st.markdown(f'<div class="kpi"><div class="kpi-val" style="color:{q_color}">{games_h}</div><div class="kpi-lbl">Partidos analizados {M["home"][:12]}</div></div>', unsafe_allow_html=True)
    with c2:
        games_a = int(ap.get("n_games",0))
        q_color2= "#3ecf8e" if games_a>=10 else "#f5c842" if games_a>=5 else "#f4622a"
        st.markdown(f'<div class="kpi"><div class="kpi-val" style="color:{q_color2}">{games_a}</div><div class="kpi-lbl">Partidos analizados {M["away"][:12]}</div></div>', unsafe_allow_html=True)
    with c3:
        sources_active = sum([bool(get_fd_key()),bool(get_as_key()),bool(get_odds_key()),True,True])
        st.markdown(f'<div class="kpi"><div class="kpi-val">{sources_active}/5</div><div class="kpi-lbl">Fuentes de datos activas</div></div>', unsafe_allow_html=True)

    col1,col2 = st.columns(2)
    col1.markdown(f"**{M['home']}:** {hp.get('source','N/A')}")
    col2.markdown(f"**{M['away']}:** {ap.get('source','N/A')}")

    if games_h < 5 or games_a < 5:
        st.warning("Datos insuficientes (< 5 partidos). Activa mas fuentes en el sidebar para mejorar la precision.")

    # Weather & Elo
    if weather:
        icon = "🌧️" if weather["rain"]>2 else "💨" if weather["wind"]>30 else "☀️" if weather["code"]<3 else "☁️"
        st.info(f"{icon} **Clima:** {weather['cond']} | {weather['temp']}°C | Lluvia: {weather['rain']}mm | Viento: {weather['wind']}km/h — ajustado en el modelo")

    if home_elo and away_elo:
        diff = round(home_elo["elo"] - away_elo["elo"])
        fav  = M["home"] if diff>0 else M["away"]
        st.markdown(f'<div class="elo-box">🏆 <b>Elo Rating</b> — {M["home"]}: <b>{round(home_elo["elo"])}</b> | {M["away"]}: <b>{round(away_elo["elo"])}</b> | Diferencia: <b>{abs(diff)}</b> puntos a favor de <b>{fav}</b> (considerado en Monte Carlo)</div>', unsafe_allow_html=True)

    # ── CUOTAS EN VIVO ────────────────────────────────────────
    if odds:
        sec("CUOTAS EN TIEMPO REAL")
        st.markdown(f'<div style="font-size:.75rem;color:#505070;margin-bottom:8px">Fuente: {odds.get("bookmaker","")} via the-odds-api.com</div>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        for col,label,key in [(c1,M["home"][:14],"odd_home"),(c2,"Empate","odd_draw"),(c3,M["away"][:14],"odd_away")]:
            ov = odds.get(key,0)
            kpi(f"{ov:.2f}" if ov else "N/D", f"{label}\n(impl. {implied(ov)}%)", col)

    # ── BET SUGGESTION ────────────────────────────────────────
    sec("SUGERENCIA DE APUESTA")
    render_bet_suggestion(bet, M["home"], M["away"], st.session_state.get("bankroll",100))

    # ── PREDICCIONES ──────────────────────────────────────────
    sec("PREDICCIONES CON NIVEL DE CONFIANZA")
    high=[p for p in preds if p["conf"]>=80]
    med =[p for p in preds if 60<=p["conf"]<80]
    low =[p for p in preds if p["conf"]<60]
    c1,c2,c3=st.columns(3)
    kpi(str(len(high)),"Alta confianza >=80%",c1)
    kpi(str(len(med)), "Confianza media 60-79%",c2)
    kpi(str(len(low)), "Baja confianza <60%",c3)
    st.markdown("<br>",unsafe_allow_html=True)
    if high:
        st.markdown("#### ✅ Alta confianza (>=80%)")
        for p in high: render_pred(p)
    if med:
        st.markdown("#### ⚡ Confianza media (60-79%)")
        for p in med: render_pred(p)
    if low:
        st.markdown("#### ⚠️ Baja confianza (<60%) — Evitar")
        for p in low: render_pred(p)

    # ── 1X2 ──────────────────────────────────────────────────
    sec("PROBABILIDADES 1X2")
    prob_bar(f"Local: {M['home']}",  R["phw"],"#3ecf8e")
    prob_bar("Empate",               R["pd"], "#f5c842")
    prob_bar(f"Visita: {M['away']}", R["paw"],"#f4622a")

    # ── GOLES ─────────────────────────────────────────────────
    sec("GOLES PROYECTADOS")
    c1,c2,c3,c4=st.columns(4)
    kpi(R["lh"],         f"Goles esp.\n{M['home'][:12]}",c1)
    kpi(R["la"],         f"Goles esp.\n{M['away'][:12]}",c2)
    kpi(f"{R['o25']}%",  "Mas de 2.5 Goles",            c3)
    kpi(f"{R['btts']}%", "Ambos Anotan BTTS",            c4)

    # ── MARCADORES ────────────────────────────────────────────
    sec("MARCADORES MAS PROBABLES")
    st.dataframe(pd.DataFrame(R["top"],columns=["Marcador","Prob %"])
                 .style.background_gradient(subset=["Prob %"],cmap="Oranges")
                 .format({"Prob %":"{:.1f}%"}),
                 use_container_width=True, hide_index=True)

    # ── CORNERS ───────────────────────────────────────────────
    sec("CORNERS")
    c1,c2,c3,c4=st.columns(4)
    kpi(R["hc"],          f"Corners {M['home'][:12]}",c1)
    kpi(R["ac"],          f"Corners {M['away'][:12]}",c2)
    kpi(R["tc"],          "Total Corners",            c3)
    kpi(f"{R['co85']}%",  "Mas de 8.5",               c4)

    # ── TARJETAS ──────────────────────────────────────────────
    sec("TARJETAS")
    c1,c2,c3,c4=st.columns(4)
    kpi(R["hy"], f"Amarillas {M['home'][:12]}",c1)
    kpi(R["ay"], f"Amarillas {M['away'][:12]}",c2)
    kpi(R["ty"], "Total Amarillas",             c3)
    kpi(R["tr"], "Rojas Totales",               c4)

    # ── FALTAS & TIROS ────────────────────────────────────────
    sec("FALTAS Y TIROS A PUERTA")
    c1,c2=st.columns(2)
    with c1:
        st.dataframe(pd.DataFrame({"Equipo":[M["home"],M["away"],"TOTAL"],
            "Faltas":[R["hf"],R["af"],R["tf"]]}), use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(pd.DataFrame({"Equipo":[M["home"],M["away"]],
            "Tiros a puerta":[R["hs"],R["as_"]]}), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Analisis estadistico educativo. Alta confianza = mayor probabilidad estadistica, NO garantia. Apuesta con responsabilidad y nunca mas de lo que puedes perder.")
