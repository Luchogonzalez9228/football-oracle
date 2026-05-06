# ================================================================
#  ⚽ FOOTBALL ORACLE PRO — Arquitectura Multi-API
#  4 fuentes de datos | Monte Carlo 10,000 sims | Sin pago
# ================================================================
#
#  FUENTES DE DATOS (todas GRATUITAS):
#  1. football-data.org  — fixtures, resultados, tablas (Free tier)
#  2. api-sports.io      — estadísticas de equipo (Free tier)
#  3. the-odds-api.com   — cuotas en tiempo real (Free 500 req/mes)
#  4. open-meteo.com     — clima del estadio (100% gratis, sin key)
#
#  PEGA TUS KEYS ABAJO — solo las que tengas, el resto es opcional
# ================================================================

import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# ─── KEYS — pega las tuyas aquí (o en Streamlit Secrets) ────────
FD_KEY    = "a2aef808a68d4cd6ba2ad97f9953ec81"   # football-data.org  → https://www.football-data.org/client/register
APISPORTS = "70cb24441a57cc0a28c2fd7dd3b76110"   # api-sports.io      → https://dashboard.api-sports.io
ODDS_KEY  = "f028e4d3689b54c609ce7137fc6a40ba"   # the-odds-api.com   → https://the-odds-api.com/#get-access
# open-meteo no necesita key
# ────────────────────────────────────────────────────────────────

N_SIM = 10_000

# ── Load from Streamlit Secrets if available ─────────────────────
def _secret(k, fallback=""):
    try:    return st.secrets.get(k, fallback)
    except: return fallback

def get_fd_key():    return st.session_state.get("fd_key",    _secret("FD_KEY",    FD_KEY))
def get_as_key():    return st.session_state.get("as_key",    _secret("APISPORTS", APISPORTS))
def get_odds_key():  return st.session_state.get("odds_key",  _secret("ODDS_KEY",  ODDS_KEY))

