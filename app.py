# ================================================================
#  FOOTBALL ORACLE PRO v5.0 — Professional Betting Suite
#  Triple-Capa | Binomial Negativa | Value Bet EV>1.05
#  Kelly 0.25 | Fatiga | Clima | ROI | 100% Espanol
# ================================================================

import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import math, json, warnings
warnings.filterwarnings("ignore")

# ================================================================
#  KEYS — Integradas
# ================================================================
FD_KEY    = "a2aef808a68d4cd6ba2ad97f9953ec81"
APISPORTS = "70cb24441a57cc0a28c2fd7dd3b76110"
ODDS_KEY  = "f028e4d3689b54c609ce7137fc6a40ba"

def _s(k, d=""):
    try:    return st.secrets.get(k, d)
    except: return d

FD_KEY    = _s("FD_KEY",    FD_KEY)
APISPORTS = _s("APISPORTS", APISPORTS)
ODDS_KEY  = _s("ODDS_KEY",  ODDS_KEY)

FD_HDR  = {"X-Auth-Token": FD_KEY}
AS_HDR  = {"x-apisports-key": APISPORTS}
FD_BASE = "https://api.football-data.org/v4"
AS_BASE = "https://v3.football.api-sports.io"
OD_BASE = "https://api.the-odds-api.com/v4"

N_SIM      = 10_000
DAYS_AHEAD = 45
EV_MINIMO  = 1.05   # Umbral de Value Bet

# ================================================================
#  CAPA 3: DICCIONARIO HARDCODED — Mundial 2026 + Promedios liga
#  Basado en Qatar 2022, Rusia 2018 y promedios de cada liga
# ================================================================
PROMEDIOS_HARDCODED = {
    # Mundial — basado en Qatar 2022 + Rusia 2018
    "FIFA Mundial 2026": {
        "DEFAULT": {"gf": 1.18, "gc": 1.18, "std_gf": 0.85, "std_gc": 0.85,
                    "corners": 4.8, "amarillas": 1.9, "rojas": 0.12, "faltas": 13.5, "tiros": 4.1},
        "grupos_fuertes": {"gf": 1.45, "gc": 0.95, "std_gf": 0.90, "std_gc": 0.70},
        "grupos_debiles": {"gf": 0.85, "gc": 1.55, "std_gf": 0.75, "std_gc": 0.95},
    },
    # Ligas Latam
    "Liga BetPlay (COL)": {
        "DEFAULT": {"gf": 1.22, "gc": 1.22, "std_gf": 0.95, "std_gc": 0.95,
                    "corners": 4.9, "amarillas": 2.4, "rojas": 0.18, "faltas": 16.2, "tiros": 4.0},
    },
    "Liga Profesional (ARG)": {
        "DEFAULT": {"gf": 1.35, "gc": 1.35, "std_gf": 1.05, "std_gc": 1.05,
                    "corners": 5.1, "amarillas": 2.6, "rojas": 0.20, "faltas": 17.1, "tiros": 4.2},
    },
    "Serie A Brasileirao (BRA)": {
        "DEFAULT": {"gf": 1.28, "gc": 1.28, "std_gf": 0.98, "std_gc": 0.98,
                    "corners": 5.0, "amarillas": 2.2, "rojas": 0.15, "faltas": 15.4, "tiros": 4.1},
    },
    "Copa Libertadores": {
        "DEFAULT": {"gf": 1.20, "gc": 1.20, "std_gf": 0.90, "std_gc": 0.90,
                    "corners": 4.7, "amarillas": 2.1, "rojas": 0.14, "faltas": 14.8, "tiros": 3.9},
    },
    "Copa Sudamericana": {
        "DEFAULT": {"gf": 1.18, "gc": 1.18, "std_gf": 0.88, "std_gc": 0.88,
                    "corners": 4.6, "amarillas": 2.0, "rojas": 0.13, "faltas": 14.5, "tiros": 3.8},
    },
    # Ligas Europeas
    "Premier League (ENG)": {
        "DEFAULT": {"gf": 1.48, "gc": 1.48, "std_gf": 1.02, "std_gc": 1.02,
                    "corners": 5.4, "amarillas": 1.6, "rojas": 0.07, "faltas": 11.2, "tiros": 5.1},
    },
    "La Liga (ESP)": {
        "DEFAULT": {"gf": 1.42, "gc": 1.42, "std_gf": 1.00, "std_gc": 1.00,
                    "corners": 5.2, "amarillas": 2.0, "rojas": 0.09, "faltas": 12.8, "tiros": 4.9},
    },
    "Bundesliga (GER)": {
        "DEFAULT": {"gf": 1.60, "gc": 1.60, "std_gf": 1.10, "std_gc": 1.10,
                    "corners": 5.5, "amarillas": 1.7, "rojas": 0.07, "faltas": 11.5, "tiros": 5.3},
    },
    "Serie A Italia (ITA)": {
        "DEFAULT": {"gf": 1.38, "gc": 1.38, "std_gf": 0.98, "std_gc": 0.98,
                    "corners": 5.0, "amarillas": 2.1, "rojas": 0.10, "faltas": 13.1, "tiros": 4.7},
    },
    "Ligue 1 (FRA)": {
        "DEFAULT": {"gf": 1.40, "gc": 1.40, "std_gf": 0.99, "std_gc": 0.99,
                    "corners": 5.1, "amarillas": 1.9, "rojas": 0.08, "faltas": 12.5, "tiros": 4.8},
    },
    "UEFA Champions League": {
        "DEFAULT": {"gf": 1.55, "gc": 1.55, "std_gf": 1.08, "std_gc": 1.08,
                    "corners": 5.6, "amarillas": 1.8, "rojas": 0.08, "faltas": 12.0, "tiros": 5.5},
    },
    "MLS (USA)": {
        "DEFAULT": {"gf": 1.42, "gc": 1.42, "std_gf": 1.00, "std_gc": 1.00,
                    "corners": 5.0, "amarillas": 1.8, "rojas": 0.09, "faltas": 12.8, "tiros": 4.5},
    },
}

def defaults_liga(nombre_liga):
    """Retorna promedios hardcoded para la liga como último recurso."""
    d = PROMEDIOS_HARDCODED.get(nombre_liga, {}).get("DEFAULT",
        {"gf":1.30,"gc":1.30,"std_gf":0.95,"std_gc":0.95,
         "corners":5.0,"amarillas":1.9,"rojas":0.10,"faltas":13.0,"tiros":4.5})
    return {
        "goles_a_favor":  d["gf"], "goles_contra":   d["gc"],
        "std_a_favor":    d["std_gf"], "std_contra": d["std_gc"],
        "btts_pct": 0.46, "cs_pct": 0.26,
        "tiros":    d["tiros"], "amarillas": d["amarillas"],
        "rojas":    d["rojas"], "faltas":    d["faltas"],
        "corners":  d["corners"],
        "fuente":   "Promedio historico de liga (Capa 3 — Hardcoded)",
        "partidos": 0,
    }

# ================================================================
#  LIGAS
# ================================================================
LIGAS = {
    # Latinoamerica
    "Liga BetPlay (COL)":        {"as_id":239,"fd_code":None, "season":2025,"region":"Latinoamerica","odds_key":"soccer_colombia_primera_a"},
    "Liga Profesional (ARG)":    {"as_id":128,"fd_code":None, "season":2025,"region":"Latinoamerica","odds_key":"soccer_argentina_primera_division"},
    "Serie A Brasileirao (BRA)": {"as_id":71, "fd_code":None, "season":2025,"region":"Latinoamerica","odds_key":"soccer_brazil_campeonato"},
    "Copa Libertadores":         {"as_id":13, "fd_code":"CLI","season":2025,"region":"Latinoamerica","odds_key":"soccer_conmebol_copa_libertadores"},
    "Copa Sudamericana":         {"as_id":11, "fd_code":None, "season":2025,"region":"Latinoamerica","odds_key":None},
    # Europa
    "Premier League (ENG)":      {"as_id":39, "fd_code":"PL", "season":2024,"region":"Europa","odds_key":"soccer_england_league1"},
    "La Liga (ESP)":             {"as_id":140,"fd_code":"PD", "season":2024,"region":"Europa","odds_key":"soccer_spain_la_liga"},
    "Bundesliga (GER)":          {"as_id":78, "fd_code":"BL1","season":2024,"region":"Europa","odds_key":"soccer_germany_bundesliga"},
    "Serie A Italia (ITA)":      {"as_id":135,"fd_code":"SA", "season":2024,"region":"Europa","odds_key":"soccer_italy_serie_a"},
    "Ligue 1 (FRA)":             {"as_id":61, "fd_code":"FL1","season":2024,"region":"Europa","odds_key":"soccer_france_ligue_one"},
    "UEFA Champions League":     {"as_id":2,  "fd_code":"CL", "season":2024,"region":"Europa","odds_key":"soccer_uefa_champs_league"},
    # Global
    "FIFA Mundial 2026":         {"as_id":1,  "fd_code":None, "season":2026,"region":"Global","odds_key":"soccer_fifa_world_cup"},
    "MLS (USA)":                 {"as_id":253,"fd_code":None, "season":2025,"region":"Global","odds_key":"soccer_usa_mls"},
}

