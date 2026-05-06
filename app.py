# ================================================================
#  FOOTBALL ORACLE PRO v3.5 — Versión Definitiva
#  Multi-API | Deep Data | Monte Carlo con Varianza | Kelly
# ================================================================

import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import math

# ================================================================
#  KEYS — Integradas y listas para usar
# ================================================================
FD_KEY    = "a2aef808a68d4cd6ba2ad97f9953ec81"   # football-data.org
APISPORTS = "70cb24441a57cc0a28c2fd7dd3b76110"   # api-sports.io
ODDS_KEY  = "f028e4d3689b54c609ce7137fc6a40ba"   # the-odds-api.com
# open-meteo.com — sin key necesaria
# ================================================================

N_SIM      = 10_000
DAYS_AHEAD = 45

# ── Lectura de Secrets de Streamlit (override opcional) ──────────
def _s(k, d=""):
    try:    return st.secrets.get(k, d)
    except: return d

FD_KEY    = _s("FD_KEY",    FD_KEY)
APISPORTS = _s("APISPORTS", APISPORTS)
ODDS_KEY  = _s("ODDS_KEY",  ODDS_KEY)

FD_HDR = {"X-Auth-Token": FD_KEY}
AS_HDR = {"x-apisports-key": APISPORTS}
FD_BASE = "https://api.football-data.org/v4"
AS_BASE = "https://v3.football.api-sports.io"
OD_BASE = "https://api.the-odds-api.com/v4"

# ================================================================
#  LIGAS — Solo las de valor
# ================================================================
LIGAS = {
    "Liga BetPlay Dimayor (COL)":    {"as_id": 239, "fd_code": None,  "season": 2025, "region": "Latinoamerica"},
    "Liga Profesional (ARG)":        {"as_id": 128, "fd_code": None,  "season": 2025, "region": "Latinoamerica"},
    "Serie A Brasileirao (BRA)":     {"as_id": 71,  "fd_code": None,  "season": 2025, "region": "Latinoamerica"},
    "UEFA Champions League":         {"as_id": 2,   "fd_code": "CL",  "season": 2024, "region": "Internacional"},
    "Premier League (ENG)":          {"as_id": 39,  "fd_code": "PL",  "season": 2024, "region": "Internacional"},
    "La Liga (ESP)":                 {"as_id": 140, "fd_code": "PD",  "season": 2024, "region": "Internacional"},
    "FIFA Mundial 2026":             {"as_id": 1,   "fd_code": None,  "season": 2026, "region": "Internacional"},
}

ODDS_MAP = {
    "Liga BetPlay Dimayor (COL)":   "soccer_colombia_primera_a",
    "Liga Profesional (ARG)":       "soccer_argentina_primera_division",
    "Serie A Brasileirao (BRA)":    "soccer_brazil_campeonato",
    "UEFA Champions League":        "soccer_uefa_champs_league",
    "Premier League (ENG)":         "soccer_england_league1",
    "La Liga (ESP)":                "soccer_spain_la_liga",
}

COORDENADAS = {
    "Liga BetPlay Dimayor (COL)":   ( 4.71, -74.07),
    "Liga Profesional (ARG)":       (-34.60, -58.44),
    "Serie A Brasileirao (BRA)":    (-23.54, -46.63),
    "UEFA Champions League":        ( 51.50,  -0.12),
    "Premier League (ENG)":         ( 51.50,  -0.12),
    "La Liga (ESP)":                ( 40.45,  -3.69),
    "FIFA Mundial 2026":            ( 29.76, -95.37),
}