# ================================================================
st.set_page_config(page_title="Football Oracle PRO", page_icon="⚽",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,700&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#07070f;color:#e2e2f0;}
/* Hero */
.hero{background:linear-gradient(135deg,#0d0d1c 0%,#180808 100%);
  border:1px solid #252535;border-radius:18px;padding:32px 36px 24px;
  margin-bottom:28px;position:relative;overflow:hidden;}
.hero::after{content:'';position:absolute;top:-80px;right:-80px;
  width:300px;height:300px;background:radial-gradient(circle,rgba(244,98,42,.12),transparent 70%);}
.hero h1{font-family:'Bebas Neue',sans-serif;font-size:clamp(2.2rem,6vw,3.5rem);
  color:#f4622a;letter-spacing:3px;line-height:.95;}
.hero .sub{color:#606080;font-size:.82rem;margin-top:8px;letter-spacing:.5px;}
.hero .apis{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;}
.api-pill{background:#13131f;border:1px solid #252535;border-radius:99px;
  padding:3px 10px;font-size:.72rem;color:#7070a0;}
.api-pill.active{border-color:#3ecf8e44;color:#3ecf8e;background:rgba(62,207,142,.08);}
.api-pill.inactive{border-color:#f4622a33;color:#f4622a55;}
/* Sections */
.sec{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#f4622a;
  letter-spacing:2px;border-bottom:1px solid #1e1e2e;padding-bottom:5px;margin:22px 0 14px;}
/* Cards */
.kpi{background:#0f0f1c;border:1px solid #1e1e2e;border-radius:12px;
  padding:14px 16px;text-align:center;margin-bottom:6px;}
.kpi-val{font-family:'Bebas Neue',sans-serif;font-size:2rem;color:#f5c842;line-height:1.1;}
.kpi-lbl{font-size:.65rem;color:#404060;letter-spacing:2px;text-transform:uppercase;margin-top:2px;}
/* Prediction cards */
.pc{border-radius:12px;padding:15px 18px;margin-bottom:9px;
  display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.pc-high{background:#09150f;border:1px solid #3ecf8e33;}
.pc-med {background:#141108;border:1px solid #f5c84233;}
.pc-low {background:#150808;border:1px solid #f4622a33;}
.pc-mkt {font-size:.65rem;color:#404060;letter-spacing:2px;text-transform:uppercase;min-width:110px;}
.pc-pick{font-weight:600;font-size:.9rem;flex:1;}
.pc-det {font-size:.72rem;color:#505070;margin-top:2px;}
.badge{display:inline-block;border-radius:6px;padding:2px 9px;
  font-size:.68rem;font-weight:700;letter-spacing:.5px;margin-top:3px;}
.b-high{background:rgba(62,207,142,.15);color:#3ecf8e;}
.b-med {background:rgba(245,200,66,.12);color:#f5c842;}
.b-low {background:rgba(244,98,42,.15);color:#f4622a;}
/* Prob bar */
.prow{margin:7px 0;}
.prow-lbl{font-size:.78rem;color:#8080a0;margin-bottom:2px;}
.pbar{background:#151525;border-radius:99px;height:9px;overflow:hidden;}
.pfill{height:100%;border-radius:99px;}
/* Matchup */
.match{background:#0f0f1c;border:1px solid #1e1e2e;border-radius:14px;
  padding:20px;text-align:center;margin:14px 0;}
.tn{font-family:'Bebas Neue',sans-serif;font-size:1.7rem;color:#e2e2f0;}
.vs{font-family:'Bebas Neue',sans-serif;font-size:2.2rem;color:#f4622a;}
/* Source tag */
.src{font-size:.65rem;background:#13131f;border:1px solid #1e1e2e;
  border-radius:4px;padding:1px 6px;color:#505070;margin-left:6px;}
/* Odds box */
.odds-box{background:#0f0f1c;border:1px solid #252535;border-radius:10px;
  padding:12px 16px;margin:8px 0;}
.odds-row{display:flex;justify-content:space-between;align-items:center;
  padding:5px 0;border-bottom:1px solid #1a1a2a;}
.odds-row:last-child{border-bottom:none;}
.odds-label{font-size:.8rem;color:#8080a0;}
.odds-val{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#f5c842;}
.odds-implied{font-size:.7rem;color:#505070;}
/* Buttons */
.stButton>button{background:#f4622a!important;color:#fff!important;
  border:none!important;border-radius:10px!important;font-weight:700!important;
  padding:13px 20px!important;width:100%!important;font-size:.95rem!important;letter-spacing:1px!important;}
.stButton>button:hover{background:#c04a1e!important;}
#MainMenu,footer,header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ================================================================
#  DATA SOURCES
# ================================================================

# ── SOURCE 1: football-data.org ───────────────────────────────────
FD_BASE = "https://api.football-data.org/v4"
FD_COMPETITIONS = {
    "Premier League (ENG)":             "PL",
    "La Liga (ESP)":                     "PD",
    "Bundesliga (GER)":                  "BL1",
    "Serie A (ITA)":                     "SA",
    "Ligue 1 (FRA)":                     "FL1",
    "Eredivisie (NED)":                  "DED",
    "Primeira Liga (POR)":               "PPL",
    "Championship (ENG)":                "ELC",
    "UEFA Champions League":             "CL",
    "UEFA Europa League":                "EL",
    "Copa Libertadores":                 "CLI",
    "World Cup Qualifying (S.America)":  "WC",
    "FIFA World Cup 2026":               "WC",   # Fase de grupos / torneo
    "Euro 2024 / Nations League":        "EC",   # Competiciones UEFA de selecciones
}

@st.cache_data(ttl=1800, show_spinner=False)
def fd_get_fixtures(comp_code):
    key = get_fd_key()
    if not key:
        return []
    today = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            f"{FD_BASE}/competitions/{comp_code}/matches",
            headers={"X-Auth-Token": key},
            params={"dateFrom": today, "dateTo": future, "status": "SCHEDULED"},
            timeout=12
        )
        if r.status_code != 200:
            return []
        matches = r.json().get("matches", [])
        result = []
        for m in matches:
            home = m.get("homeTeam", {}).get("shortName") or m.get("homeTeam", {}).get("name", "?")
            away = m.get("awayTeam", {}).get("shortName") or m.get("awayTeam", {}).get("name", "?")
            home_id = m.get("homeTeam", {}).get("id")
            away_id = m.get("awayTeam", {}).get("id")
            date_str = (m.get("utcDate","")[:10])
            result.append({
                "id": m.get("id"), "date": date_str,
                "home": home, "away": away,
                "home_id": home_id, "away_id": away_id,
                "comp": comp_code, "source": "football-data.org",
                "display": f"📅 {date_str}  |  {home}  vs  {away}"
            })
        return result
    except:
        return []

@st.cache_data(ttl=3600, show_spinner=False)
def fd_get_team_matches(team_id, limit=15):
    key = get_fd_key()
    if not key or not team_id:
        return []
    try:
        r = requests.get(
            f"{FD_BASE}/teams/{team_id}/matches",
            headers={"X-Auth-Token": key},
            params={"status": "FINISHED", "limit": limit},
            timeout=12
        )
        if r.status_code != 200:
            return []
        return r.json().get("matches", [])
    except:
        return []

# ── SOURCE 2: api-sports.io ───────────────────────────────────────
AS_BASE = "https://v3.football.api-sports.io"
AS_LEAGUES = {
    "Premier League (ENG)":             {"id": 39,  "season": 2024},
    "La Liga (ESP)":                     {"id": 140, "season": 2024},
    "Bundesliga (GER)":                  {"id": 78,  "season": 2024},
    "Serie A (ITA)":                     {"id": 135, "season": 2024},
    "Ligue 1 (FRA)":                     {"id": 61,  "season": 2024},
    "Eredivisie (NED)":                  {"id": 88,  "season": 2024},
    "Primeira Liga (POR)":               {"id": 94,  "season": 2024},
    "Championship (ENG)":                {"id": 40,  "season": 2024},
    "UEFA Champions League":             {"id": 2,   "season": 2024},
    "UEFA Europa League":                {"id": 3,   "season": 2024},
    "Copa Libertadores":                 {"id": 13,  "season": 2025},
    "World Cup Qualifying (S.America)":  {"id": 29,  "season": 2025},
    "World Cup Qualifying (Europe)":     {"id": 32,  "season": 2025},
    "World Cup Qualifying (CONCACAF)":   {"id": 31,  "season": 2025},
    "World Cup Qualifying (Africa)":     {"id": 30,  "season": 2025},
    "World Cup Qualifying (Asia)":       {"id": 36,  "season": 2025},
    "FIFA World Cup 2026":               {"id": 1,   "season": 2026},
    "Euro 2024 / Nations League":        {"id": 5,   "season": 2024},
    "Copa America 2024":                 {"id": 9,   "season": 2024},
    "Africa Cup of Nations":             {"id": 6,   "season": 2025},
    "CONCACAF Gold Cup":                 {"id": 20,  "season": 2025},
}

@st.cache_data(ttl=3600, show_spinner=False)
def as_get_fixtures(league_id, season):
    key = get_as_key()
    if not key:
        return []
    today  = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    headers = {"x-apisports-key": key}
    for params in [
        {"league": league_id, "season": season, "from": today, "to": future},
        {"league": league_id, "season": season, "from": today, "to": future, "status": "NS"},
    ]:
        try:
            r = requests.get(f"{AS_BASE}/fixtures", headers=headers, params=params, timeout=12)
            data = r.json().get("response", [])
            if data:
                result = []
                for f in data:
                    fix   = f.get("fixture", {})
                    teams = f.get("teams",   {})
                    st_s  = fix.get("status", {}).get("short","")
                    if st_s in ("FT","AET","PEN","CANC","ABD"):
                        continue
                    result.append({
                        "id":      fix.get("id"),
                        "date":    fix.get("date","")[:10],
                        "home":    teams.get("home",{}).get("name","?"),
                        "away":    teams.get("away",{}).get("name","?"),
                        "home_id": teams.get("home",{}).get("id"),
                        "away_id": teams.get("away",{}).get("id"),
                        "season":  season,
                        "source":  "api-sports.io",
                        "display": f"📅 {fix.get('date','')[:10]}  |  {teams.get('home',{}).get('name','?')}  vs  {teams.get('away',{}).get('name','?')}",
                    })
                if result:
                    return result
        except:
            continue
    return []

@st.cache_data(ttl=3600, show_spinner=False)
def as_get_stats(team_id, league_id, season):
    key = get_as_key()
    if not key:
        return {}
    headers = {"x-apisports-key": key}
    for s in [season, season-1]:
        try:
            r = requests.get(f"{AS_BASE}/teams/statistics",
                             headers=headers,
                             params={"team": team_id, "league": league_id, "season": s},
                             timeout=12)
            data = r.json().get("response", {})
            if data:
                return data
        except:
            continue
    return {}

# ── SOURCE 3: the-odds-api.com ────────────────────────────────────
ODDS_BASE = "https://api.the-odds-api.com/v4"
ODDS_SPORT_MAP = {
    "Premier League (ENG)":             "soccer_england_league1",
    "La Liga (ESP)":                     "soccer_spain_la_liga",
    "Bundesliga (GER)":                  "soccer_germany_bundesliga",
    "Serie A (ITA)":                     "soccer_italy_serie_a",
    "Ligue 1 (FRA)":                     "soccer_france_ligue_one",
    "UEFA Champions League":             "soccer_uefa_champs_league",
    "UEFA Europa League":                "soccer_uefa_europa_league",
    "FIFA World Cup 2026":               "soccer_fifa_world_cup",
    "World Cup Qualifying (Europe)":     "soccer_uefa_european_championship",
    "World Cup Qualifying (S.America)":  "soccer_conmebol_copa_america",
    "Copa America 2024":                 "soccer_conmebol_copa_america",
}

@st.cache_data(ttl=1800, show_spinner=False)
def get_odds(sport_key, home_team, away_team):
    key = get_odds_key()
    if not key or not sport_key:
        return None
    try:
        r = requests.get(
            f"{ODDS_BASE}/sports/{sport_key}/odds",
            params={"apiKey": key, "regions": "eu", "markets": "h2h,totals",
                    "oddsFormat": "decimal"},
            timeout=12
        )
        if r.status_code != 200:
            return None
        events = r.json()
        ht_lower = home_team.lower()
        at_lower = away_team.lower()
        for ev in events:
            ht = ev.get("home_team","").lower()
            at = ev.get("away_team","").lower()
            if (ht_lower[:6] in ht or ht[:6] in ht_lower) and \
               (at_lower[:6] in at or at[:6] in at_lower):
                bookmakers = ev.get("bookmakers", [])
                if not bookmakers:
                    return None
                bk = bookmakers[0]
                result = {"home": home_team, "away": away_team, "bookmaker": bk.get("title","")}
                for mkt in bk.get("markets", []):
                    if mkt["key"] == "h2h":
                        for o in mkt.get("outcomes",[]):
                            if o["name"] == ev["home_team"]:  result["odd_home"] = o["price"]
                            elif o["name"] == "Draw":          result["odd_draw"] = o["price"]
                            elif o["name"] == ev["away_team"]: result["odd_away"] = o["price"]
                    elif mkt["key"] == "totals":
                        for o in mkt.get("outcomes",[]):
                            if o["name"] == "Over":  result["odd_over25"] = o["price"]
                            elif o["name"]=="Under": result["odd_under25"] = o["price"]
                return result
        return None
    except:
        return None

# ── SOURCE 4: open-meteo.com (no key needed) ─────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def get_weather(lat=51.5, lon=-0.1, label="Estadio"):
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon,
                    "current": "temperature_2m,precipitation,windspeed_10m,weathercode",
                    "timezone": "auto"},
            timeout=8
        )
        c = r.json().get("current",{})
        code = c.get("weathercode", 0)
        cond = "Despejado" if code < 3 else "Nublado" if code < 50 else "Lluvioso" if code < 80 else "Tormenta"
        return {
            "temp":   c.get("temperature_2m","N/A"),
            "rain":   c.get("precipitation", 0),
            "wind":   c.get("windspeed_10m", 0),
            "cond":   cond,
            "code":   code,
        }
    except:
        return None

# Coords of main stadiums
STADIUM_COORDS = {
    "Premier League (ENG)":             (51.50,  -0.12),
    "La Liga (ESP)":                     (40.45,  -3.69),
    "Bundesliga (GER)":                  (48.21,  11.62),
    "Serie A (ITA)":                     (45.47,   9.12),
    "Ligue 1 (FRA)":                     (48.85,   2.35),
    "Eredivisie (NED)":                  (52.31,   4.94),
    "Primeira Liga (POR)":               (38.75,  -9.18),
    "UEFA Champions League":             (51.50,  -0.12),
    "UEFA Europa League":                (51.50,  -0.12),
    "Copa Libertadores":                 (-34.6, -58.44),
    "World Cup Qualifying (S.America)":  (-34.6, -58.44),
    "World Cup Qualifying (Europe)":     (48.85,   2.35),
    "World Cup Qualifying (CONCACAF)":   (19.43, -99.13),
    "World Cup Qualifying (Africa)":     (-1.29,  36.82),
    "World Cup Qualifying (Asia)":       (35.69, 139.69),
    "Championship (ENG)":                (51.50,  -0.12),
    "FIFA World Cup 2026":               (29.76, -95.37),  # Houston (sede principal)
    "Euro 2024 / Nations League":        (48.85,   2.35),
    "Copa America 2024":                 (25.77, -80.19),  # Miami
    "Africa Cup of Nations":             ( 3.86,  11.52),  # Yaounde
    "CONCACAF Gold Cup":                 (34.05,-118.24),  # Los Angeles
}

# ================================================================
#  STATISTICAL ENGINE
# ================================================================

def safe_float(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def extract_profile_from_fd_matches(matches, team_id):
    """Extract stats from football-data.org match history."""
    gf_list, ga_list = [], []
    for m in matches:
        ht_id = m.get("homeTeam",{}).get("id")
        s = m.get("score",{}).get("fullTime",{})
        if not s.get("home") and s.get("home") != 0: continue
        if ht_id == team_id:
            gf_list.append(s.get("home",0) or 0)
            ga_list.append(s.get("away",0) or 0)
        else:
            gf_list.append(s.get("away",0) or 0)
            ga_list.append(s.get("home",0) or 0)
    if not gf_list:
        return None
    return {
        "goals_for":     round(np.mean(gf_list[-10:]), 3),
        "goals_against": round(np.mean(ga_list[-10:]), 3),
        "clean_sheets":  sum(1 for g in ga_list[-10:] if g==0),
        "btts":          sum(1 for gf,ga in zip(gf_list[-10:],ga_list[-10:]) if gf>0 and ga>0),
        "shots_on":      4.5,
        "yellows":       1.8,
        "reds":          0.1,
        "fouls":         12.0,
        "corners":       5.2,
        "source":        "football-data.org (histórico real)",
        "n_games":       len(gf_list),
    }

def extract_profile_from_as_stats(stats, is_home=True):
    """Extract profile from api-sports.io statistics."""
    if not stats:
        return None
    v = "home" if is_home else "away"
    def g(path, d=0.0):
        try:
            x = stats
            for k in path: x = x[k]
            return safe_float(x, d)
        except: return d
    gf = g(["goals","for","average",v]) or g(["goals","for","average","total"]) or 0
    ga = g(["goals","against","average",v]) or g(["goals","against","average","total"]) or 0
    if gf == 0 and ga == 0:
        return None
    def card_avg(color):
        d = stats.get("cards",{}).get(color,{})
        vals = [safe_float(vv) for vv in d.values() if safe_float(vv)>0]
        return round(sum(vals)/len(vals),2) if vals else (1.8 if color=="yellow" else 0.1)
    return {
        "goals_for":     max(0.3, gf),
        "goals_against": max(0.3, ga),
        "shots_on":      g(["shots","on","average"], 4.5),
        "yellows":       card_avg("yellow"),
        "reds":          card_avg("red"),
        "fouls":         g(["fouls","committed","average"], 12.0),
        "corners":       g(["corners","total","average"], 5.2),
        "source":        "api-sports.io (stats de temporada)",
        "n_games":       safe_float(stats.get("fixtures",{}).get("played",{}).get("total",0)),
    }

def merge_profiles(fd_profile, as_profile):
    """Combine both sources for maximum accuracy."""
    if fd_profile and as_profile:
        return {
            "goals_for":     round((fd_profile["goals_for"]*0.6 + as_profile["goals_for"]*0.4), 3),
            "goals_against": round((fd_profile["goals_against"]*0.6 + as_profile["goals_against"]*0.4), 3),
            "shots_on":      as_profile.get("shots_on", 4.5),
            "yellows":       as_profile.get("yellows", 1.8),
            "reds":          as_profile.get("reds", 0.1),
            "fouls":         as_profile.get("fouls", 12.0),
            "corners":       as_profile.get("corners", 5.2),
            "source":        "Fusion football-data.org + api-sports.io",
            "n_games":       fd_profile.get("n_games", 0),
        }
    return fd_profile or as_profile or {
        "goals_for": 1.3, "goals_against": 1.1, "shots_on": 4.5,
        "yellows": 1.8, "reds": 0.1, "fouls": 12.0, "corners": 5.2,
        "source": "Valores de liga (datos insuficientes)", "n_games": 0,
    }

def weather_adjustment(profile, weather, is_home=True):
    """Adjust predictions based on weather conditions."""
    if not weather:
        return profile
    adj = dict(profile)
    rain = weather.get("rain", 0)
    wind = weather.get("wind", 0)
    # Rain reduces goals and shots, increases fouls
    if rain > 2:
        adj["goals_for"]  = round(adj["goals_for"] * 0.92, 3)
        adj["shots_on"]   = round(adj["shots_on"]  * 0.90, 3)
        adj["fouls"]      = round(adj["fouls"]      * 1.05, 3)
        adj["corners"]    = round(adj["corners"]    * 1.03, 3)
    # Wind reduces corners and long shots
    if wind > 30:
        adj["corners"]    = round(adj["corners"]    * 0.95, 3)
        adj["shots_on"]   = round(adj["shots_on"]   * 0.96, 3)
    return adj

def run_monte_carlo(hp, ap, weather=None):
    hp = weather_adjustment(hp, weather, True)
    ap = weather_adjustment(ap, weather, False)
    rng = np.random.default_rng(42)
    league_avg = 1.35
    lh = max(0.3, hp["goals_for"] * (ap["goals_against"]/league_avg) * 1.12)
    la = max(0.3, ap["goals_for"] * (hp["goals_against"]/league_avg))
    hg  = rng.poisson(lh, N_SIM); ag = rng.poisson(la, N_SIM)
    tot = hg + ag
    def p(n): return round(n/N_SIM*100, 1)
    hc = rng.poisson(hp["corners"], N_SIM); ac = rng.poisson(ap["corners"], N_SIM)
    hy = rng.poisson(hp["yellows"], N_SIM); ay = rng.poisson(ap["yellows"], N_SIM)
    hr = rng.poisson(hp["reds"],    N_SIM); ar = rng.poisson(ap["reds"],    N_SIM)
    hf = rng.poisson(hp["fouls"],   N_SIM); af = rng.poisson(ap["fouls"],   N_SIM)
    hs = rng.poisson(hp["shots_on"],N_SIM); as_= rng.poisson(ap["shots_on"],N_SIM)
    scores = {}
    for h,a in zip(hg,ag):
        k=f"{h}-{a}"; scores[k]=scores.get(k,0)+1
    return {
        "phw":p(np.sum(hg>ag)), "pd":p(np.sum(hg==ag)), "paw":p(np.sum(hg<ag)),
        "lh":round(lh,2), "la":round(la,2),
        "o25":p(np.sum(tot>2.5)), "u25":p(np.sum(tot<=2.5)),
        "btts":p(np.sum((hg>0)&(ag>0))), "no_btts":p(np.sum(~((hg>0)&(ag>0)))),
        "hc":round(np.mean(hc),2), "ac":round(np.mean(ac),2), "tc":round(np.mean(hc+ac),2),
        "co85":p(np.sum(hc+ac>8.5)), "cu85":p(np.sum(hc+ac<=8.5)),
        "hy":round(np.mean(hy),2), "ay":round(np.mean(ay),2), "ty":round(np.mean(hy+ay),2),
        "hr":round(np.mean(hr),2), "ar":round(np.mean(ar),2), "tr":round(np.mean(hr+ar),2),
        "hf":round(np.mean(hf),2), "af":round(np.mean(af),2), "tf":round(np.mean(hf+af),2),
        "hs":round(np.mean(hs),2), "as_":round(np.mean(as_),2),
        "top":[(s,p(c)) for s,c in sorted(scores.items(),key=lambda x:-x[1])[:9]],
        "lh_raw":lh, "la_raw":la,
    }

# ================================================================
#  CONFIDENCE & PREDICTIONS
# ================================================================

def conf_info(c):
    if c >= 80:   return ("#3ecf8e","✅ ALTA",  "pc-high","b-high")
    elif c >= 60: return ("#f5c842","⚡ MEDIA", "pc-med", "b-med")
    else:         return ("#f4622a","⚠️ BAJA",  "pc-low", "b-low")

def odds_implied(odd):
    if not odd or odd <= 0: return 0
    return round(100/odd, 1)

def build_predictions(R, hn, an, odds=None):
    rows = []
    best1x2 = max([(R["phw"],f"Victoria {hn}"),(R["pd"],"Empate"),(R["paw"],f"Victoria {an}")],key=lambda x:x[0])
    conf_adj = best1x2[0]
    if odds:
        implied = odds_implied(odds.get("odd_home") if "Victoria "+hn==best1x2[1] else
                               odds.get("odd_draw") if "Empate"==best1x2[1] else odds.get("odd_away"))
        if implied: conf_adj = round((best1x2[0]*0.7 + implied*0.3), 1)
    rows.append({"mkt":"Resultado 1X2","pick":best1x2[1],"conf":conf_adj,
                 "det":f"Local {R['phw']}% / Empate {R['pd']}% / Visita {R['paw']}%"})
    o,u = R["o25"],R["u25"]
    rows.append({"mkt":"Goles O/U 2.5",
                 "pick":"Mas de 2.5 goles" if o>=u else "Menos de 2.5 goles",
                 "conf":max(o,u), "det":f"Goles esperados: {round(R['lh']+R['la'],2)}"})
    rows.append({"mkt":"Ambos Marcan BTTS",
                 "pick":"Si — Ambos anotan" if R["btts"]>=R["no_btts"] else "No — Alguno no anota",
                 "conf":max(R["btts"],R["no_btts"]),
                 "det":f"lambda local {R['lh']} / lambda visita {R['la']}"})
    co,cu = R["co85"],R["cu85"]
    rows.append({"mkt":"Corners O/U 8.5",
                 "pick":"Mas de 8.5 corners" if co>=cu else "Menos de 8.5 corners",
                 "conf":max(co,cu), "det":f"Total esperado: {R['tc']} corners"})
    dc1=min(round(R["phw"]+R["pd"],1),99.0); dc2=min(round(R["paw"]+R["pd"],1),99.0)
    rows.append({"mkt":"Doble Oportunidad",
                 "pick":f"{hn} o Empate" if dc1>=dc2 else f"{an} o Empate",
                 "conf":max(dc1,dc2), "det":"Cubre dos resultados posibles"})
    ty=R["ty"]; line=max(1,round(ty)-1)
    prob_y=min(95.0,max(5.0,round(50+(ty-line-0.5)*18,1)))
    rows.append({"mkt":f"Amarillas O {line}.5",
                 "pick":f"Mas de {line}.5 amarillas","conf":prob_y,
                 "det":f"Total amarillas esperadas: {ty}"})
    top=R["top"][0]
    rows.append({"mkt":"Marcador Exacto","pick":f"Resultado {top[0]}","conf":top[1],
                 "det":"Marcador mas frecuente en 10,000 simulaciones"})
    return sorted(rows, key=lambda x:-x["conf"])

def render_pred(pred):
    color,badge,pc_cls,b_cls = conf_info(pred["conf"])
    c = pred["conf"]; w = int(min(c,100))
    warn = ""
    if c < 60:
        warn = f'<div style="margin-top:8px;padding:5px 10px;background:rgba(244,98,42,.1);border-radius:6px;font-size:.75rem;color:#f4622a">⚠️ RIESGO ALTO — Confianza {c}%. Evita apostar en este mercado.</div>'
    elif c < 80:
        warn = f'<div style="margin-top:8px;padding:5px 10px;background:rgba(245,200,66,.08);border-radius:6px;font-size:.75rem;color:#f5c842">⚡ Confianza media ({c}%). Analiza bien antes de apostar.</div>'
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

def prob_bar(label, val, color):
    st.markdown(f"""<div class="prow">
      <div class="prow-lbl">{label} — <b style="color:{color}">{val}%</b></div>
      <div class="pbar"><div class="pfill" style="width:{min(val,100)}%;background:{color}"></div></div>
    </div>""", unsafe_allow_html=True)

def kpi(val, label, col):
    col.markdown(f'<div class="kpi"><div class="kpi-val">{val}</div><div class="kpi-lbl">{label}</div></div>',
                 unsafe_allow_html=True)

def sec(t): st.markdown(f'<div class="sec">{t}</div>', unsafe_allow_html=True)

# ================================================================
#  SIDEBAR
# ================================================================
with st.sidebar:
    st.markdown("## Configuracion de APIs")

    fd_k  = st.text_input("football-data.org Key", value=st.session_state.get("fd_key",""), type="password")
    as_k  = st.text_input("api-sports.io Key",      value=st.session_state.get("as_key",""), type="password")
    odds_k= st.text_input("the-odds-api.com Key",   value=st.session_state.get("odds_key",""), type="password")
    if fd_k:   st.session_state["fd_key"]   = fd_k
    if as_k:   st.session_state["as_key"]   = as_k
    if odds_k: st.session_state["odds_key"] = odds_k

    # Status
    st.markdown("---")
    st.markdown("**Estado de APIs:**")
    fd_ok   = bool(get_fd_key())
    as_ok   = bool(get_as_key())
    odds_ok = bool(get_odds_key())
    st.markdown(f"{'✅' if fd_ok   else '⬜'} football-data.org")
    st.markdown(f"{'✅' if as_ok   else '⬜'} api-sports.io")
    st.markdown(f"{'✅' if odds_ok else '⬜'} the-odds-api.com")
    st.markdown("✅ open-meteo.com (sin key)")

    if st.button("Probar conexiones"):
        if fd_ok:
            try:
                r = requests.get(f"{FD_BASE}/competitions", headers={"X-Auth-Token": get_fd_key()}, timeout=8)
                st.success(f"football-data: HTTP {r.status_code}")
            except Exception as e: st.error(f"football-data: {e}")
        if as_ok:
            try:
                r = requests.get(f"{AS_BASE}/status", headers={"x-apisports-key": get_as_key()}, timeout=8)
                d = r.json().get("response",{})
                req = d.get("requests",{})
                st.success(f"api-sports: {req.get('current',0)}/{req.get('limit_day',100)} req hoy")
            except Exception as e: st.error(f"api-sports: {e}")
        if odds_ok:
            try:
                r = requests.get(f"{ODDS_BASE}/sports", params={"apiKey": get_odds_key()}, timeout=8)
                st.success(f"odds-api: HTTP {r.status_code}")
            except Exception as e: st.error(f"odds-api: {e}")
        try:
            r = requests.get("https://api.open-meteo.com/v1/forecast",
                             params={"latitude":51.5,"longitude":-0.1,"current":"temperature_2m"}, timeout=8)
            st.success(f"open-meteo: {r.json().get('current',{}).get('temperature_2m','?')}°C en Londres")
        except Exception as e: st.error(f"open-meteo: {e}")

    st.markdown("---")
    st.markdown("**Leyenda:**")
    st.markdown("✅ **ALTA** >= 80%")
    st.markdown("⚡ **MEDIA** 60–79%")
    st.markdown("⚠️ **BAJA** < 60%")
    st.markdown("---")
    st.markdown("**Modelo:** Poisson + Monte Carlo")
    st.markdown("**Sims:** 10,000")
    st.markdown("**Fuentes:** 4 APIs")

# ================================================================
#  MAIN UI
# ================================================================

# Active API pills
fd_ok_now   = bool(get_fd_key())
as_ok_now   = bool(get_as_key())
odds_ok_now = bool(get_odds_key())

def pill(name, active):
    cls = "active" if active else "inactive"
    icon = "✅" if active else "○"
    return f'<span class="api-pill {cls}">{icon} {name}</span>'

st.markdown(f"""
<div class="hero">
  <h1>FOOTBALL ORACLE PRO</h1>
  <div class="sub">Monte Carlo 10,000 sims · Sistema Multi-API · Confiabilidad por mercado</div>
  <div class="apis">
    {pill("football-data.org", fd_ok_now)}
    {pill("api-sports.io", as_ok_now)}
    {pill("the-odds-api.com", odds_ok_now)}
    {pill("open-meteo.com", True)}
  </div>
</div>
""", unsafe_allow_html=True)

if not fd_ok_now and not as_ok_now:
    st.warning("Necesitas al menos UNA key activa para cargar partidos. Pegala en el sidebar (icono menu arriba a la izquierda).")
    st.markdown("""
    ### Como obtener las keys (todas GRATUITAS):

    **1. football-data.org** (recomendado — mas generoso en Free)
    - Ve a https://www.football-data.org/client/register
    - Registrate gratis
    - Tu key llega al correo instantaneamente
    - Permite: Premier League, La Liga, Serie A, Bundesliga, Ligue 1, UCL, etc.

    **2. api-sports.io** (complementario)
    - Ya tienes tu key — usala para estadísticas de equipo

    **3. the-odds-api.com** (cuotas en vivo — opcional)
    - Ve a https://the-odds-api.com/#get-access
    - Registrate gratis (500 requests/mes)

    **4. open-meteo.com** — Ya funciona, sin registro.
    """)
    st.stop()

# ── STEP 1: Liga ──────────────────────────────────────────────────
sec("① ELIGE LA LIGA")
all_leagues = list(set(list(FD_COMPETITIONS.keys()) + list(AS_LEAGUES.keys())))
all_leagues_sorted = sorted(all_leagues)
league_name = st.selectbox("Liga", all_leagues_sorted, label_visibility="collapsed")

# ── STEP 2: Partido ───────────────────────────────────────────────
sec("② ELIGE EL PARTIDO")

fixtures = []
source_used = None

with st.spinner("Buscando partidos en todas las fuentes disponibles..."):
    # Try football-data.org first (more reliable Free tier)
    if fd_ok_now and league_name in FD_COMPETITIONS:
        fixtures = fd_get_fixtures(FD_COMPETITIONS[league_name])
        if fixtures: source_used = "football-data.org"

    # Fallback: api-sports.io
    if not fixtures and as_ok_now and league_name in AS_LEAGUES:
        lg = AS_LEAGUES[league_name]
        fixtures = as_get_fixtures(lg["id"], lg["season"])
        if fixtures: source_used = "api-sports.io"

if not fixtures:
    st.warning(f"No se encontraron partidos proximos para **{league_name}** en los proximos 14 dias.")
    st.info("Prueba con otra liga o agrega mas keys en el sidebar.")
    st.stop()

st.success(f"Partidos cargados desde **{source_used}** — {len(fixtures)} encontrados")

match_map = {f["display"]: f for f in fixtures}
sel = st.selectbox("Partido", list(match_map.keys()), label_visibility="collapsed")
M = match_map[sel]

st.markdown(f"""
<div class="match">
  <span class="tn">{M['home']}</span>
  &nbsp;&nbsp;<span class="vs">VS</span>&nbsp;&nbsp;
  <span class="tn">{M['away']}</span>
  <br><span style="color:#404060;font-size:.82rem">📅 {M['date']}  ·  Datos: {M.get('source','')}</span>
</div>
""", unsafe_allow_html=True)

# ── STEP 3: Analyze ───────────────────────────────────────────────
if st.button("ANALIZAR CON MONTE CARLO — 10,000 SIMULACIONES"):
    with st.spinner("Recopilando datos de todas las fuentes y simulando..."):
        home_id = M.get("home_id"); away_id = M.get("away_id")

        # Get historical matches from football-data.org
        fd_home_matches = fd_get_team_matches(home_id) if fd_ok_now and home_id else []
        fd_away_matches = fd_get_team_matches(away_id) if fd_ok_now and away_id else []

        fd_hp = extract_profile_from_fd_matches(fd_home_matches, home_id) if fd_home_matches else None
        fd_ap = extract_profile_from_fd_matches(fd_away_matches, away_id) if fd_away_matches else None

        # Get stats from api-sports
        lg_info = AS_LEAGUES.get(league_name, {})
        as_hp_raw = as_get_stats(home_id, lg_info.get("id"), lg_info.get("season",2024)) if as_ok_now and home_id and lg_info else {}
        as_ap_raw = as_get_stats(away_id, lg_info.get("id"), lg_info.get("season",2024)) if as_ok_now and away_id and lg_info else {}

        as_hp = extract_profile_from_as_stats(as_hp_raw, is_home=True)
        as_ap = extract_profile_from_as_stats(as_ap_raw, is_home=False)

        # Merge sources
        hp = merge_profiles(fd_hp, as_hp)
        ap = merge_profiles(fd_ap, as_ap)

        # Get odds from the-odds-api
        sport_key = ODDS_SPORT_MAP.get(league_name)
        odds = get_odds(sport_key, M["home"], M["away"]) if odds_ok_now and sport_key else None

        # Get weather
        coords = STADIUM_COORDS.get(league_name, (51.5, -0.1))
        weather = get_weather(coords[0], coords[1], league_name)

        # Run simulation
        R = run_monte_carlo(hp, ap, weather)
        preds = build_predictions(R, M["home"], M["away"], odds)

    st.success("10,000 simulaciones completadas")

    # ── DATA SOURCES USED ─────────────────────────────────────
    sec("FUENTES DE DATOS UTILIZADAS")
    c1,c2 = st.columns(2)
    with c1:
        st.markdown(f"**{M['home']}:** {hp.get('source','N/A')} ({int(hp.get('n_games',0))} partidos)")
    with c2:
        st.markdown(f"**{M['away']}:** {ap.get('source','N/A')} ({int(ap.get('n_games',0))} partidos)")
    if weather:
        icon = "🌧️" if weather["rain"]>2 else "💨" if weather["wind"]>30 else "☀️" if weather["code"]<3 else "☁️"
        st.info(f"{icon} **Clima del partido:** {weather['cond']} | {weather['temp']}°C | Lluvia: {weather['rain']}mm | Viento: {weather['wind']}km/h — *Condiciones consideradas en el modelo*")

    # ── ODDS REALES ───────────────────────────────────────────
    if odds:
        sec("CUOTAS EN TIEMPO REAL")
        st.markdown(f'<div style="font-size:.75rem;color:#505070;margin-bottom:6px">Fuente: {odds.get("bookmaker","")} via the-odds-api.com</div>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        for col, team, odd_key in [(c1,M["home"],"odd_home"),(c2,"Empate","odd_draw"),(c3,M["away"],"odd_away")]:
            odd_val = odds.get(odd_key, 0)
            implied = odds_implied(odd_val)
            kpi(f"{odd_val:.2f}" if odd_val else "N/A", f"{team[:14]}\n(impl. {implied}%)", col)

    # ── PREDICTIONS ───────────────────────────────────────────
    sec("PREDICCIONES CON NIVEL DE CONFIANZA")
    high = [p for p in preds if p["conf"]>=80]
    med  = [p for p in preds if 60<=p["conf"]<80]
    low  = [p for p in preds if p["conf"]<60]
    c1,c2,c3 = st.columns(3)
    kpi(str(len(high)), "Alta confianza >=80%",   c1)
    kpi(str(len(med)),  "Confianza media 60-79%", c2)
    kpi(str(len(low)),  "Baja confianza <60%",    c3)
    st.markdown("<br>", unsafe_allow_html=True)
    if high:
        st.markdown("#### ✅ Alta confianza (>=80%) — Estadisticamente solidas")
        for p in high: render_pred(p)
    if med:
        st.markdown("#### ⚡ Confianza media (60–79%) — Analiza antes de apostar")
        for p in med: render_pred(p)
    if low:
        st.markdown("#### ⚠️ Baja confianza (<60%) — Alto riesgo, evitar")
        for p in low: render_pred(p)

    # ── 1X2 ──────────────────────────────────────────────────
    sec("PROBABILIDADES 1X2")
    prob_bar(f"Local: {M['home']}", R["phw"], "#3ecf8e")
    prob_bar("Empate",               R["pd"],  "#f5c842")
    prob_bar(f"Visita: {M['away']}", R["paw"], "#f4622a")

    # ── Goles ─────────────────────────────────────────────────
    sec("GOLES PROYECTADOS")
    c1,c2,c3,c4 = st.columns(4)
    kpi(R["lh"],          f"Goles esp.\n{M['home'][:12]}", c1)
    kpi(R["la"],          f"Goles esp.\n{M['away'][:12]}", c2)
    kpi(f"{R['o25']}%",   "Mas de 2.5 Goles",  c3)
    kpi(f"{R['btts']}%",  "Ambos Anotan BTTS", c4)

    # ── Top marcadores ────────────────────────────────────────
    sec("MARCADORES MAS PROBABLES")
    st.dataframe(
        pd.DataFrame(R["top"], columns=["Marcador","Prob %"])
          .style.background_gradient(subset=["Prob %"], cmap="Oranges")
          .format({"Prob %":"{:.1f}%"}),
        use_container_width=True, hide_index=True)

    # ── Corners ───────────────────────────────────────────────
    sec("CORNERS")
    c1,c2,c3,c4 = st.columns(4)
    kpi(R["hc"], f"Corners {M['home'][:12]}", c1)
    kpi(R["ac"], f"Corners {M['away'][:12]}", c2)
    kpi(R["tc"], "Total Corners",              c3)
    kpi(f"{R['co85']}%","Mas de 8.5",         c4)

    # ── Tarjetas ──────────────────────────────────────────────
    sec("TARJETAS")
    c1,c2,c3,c4 = st.columns(4)
    kpi(R["hy"], f"Amarillas {M['home'][:12]}", c1)
    kpi(R["ay"], f"Amarillas {M['away'][:12]}", c2)
    kpi(R["ty"], "Total Amarillas",              c3)
    kpi(R["tr"], "Rojas Totales",                c4)

    # ── Faltas & Tiros ────────────────────────────────────────
    sec("FALTAS Y TIROS A PUERTA")
    c1,c2 = st.columns(2)
    with c1:
        st.dataframe(pd.DataFrame({"Equipo":[M["home"],M["away"],"TOTAL"],
            "Faltas":[R["hf"],R["af"],R["tf"]]}), use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(pd.DataFrame({"Equipo":[M["home"],M["away"]],
            "Tiros a puerta":[R["hs"],R["as_"]]}), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Analisis estadistico con fines educativos. Alta confianza = mayor probabilidad estadistica, NO garantia de resultado. Apuesta con responsabilidad.")