COORDENADAS = {
    "Liga BetPlay (COL)":        ( 4.71,-74.07),
    "Liga Profesional (ARG)":    (-34.60,-58.44),
    "Serie A Brasileirao (BRA)": (-23.54,-46.63),
    "Copa Libertadores":         (-23.54,-46.63),
    "Copa Sudamericana":         (-34.60,-58.44),
    "Premier League (ENG)":      ( 51.50,-0.12),
    "La Liga (ESP)":             ( 40.45,-3.69),
    "Bundesliga (GER)":          ( 48.21, 11.62),
    "Serie A Italia (ITA)":      ( 45.47,  9.12),
    "Ligue 1 (FRA)":             ( 48.85,  2.35),
    "UEFA Champions League":     ( 51.50,-0.12),
    "FIFA Mundial 2026":         ( 29.76,-95.37),
    "MLS (USA)":                 ( 34.05,-118.24),
}

LATAM_PRIO = {"Liga BetPlay (COL)","Liga Profesional (ARG)","Serie A Brasileirao (BRA)",
              "Copa Libertadores","Copa Sudamericana"}

# ================================================================
#  CONFIG STREAMLIT + CSS
# ================================================================
st.set_page_config(
    page_title="Football Oracle PRO v5.0",
    page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;700&display=swap');
*{box-sizing:border-box;margin:0;padding:0;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#05050d;color:#ddddf5;}

/* HERO */
.hero{background:linear-gradient(140deg,#0a0a1e 0%,#140608 100%);
  border:1px solid #1c1c32;border-radius:20px;padding:36px 40px 28px;
  margin-bottom:28px;position:relative;overflow:hidden;}
.hero::before{content:'';position:absolute;top:-80px;right:-80px;width:360px;height:360px;
  background:radial-gradient(circle,rgba(244,98,42,.11) 0%,transparent 65%);pointer-events:none;}
.hero::after{content:'v5.0';position:absolute;bottom:-16px;right:24px;
  font-family:'Bebas Neue',sans-serif;font-size:8rem;color:rgba(244,98,42,.04);
  letter-spacing:6px;pointer-events:none;}
.hero-ver{font-size:.68rem;color:#f4622a88;letter-spacing:5px;text-transform:uppercase;margin-bottom:8px;}
.hero h1{font-family:'Bebas Neue',sans-serif;font-size:clamp(2rem,5vw,3.2rem);
  color:#f4622a;letter-spacing:3px;line-height:.92;margin:0;}
.hero-sub{color:#404060;font-size:.78rem;margin-top:10px;line-height:1.5;}
.api-row{display:flex;gap:6px;flex-wrap:wrap;margin-top:14px;}
.apill{padding:3px 10px;border-radius:99px;font-size:.67rem;font-weight:600;letter-spacing:.5px;}
.aon{background:rgba(62,207,142,.09);color:#3ecf8e;border:1px solid #3ecf8e33;}
.aoff{background:rgba(244,98,42,.07);color:#f4622a44;border:1px solid #f4622a18;}

/* SECCION */
.sec{font-family:'Bebas Neue',sans-serif;font-size:1.2rem;color:#f4622a;
  letter-spacing:3px;border-bottom:1px solid #161628;padding-bottom:5px;margin:22px 0 14px;}

/* KPI */
.kpi{background:#0a0a1a;border:1px solid #181830;border-radius:14px;
  padding:14px 12px;text-align:center;margin-bottom:6px;}
.kv{font-family:'Bebas Neue',sans-serif;font-size:1.9rem;color:#f5c842;line-height:1.1;}
.kl{font-size:.6rem;color:#30304a;letter-spacing:2px;text-transform:uppercase;margin-top:2px;}

/* MATCH BOX */
.mbox{background:#0a0a1a;border:1px solid #181830;border-radius:16px;
  padding:22px;text-align:center;margin:14px 0;}
.tn{font-family:'Bebas Neue',sans-serif;font-size:1.75rem;color:#ddddf5;}
.vs{font-family:'Bebas Neue',sans-serif;font-size:2.2rem;color:#f4622a;margin:0 8px;}
.mmeta{color:#28284a;font-size:.75rem;margin-top:6px;}
.src-chip{background:#0f0f20;border:1px solid #181830;border-radius:4px;
  padding:1px 6px;font-size:.62rem;color:#383858;margin-left:4px;}

/* PREDICTION CARDS */
.pc{border-radius:14px;padding:15px 18px;margin-bottom:10px;
  display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.pc-h{background:#07120a;border:1px solid #3ecf8e28;}
.pc-m{background:#131008;border:1px solid #f5c84224;}
.pc-l{background:#120608;border:1px solid #f4622a22;}
.pmkt{font-size:.62rem;color:#303052;letter-spacing:2px;text-transform:uppercase;min-width:125px;}
.ppick{font-weight:600;font-size:.9rem;flex:1;color:#ddddf5;}
.pdet{font-size:.7rem;color:#383858;margin-top:3px;}
.pbadge{display:inline-block;border-radius:6px;padding:2px 8px;
  font-size:.66rem;font-weight:700;letter-spacing:.5px;margin-top:4px;}
.bh{background:rgba(62,207,142,.12);color:#3ecf8e;}
.bm{background:rgba(245,200,66,.10);color:#f5c842;}
.bl_c{background:rgba(244,98,42,.12);color:#f4622a;}

/* VALUE BET BOX */
.vb-yes{background:linear-gradient(135deg,#061206,#040d04);
  border:2px solid #3ecf8e44;border-radius:12px;padding:14px 18px;margin:8px 0;}
.vb-no{background:#0d0808;border:1px solid #f4622a22;
  border-radius:10px;padding:10px 14px;margin:8px 0;font-size:.78rem;color:#604050;}

/* BET BOX */
.bet-box{background:linear-gradient(140deg,#071407,#050d05);
  border:2px solid #3ecf8e44;border-radius:18px;padding:26px 30px;margin:14px 0;}
.bet-title{font-family:'Bebas Neue',sans-serif;color:#3ecf8e;
  font-size:1.5rem;letter-spacing:3px;margin-bottom:16px;}
.bet-row{display:flex;justify-content:space-between;align-items:center;
  padding:7px 0;border-bottom:1px solid #0c1c0c;}
.bet-row:last-child{border-bottom:none;}
.bet-lbl{font-size:.78rem;color:#405040;}
.bet-val{font-family:'Bebas Neue',sans-serif;font-size:1.25rem;color:#f5c842;}
.combo-box{background:#081208;border:1px solid #3ecf8e1a;
  border-radius:10px;padding:14px;margin-top:14px;}
.bet-warn{background:#100808;border:1px solid #f4622a18;
  border-radius:8px;padding:10px 14px;margin-top:12px;
  font-size:.75rem;color:#604050;line-height:1.55;}

/* DATA CAPA BADGE */
.capa-badge{display:inline-block;border-radius:6px;padding:2px 9px;
  font-size:.65rem;font-weight:700;letter-spacing:.5px;}
.capa-1{background:rgba(62,207,142,.12);color:#3ecf8e;}
.capa-2{background:rgba(79,142,247,.12);color:#4f8ef7;}
.capa-3{background:rgba(245,200,66,.10);color:#f5c842;}

/* PROB BAR */
.prow{margin:8px 0;}
.prow-lbl{font-size:.76rem;color:#505078;margin-bottom:3px;}
.pbar{background:#0f0f20;border-radius:99px;height:9px;overflow:hidden;}
.pfill{height:100%;border-radius:99px;}

/* ROI BOX */
.roi-box{background:#0a0a1a;border:1px solid #1a1a32;border-radius:12px;
  padding:14px 18px;margin:8px 0;}

/* ALERTA */
.alerta-fatiga{background:#140a04;border-left:3px solid #f5c842;
  border-radius:0 8px 8px 0;padding:10px 14px;font-size:.78rem;color:#a07040;margin:8px 0;}
.alerta-clima{background:#040a14;border-left:3px solid #4f8ef7;
  border-radius:0 8px 8px 0;padding:10px 14px;font-size:.78rem;color:#4080a0;margin:8px 0;}

/* BUTTONS */
.stButton>button{background:#f4622a!important;color:#fff!important;
  border:none!important;border-radius:12px!important;font-weight:700!important;
  padding:14px 20px!important;width:100%!important;font-size:.93rem!important;
  letter-spacing:1px!important;}
.stButton>button:hover{background:#d0501e!important;}
#MainMenu,footer,header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ================================================================
#  HELPERS
# ================================================================
def _f(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def impl(odd):
    if not odd or odd <= 0: return 0
    return round(100 / odd, 1)

def kelly(prob_pct, odd, bankroll=100, fraccion=0.25):
    if not odd or odd <= 1.0: return 0
    p = prob_pct / 100; q = 1 - p; b = odd - 1
    k = max(0, (b*p - q) / b) * fraccion
    return round(k * bankroll, 2)

def roi_estimado(prob_pct, odd):
    if not odd: return None
    ev = (prob_pct/100) * odd - 1
    return round(ev * 100, 2)

def ev_check(prob_pct, odd):
    """Verifica si EV >= 5% sobre la casa."""
    if not odd: return False, 0
    ev = (prob_pct/100) * odd
    return ev >= EV_MINIMO, round(ev, 4)

# ================================================================
#  CAPA 1: football-data.org
# ================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def fd_partidos(fd_code):
    if not fd_code or not FD_KEY: return []
    hoy    = datetime.now().strftime("%Y-%m-%d")
    futuro = (datetime.now() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    try:
        r = requests.get(f"{FD_BASE}/competitions/{fd_code}/matches",
                         headers=FD_HDR,
                         params={"dateFrom":hoy,"dateTo":futuro,"status":"SCHEDULED"},
                         timeout=14)
        if r.status_code != 200: return []
        res = []
        for m in r.json().get("matches",[]):
            home = m.get("homeTeam",{}).get("shortName") or m.get("homeTeam",{}).get("name","?")
            away = m.get("awayTeam",{}).get("shortName") or m.get("awayTeam",{}).get("name","?")
            fecha = m.get("utcDate","")[:10]
            res.append({"id":m.get("id"),"fecha":fecha,"local":home,"visita":away,
                        "id_local_fd":m.get("homeTeam",{}).get("id"),
                        "id_visita_fd":m.get("awayTeam",{}).get("id"),
                        "id_local_as":None,"id_visita_as":None,
                        "ultimo_partido_local":None,"ultimo_partido_visita":None,
                        "fuente":"football-data.org (Capa 1)",
                        "capa":1,
                        "display":f"📅 {fecha}  |  {home}  vs  {away}"})
        return res
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def fd_historial(team_id, limit=50):
    if not team_id or not FD_KEY: return []
    try:
        r = requests.get(f"{FD_BASE}/teams/{team_id}/matches",
                         headers=FD_HDR,
                         params={"status":"FINISHED","limit":limit},
                         timeout=14)
        if r.status_code != 200: return []
        return r.json().get("matches",[])
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def fd_ultimo_partido(team_id):
    """Retorna la fecha del ultimo partido para calcular fatiga."""
    matches = fd_historial(team_id, limit=3)
    if not matches: return None
    fechas = [m.get("utcDate","")[:10] for m in matches if m.get("utcDate")]
    return max(fechas) if fechas else None

# ================================================================
#  CAPA 1: api-sports.io
# ================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def as_partidos(league_id, season):
    hoy    = datetime.now().strftime("%Y-%m-%d")
    futuro = (datetime.now() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    for params in [
        {"league":league_id,"season":season,"from":hoy,"to":futuro},
        {"league":league_id,"season":season,"status":"NS","from":hoy,"to":futuro},
        {"league":league_id,"season":season},
    ]:
        try:
            r = requests.get(f"{AS_BASE}/fixtures", headers=AS_HDR,
                             params=params, timeout=14)
            data = r.json()
            if data.get("errors") not in (None,[],{}): continue
            items = data.get("response",[])
            if not items: continue
            res = []
            for f in items:
                fix   = f.get("fixture",{})
                teams = f.get("teams",{})
                if fix.get("status",{}).get("short","") in ("FT","AET","PEN","CANC","ABD","PST"): continue
                home = teams.get("home",{}).get("name","?")
                away = teams.get("away",{}).get("name","?")
                fecha = fix.get("date","")[:10]
                res.append({"id":fix.get("id"),"fecha":fecha,"local":home,"visita":away,
                            "id_local_as":teams.get("home",{}).get("id"),
                            "id_visita_as":teams.get("away",{}).get("id"),
                            "id_local_fd":None,"id_visita_fd":None,
                            "ultimo_partido_local":None,"ultimo_partido_visita":None,
                            "fuente":"api-sports.io (Capa 1)",
                            "capa":1,
                            "display":f"📅 {fecha}  |  {home}  vs  {away}"})
            if res: return res
        except: continue
    return []

@st.cache_data(ttl=3600, show_spinner=False)
def as_estadisticas(team_id, league_id, season):
    if not team_id: return {}
    resultados = []
    for s in [season, season-1]:
        try:
            r = requests.get(f"{AS_BASE}/teams/statistics", headers=AS_HDR,
                             params={"team":team_id,"league":league_id,"season":s},
                             timeout=12)
            d = r.json().get("response",{})
            if d:
                j = _f(d.get("fixtures",{}).get("played",{}).get("total",0))
                resultados.append({"data":d,"jugados":j,"season":s})
        except: continue
    if not resultados: return {}
    resultados.sort(key=lambda x:-x["jugados"])
    if len(resultados)>=2 and resultados[0]["jugados"]<8:
        return _fusionar_stats(resultados[0]["data"], resultados[1]["data"])
    return resultados[0]["data"]

def _fusionar_stats(s1, s2):
    j1 = max(1, _f(s1.get("fixtures",{}).get("played",{}).get("total",0)))
    j2 = max(1, _f(s2.get("fixtures",{}).get("played",{}).get("total",0)))
    w1 = j1/(j1+j2); w2 = j2/(j1+j2)
    fusion = dict(s1)
    for venue in ["home","away","total"]:
        try:
            gf1=_f(s1.get("goals",{}).get("for",{}).get("average",{}).get(venue,0))
            gf2=_f(s2.get("goals",{}).get("for",{}).get("average",{}).get(venue,0))
            ga1=_f(s1.get("goals",{}).get("against",{}).get("average",{}).get(venue,0))
            ga2=_f(s2.get("goals",{}).get("against",{}).get("average",{}).get(venue,0))
            fusion.setdefault("goals",{}).setdefault("for",{}).setdefault("average",{})[venue]     = round(gf1*w1+gf2*w2,3)
            fusion.setdefault("goals",{}).setdefault("against",{}).setdefault("average",{})[venue] = round(ga1*w1+ga2*w2,3)
        except: pass
    fusion["_fusionado"]=True; fusion["_j1"]=j1; fusion["_j2"]=j2
    return fusion

@st.cache_data(ttl=3600, show_spinner=False)
def as_ultimos(team_id, season, n=20):
    if not team_id: return []
    for s in [season, season-1]:
        try:
            r = requests.get(f"{AS_BASE}/fixtures", headers=AS_HDR,
                             params={"team":team_id,"season":s,"status":"FT","last":n},
                             timeout=12)
            d = r.json().get("response",[])
            if d: return d
        except: continue
    return []

@st.cache_data(ttl=3600, show_spinner=False)
def as_buscar_equipo(nombre):
    try:
        r = requests.get(f"{AS_BASE}/teams", headers=AS_HDR,
                         params={"search":nombre[:12]}, timeout=10)
        items = r.json().get("response",[])
        if items: return items[0].get("team",{}).get("id")
    except: pass
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def as_ultimo_partido_fecha(team_id, season):
    """Fecha del ultimo partido jugado (para fatiga)."""
    items = as_ultimos(team_id, season, n=3)
    if not items: return None
    fechas = [f.get("fixture",{}).get("date","")[:10] for f in items if f.get("fixture",{}).get("date")]
    return max(fechas) if fechas else None

# ================================================================
#  CAPA 2: Web Scraping de emergencia (pandas.read_html)
# ================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def scrape_partidos_emergencia(nombre_liga):
    """
    Capa 2 — Web Scraping de emergencia via pandas.read_html.
    Intenta obtener fixtures de fuentes publicas cuando APIs fallan.
    """
    intentos = []

    # Mapeo liga → busqueda en flashscore/soccerway pattern
    liga_map = {
        "Liga BetPlay (COL)":        "https://www.flashscore.com/football/colombia/primera-a/",
        "Liga Profesional (ARG)":    "https://www.flashscore.com/football/argentina/liga-profesional/",
        "Serie A Brasileirao (BRA)": "https://www.flashscore.com/football/brazil/serie-a/",
        "Premier League (ENG)":      "https://www.flashscore.com/football/england/premier-league/",
        "La Liga (ESP)":             "https://www.flashscore.com/football/spain/laliga/",
        "UEFA Champions League":     "https://www.flashscore.com/football/europe/champions-league/",
    }

    # Intento con FBRef para estadísticas publicas (tablas HTML)
    fbref_map = {
        "Premier League (ENG)":      "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures",
        "La Liga (ESP)":             "https://fbref.com/en/comps/12/schedule/La-Liga-Scores-and-Fixtures",
        "Bundesliga (GER)":          "https://fbref.com/en/comps/20/schedule/Bundesliga-Scores-and-Fixtures",
        "Serie A Italia (ITA)":      "https://fbref.com/en/comps/11/schedule/Serie-A-Scores-and-Fixtures",
        "Ligue 1 (FRA)":             "https://fbref.com/en/comps/13/schedule/Ligue-1-Scores-and-Fixtures",
        "UEFA Champions League":     "https://fbref.com/en/comps/8/schedule/Champions-League-Scores-and-Fixtures",
    }

    hoy    = datetime.now().strftime("%Y-%m-%d")
    futuro = (datetime.now() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")

    # Intentar FBRef
    if nombre_liga in fbref_map:
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; FootballOracle/5.0)"}
            r = requests.get(fbref_map[nombre_liga], headers=headers, timeout=15)
            if r.status_code == 200:
                tablas = pd.read_html(r.text)
                for tabla in tablas:
                    cols = [str(c).lower() for c in tabla.columns]
                    if not (any(x in cols for x in ["date","fecha"]) and any(x in cols for x in ["home","local"])):
                        continue
                    tabla.columns = [str(c).lower() for c in tabla.columns]
                    col_fecha = next((c for c in tabla.columns if "date" in c or "fecha" in c), None)
                    col_home  = next((c for c in tabla.columns if "home" in c or "local" in c), None)
                    col_away  = next((c for c in tabla.columns if "away" in c or "visita" in c or "visitor" in c), None)
                    if not (col_fecha and col_home and col_away):
                        continue
                    res = []
                    for _, row in tabla.iterrows():
                        try:
                            fecha_raw = str(row[col_fecha])
                            home_raw  = str(row[col_home])
                            away_raw  = str(row[col_away])
                            if fecha_raw in ("nan","None","") or home_raw in ("nan","None","") or away_raw in ("nan","None",""):
                                continue
                            try:
                                fecha_dt = pd.to_datetime(fecha_raw).strftime("%Y-%m-%d")
                            except Exception:
                                continue
                            if fecha_dt < hoy or fecha_dt > futuro:
                                continue
                            score_col = next((c for c in tabla.columns if "score" in c or "result" in c), None)
                            if score_col:
                                score_val = str(row.get(score_col,""))
                                if score_val not in ("nan","None","","–","-") and any(ch.isdigit() for ch in score_val):
                                    continue
                            res.append({
                                "id": None, "fecha": fecha_dt,
                                "local": home_raw.strip(), "visita": away_raw.strip(),
                                "id_local_fd":None,"id_visita_fd":None,
                                "id_local_as":None,"id_visita_as":None,
                                "ultimo_partido_local":None,"ultimo_partido_visita":None,
                                "fuente":"FBRef.com (Capa 2 — Scraping)",
                                "capa":2,
                                "display":f"📅 {fecha_dt}  |  {home_raw.strip()}  vs  {away_raw.strip()}"
                            })
                        except Exception:
                            continue
                    if res:
                        return res
        except Exception:
            pass

    return []

# ================================================================
#  CASCADA INTELIGENTE DE PARTIDOS
# ================================================================
def cargar_partidos_cascada(nombre_liga):
    """
    Capa 1 → APIs principales
    Capa 2 → Web Scraping FBRef
    Capa 3 → Sin partidos (muestra promedios y espera nueva busqueda)
    """
    lg     = LIGAS[nombre_liga]
    as_id  = lg["as_id"]
    fd_cod = lg["fd_code"]
    season = lg["season"]
    es_latam = nombre_liga in LATAM_PRIO
    partidos = []; fuente = None; capa = 0

    # ── CAPA 1 ───────────────────────────────────────────────
    if es_latam:
        partidos = as_partidos(as_id, season)
        if partidos: fuente="api-sports.io"; capa=1
        if not partidos and fd_cod:
            partidos = fd_partidos(fd_cod)
            if partidos: fuente="football-data.org"; capa=1
    else:
        if fd_cod:
            partidos = fd_partidos(fd_cod)
            if partidos: fuente="football-data.org"; capa=1
        if not partidos:
            partidos = as_partidos(as_id, season)
            if partidos: fuente="api-sports.io"; capa=1

    # ── CAPA 2 ───────────────────────────────────────────────
    if not partidos:
        partidos = scrape_partidos_emergencia(nombre_liga)
        if partidos: fuente="FBRef.com (scraping)"; capa=2

    return partidos, fuente, capa

# ================================================================
#  MODULO DE FATIGA Y CONTEXTO
# ================================================================
def calcular_fatiga(fecha_ultimo_partido):
    """
    Retorna factor multiplicador de rendimiento.
    < 72h → factor 0.92 (8% menos eficiencia)
    72–96h → factor 0.97
    > 96h → factor 1.00 (normal)
    """
    if not fecha_ultimo_partido: return 1.0, None
    try:
        ult  = datetime.strptime(fecha_ultimo_partido, "%Y-%m-%d")
        hoy  = datetime.now()
        diff = (hoy - ult).total_seconds() / 3600  # horas
        if diff < 72:
            return 0.92, f"⚡ Jugó hace {int(diff)}h — Fatiga alta (factor ×0.92)"
        elif diff < 96:
            return 0.97, f"⚡ Jugó hace {int(diff)}h — Fatiga leve (factor ×0.97)"
        else:
            return 1.0, None
    except: return 1.0, None

def factor_clima(clima):
    """
    Retorna multiplicador para goles segun condiciones climaticas.
    Lluvia > 3mm o Temperatura > 32°C → sesgo hacia Under.
    """
    if not clima: return 1.0, 1.0, None
    lluvia = clima.get("lluvia", 0)
    temp   = clima.get("temp", 20)
    viento = clima.get("viento", 0)
    notas  = []
    f_gol  = 1.0  # multiplicador goles a favor
    f_def  = 1.0  # multiplicador goles en contra

    if isinstance(temp, (int, float)) and temp > 32:
        f_gol  = round(f_gol  * 0.93, 3)
        f_def  = round(f_def  * 0.93, 3)
        notas.append(f"🌡️ Calor extremo {temp}°C → sesgo Under (×0.93)")
    if lluvia > 3:
        f_gol  = round(f_gol  * 0.90, 3)
        notas.append(f"🌧️ Lluvia {lluvia}mm → sesgo Under (×0.90)")
    elif lluvia > 1.5:
        f_gol  = round(f_gol  * 0.95, 3)
        notas.append(f"🌦️ Lluvia leve {lluvia}mm → leve sesgo Under (×0.95)")
    if viento > 35:
        f_gol  = round(f_gol  * 0.96, 3)
        notas.append(f"💨 Viento {viento}km/h → menos tiros precisos (×0.96)")

    nota_final = " | ".join(notas) if notas else None
    return f_gol, f_def, nota_final

# ================================================================
#  CAPA DE ESTADISTICAS — Construccion de perfiles
# ================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def obtener_clima(lat, lon):
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params={"latitude":lat,"longitude":lon,
                                 "current":"temperature_2m,precipitation,windspeed_10m,weathercode",
                                 "timezone":"auto"}, timeout=8)
        c = r.json().get("current",{})
        code = c.get("weathercode",0)
        cond = ("Despejado" if code<3 else "Nublado" if code<50
                else "Lluvioso" if code<80 else "Tormenta")
        return {"temp":c.get("temperature_2m","?"),"lluvia":c.get("precipitation",0),
                "viento":c.get("windspeed_10m",0),"cond":cond,"code":code}
    except: return None

def perfil_de_fd(matches, team_id):
    gf, ga = [], []
    for m in matches:
        ht = m.get("homeTeam",{}).get("id")
        s  = m.get("score",{}).get("fullTime",{})
        h  = s.get("home"); a = s.get("away")
        if h is None or a is None: continue
        if ht==team_id: gf.append(_f(h)); ga.append(_f(a))
        else:           gf.append(_f(a)); ga.append(_f(h))
    if not gf: return None
    n    = min(len(gf), 20)
    gf_n = gf[-n:]; ga_n = ga[-n:]
    btts = sum(1 for x,y in zip(gf_n,ga_n) if x>0 and y>0)
    cs   = sum(1 for y in ga_n if y==0)
    return {"goles_a_favor":round(np.mean(gf_n),3),"goles_contra":round(np.mean(ga_n),3),
            "std_a_favor":round(np.std(gf_n),3),"std_contra":round(np.std(ga_n),3),
            "btts_pct":round(btts/n,2),"cs_pct":round(cs/n,2),
            "tiros":4.5,"amarillas":1.8,"rojas":0.1,"faltas":12.0,"corners":5.2,
            "fuente":"football-data.org","partidos":len(gf)}

def perfil_de_as(stats, is_local=True):
    if not stats: return None
    v = "home" if is_local else "away"
    def g(ruta, d=0.0):
        try:
            x=stats
            for k in ruta: x=x[k]
            return _f(x,d)
        except: return d
    gf = g(["goals","for","average",v])     or g(["goals","for","average","total"])     or 0
    ga = g(["goals","against","average",v]) or g(["goals","against","average","total"]) or 0
    if gf==0 and ga==0: return None
    def card_avg(color):
        d    = stats.get("cards",{}).get(color,{})
        vals = [_f(vv) for vv in d.values() if _f(vv)>0]
        return round(sum(vals)/len(vals),2) if vals else (1.8 if color=="yellow" else 0.1)
    jugados = _f(stats.get("fixtures",{}).get("played",{}).get("total",0))
    return {"goles_a_favor":max(0.3,gf),"goles_contra":max(0.3,ga),
            "std_a_favor":max(0.3,gf)*0.55,"std_contra":max(0.3,ga)*0.55,
            "tiros":g(["shots","on","average"],4.5),
            "amarillas":card_avg("yellow"),"rojas":card_avg("red"),
            "faltas":g(["fouls","committed","average"],12.0),
            "corners":g(["corners","total","average"],5.2),
            "btts_pct":0.45,"cs_pct":0.27,
            "fuente":"api-sports.io","partidos":int(jugados)}

def enriquecer_ultimos(perfil, ultimos, team_id):
    if not ultimos or not perfil: return perfil
    gf_l, ga_l = [], []
    for f in ultimos:
        teams=f.get("teams",{}); goals=f.get("goals",{})
        es_local = teams.get("home",{}).get("id")==team_id
        h=goals.get("home",0) or 0; a=goals.get("away",0) or 0
        gf_l.append(h if es_local else a); ga_l.append(a if es_local else h)
    if gf_l:
        n=len(gf_l)
        perfil["btts_pct"]    = round(sum(1 for x,y in zip(gf_l,ga_l) if x>0 and y>0)/n,2)
        perfil["cs_pct"]      = round(sum(1 for y in ga_l if y==0)/n,2)
        perfil["std_a_favor"] = round(np.std(gf_l),3)
        perfil["std_contra"]  = round(np.std(ga_l),3)
    return perfil

def fusionar_perfiles(fd_p, as_p, nombre_liga):
    """Fusión 70/30 por partidos. Capa 3 si ambos vacíos."""
    defaults = defaults_liga(nombre_liga)
    if fd_p and as_p:
        p_fd=fd_p.get("partidos",0); p_as=as_p.get("partidos",0)
        if p_fd>=p_as: w1,w2,s1,s2=0.70,0.30,fd_p,as_p
        else:          w1,w2,s1,s2=0.70,0.30,as_p,fd_p
        m={}
        for k in ["goles_a_favor","goles_contra","std_a_favor","std_contra"]:
            m[k]=round(s1.get(k,defaults[k])*w1+s2.get(k,defaults[k])*w2,3)
        for k in ["tiros","amarillas","rojas","faltas","corners","btts_pct","cs_pct"]:
            m[k]=s1.get(k,defaults[k])
        m["fuente"]=f"Fusión 70/30 ({s1['fuente'].split('(')[0].strip()})"
        m["partidos"]=max(p_fd,p_as)
        return m
    p = fd_p or as_p
    if p:
        for k,v in defaults.items():
            if k not in p: p[k]=v
        p["capa_datos"]=1
        return p
    # CAPA 3
    defaults["capa_datos"] = 3
    return defaults

def aplicar_fatiga_y_clima(perfil, factor_fat, factor_clima_gol):
    p = dict(perfil)
    p["goles_a_favor"]  = round(p["goles_a_favor"]  * factor_fat * factor_clima_gol, 3)
    p["goles_contra"]   = round(p["goles_contra"]   * factor_clima_gol, 3)
    p["std_a_favor"]    = round(p.get("std_a_favor", p["goles_a_favor"]*0.55) * factor_fat, 3)
    return p

# ================================================================
#  MOTOR MONTE CARLO — Binomial Negativa + Varianza Real
# ================================================================
def correr_montecarlo(lp, vp):
    avg_liga = 1.35
    lh = max(0.25, lp["goles_a_favor"] * (vp["goles_contra"]/avg_liga) * 1.12)
    la = max(0.25, vp["goles_a_favor"] * (lp["goles_contra"]/avg_liga))

    std_h = max(0.40, lp.get("std_a_favor", lh*0.55))
    std_a = max(0.40, vp.get("std_a_favor", la*0.55))

    rng = np.random.default_rng(42)

    def simular_nb(mu, std, n):
        """Binomial Negativa cuando varianza > media (sobredispersion real)."""
        var = std**2
        if var > mu * 1.05 and mu > 0.1:
            r_nb = mu**2 / max(var-mu, 0.01)
            p_nb = r_nb / (r_nb + mu)
            return rng.negative_binomial(max(1, int(round(r_nb))), min(0.9999, p_nb), n)
        return rng.poisson(mu, n)

    hg  = simular_nb(lh, std_h, N_SIM)
    ag  = simular_nb(la, std_a, N_SIM)
    tot = hg + ag

    def p(n): return round(n/N_SIM*100, 1)

    hc  = rng.poisson(lp["corners"],   N_SIM); ac = rng.poisson(vp["corners"],   N_SIM)
    hy  = rng.poisson(lp["amarillas"], N_SIM); ay = rng.poisson(vp["amarillas"], N_SIM)
    hr  = rng.poisson(lp["rojas"],     N_SIM); ar = rng.poisson(vp["rojas"],     N_SIM)
    hf  = rng.poisson(lp["faltas"],    N_SIM); af = rng.poisson(vp["faltas"],    N_SIM)
    hs  = rng.poisson(lp["tiros"],     N_SIM); as_= rng.poisson(vp["tiros"],     N_SIM)

    scores={}
    for h,a in zip(hg,ag): k=f"{h}-{a}"; scores[k]=scores.get(k,0)+1

    var_h = std_h**2
    modelo = "Neg.Binomial" if var_h > lh*1.05 else "Poisson"

    return {
        "p_local":  p(np.sum(hg>ag)),
        "p_empate": p(np.sum(hg==ag)),
        "p_visita": p(np.sum(hg<ag)),
        "lh":round(lh,2), "la":round(la,2),
        "o15":p(np.sum(tot>1.5)), "u15":p(np.sum(tot<=1.5)),
        "o25":p(np.sum(tot>2.5)), "u25":p(np.sum(tot<=2.5)),
        "o35":p(np.sum(tot>3.5)), "u35":p(np.sum(tot<=3.5)),
        "btts":p(np.sum((hg>0)&(ag>0))), "no_btts":p(np.sum(~((hg>0)&(ag>0)))),
        "hc":round(np.mean(hc),2), "ac":round(np.mean(ac),2),
        "tc":round(np.mean(hc+ac),2),
        "co65":p(np.sum(hc+ac>6.5)),  "co85":p(np.sum(hc+ac>8.5)),
        "co105":p(np.sum(hc+ac>10.5)),"cu85":p(np.sum(hc+ac<=8.5)),
        "hy":round(np.mean(hy),2), "ay":round(np.mean(ay),2),
        "ty":round(np.mean(hy+ay),2),
        "hr":round(np.mean(hr),2), "ar":round(np.mean(ar),2),
        "tr":round(np.mean(hr+ar),2),
        "hf":round(np.mean(hf),2), "af":round(np.mean(af),2),
        "tf":round(np.mean(hf+af),2),
        "hs":round(np.mean(hs),2), "as_":round(np.mean(as_),2),
        "top":[(s,p(c)) for s,c in sorted(scores.items(),key=lambda x:-x[1])[:9]],
        "std_h":round(std_h,3), "std_a":round(std_a,3),
        "modelo":modelo,
    }

# ================================================================
#  PREDICCIONES + VALUE BET
# ================================================================
def info_conf(c):
    if c>=80:   return "#3ecf8e","✅ ALTA",  "pc-h","bh"
    elif c>=60: return "#f5c842","⚡ MEDIA", "pc-m","bm"
    else:       return "#f4622a","⚠️ BAJA",  "pc-l","bl_c"

def construir_predicciones(R, local, visita, cuotas=None):
    filas=[]

    # 1X2
    cands=[(R["p_local"],f"Victoria {local}"),(R["p_empate"],"Empate"),(R["p_visita"],f"Victoria {visita}")]
    mejor=max(cands,key=lambda x:x[0])
    conf=mejor[0]
    if cuotas:
        km={f"Victoria {local}":"cuota_local","Empate":"cuota_empate",f"Victoria {visita}":"cuota_visita"}
        odd=cuotas.get(km.get(mejor[1],""))
        if odd: conf=round(mejor[0]*0.65+impl(odd)*0.35,1)
    filas.append({"mkt":"Resultado 1X2","pick":mejor[1],"conf":conf,
                  "det":f"Local {R['p_local']}% / Empate {R['p_empate']}% / Visita {R['p_visita']}%",
                  "cuota_key":("cuota_local" if "Victoria "+local==mejor[1]
                                else "cuota_empate" if "Empate"==mejor[1] else "cuota_visita")})

    # Goles multiples lineas
    for line,ov,uv,ck in [("1.5",R["o15"],R["u15"],"cuota_o15"),
                            ("2.5",R["o25"],R["u25"],"cuota_o25"),
                            ("3.5",R["o35"],R["u35"],"cuota_o35")]:
        pick = f"Mas de {line} goles" if ov>=uv else f"Menos de {line} goles"
        ck2  = ck if ov>=uv else ck.replace("o","u")
        filas.append({"mkt":f"Goles O/U {line}","pick":pick,"conf":max(ov,uv),
                      "det":f"Goles esperados: {round(R['lh']+R['la'],2)}","cuota_key":ck2})

    # BTTS
    filas.append({"mkt":"Ambos Marcan (BTTS)",
                  "pick":"Si — Ambos anotan" if R["btts"]>=R["no_btts"] else "No — Alguno no anota",
                  "conf":max(R["btts"],R["no_btts"]),
                  "det":f"λ local {R['lh']} / λ visita {R['la']}","cuota_key":None})

    # Corners
    for line,ov,uv in [("6.5",R["co65"],100-R["co65"]),
                        ("8.5",R["co85"],R["cu85"]),
                        ("10.5",R["co105"],100-R["co105"])]:
        pick=f"Mas de {line}" if ov>=uv else f"Menos de {line}"
        filas.append({"mkt":f"Corners O/U {line}","pick":pick,"conf":max(ov,uv),
                      "det":f"Total esperado: {R['tc']} corners","cuota_key":None})

    # Doble oportunidad
    dc1=min(round(R["p_local"]+R["p_empate"],1),99.0)
    dc2=min(round(R["p_visita"]+R["p_empate"],1),99.0)
    filas.append({"mkt":"Doble Oportunidad",
                  "pick":f"{local} o Empate" if dc1>=dc2 else f"{visita} o Empate",
                  "conf":max(dc1,dc2),"det":"Cubre dos de tres resultados","cuota_key":None})

    # Tarjetas
    ty=R["ty"]; ly=max(1,round(ty)-1)
    py=min(95.0,max(5.0,round(50+(ty-ly-0.5)*18,1)))
    filas.append({"mkt":f"Amarillas O {ly}.5","pick":f"Mas de {ly}.5 amarillas",
                  "conf":py,"det":f"Total esperado: {ty} amarillas","cuota_key":None})

    # Marcador exacto
    top=R["top"][0]
    filas.append({"mkt":"Marcador Exacto","pick":f"Resultado {top[0]}",
                  "conf":top[1],"det":"Mas frecuente en 10,000 simulaciones","cuota_key":None})

    # Agregar EV y Value Bet a cada fila
    for f in filas:
        odd_val = cuotas.get(f["cuota_key"]) if cuotas and f.get("cuota_key") else None
        es_vb, ev_val = ev_check(f["conf"], odd_val)
        f["odd_val"]  = odd_val
        f["es_vb"]    = es_vb
        f["ev_val"]   = ev_val
        f["roi_est"]  = roi_estimado(f["conf"], odd_val)

    return sorted(filas, key=lambda x: (-x["conf"], -(x["ev_val"] or 0)))

# ================================================================
#  SUGERENCIA DE APUESTA — EV > 1.05 obligatorio
# ================================================================
def generar_sugerencia(predicciones, local, visita, cuotas, bankroll=100):
    # Solo recomienda si EV >= 1.05
    candidatos = [p for p in predicciones if p["conf"]>=70 and p.get("odd_val")]
    vb_puras   = [p for p in candidatos if p.get("es_vb")]
    pool       = vb_puras if vb_puras else candidatos[:1]
    if not pool: return None

    mejor = max(pool, key=lambda x: (x.get("ev_val") or 0, x["conf"]))
    conf  = mejor["conf"]
    odd   = mejor.get("odd_val")
    ev    = mejor.get("ev_val", 0)
    roi   = mejor.get("roi_est")
    stake = kelly(conf, odd or 1.85, bankroll) if odd else None

    riesgo = ("BAJO","#3ecf8e") if conf>=85 else ("MEDIO","#f5c842") if conf>=75 else ("ALTO","#f4622a")
    ventaja= round(conf - impl(odd), 1) if odd else None

    # Combinada si hay 2+ VB
    combinada = None
    if len(vb_puras) >= 2:
        c2 = vb_puras[1]
        conf_combo = round(vb_puras[0]["conf"] * vb_puras[1]["conf"] / 100, 1)
        if conf_combo >= 45:
            combinada = {"picks": [vb_puras[0]["pick"], vb_puras[1]["pick"]],
                         "conf": conf_combo,
                         "mkts": [vb_puras[0]["mkt"], vb_puras[1]["mkt"]]}

    return {"pick":mejor["pick"],"mkt":mejor["mkt"],"conf":conf,
            "odd":odd,"ev":ev,"roi":roi,"stake":stake,
            "impl":impl(odd),"ventaja":ventaja,
            "riesgo":riesgo,"combinada":combinada,
            "es_vb":mejor.get("es_vb",False)}

# ================================================================
#  CUOTAS
# ================================================================
@st.cache_data(ttl=1800, show_spinner=False)
def obtener_cuotas(sport_key, local, visita):
    if not sport_key or not ODDS_KEY: return None
    try:
        r = requests.get(f"{OD_BASE}/sports/{sport_key}/odds",
                         params={"apiKey":ODDS_KEY,"regions":"eu",
                                 "markets":"h2h,totals","oddsFormat":"decimal"},
                         timeout=12)
        if r.status_code != 200: return None
        hl=local.lower(); al=visita.lower()
        for ev in r.json():
            h2=ev.get("home_team","").lower(); a2=ev.get("away_team","").lower()
            if (hl[:6] in h2 or h2[:6] in hl) and (al[:6] in a2 or a2[:6] in al):
                bk=(ev.get("bookmakers") or [{}])[0]
                res={"local":local,"visita":visita,"casa":bk.get("title","")}
                for mkt in bk.get("markets",[]):
                    if mkt["key"]=="h2h":
                        for o in mkt.get("outcomes",[]):
                            n=o["name"].lower()
                            if hl[:5] in n:   res["cuota_local"]=o["price"]
                            elif "draw" in n: res["cuota_empate"]=o["price"]
                            else:             res["cuota_visita"]=o["price"]
                    elif mkt["key"]=="totals":
                        for o in mkt.get("outcomes",[]):
                            if o["name"]=="Over":  res["cuota_o25"]=o["price"]
                            elif o["name"]=="Under":res["cuota_u25"]=o["price"]
                return res
    except: pass
    return None

# ================================================================
#  RENDER UI
# ================================================================
def render_pred(pred):
    color,badge,pc_cls,b_cls = info_conf(pred["conf"])
    c=pred["conf"]; w=int(min(c,100))
    vb_html=""
    if pred.get("es_vb") and pred.get("odd_val"):
        vb_html=f'<div style="margin-top:6px;padding:4px 10px;background:rgba(62,207,142,.1);border-radius:6px;font-size:.7rem;color:#3ecf8e">💎 VALUE BET — EV {pred["ev_val"]:.3f} | ROI est. {pred["roi_est"]:+.1f}%</div>'
    elif pred.get("odd_val") and not pred.get("es_vb"):
        vb_html=f'<div style="margin-top:5px;padding:4px 10px;background:rgba(244,98,42,.07);border-radius:6px;font-size:.7rem;color:#804050">EV {pred.get("ev_val",0):.3f} — Sin ventaja suficiente (umbral 1.05)</div>'
    alerta=""
    if c<60:
        alerta=f'<div style="margin-top:6px;padding:5px 10px;background:rgba(244,98,42,.08);border-radius:6px;font-size:.73rem;color:#f4622a">⚠️ Confianza baja ({c}%) — No apostar.</div>'
    elif c<80:
        alerta=f'<div style="margin-top:5px;padding:5px 10px;background:rgba(245,200,66,.07);border-radius:6px;font-size:.73rem;color:#f5c842">⚡ Confianza media ({c}%) — Analiza antes de apostar.</div>'

    st.markdown(f"""
    <div class="pc {pc_cls}">
      <div style="min-width:128px"><div class="pmkt">{pred['mkt']}</div></div>
      <div style="flex:1">
        <div class="ppick">{pred['pick']}</div>
        <div class="pdet">{pred['det']}</div>
        {vb_html}
      </div>
      <div style="text-align:center;min-width:95px">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;color:{color};line-height:1">{c}%</div>
        <div style="background:#0a0a1a;border-radius:99px;height:6px;overflow:hidden;margin:4px 0">
          <div style="width:{w}%;height:100%;background:{color};border-radius:99px"></div>
        </div>
        <span class="pbadge {b_cls}">{badge}</span>
      </div>
    </div>{alerta}""", unsafe_allow_html=True)

def render_sugerencia(sug, bankroll):
    if not sug:
        st.markdown('<div class="vb-no">⚠️ No se encontró ninguna apuesta con EV ≥ 1.05 en este partido. El modelo recomienda NO apostar en este juego.</div>', unsafe_allow_html=True)
        return
    color,_,_,_ = info_conf(sug["conf"])
    rl,rc = sug["riesgo"]

    vb_html=""
    if sug.get("es_vb"):
        vb_html=f'<div class="vb-yes">💎 <b>VALUE BET CONFIRMADA</b> — EV {sug["ev"]:.3f} (necesario &gt;1.05) | Ventaja de +{sug["ventaja"]}% sobre la casa | ROI estimado: <b>{sug["roi"]:+.1f}%</b></div>'
    else:
        vb_html=f'<div style="background:#100808;border:1px solid #f5c84222;border-radius:8px;padding:8px 14px;margin-top:8px;font-size:.78rem;color:#806040">⚡ Selección por mayor confianza. Sin cuota disponible para calcular EV exacto.</div>'

    cuota_txt  = f"{sug['odd']:.2f}" if sug["odd"] else "N/D (sin cuota en vivo)"
    impl_txt   = f"{sug['impl']}% implícito" if sug["impl"] else "N/D"
    stake_txt  = f"${sug['stake']:.2f} de ${bankroll} ({round(sug['stake']/bankroll*100,1) if bankroll>0 else 0}% del bankroll)" if sug["stake"] else "Sin cuota para calcular"
    roi_txt    = f"{sug['roi']:+.1f}%" if sug["roi"] is not None else "N/D"

    combo_html=""
    if sug.get("combinada"):
        cmb=sug["combinada"]
        combo_html=f"""
        <div class="combo-box">
          <div style="font-size:.62rem;color:#204020;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">Apuesta Combinada (2 Value Bets)</div>
          <div style="font-weight:600;font-size:.88rem;color:#c0d0c0">{"  +  ".join(cmb['picks'])}</div>
          <div style="font-size:.7rem;color:#305030;margin-top:4px">{" / ".join(cmb['mkts'])}</div>
          <div style="font-size:.72rem;color:#3ecf8e66;margin-top:4px">Confianza combinada: {cmb['conf']}% — Mayor cuota potencial, mayor riesgo</div>
        </div>"""

    st.markdown(f"""
    <div class="bet-box">
      <div class="bet-title">SUGERENCIA DE APUESTA</div>
      <div class="bet-row">
        <span class="bet-lbl">Mercado recomendado</span>
        <span class="bet-val">{sug['mkt']}</span>
      </div>
      <div class="bet-row">
        <span class="bet-lbl">Seleccion</span>
        <span style="font-weight:700;font-size:.9rem;color:#ddddf5">{sug['pick']}</span>
      </div>
      <div class="bet-row">
        <span class="bet-lbl">Confianza estadistica</span>
        <span style="font-family:'Bebas Neue',sans-serif;font-size:1.6rem;color:{color}">{sug['conf']}%</span>
      </div>
      <div class="bet-row">
        <span class="bet-lbl">Cuota de referencia</span>
        <span class="bet-val">{cuota_txt}</span>
      </div>
      <div class="bet-row">
        <span class="bet-lbl">Probabilidad implicita</span>
        <span style="color:#606080;font-size:.88rem">{impl_txt}</span>
      </div>
      <div class="bet-row">
        <span class="bet-lbl">ROI estimado</span>
        <span style="color:#f5c842;font-weight:700">{roi_txt}</span>
      </div>
      <div class="bet-row">
        <span class="bet-lbl">Nivel de riesgo</span>
        <span style="color:{rc};font-weight:700">{rl}</span>
      </div>
      <div class="bet-row">
        <span class="bet-lbl">Stake Kelly x0.25</span>
        <span style="color:#f5c842;font-weight:600;font-size:.85rem">{stake_txt}</span>
      </div>
      {vb_html}
      {combo_html}
      <div class="bet-warn">
        ⚠️ <b>Criterio de Kelly fraccionado al 25%</b> para proteger tu bankroll.
        Solo se recomienda apostar cuando EV ≥ 1.05 (ventaja real sobre la casa).
        Este análisis es estadístico — no es garantía de resultado.
        Nunca apuestes más de lo que puedes perder.
      </div>
    </div>""", unsafe_allow_html=True)

def barra(label, val, color):
    st.markdown(f"""<div class="prow">
      <div class="prow-lbl">{label} — <b style="color:{color}">{val}%</b></div>
      <div class="pbar"><div class="pfill" style="width:{min(val,100)}%;background:{color}"></div></div>
    </div>""", unsafe_allow_html=True)

def kpi(val, label, col):
    col.markdown(f'<div class="kpi"><div class="kv">{val}</div><div class="kl">{label}</div></div>', unsafe_allow_html=True)

def seccion(txt):
    st.markdown(f'<div class="sec">{txt}</div>', unsafe_allow_html=True)

def pill(nombre, activa):
    c="aon" if activa else "aoff"; i="✅" if activa else "○"
    return f'<span class="apill {c}">{i} {nombre}</span>'

def capa_badge(capa):
    if capa==1:   return '<span class="capa-badge capa-1">Capa 1 — API</span>'
    elif capa==2: return '<span class="capa-badge capa-2">Capa 2 — Scraping</span>'
    else:         return '<span class="capa-badge capa-3">Capa 3 — Historico</span>'

# ================================================================
#  SIDEBAR
# ================================================================
with st.sidebar:
    st.markdown("## Configuracion")
    st.markdown("---")
    bankroll = st.number_input("Bankroll para Kelly ($)",
                                min_value=10, max_value=1000000,
                                value=st.session_state.get("bankroll",100), step=10,
                                help="Capital total para apuestas")
    st.session_state["bankroll"] = bankroll

    st.markdown(f"**Umbral Value Bet:** EV ≥ {EV_MINIMO}")
    st.markdown(f"**Ventana:** {DAYS_AHEAD} dias")
    st.markdown("---")

    if st.button("Probar conexiones"):
        with st.spinner("Probando..."):
            try:
                r=requests.get(f"{FD_BASE}/competitions",headers=FD_HDR,timeout=8)
                st.success(f"football-data.org: HTTP {r.status_code}")
            except Exception as e: st.error(f"FD: {e}")
            try:
                r=requests.get(f"{AS_BASE}/status",headers=AS_HDR,timeout=8)
                d=r.json().get("response",{})
                req=d.get("requests",{})
                st.success(f"api-sports: {req.get('current',0)}/{req.get('limit_day',100)} req | Plan: {d.get('subscription',{}).get('plan','?')}")
            except Exception as e: st.error(f"AS: {e}")
            try:
                r=requests.get(f"{OD_BASE}/sports",params={"apiKey":ODDS_KEY},timeout=8)
                rem=r.headers.get("x-requests-remaining","?")
                st.success(f"odds-api: HTTP {r.status_code} | Restantes: {rem}")
            except Exception as e: st.error(f"Odds: {e}")
            try:
                r=requests.get("https://api.open-meteo.com/v1/forecast",
                               params={"latitude":4.71,"longitude":-74.07,"current":"temperature_2m"},timeout=8)
                t=r.json().get("current",{}).get("temperature_2m","?")
                st.success(f"open-meteo: {t}°C en Bogota ✅")
            except: st.error("open-meteo: sin respuesta")

    st.markdown("---")
    st.markdown("**Leyenda:**")
    st.markdown("✅ **ALTA** ≥ 80%")
    st.markdown("⚡ **MEDIA** 60–79%")
    st.markdown("⚠️ **BAJA** < 60%")
    st.markdown("💎 **VALUE BET** EV ≥ 1.05")
    st.markdown("---")
    st.markdown("**Motor:**")
    st.markdown("Binomial Negativa / Poisson")
    st.markdown("Fusión 70/30 por partidos")
    st.markdown("Multi-temporada automatico")
    st.markdown("Fatiga < 72h")
    st.markdown("Ajuste clima + calor")
    st.markdown("Cascada 3 capas")

# ================================================================
#  MAIN
# ================================================================
st.markdown(f"""
<div class="hero">
  <div class="hero-ver">PROFESSIONAL BETTING SUITE</div>
  <h1>FOOTBALL ORACLE PRO</h1>
  <div class="hero-sub">
    v5.0 · Triple Capa de Datos · Binomial Negativa · Value Bet EV≥1.05 ·
    Fatiga · Clima · Kelly x0.25 · ROI · 10,000 Simulaciones
  </div>
  <div class="api-row">
    {pill("football-data.org", bool(FD_KEY))}
    {pill("api-sports.io",     bool(APISPORTS))}
    {pill("the-odds-api",      bool(ODDS_KEY))}
    {pill("open-meteo",        True)}
    {pill("FBRef (Capa 2)",    True)}
  </div>
</div>
""", unsafe_allow_html=True)

# ── LIGA ──────────────────────────────────────────────────────────
seccion("① ELIGE LA LIGA")

regiones = {}
for nombre, info in LIGAS.items():
    r = info["region"]
    regiones.setdefault(r, []).append(nombre)

c1, c2 = st.columns(2)
with c1:
    region = st.selectbox("Region", list(regiones.keys()), label_visibility="collapsed")
with c2:
    nombre_liga = st.selectbox("Liga", regiones[region], label_visibility="collapsed")

# ── PARTIDO ───────────────────────────────────────────────────────
seccion("② ELIGE EL PARTIDO")

with st.spinner(f"Buscando partidos (Cascada 3 capas — {DAYS_AHEAD} dias)..."):
    partidos, fuente_usada, capa_usada = cargar_partidos_cascada(nombre_liga)

if not partidos:
    st.warning(f"No se encontraron partidos para **{nombre_liga}** en ninguna de las 3 capas.")
    lg = LIGAS[nombre_liga]
    with st.expander("Diagnostico de API"):
        try:
            hoy=datetime.now().strftime("%Y-%m-%d")
            fut=(datetime.now()+timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
            r=requests.get(f"{AS_BASE}/fixtures",headers=AS_HDR,
                           params={"league":lg["as_id"],"season":lg["season"],"from":hoy,"to":fut},timeout=12)
            d=r.json()
            st.code(f"HTTP {r.status_code} | results: {d.get('results',0)} | errors: {d.get('errors',{})}")
        except Exception as e: st.error(str(e))
    st.stop()

capa_label = ["","🟢 Capa 1 (API)","🔵 Capa 2 (Scraping)","🟡 Capa 3 (Historico)"][capa_usada] if capa_usada<=3 else ""
st.success(f"{len(partidos)} partido(s) encontrado(s) — {capa_label} — fuente: **{fuente_usada}**")

mapa = {p["display"]: p for p in partidos}
sel  = st.selectbox("Partido", list(mapa.keys()), label_visibility="collapsed")
M    = mapa[sel]

st.markdown(f"""
<div class="mbox">
  <span class="tn">{M['local']}</span>
  <span class="vs">VS</span>
  <span class="tn">{M['visita']}</span>
  <div class="mmeta">📅 {M['fecha']} &nbsp;·&nbsp; <span class="src-chip">{M.get('fuente','')}</span> &nbsp; {capa_badge(M.get('capa',1))}</div>
</div>
""", unsafe_allow_html=True)

# ── ANÁLISIS ──────────────────────────────────────────────────────
if st.button("ANALIZAR CON MONTE CARLO — 10,000 SIMULACIONES"):
    with st.spinner("Ejecutando análisis profundo..."):
        lg      = LIGAS[nombre_liga]
        season  = lg["season"]
        as_id   = lg["as_id"]

        # Resolver IDs
        id_local_as  = M.get("id_local_as")  or as_buscar_equipo(M["local"])
        id_visita_as = M.get("id_visita_as") or as_buscar_equipo(M["visita"])
        id_local_fd  = M.get("id_local_fd")
        id_visita_fd = M.get("id_visita_fd")

        # Estadisticas
        hist_local   = fd_historial(id_local_fd,  50) if id_local_fd  else []
        hist_visita  = fd_historial(id_visita_fd, 50) if id_visita_fd else []
        stats_local  = as_estadisticas(id_local_as,  as_id, season) if id_local_as  else {}
        stats_visita = as_estadisticas(id_visita_as, as_id, season) if id_visita_as else {}
        ult_local    = as_ultimos(id_local_as,  season, 20) if id_local_as  else []
        ult_visita   = as_ultimos(id_visita_as, season, 20) if id_visita_as else []

        # Perfiles
        fd_lp = perfil_de_fd(hist_local,  id_local_fd)
        fd_vp = perfil_de_fd(hist_visita, id_visita_fd)
        as_lp = perfil_de_as(stats_local,  is_local=True)
        as_vp = perfil_de_as(stats_visita, is_local=False)

        fd_lp = enriquecer_ultimos(fd_lp, ult_local,  id_local_as)  if fd_lp else fd_lp
        fd_vp = enriquecer_ultimos(fd_vp, ult_visita, id_visita_as) if fd_vp else fd_vp

        lp = fusionar_perfiles(fd_lp, as_lp, nombre_liga)
        vp = fusionar_perfiles(fd_vp, as_vp, nombre_liga)

        # Fatiga
        ult_fecha_local  = as_ultimo_partido_fecha(id_local_as,  season) if id_local_as  else fd_ultimo_partido(id_local_fd)  if id_local_fd  else None
        ult_fecha_visita = as_ultimo_partido_fecha(id_visita_as, season) if id_visita_as else fd_ultimo_partido(id_visita_fd) if id_visita_fd else None
        fat_l, fat_l_msg = calcular_fatiga(ult_fecha_local)
        fat_v, fat_v_msg = calcular_fatiga(ult_fecha_visita)

        # Clima
        coords = COORDENADAS.get(nombre_liga, (4.71,-74.07))
        clima  = obtener_clima(coords[0], coords[1])
        f_clima_gol, _, clima_msg = factor_clima(clima)

        # Aplicar factores
        lp = aplicar_fatiga_y_clima(lp, fat_l, f_clima_gol)
        vp = aplicar_fatiga_y_clima(vp, fat_v, f_clima_gol)

        # Cuotas
        sport_key = lg.get("odds_key")
        cuotas    = obtener_cuotas(sport_key, M["local"], M["visita"]) if sport_key else None

        # Monte Carlo
        R     = correr_montecarlo(lp, vp)
        preds = construir_predicciones(R, M["local"], M["visita"], cuotas)
        sug   = generar_sugerencia(preds, M["local"], M["visita"], cuotas or {},
                                    st.session_state.get("bankroll",100))

    st.success("✅ 10,000 simulaciones completadas")

    # ── CALIDAD DE DATOS ──────────────────────────────────────
    seccion("CALIDAD DE DATOS")
    p_l = int(lp.get("partidos",0)); p_v = int(vp.get("partidos",0))
    def cq(n): return "#3ecf8e" if n>=10 else "#f5c842" if n>=5 else "#f4622a"

    c1,c2,c3 = st.columns(3)
    c1.markdown(f'<div class="kpi"><div class="kv" style="color:{cq(p_l)}">{p_l}</div><div class="kl">Partidos {M["local"][:14]}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi"><div class="kv" style="color:{cq(p_v)}">{p_v}</div><div class="kl">Partidos {M["visita"][:14]}</div></div>', unsafe_allow_html=True)
    kpi(R["modelo"], "Motor MC", c3)

    col1,col2 = st.columns(2)
    col1.markdown(f'**{M["local"]}:** <span class="src-chip">{lp.get("fuente","?")}</span>', unsafe_allow_html=True)
    col2.markdown(f'**{M["visita"]}:** <span class="src-chip">{vp.get("fuente","?")}</span>', unsafe_allow_html=True)

    capa_datos = lp.get("capa_datos",1)
    if capa_datos==3:
        st.markdown('<div style="background:#141002;border-left:3px solid #f5c842;border-radius:0 8px 8px 0;padding:10px 14px;font-size:.78rem;color:#a07030;margin:8px 0">🟡 <b>Capa 3 activa</b> — Sin datos de APIs para este equipo. Usando promedios históricos de la liga. Activa más fuentes para mayor precisión.</div>', unsafe_allow_html=True)
    elif p_l<5 or p_v<5:
        st.markdown('<div style="background:#141002;border-left:3px solid #f5c842;border-radius:0 8px 8px 0;padding:10px 14px;font-size:.78rem;color:#a07030;margin:8px 0">⚡ Datos limitados (&lt;5 partidos). Las predicciones pueden tener menor precisión.</div>', unsafe_allow_html=True)

    # Fatiga
    if fat_l_msg:
        st.markdown(f'<div class="alerta-fatiga">⚡ <b>{M["local"]}:</b> {fat_l_msg}</div>', unsafe_allow_html=True)
    if fat_v_msg:
        st.markdown(f'<div class="alerta-fatiga">⚡ <b>{M["visita"]}:</b> {fat_v_msg}</div>', unsafe_allow_html=True)

    # Clima
    if clima:
        ico = "🌧️" if clima["lluvia"]>2 else "🌡️" if (isinstance(clima["temp"],(int,float)) and clima["temp"]>32) else "💨" if clima["viento"]>35 else "☀️" if clima["code"]<3 else "☁️"
        st.markdown(f'<div class="alerta-clima">{ico} <b>Clima:</b> {clima["cond"]} | {clima["temp"]}°C | Lluvia: {clima["lluvia"]}mm | Viento: {clima["viento"]}km/h{(" | " + clima_msg) if clima_msg else ""}</div>', unsafe_allow_html=True)

    # ── CUOTAS EN VIVO ────────────────────────────────────────
    if cuotas:
        seccion("CUOTAS EN TIEMPO REAL")
        st.markdown(f'<div style="font-size:.7rem;color:#28284a;margin-bottom:10px">Fuente: {cuotas.get("casa","")} via the-odds-api.com</div>', unsafe_allow_html=True)
        c1,c2,c3 = st.columns(3)
        for col,label,key in [(c1,M["local"][:14],"cuota_local"),(c2,"Empate","cuota_empate"),(c3,M["visita"][:14],"cuota_visita")]:
            ov=cuotas.get(key,0)
            kpi(f"{ov:.2f}" if ov else "N/D", f"{label} (impl. {impl(ov)}%)", col)

    # ── SUGERENCIA ────────────────────────────────────────────
    seccion("SUGERENCIA DE APUESTA — VALUE BET EV≥1.05")
    render_sugerencia(sug, st.session_state.get("bankroll",100))

    # ── PREDICCIONES ──────────────────────────────────────────
    seccion("PREDICCIONES POR NIVEL DE CONFIANZA")
    altas  = [p for p in preds if p["conf"]>=80]
    medias = [p for p in preds if 60<=p["conf"]<80]
    bajas  = [p for p in preds if p["conf"]<60]
    vb_count = sum(1 for p in preds if p.get("es_vb"))

    c1,c2,c3,c4 = st.columns(4)
    kpi(str(len(altas)),  "ALTA ≥80% ✅",    c1)
    kpi(str(len(medias)), "MEDIA 60-79% ⚡",  c2)
    kpi(str(len(bajas)),  "BAJA <60% ⚠️",    c3)
    kpi(str(vb_count),    "Value Bets 💎",    c4)

    st.markdown("<br>", unsafe_allow_html=True)
    if altas:
        st.markdown("#### ✅ Alta confianza (≥80%)")
        for p in altas: render_pred(p)
    if medias:
        st.markdown("#### ⚡ Confianza media (60–79%)")
        for p in medias: render_pred(p)
    if bajas:
        st.markdown("#### ⚠️ Baja confianza (<60%) — No apostar")
        for p in bajas: render_pred(p)

    # ── 1X2 ──────────────────────────────────────────────────
    seccion("PROBABILIDADES 1X2")
    barra(f"Local: {M['local']}",   R["p_local"],  "#3ecf8e")
    barra("Empate",                  R["p_empate"], "#f5c842")
    barra(f"Visita: {M['visita']}", R["p_visita"], "#f4622a")

    # ── GOLES ─────────────────────────────────────────────────
    seccion("GOLES PROYECTADOS")
    c1,c2,c3,c4 = st.columns(4)
    kpi(R["lh"],         f"Goles esp.\n{M['local'][:12]}",  c1)
    kpi(R["la"],         f"Goles esp.\n{M['visita'][:12]}", c2)
    kpi(f"{R['o25']}%",  "Mas de 2.5",                      c3)
    kpi(f"{R['btts']}%", "BTTS",                             c4)

    # ── MARCADORES ────────────────────────────────────────────
    seccion("MARCADORES MAS PROBABLES")
    st.dataframe(
        pd.DataFrame(R["top"], columns=["Marcador","Prob %"])
          .style.background_gradient(subset=["Prob %"], cmap="Oranges")
          .format({"Prob %":"{:.1f}%"}),
        use_container_width=True, hide_index=True)

    # ── CORNERS ───────────────────────────────────────────────
    seccion("CORNERS")
    c1,c2,c3,c4 = st.columns(4)
    kpi(R["hc"],         f"Corners {M['local'][:12]}",  c1)
    kpi(R["ac"],         f"Corners {M['visita'][:12]}", c2)
    kpi(R["tc"],         "Total Corners",                c3)
    kpi(f"{R['co85']}%", "Mas de 8.5",                  c4)

    # ── TARJETAS ──────────────────────────────────────────────
    seccion("TARJETAS")
    c1,c2,c3,c4 = st.columns(4)
    kpi(R["hy"], f"Amarillas {M['local'][:12]}",  c1)
    kpi(R["ay"], f"Amarillas {M['visita'][:12]}", c2)
    kpi(R["ty"], "Total Amarillas",                c3)
    kpi(R["tr"], "Rojas Totales",                  c4)

    # ── FALTAS & TIROS ────────────────────────────────────────
    seccion("FALTAS Y TIROS A PUERTA")
    c1,c2 = st.columns(2)
    with c1:
        st.dataframe(pd.DataFrame({
            "Equipo":[M["local"],M["visita"],"TOTAL"],
            "Faltas":[R["hf"],R["af"],R["tf"]]
        }), use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(pd.DataFrame({
            "Equipo":[M["local"],M["visita"]],
            "Tiros a puerta":[R["hs"],R["as_"]]
        }), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Football Oracle PRO v5.0 — Solo se recomienda apostar cuando EV ≥ 1.05 (ventaja real sobre la casa). El Criterio de Kelly fraccionado al 25% protege tu bankroll. Análisis estadístico educativo — no garantía de resultado. Apuesta con responsabilidad.")