# ================================================================
#  STREAMLIT CONFIG & CSS
# ================================================================
st.set_page_config(
    page_title="Football Oracle PRO v3.5",
    page_icon="⚽", layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;700&display=swap');
*{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#06060e;color:#e2e2f0;}

.hero{
  background:linear-gradient(135deg,#0c0c1e 0%,#160808 100%);
  border:1px solid #20203a;border-radius:20px;
  padding:36px 40px 28px;margin-bottom:30px;
  position:relative;overflow:hidden;
}
.hero::before{
  content:'';position:absolute;top:-100px;right:-100px;
  width:400px;height:400px;
  background:radial-gradient(circle,rgba(244,98,42,.10) 0%,transparent 65%);
}
.hero::after{
  content:'ORACLE';position:absolute;bottom:-20px;right:20px;
  font-family:'Bebas Neue',sans-serif;font-size:9rem;
  color:rgba(244,98,42,.04);letter-spacing:8px;pointer-events:none;
}
.hero h1{font-family:'Bebas Neue',sans-serif;font-size:clamp(2rem,5vw,3.2rem);
  color:#f4622a;letter-spacing:3px;line-height:.9;margin:0;}
.hero .ver{font-size:.75rem;color:#f4622a88;letter-spacing:4px;margin-bottom:8px;}
.hero .sub{color:#50507a;font-size:.82rem;margin-top:10px;letter-spacing:.3px;}
.api-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;}
.apill{padding:3px 10px;border-radius:99px;font-size:.68rem;font-weight:600;letter-spacing:.5px;}
.apill-on{background:rgba(62,207,142,.1);color:#3ecf8e;border:1px solid #3ecf8e44;}
.apill-off{background:rgba(244,98,42,.08);color:#f4622a55;border:1px solid #f4622a22;}

.sec{font-family:'Bebas Neue',sans-serif;font-size:1.25rem;color:#f4622a;
  letter-spacing:3px;border-bottom:1px solid #18182a;padding-bottom:6px;margin:24px 0 16px;}

.kpi{background:#0c0c1c;border:1px solid #1a1a2e;border-radius:14px;
  padding:16px;text-align:center;margin-bottom:8px;}
.kv{font-family:'Bebas Neue',sans-serif;font-size:2.1rem;color:#f5c842;line-height:1.1;}
.kl{font-size:.62rem;color:#35354a;letter-spacing:2px;text-transform:uppercase;margin-top:3px;}

.match-box{background:#0c0c1c;border:1px solid #1a1a2e;border-radius:16px;
  padding:24px;text-align:center;margin:16px 0;}
.tn{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;color:#e2e2f0;}
.vs{font-family:'Bebas Neue',sans-serif;font-size:2.4rem;color:#f4622a;margin:0 8px;}
.match-meta{color:#30304a;font-size:.78rem;margin-top:6px;}

.pc{border-radius:14px;padding:16px 20px;margin-bottom:10px;
  display:flex;align-items:center;gap:16px;flex-wrap:wrap;}
.pc-h{background:#08140c;border:1px solid #3ecf8e2a;}
.pc-m{background:#14120a;border:1px solid #f5c8422a;}
.pc-l{background:#14080a;border:1px solid #f4622a2a;}
.pmkt{font-size:.62rem;color:#30304a;letter-spacing:2px;text-transform:uppercase;min-width:120px;}
.ppick{font-weight:600;font-size:.92rem;flex:1;}
.pdet{font-size:.72rem;color:#40406a;margin-top:3px;}
.pbadge{display:inline-block;border-radius:6px;padding:3px 10px;
  font-size:.68rem;font-weight:700;letter-spacing:.5px;margin-top:4px;}
.ph{background:rgba(62,207,142,.12);color:#3ecf8e;}
.pm{background:rgba(245,200,66,.1);color:#f5c842;}
.pl{background:rgba(244,98,42,.12);color:#f4622a;}

.bet-box{
  background:linear-gradient(135deg,#08160c,#060e08);
  border:2px solid #3ecf8e44;border-radius:16px;
  padding:24px 28px;margin:14px 0;
}
.bet-title{font-family:'Bebas Neue',sans-serif;color:#3ecf8e;
  font-size:1.5rem;letter-spacing:3px;margin-bottom:14px;}
.bet-row{display:flex;justify-content:space-between;align-items:center;
  padding:7px 0;border-bottom:1px solid #0f1f12;}
.bet-row:last-child{border-bottom:none;}
.bl{font-size:.8rem;color:#50507a;}
.bv{font-family:'Bebas Neue',sans-serif;font-size:1.3rem;color:#f5c842;}
.value-yes{background:rgba(62,207,142,.12);border:1px solid #3ecf8e33;
  border-radius:8px;padding:8px 14px;margin-top:10px;font-size:.8rem;color:#3ecf8e;}
.value-no{background:rgba(244,98,42,.08);border:1px solid #f4622a22;
  border-radius:8px;padding:8px 14px;margin-top:10px;font-size:.8rem;color:#f4622a88;}
.combo-box{background:#091409;border:1px solid #3ecf8e22;
  border-radius:10px;padding:14px;margin-top:14px;}
.bet-warn{background:#140a0a;border:1px solid #f4622a22;
  border-radius:8px;padding:10px 14px;margin-top:12px;font-size:.78rem;color:#80506a;line-height:1.5;}

.pbar-wrap{background:#0f0f1f;border-radius:99px;height:10px;overflow:hidden;}
.pbar-fill{height:100%;border-radius:99px;}
.prow{margin:8px 0;}
.prow-lbl{font-size:.78rem;color:#60608a;margin-bottom:3px;}

.dq-bar{height:6px;border-radius:99px;margin-top:4px;}
.src-chip{display:inline-block;background:#0f0f1f;border:1px solid #1a1a2e;
  border-radius:4px;padding:1px 7px;font-size:.65rem;color:#40406a;margin-left:6px;}
.warn-data{background:#140e04;border-left:3px solid #f5c842;
  border-radius:0 8px 8px 0;padding:10px 14px;font-size:.8rem;color:#a09060;margin:8px 0;}

.stButton>button{background:#f4622a!important;color:#fff!important;
  border:none!important;border-radius:12px!important;font-weight:700!important;
  padding:14px 20px!important;width:100%!important;font-size:.95rem!important;
  letter-spacing:1px!important;transition:.2s!important;}
.stButton>button:hover{background:#d0501e!important;transform:translateY(-1px)!important;}
#MainMenu,footer,header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ================================================================
#  CAPA DE DATOS — SOURCE 1: football-data.org
# ================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def fd_partidos(fd_code, season=None):
    if not fd_code: return []
    today  = datetime.now().strftime("%Y-%m-%d")
    futuro = (datetime.now() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    try:
        r = requests.get(
            f"{FD_BASE}/competitions/{fd_code}/matches",
            headers=FD_HDR,
            params={"dateFrom": today, "dateTo": futuro, "status": "SCHEDULED"},
            timeout=14
        )
        if r.status_code != 200: return []
        resultado = []
        for m in r.json().get("matches", []):
            home = m.get("homeTeam",{}).get("shortName") or m.get("homeTeam",{}).get("name","?")
            away = m.get("awayTeam",{}).get("shortName") or m.get("awayTeam",{}).get("name","?")
            resultado.append({
                "id":       m.get("id"),
                "fecha":    m.get("utcDate","")[:10],
                "local":    home,
                "visita":   away,
                "id_local_fd":   m.get("homeTeam",{}).get("id"),
                "id_visita_fd":  m.get("awayTeam",{}).get("id"),
                "id_local_as":   None,
                "id_visita_as":  None,
                "fuente":   "football-data.org",
                "display":  f"📅 {m.get('utcDate','')[:10]}  |  {home}  vs  {away}",
            })
        return resultado
    except: return []

@st.cache_data(ttl=3600, show_spinner=False)
def fd_historial(team_id, limit=50):
    if not team_id: return []
    try:
        r = requests.get(
            f"{FD_BASE}/teams/{team_id}/matches",
            headers=FD_HDR,
            params={"status": "FINISHED", "limit": limit},
            timeout=14
        )
        if r.status_code != 200: return []
        return r.json().get("matches", [])
    except: return []

# ================================================================
#  CAPA DE DATOS — SOURCE 2: api-sports.io
# ================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def as_partidos(league_id, season):
    today  = datetime.now().strftime("%Y-%m-%d")
    futuro = (datetime.now() + timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
    estrategias = [
        {"league": league_id, "season": season, "from": today, "to": futuro},
        {"league": league_id, "season": season, "status": "NS", "from": today, "to": futuro},
        {"league": league_id, "season": season},
    ]
    for params in estrategias:
        try:
            r = requests.get(f"{AS_BASE}/fixtures", headers=AS_HDR,
                             params=params, timeout=14)
            data = r.json()
            errs = data.get("errors", {})
            if errs and errs not in ([], {}): continue
            items = data.get("response", [])
            if not items: continue
            resultado = []
            for f in items:
                fix   = f.get("fixture", {})
                teams = f.get("teams",   {})
                if fix.get("status",{}).get("short","") in ("FT","AET","PEN","CANC","ABD","PST"): continue
                home = teams.get("home",{}).get("name","?")
                away = teams.get("away",{}).get("name","?")
                fecha = fix.get("date","")[:10]
                resultado.append({
                    "id":          fix.get("id"),
                    "fecha":       fecha,
                    "local":       home,
                    "visita":      away,
                    "id_local_as":  teams.get("home",{}).get("id"),
                    "id_visita_as": teams.get("away",{}).get("id"),
                    "id_local_fd":  None,
                    "id_visita_fd": None,
                    "fuente":      "api-sports.io",
                    "display":     f"📅 {fecha}  |  {home}  vs  {away}",
                })
            if resultado: return resultado
        except: continue
    return []

@st.cache_data(ttl=3600, show_spinner=False)
def as_estadisticas(team_id, league_id, season):
    """Carga estadísticas multi-temporada: actual + anterior si datos bajos."""
    if not team_id: return {}
    resultados = []
    for s in [season, season - 1, season + 1]:
        try:
            r = requests.get(f"{AS_BASE}/teams/statistics", headers=AS_HDR,
                             params={"team": team_id, "league": league_id, "season": s},
                             timeout=12)
            d = r.json().get("response", {})
            if d:
                jugados = _f(d.get("fixtures",{}).get("played",{}).get("total", 0))
                resultados.append({"data": d, "jugados": jugados, "season": s})
        except: continue
    if not resultados: return {}
    # Retorna el mas completo, o fusiona si el actual tiene pocos datos
    resultados.sort(key=lambda x: -x["jugados"])
    if len(resultados) >= 2 and resultados[0]["jugados"] < 8:
        # Fusionar los dos primeros
        return _fusionar_stats(resultados[0]["data"], resultados[1]["data"])
    return resultados[0]["data"]

def _fusionar_stats(s1, s2):
    """Fusiona dos objetos de estadísticas ponderando por partidos jugados."""
    j1 = max(1, _f(s1.get("fixtures",{}).get("played",{}).get("total",0)))
    j2 = max(1, _f(s2.get("fixtures",{}).get("played",{}).get("total",0)))
    w1 = j1 / (j1 + j2)
    w2 = j2 / (j1 + j2)
    # Para goals averages, fusionamos manualmente
    fusion = dict(s1)
    for venue in ["home", "away", "total"]:
        try:
            gf1 = _f(s1.get("goals",{}).get("for",{}).get("average",{}).get(venue, 0))
            gf2 = _f(s2.get("goals",{}).get("for",{}).get("average",{}).get(venue, 0))
            ga1 = _f(s1.get("goals",{}).get("against",{}).get("average",{}).get(venue, 0))
            ga2 = _f(s2.get("goals",{}).get("against",{}).get("average",{}).get(venue, 0))
            if "goals" not in fusion: fusion["goals"] = {}
            if "for"     not in fusion["goals"]: fusion["goals"]["for"] = {}
            if "against" not in fusion["goals"]: fusion["goals"]["against"] = {}
            if "average" not in fusion["goals"]["for"]:     fusion["goals"]["for"]["average"] = {}
            if "average" not in fusion["goals"]["against"]: fusion["goals"]["against"]["average"] = {}
            fusion["goals"]["for"]["average"][venue]     = round(gf1*w1 + gf2*w2, 3)
            fusion["goals"]["against"]["average"][venue] = round(ga1*w1 + ga2*w2, 3)
        except: pass
    fusion["_fusionado"] = True
    fusion["_j1"] = j1; fusion["_j2"] = j2
    return fusion

@st.cache_data(ttl=3600, show_spinner=False)
def as_ultimos(team_id, season, n=20):
    if not team_id: return []
    for s in [season, season - 1]:
        try:
            r = requests.get(f"{AS_BASE}/fixtures", headers=AS_HDR,
                             params={"team": team_id, "season": s,
                                     "status": "FT", "last": n}, timeout=12)
            d = r.json().get("response", [])
            if d: return d
        except: continue
    return []

@st.cache_data(ttl=3600, show_spinner=False)
def as_buscar_equipo(nombre):
    """Busca un equipo por nombre para sincronizar IDs entre fuentes."""
    try:
        r = requests.get(f"{AS_BASE}/teams", headers=AS_HDR,
                         params={"search": nombre[:12]}, timeout=10)
        equipos = r.json().get("response", [])
        if equipos:
            return equipos[0].get("team", {}).get("id")
    except: pass
    return None

# ================================================================
#  CAPA DE DATOS — SOURCE 3: the-odds-api
# ================================================================

@st.cache_data(ttl=1800, show_spinner=False)
def obtener_cuotas(sport_key, local, visita):
    if not sport_key or not ODDS_KEY: return None
    try:
        r = requests.get(f"{OD_BASE}/sports/{sport_key}/odds",
                         params={"apiKey": ODDS_KEY, "regions": "eu",
                                 "markets": "h2h,totals", "oddsFormat": "decimal"},
                         timeout=12)
        if r.status_code != 200: return None
        hl = local.lower(); al = visita.lower()
        for ev in r.json():
            h2 = ev.get("home_team","").lower()
            a2 = ev.get("away_team","").lower()
            if (hl[:6] in h2 or h2[:6] in hl) and (al[:6] in a2 or a2[:6] in al):
                bk  = (ev.get("bookmakers") or [{}])[0]
                res = {"local": local, "visita": visita,
                       "casa": bk.get("title",""), "sport": sport_key}
                for mkt in bk.get("markets", []):
                    if mkt["key"] == "h2h":
                        for o in mkt.get("outcomes", []):
                            n = o["name"].lower()
                            if hl[:5] in n:   res["cuota_local"]  = o["price"]
                            elif "draw" in n: res["cuota_empate"] = o["price"]
                            else:             res["cuota_visita"] = o["price"]
                    elif mkt["key"] == "totals":
                        for o in mkt.get("outcomes", []):
                            if o["name"] == "Over":  res["cuota_o25"] = o["price"]
                            elif o["name"]=="Under": res["cuota_u25"] = o["price"]
                return res
    except: pass
    return None

# ================================================================
#  CAPA DE DATOS — SOURCE 4: open-meteo
# ================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def obtener_clima(lat, lon):
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast",
                         params={"latitude": lat, "longitude": lon,
                                 "current": "temperature_2m,precipitation,windspeed_10m,weathercode",
                                 "timezone": "auto"}, timeout=8)
        c    = r.json().get("current", {})
        code = c.get("weathercode", 0)
        cond = ("Despejado" if code < 3 else "Nublado" if code < 50
                else "Lluvioso" if code < 80 else "Tormenta")
        return {"temp": c.get("temperature_2m","?"), "lluvia": c.get("precipitation", 0),
                "viento": c.get("windspeed_10m", 0), "cond": cond, "code": code}
    except: return None

# ================================================================
#  CARGADOR INTELIGENTE DE PARTIDOS — Fallback automático
# ================================================================

def cargar_partidos(nombre_liga):
    """
    Prioridad:
    - Latam → api-sports primero, football-data como fallback
    - Europa / UCL → football-data primero, api-sports como fallback
    """
    lg     = LIGAS[nombre_liga]
    as_id  = lg["as_id"]
    fd_cod = lg["fd_code"]
    season = lg["season"]
    region = lg["region"]
    es_latam = (region == "Latinoamerica")

    partidos = []; fuente = None

    if es_latam:
        partidos = as_partidos(as_id, season)
        if partidos: fuente = "api-sports.io"
        if not partidos and fd_cod:
            partidos = fd_partidos(fd_cod)
            if partidos: fuente = "football-data.org"
    else:
        if fd_cod:
            partidos = fd_partidos(fd_cod)
            if partidos: fuente = "football-data.org"
        if not partidos:
            partidos = as_partidos(as_id, season)
            if partidos: fuente = "api-sports.io"

    return partidos, fuente

# ================================================================
#  CARGADOR INTELIGENTE DE ESTADÍSTICAS — Sync de IDs
# ================================================================

def cargar_estadisticas(partido, nombre_liga):
    lg      = LIGAS[nombre_liga]
    as_id   = lg["as_id"]
    season  = lg["season"]

    # Resolver IDs de api-sports
    id_local_as  = partido.get("id_local_as")
    id_visita_as = partido.get("id_visita_as")
    if not id_local_as:
        id_local_as  = as_buscar_equipo(partido["local"])
    if not id_visita_as:
        id_visita_as = as_buscar_equipo(partido["visita"])

    id_local_fd  = partido.get("id_local_fd")
    id_visita_fd = partido.get("id_visita_fd")

    # Cargar datos
    hist_local   = fd_historial(id_local_fd,  50) if id_local_fd  else []
    hist_visita  = fd_historial(id_visita_fd, 50) if id_visita_fd else []
    stats_local  = as_estadisticas(id_local_as,  as_id, season) if id_local_as  else {}
    stats_visita = as_estadisticas(id_visita_as, as_id, season) if id_visita_as else {}
    ult_local    = as_ultimos(id_local_as,  season, 20) if id_local_as  else []
    ult_visita   = as_ultimos(id_visita_as, season, 20) if id_visita_as else []

    return {
        "local":  {"hist": hist_local,  "stats": stats_local,  "ultimos": ult_local,
                   "id_fd": id_local_fd,  "id_as": id_local_as,  "nombre": partido["local"]},
        "visita": {"hist": hist_visita, "stats": stats_visita, "ultimos": ult_visita,
                   "id_fd": id_visita_fd, "id_as": id_visita_as, "nombre": partido["visita"]},
        "season": season, "league_id": as_id,
    }

# ================================================================
#  MOTOR ESTADÍSTICO — Perfiles con varianza
# ================================================================

def _f(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def perfil_de_fd(matches, team_id):
    """Extrae perfil con MEDIA + DESVIACION ESTANDAR de historial FD."""
    gf_lst, ga_lst = [], []
    for m in matches:
        ht = m.get("homeTeam", {}).get("id")
        s  = m.get("score", {}).get("fullTime", {})
        h  = s.get("home"); a = s.get("away")
        if h is None or a is None: continue
        if ht == team_id:
            gf_lst.append(_f(h)); ga_lst.append(_f(a))
        else:
            gf_lst.append(_f(a)); ga_lst.append(_f(h))
    if not gf_lst: return None
    n = min(len(gf_lst), 20)
    gf = gf_lst[-n:]; ga = ga_lst[-n:]
    btts = sum(1 for x,y in zip(gf,ga) if x>0 and y>0)
    cs   = sum(1 for y in ga if y==0)
    return {
        "goles_a_favor":  round(np.mean(gf), 3),
        "goles_contra":   round(np.mean(ga), 3),
        "std_a_favor":    round(np.std(gf),  3),
        "std_contra":     round(np.std(ga),  3),
        "btts_pct":       round(btts / n, 2),
        "cs_pct":         round(cs   / n, 2),
        "tiros":          4.5, "amarillas": 1.8, "rojas": 0.1,
        "faltas": 12.0, "corners": 5.2,
        "fuente": "football-data.org (historico real)",
        "partidos": len(gf_lst),
    }

def perfil_de_as(stats, is_local=True):
    """Extrae perfil con estadísticas de temporada de AS."""
    if not stats: return None
    v = "home" if is_local else "away"
    def g(ruta, d=0.0):
        try:
            x = stats
            for k in ruta: x = x[k]
            return _f(x, d)
        except: return d
    gf = g(["goals","for","average",v])   or g(["goals","for","average","total"])   or 0
    ga = g(["goals","against","average",v]) or g(["goals","against","average","total"]) or 0
    if gf == 0 and ga == 0: return None

    def card_avg(color):
        d    = stats.get("cards", {}).get(color, {})
        vals = [_f(vv) for vv in d.values() if _f(vv) > 0]
        return round(sum(vals)/len(vals), 2) if vals else (1.8 if color=="yellow" else 0.1)

    jugados = _f(stats.get("fixtures",{}).get("played",{}).get("total", 0))
    return {
        "goles_a_favor": max(0.3, gf),
        "goles_contra":  max(0.3, ga),
        "std_a_favor":   max(0.3, gf) * 0.55,   # aprox si no hay std directo
        "std_contra":    max(0.3, ga) * 0.55,
        "btts_pct":      0.45,
        "cs_pct":        0.28,
        "tiros":         g(["shots","on","average"], 4.5),
        "amarillas":     card_avg("yellow"),
        "rojas":         card_avg("red"),
        "faltas":        g(["fouls","committed","average"], 12.0),
        "corners":       g(["corners","total","average"], 5.2),
        "fuente":        f"api-sports.io ({'fusionado' if stats.get('_fusionado') else 'temporada'})",
        "partidos":      int(jugados),
    }

def enriquecer_con_ultimos(perfil, ultimos, team_id):
    """Añade BTTS, CS y std reales de los últimos partidos de AS."""
    if not ultimos or not perfil: return perfil
    gf_l, ga_l = [], []
    for f in ultimos:
        teams = f.get("teams", {}); goals = f.get("goals", {})
        es_local = teams.get("home",{}).get("id") == team_id
        h = goals.get("home", 0) or 0; a = goals.get("away", 0) or 0
        gf_l.append(h if es_local else a)
        ga_l.append(a if es_local else h)
    if gf_l:
        n = len(gf_l)
        perfil["btts_pct"]    = round(sum(1 for x,y in zip(gf_l,ga_l) if x>0 and y>0)/n, 2)
        perfil["cs_pct"]      = round(sum(1 for y in ga_l if y==0)/n, 2)
        perfil["std_a_favor"] = round(np.std(gf_l), 3)
        perfil["std_contra"]  = round(np.std(ga_l), 3)
    return perfil

def fusionar_perfiles(fd_p, as_p):
    """
    Fusión inteligente: 70% al de más partidos, 30% al otro.
    Si solo hay uno, usa ese con defaults para campos faltantes.
    """
    defaults = {
        "goles_a_favor": 1.30, "goles_contra": 1.10,
        "std_a_favor": 0.72, "std_contra": 0.65,
        "btts_pct": 0.45, "cs_pct": 0.27,
        "tiros": 4.5, "amarillas": 1.8, "rojas": 0.1,
        "faltas": 12.0, "corners": 5.2,
        "fuente": "Promedio de liga (datos insuficientes)",
        "partidos": 0,
    }

    if fd_p and as_p:
        p_fd = fd_p.get("partidos", 0)
        p_as = as_p.get("partidos", 0)
        if p_fd >= p_as:
            w1, w2, src1, src2 = 0.70, 0.30, fd_p, as_p
        else:
            w1, w2, src1, src2 = 0.70, 0.30, as_p, fd_p
        m = {}
        for k in ["goles_a_favor","goles_contra","std_a_favor","std_contra"]:
            m[k] = round(src1.get(k, defaults[k])*w1 + src2.get(k, defaults[k])*w2, 3)
        for k in ["tiros","amarillas","rojas","faltas","corners","btts_pct","cs_pct"]:
            m[k] = src1.get(k, defaults[k])
        m["fuente"]   = f"Fusión 70/30 ({src1['fuente'].split('(')[0].strip()})"
        m["partidos"] = max(p_fd, p_as)
        return m

    p = fd_p or as_p
    if p:
        for k, v in defaults.items():
            if k not in p: p[k] = v
        return p
    return defaults

def ajuste_clima(perfil, clima):
    if not clima: return perfil
    p = dict(perfil)
    lluvia = clima.get("lluvia", 0); viento = clima.get("viento", 0)
    if lluvia > 2:
        p["goles_a_favor"] = round(p["goles_a_favor"] * 0.91, 3)
        p["tiros"]         = round(p["tiros"]         * 0.89, 3)
        p["faltas"]        = round(p["faltas"]        * 1.06, 3)
        p["corners"]       = round(p["corners"]       * 1.04, 3)
    if viento > 30:
        p["corners"]       = round(p["corners"]       * 0.94, 3)
        p["tiros"]         = round(p["tiros"]         * 0.95, 3)
    return p

# ================================================================
#  MOTOR MONTE CARLO — Con varianza real
# ================================================================

def correr_montecarlo(lp, vp, clima=None):
    lp = ajuste_clima(lp, clima)
    vp = ajuste_clima(vp, clima)

    avg_liga = 1.35
    # Lambdas esperados (goles esperados por partido)
    lh = max(0.25, lp["goles_a_favor"] * (vp["goles_contra"] / avg_liga) * 1.12)
    la = max(0.25, vp["goles_a_favor"] * (lp["goles_contra"] / avg_liga))

    # Desviaciones estándar para mayor realismo
    std_h = max(0.4, lp.get("std_a_favor", lh * 0.55))
    std_a = max(0.4, vp.get("std_a_favor", la * 0.55))

    rng = np.random.default_rng(42)

    # Simulación con distribución Poisson ajustada por varianza
    # Usamos Negative Binomial cuando varianza > media (sobredispersión)
    def simular(mu, std, n):
        varianza = std ** 2
        if varianza > mu * 1.1 and mu > 0:
            # Negative Binomial: más realista para equipos irregulares
            r_nb = mu**2 / max(varianza - mu, 0.01)
            p_nb = r_nb / (r_nb + mu)
            return rng.negative_binomial(max(1, r_nb), min(0.999, p_nb), n)
        else:
            return rng.poisson(mu, n)

    hg  = simular(lh, std_h, N_SIM)
    ag  = simular(la, std_a, N_SIM)
    tot = hg + ag

    def p(n): return round(n / N_SIM * 100, 1)

    hc  = rng.poisson(lp["corners"],    N_SIM)
    ac  = rng.poisson(vp["corners"],    N_SIM)
    hy  = rng.poisson(lp["amarillas"],  N_SIM)
    ay  = rng.poisson(vp["amarillas"],  N_SIM)
    hr  = rng.poisson(lp["rojas"],      N_SIM)
    ar  = rng.poisson(vp["rojas"],      N_SIM)
    hf  = rng.poisson(lp["faltas"],     N_SIM)
    af  = rng.poisson(vp["faltas"],     N_SIM)
    hs  = rng.poisson(lp["tiros"],      N_SIM)
    as_ = rng.poisson(vp["tiros"],      N_SIM)

    scores = {}
    for h, a in zip(hg, ag):
        k = f"{h}-{a}"; scores[k] = scores.get(k, 0) + 1

    return {
        "p_local":   p(np.sum(hg > ag)),
        "p_empate":  p(np.sum(hg == ag)),
        "p_visita":  p(np.sum(hg < ag)),
        "lh": round(lh, 2), "la": round(la, 2),
        "o25": p(np.sum(tot > 2.5)),  "u25": p(np.sum(tot <= 2.5)),
        "o15": p(np.sum(tot > 1.5)),  "u15": p(np.sum(tot <= 1.5)),
        "o35": p(np.sum(tot > 3.5)),  "u35": p(np.sum(tot <= 3.5)),
        "btts":    p(np.sum((hg > 0) & (ag > 0))),
        "no_btts": p(np.sum(~((hg > 0) & (ag > 0)))),
        "hc": round(np.mean(hc),2), "ac": round(np.mean(ac),2),
        "tc": round(np.mean(hc+ac),2),
        "co85": p(np.sum(hc+ac > 8.5)), "cu85": p(np.sum(hc+ac <= 8.5)),
        "co105":p(np.sum(hc+ac > 10.5)),"co65": p(np.sum(hc+ac > 6.5)),
        "hy": round(np.mean(hy),2), "ay": round(np.mean(ay),2),
        "ty": round(np.mean(hy+ay),2),
        "hr": round(np.mean(hr),2), "ar": round(np.mean(ar),2),
        "tr": round(np.mean(hr+ar),2),
        "hf": round(np.mean(hf),2), "af": round(np.mean(af),2),
        "tf": round(np.mean(hf+af),2),
        "hs": round(np.mean(hs),2), "as_": round(np.mean(as_),2),
        "top": [(s, p(c)) for s,c in sorted(scores.items(), key=lambda x:-x[1])[:9]],
        "std_h": round(std_h,3), "std_a": round(std_a,3),
        "modelo": "Negative Binomial" if (std_h**2 > lh*1.1) else "Poisson",
    }

# ================================================================
#  PREDICCIONES
# ================================================================

def info_conf(c):
    if c >= 80:   return "#3ecf8e", "✅ ALTA",  "pc-h", "ph"
    elif c >= 60: return "#f5c842", "⚡ MEDIA", "pc-m", "pm"
    else:         return "#f4622a", "⚠️ BAJA",  "pc-l", "pl"

def impl(odd):
    if not odd or odd <= 0: return 0
    return round(100 / odd, 1)

def construir_predicciones(R, local, visita, cuotas=None):
    filas = []

    # 1X2 con ajuste de cuotas
    candidatos = [(R["p_local"],f"Victoria {local}"),(R["p_empate"],"Empate"),(R["p_visita"],f"Victoria {visita}")]
    mejor = max(candidatos, key=lambda x: x[0])
    conf = mejor[0]
    if cuotas:
        key_map = {f"Victoria {local}":"cuota_local","Empate":"cuota_empate",f"Victoria {visita}":"cuota_visita"}
        odd = cuotas.get(key_map.get(mejor[1],""))
        if odd: conf = round(mejor[0]*0.65 + impl(odd)*0.35, 1)
    filas.append({"mkt":"Resultado 1X2","pick":mejor[1],"conf":conf,
                  "det":f"Local {R['p_local']}% / Empate {R['p_empate']}% / Visita {R['p_visita']}%"})

    # Goles O/U múltiples líneas
    for line, ov, uv in [("1.5", R["o15"], R["u15"]),
                          ("2.5", R["o25"], R["u25"]),
                          ("3.5", R["o35"], R["u35"])]:
        pick = f"Mas de {line} goles" if ov >= uv else f"Menos de {line} goles"
        filas.append({"mkt":f"Goles O/U {line}","pick":pick,"conf":max(ov,uv),
                      "det":f"Goles esperados: {round(R['lh']+R['la'],2)}"})

    # BTTS
    filas.append({"mkt":"Ambos Marcan (BTTS)",
                  "pick":"Si — Ambos anotan" if R["btts"]>=R["no_btts"] else "No — Alguno no anota",
                  "conf":max(R["btts"],R["no_btts"]),
                  "det":f"λ local {R['lh']} / λ visita {R['la']}"})

    # Corners múltiples líneas
    for line,ov,uv in [("6.5",R["co65"],100-R["co65"]),
                        ("8.5",R["co85"],R["cu85"]),
                        ("10.5",R["co105"],100-R["co105"])]:
        pick = f"Mas de {line} corners" if ov >= uv else f"Menos de {line} corners"
        filas.append({"mkt":f"Corners O/U {line}","pick":pick,"conf":max(ov,uv),
                      "det":f"Total esperado: {R['tc']} corners"})

    # Doble oportunidad
    dc1 = min(round(R["p_local"]+R["p_empate"],1), 99.0)
    dc2 = min(round(R["p_visita"]+R["p_empate"],1), 99.0)
    filas.append({"mkt":"Doble Oportunidad",
                  "pick":f"{local} o Empate" if dc1>=dc2 else f"{visita} o Empate",
                  "conf":max(dc1,dc2), "det":"Cubre dos de tres resultados posibles"})

    # Tarjetas
    ty = R["ty"]; line_y = max(1, round(ty) - 1)
    prob_y = min(95.0, max(5.0, round(50 + (ty - line_y - 0.5)*18, 1)))
    filas.append({"mkt":f"Amarillas O {line_y}.5","pick":f"Mas de {line_y}.5 amarillas",
                  "conf":prob_y,"det":f"Total amarillas esperadas: {ty}"})

    # Marcador exacto
    top = R["top"][0]
    filas.append({"mkt":"Marcador Exacto","pick":f"Resultado {top[0]}",
                  "conf":top[1],"det":"Marcador mas frecuente en 10,000 simulaciones"})

    return sorted(filas, key=lambda x: -x["conf"])

# ================================================================
#  CRITERIO DE KELLY + DETECTOR VALUE BET
# ================================================================

def kelly(prob, odd, bankroll=100, fraccion=0.25):
    if not odd or odd <= 1.0: return 0
    p = prob / 100; q = 1 - p; b = odd - 1
    k = (b * p - q) / b
    k = max(0, k) * fraccion
    return round(k * bankroll, 2)

def generar_sugerencia(predicciones, R, cuotas, local, visita, bankroll=100):
    altas = [p for p in predicciones if p["conf"] >= 75]
    if not altas: return None

    mejor = altas[0]
    conf  = mejor["conf"]
    pick  = mejor["pick"]
    mkt   = mejor["mkt"]

    # Buscar cuota correspondiente
    cuota_val = None
    if cuotas:
        if local in pick:    cuota_val = cuotas.get("cuota_local")
        elif "Empate" in pick: cuota_val = cuotas.get("cuota_empate")
        elif visita in pick:  cuota_val = cuotas.get("cuota_visita")
        elif "2.5" in mkt and "Mas" in pick:   cuota_val = cuotas.get("cuota_o25")
        elif "2.5" in mkt and "Menos" in pick: cuota_val = cuotas.get("cuota_u25")

    stake       = kelly(conf, cuota_val or 1.90, bankroll) if cuota_val else None
    impl_prob   = impl(cuota_val) if cuota_val else None
    value_bet   = (conf > impl_prob + 5) if impl_prob else None
    ventaja     = round(conf - impl_prob, 1) if impl_prob else None

    riesgo = ("BAJO", "#3ecf8e") if conf>=85 else ("MEDIO","#f5c842") if conf>=75 else ("ALTO","#f4622a")

    # Combinada si hay 2+ selecciones de alta confianza
    combinada = None
    if len(altas) >= 2:
        c2 = altas[1]
        conf_combo = round(altas[0]["conf"] * altas[1]["conf"] / 100, 1)
        if conf_combo >= 50:
            combinada = {"picks": [altas[0]["pick"], altas[1]["pick"]],
                         "conf": conf_combo,
                         "mercados": [altas[0]["mkt"], altas[1]["mkt"]]}

    return {"pick": pick, "mkt": mkt, "conf": conf, "cuota": cuota_val,
            "stake": stake, "impl": impl_prob, "value": value_bet,
            "ventaja": ventaja, "riesgo": riesgo, "combinada": combinada}

# ================================================================
#  RENDERIZADO UI
# ================================================================

def render_prediccion(pred):
    color, badge, pc_cls, b_cls = info_conf(pred["conf"])
    c = pred["conf"]; w = int(min(c, 100))
    alerta = ""
    if c < 60:
        alerta = f'<div style="margin-top:7px;padding:5px 12px;background:rgba(244,98,42,.08);border-radius:6px;font-size:.74rem;color:#f4622a">⚠️ RIESGO ALTO ({c}%) — No se recomienda apostar en este mercado.</div>'
    elif c < 80:
        alerta = f'<div style="margin-top:7px;padding:5px 12px;background:rgba(245,200,66,.07);border-radius:6px;font-size:.74rem;color:#f5c842">⚡ Confianza media ({c}%) — Analiza antes de apostar.</div>'
    st.markdown(f"""
    <div class="pc {pc_cls}">
      <div style="min-width:130px"><div class="pmkt">{pred['mkt']}</div></div>
      <div style="flex:1">
        <div class="ppick">{pred['pick']}</div>
        <div class="pdet">{pred['det']}</div>
      </div>
      <div style="text-align:center;min-width:100px">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;color:{color};line-height:1">{c}%</div>
        <div style="background:#0c0c1c;border-radius:99px;height:6px;overflow:hidden;margin:4px 0">
          <div style="width:{w}%;height:100%;background:{color};border-radius:99px"></div>
        </div>
        <span class="pbadge {b_cls}">{badge}</span>
      </div>
    </div>{alerta}""", unsafe_allow_html=True)

def render_sugerencia(sug, bankroll):
    if not sug: return
    color, _, _, _ = info_conf(sug["conf"])
    riesgo_lbl, riesgo_color = sug["riesgo"]

    value_html = ""
    if sug["value"] is True:
        v = sug.get("ventaja", 0)
        value_html = f'<div class="value-yes">💎 <b>VALUE BET DETECTADA</b> — Tu modelo da {sug["conf"]}% vs {sug["impl"]}% implícito de la cuota. Ventaja estadística de +{v}%. Esto es una apuesta con valor positivo.</div>'
    elif sug["value"] is False:
        value_html = f'<div class="value-no">Sin ventaja de valor — La cuota ya descuenta esta probabilidad. Procede con precaución.</div>'

    cuota_txt = f"{sug['cuota']:.2f}" if sug["cuota"] else "N/D (sin cuota en vivo)"
    stake_txt = f"${sug['stake']:.2f} de ${bankroll} ({round(sug['stake']/bankroll*100,1)}% del bankroll)" if sug["stake"] else "Estima según cuota disponible"

    combo_html = ""
    if sug.get("combinada"):
        cmb = sug["combinada"]
        combo_html = f"""
        <div class="combo-box">
          <div style="font-size:.65rem;color:#30305a;letter-spacing:2px;text-transform:uppercase;margin-bottom:8px">Apuesta Combinada Sugerida</div>
          <div style="font-weight:600;font-size:.88rem">{"  +  ".join(cmb['picks'])}</div>
          <div style="font-size:.72rem;color:#40406a;margin-top:4px">{" / ".join(cmb['mercados'])}</div>
          <div style="font-size:.75rem;color:#3ecf8e88;margin-top:4px">Confianza combinada: {cmb['conf']}% — mayor cuota potencial, mayor riesgo</div>
        </div>"""

    st.markdown(f"""
    <div class="bet-box">
      <div class="bet-title">SUGERENCIA DE APUESTA</div>
      <div class="bet-row">
        <span class="bl">Mercado recomendado</span>
        <span class="bv">{sug['mkt']}</span>
      </div>
      <div class="bet-row">
        <span class="bl">Seleccion</span>
        <span style="font-weight:700;font-size:.92rem;color:#e2e2f0">{sug['pick']}</span>
      </div>
      <div class="bet-row">
        <span class="bl">Confianza estadistica</span>
        <span style="font-family:'Bebas Neue',sans-serif;font-size:1.6rem;color:{color}">{sug['conf']}%</span>
      </div>
      <div class="bet-row">
        <span class="bl">Cuota de referencia</span>
        <span class="bv">{cuota_txt}</span>
      </div>
      <div class="bet-row">
        <span class="bl">Nivel de riesgo</span>
        <span style="color:{riesgo_color};font-weight:700;font-size:.9rem">{riesgo_lbl}</span>
      </div>
      <div class="bet-row">
        <span class="bl">Stake Kelly x0.25</span>
        <span style="color:#f5c842;font-weight:700;font-size:.88rem">{stake_txt}</span>
      </div>
      {value_html}
      {combo_html}
      <div class="bet-warn">
        ⚠️ Las sugerencias son orientativas basadas en estadística. No son garantía de resultado.
        El Criterio de Kelly usa una fracción conservadora (0.25) para proteger tu bankroll.
        Nunca apuestes más de lo que puedes perder. Juega siempre con responsabilidad.
      </div>
    </div>""", unsafe_allow_html=True)

def barra(label, val, color):
    st.markdown(f"""<div class="prow">
      <div class="prow-lbl">{label} — <b style="color:{color}">{val}%</b></div>
      <div class="pbar-wrap"><div class="pbar-fill" style="width:{min(val,100)}%;background:{color}"></div></div>
    </div>""", unsafe_allow_html=True)

def kpi(val, label, col):
    col.markdown(f'<div class="kpi"><div class="kv">{val}</div><div class="kl">{label}</div></div>',
                 unsafe_allow_html=True)

def seccion(txt):
    st.markdown(f'<div class="sec">{txt}</div>', unsafe_allow_html=True)

def pill_api(nombre, activa):
    cls = "apill-on" if activa else "apill-off"
    ico = "✅" if activa else "○"
    return f'<span class="apill {cls}">{ico} {nombre}</span>'

# ================================================================
#  SIDEBAR
# ================================================================
with st.sidebar:
    st.markdown("## Configuracion")
    st.markdown("---")
    bankroll = st.number_input(
        "Bankroll para Kelly ($)",
        min_value=10, max_value=500000,
        value=st.session_state.get("bankroll", 100), step=10,
        help="Tu capital total disponible para apuestas"
    )
    st.session_state["bankroll"] = bankroll

    st.markdown("---")
    if st.button("Probar todas las conexiones"):
        with st.spinner("Probando..."):
            # FD
            try:
                r = requests.get(f"{FD_BASE}/competitions", headers=FD_HDR, timeout=8)
                st.success(f"football-data.org: HTTP {r.status_code}")
            except Exception as e: st.error(f"FD: {e}")
            # AS
            try:
                r = requests.get(f"{AS_BASE}/status", headers=AS_HDR, timeout=8)
                d = r.json().get("response", {})
                req = d.get("requests", {})
                st.success(f"api-sports.io: {req.get('current',0)}/{req.get('limit_day',100)} req hoy | Plan: {d.get('subscription',{}).get('plan','?')}")
            except Exception as e: st.error(f"AS: {e}")
            # Odds
            try:
                r = requests.get(f"{OD_BASE}/sports", params={"apiKey": ODDS_KEY}, timeout=8)
                remaining = r.headers.get("x-requests-remaining","?")
                st.success(f"the-odds-api: HTTP {r.status_code} | Restantes: {remaining}")
            except Exception as e: st.error(f"Odds: {e}")
            # Weather
            try:
                r = requests.get("https://api.open-meteo.com/v1/forecast",
                                 params={"latitude":4.71,"longitude":-74.07,"current":"temperature_2m"}, timeout=8)
                t = r.json().get("current",{}).get("temperature_2m","?")
                st.success(f"open-meteo: {t}°C en Bogota")
            except Exception as e: st.error(f"open-meteo: {e}")

    st.markdown("---")
    st.markdown("**Leyenda de confianza:**")
    st.markdown("✅ **ALTA** ≥ 80% — Apostar")
    st.markdown("⚡ **MEDIA** 60-79% — Analizar")
    st.markdown("⚠️ **BAJA** < 60% — Evitar")
    st.markdown("💎 **VALUE BET** — Ventaja vs cuota")
    st.markdown("---")
    st.markdown("**Motor:**")
    st.markdown("Poisson / Negative Binomial")
    st.markdown("Fusión 70/30 por partidos")
    st.markdown("Multi-temporada automático")
    st.markdown("Ajuste climático")
    st.markdown(f"Ventana: {DAYS_AHEAD} días")

# ================================================================
#  INTERFAZ PRINCIPAL
# ================================================================

st.markdown(f"""
<div class="hero">
  <div class="ver">VERSION 3.5 — EDICION DEFINITIVA</div>
  <h1>FOOTBALL ORACLE PRO</h1>
  <div class="sub">
    Monte Carlo 10,000 sims · Negative Binomial · Multi-API · Deep Data 50 partidos ·
    Fusión Inteligente 70/30 · Value Bets · Criterio de Kelly
  </div>
  <div class="api-row">
    {pill_api("football-data.org", bool(FD_KEY))}
    {pill_api("api-sports.io",     bool(APISPORTS))}
    {pill_api("the-odds-api",      bool(ODDS_KEY))}
    {pill_api("open-meteo",        True)}
  </div>
</div>
""", unsafe_allow_html=True)

# ── SELECTOR DE LIGA ──────────────────────────────────────────────
seccion("① ELIGE LA LIGA")

regiones = {"Latinoamerica": [], "Internacional": []}
for nombre, info in LIGAS.items():
    regiones[info["region"]].append(nombre)

c1, c2 = st.columns(2)
with c1:
    region = st.selectbox("Region", list(regiones.keys()), label_visibility="collapsed")
with c2:
    nombre_liga = st.selectbox("Liga", regiones[region], label_visibility="collapsed")

# ── SELECTOR DE PARTIDO ───────────────────────────────────────────
seccion("② ELIGE EL PARTIDO")

with st.spinner(f"Buscando partidos en los próximos {DAYS_AHEAD} días..."):
    partidos, fuente_usada = cargar_partidos(nombre_liga)

if not partidos:
    st.warning(f"No se encontraron partidos para **{nombre_liga}** en los próximos {DAYS_AHEAD} días.")
    lg = LIGAS[nombre_liga]
    with st.expander("Diagnóstico de API"):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            fut   = (datetime.now()+timedelta(days=DAYS_AHEAD)).strftime("%Y-%m-%d")
            r = requests.get(f"{AS_BASE}/fixtures", headers=AS_HDR,
                             params={"league":lg["as_id"],"season":lg["season"],
                                     "from":today,"to":fut}, timeout=12)
            d = r.json()
            st.code(f"HTTP {r.status_code} | results: {d.get('results',0)} | errors: {d.get('errors',{})}")
        except Exception as e: st.error(str(e))
    st.stop()

st.success(f"{len(partidos)} partido(s) encontrado(s) — fuente: **{fuente_usada}**")
mapa = {p["display"]: p for p in partidos}
sel  = st.selectbox("Partido", list(mapa.keys()), label_visibility="collapsed")
M    = mapa[sel]

st.markdown(f"""
<div class="match-box">
  <span class="tn">{M['local']}</span>
  <span class="vs">VS</span>
  <span class="tn">{M['visita']}</span>
  <div class="match-meta">📅 {M['fecha']}  ·  <span class="src-chip">{M.get('fuente','')}</span></div>
</div>
""", unsafe_allow_html=True)

# ── BOTÓN DE ANÁLISIS ─────────────────────────────────────────────
if st.button("ANALIZAR CON MONTE CARLO — 10,000 SIMULACIONES"):
    with st.spinner("Cargando estadísticas profundas y ejecutando simulación..."):

        datos  = cargar_estadisticas(M, nombre_liga)
        season = datos["season"]

        # Construir perfiles desde FD
        fd_local  = perfil_de_fd(datos["local"]["hist"],  M.get("id_local_fd"))
        fd_visita = perfil_de_fd(datos["visita"]["hist"], M.get("id_visita_fd"))

        # Construir perfiles desde AS
        as_local  = perfil_de_as(datos["local"]["stats"],  is_local=True)
        as_visita = perfil_de_as(datos["visita"]["stats"], is_local=False)

        # Enriquecer con últimos partidos
        fd_local  = enriquecer_con_ultimos(fd_local,  datos["local"]["ultimos"],  datos["local"]["id_as"])  if fd_local  else fd_local
        fd_visita = enriquecer_con_ultimos(fd_visita, datos["visita"]["ultimos"], datos["visita"]["id_as"]) if fd_visita else fd_visita

        # Fusión inteligente 70/30
        lp = fusionar_perfiles(fd_local,  as_local)
        vp = fusionar_perfiles(fd_visita, as_visita)

        # Datos complementarios
        sport_key = ODDS_MAP.get(nombre_liga)
        cuotas    = obtener_cuotas(sport_key, M["local"], M["visita"]) if sport_key else None
        coords    = COORDENADAS.get(nombre_liga, (4.71, -74.07))
        clima     = obtener_clima(coords[0], coords[1])

        # Monte Carlo con varianza real
        R     = correr_montecarlo(lp, vp, clima)
        preds = construir_predicciones(R, M["local"], M["visita"], cuotas)
        sug   = generar_sugerencia(preds, R, cuotas, M["local"], M["visita"],
                                    st.session_state.get("bankroll", 100))

    st.success("✅ 10,000 simulaciones completadas")

    # ── CALIDAD DE DATOS ──────────────────────────────────────
    seccion("CALIDAD DE DATOS")
    c1, c2, c3 = st.columns(3)
    p_local  = int(lp.get("partidos", 0))
    p_visita = int(vp.get("partidos", 0))
    fuentes  = sum([bool(FD_KEY), bool(APISPORTS), bool(ODDS_KEY), True])

    def color_dato(n):
        return "#3ecf8e" if n >= 10 else "#f5c842" if n >= 5 else "#f4622a"

    c1.markdown(f'<div class="kpi"><div class="kv" style="color:{color_dato(p_local)}">{p_local}</div><div class="kl">Partidos {M["local"][:14]}</div></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="kpi"><div class="kv" style="color:{color_dato(p_visita)}">{p_visita}</div><div class="kl">Partidos {M["visita"][:14]}</div></div>', unsafe_allow_html=True)
    kpi(f"{fuentes}/4", "Fuentes activas", c3)

    col1, col2 = st.columns(2)
    col1.markdown(f'**{M["local"]}:** <span class="src-chip">{lp.get("fuente","?")}</span>', unsafe_allow_html=True)
    col2.markdown(f'**{M["visita"]}:** <span class="src-chip">{vp.get("fuente","?")}</span>', unsafe_allow_html=True)
    st.markdown(f'**Motor MC:** {R["modelo"]} | σ local: {R["std_h"]} | σ visita: {R["std_a"]}')

    if p_local < 5 or p_visita < 5:
        st.markdown('<div class="warn-data">⚡ Pocos datos disponibles (< 5 partidos). Activa más fuentes para mayor precisión. Las predicciones se basan en promedios de liga como fallback.</div>', unsafe_allow_html=True)

    if clima:
        ico = "🌧️" if clima["lluvia"]>2 else "💨" if clima["viento"]>30 else "☀️" if clima["code"]<3 else "☁️"
        st.info(f"{ico} **Clima:** {clima['cond']} | {clima['temp']}°C | Lluvia: {clima['lluvia']}mm | Viento: {clima['viento']}km/h — ajustado en el modelo")

    # ── CUOTAS EN VIVO ────────────────────────────────────────
    if cuotas:
        seccion("CUOTAS EN TIEMPO REAL")
        st.markdown(f'<div style="font-size:.72rem;color:#30305a;margin-bottom:10px">Fuente: {cuotas.get("casa","")} via the-odds-api.com</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        for col, label, key in [
            (c1, M["local"][:14],  "cuota_local"),
            (c2, "Empate",         "cuota_empate"),
            (c3, M["visita"][:14], "cuota_visita"),
        ]:
            ov = cuotas.get(key, 0)
            kpi(f"{ov:.2f}" if ov else "N/D", f"{label}\n(impl. {impl(ov)}%)", col)

    # ── SUGERENCIA DE APUESTA ─────────────────────────────────
    seccion("SUGERENCIA DE APUESTA")
    render_sugerencia(sug, st.session_state.get("bankroll", 100))

    # ── PREDICCIONES POR CONFIANZA ────────────────────────────
    seccion("PREDICCIONES POR NIVEL DE CONFIANZA")
    altas = [p for p in preds if p["conf"] >= 80]
    medias= [p for p in preds if 60 <= p["conf"] < 80]
    bajas = [p for p in preds if p["conf"] < 60]

    c1, c2, c3 = st.columns(3)
    kpi(str(len(altas)),  "Alta ≥80% ✅",   c1)
    kpi(str(len(medias)), "Media 60-79% ⚡", c2)
    kpi(str(len(bajas)),  "Baja <60% ⚠️",   c3)
    st.markdown("<br>", unsafe_allow_html=True)

    if altas:
        st.markdown("#### ✅ Alta confianza (≥80%) — Estadísticamente sólidas")
        for p in altas: render_prediccion(p)
    if medias:
        st.markdown("#### ⚡ Confianza media (60–79%) — Analiza antes de apostar")
        for p in medias: render_prediccion(p)
    if bajas:
        st.markdown("#### ⚠️ Baja confianza (<60%) — Evitar")
        for p in bajas: render_prediccion(p)

    # ── PROBABILIDADES 1X2 ────────────────────────────────────
    seccion("PROBABILIDADES 1X2")
    barra(f"Local: {M['local']}",   R["p_local"],  "#3ecf8e")
    barra("Empate",                  R["p_empate"], "#f5c842")
    barra(f"Visita: {M['visita']}", R["p_visita"], "#f4622a")

    # ── GOLES ─────────────────────────────────────────────────
    seccion("GOLES PROYECTADOS")
    c1, c2, c3, c4 = st.columns(4)
    kpi(R["lh"],          f"Goles esp.\n{M['local'][:12]}",  c1)
    kpi(R["la"],          f"Goles esp.\n{M['visita'][:12]}", c2)
    kpi(f"{R['o25']}%",   "Mas de 2.5 Goles",                c3)
    kpi(f"{R['btts']}%",  "Ambos Anotan BTTS",               c4)

    # ── MARCADORES ────────────────────────────────────────────
    seccion("MARCADORES MAS PROBABLES")
    st.dataframe(
        pd.DataFrame(R["top"], columns=["Marcador", "Prob %"])
          .style.background_gradient(subset=["Prob %"], cmap="Oranges")
          .format({"Prob %": "{:.1f}%"}),
        use_container_width=True, hide_index=True
    )

    # ── CORNERS ───────────────────────────────────────────────
    seccion("CORNERS")
    c1, c2, c3, c4 = st.columns(4)
    kpi(R["hc"],          f"Corners {M['local'][:12]}",  c1)
    kpi(R["ac"],          f"Corners {M['visita'][:12]}", c2)
    kpi(R["tc"],          "Total Corners",                c3)
    kpi(f"{R['co85']}%",  "Mas de 8.5",                  c4)

    # ── TARJETAS ──────────────────────────────────────────────
    seccion("TARJETAS")
    c1, c2, c3, c4 = st.columns(4)
    kpi(R["hy"], f"Amarillas {M['local'][:12]}",  c1)
    kpi(R["ay"], f"Amarillas {M['visita'][:12]}", c2)
    kpi(R["ty"], "Total Amarillas",                c3)
    kpi(R["tr"], "Rojas Totales",                  c4)

    # ── FALTAS Y TIROS ────────────────────────────────────────
    seccion("FALTAS Y TIROS A PUERTA")
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(pd.DataFrame({
            "Equipo":  [M["local"], M["visita"], "TOTAL"],
            "Faltas":  [R["hf"],    R["af"],     R["tf"]],
        }), use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(pd.DataFrame({
            "Equipo":          [M["local"], M["visita"]],
            "Tiros a puerta":  [R["hs"],    R["as_"]],
        }), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("Football Oracle PRO v3.5 — Análisis estadístico educativo. Alta confianza = mayor probabilidad estadística, NO garantía de resultado. El Criterio de Kelly es orientativo. Apuesta siempre con responsabilidad.")
