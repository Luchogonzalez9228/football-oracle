# ============================================================
#  ⚽  FOOTBALL ORACLE  —  Pronósticos Automáticos de Fútbol
#  Científico de Datos Senior | Monte Carlo 10,000 sims
# ============================================================

import streamlit as st
import requests
import numpy as np
import pandas as pd
from scipy import stats
import json

# ─────────────────────────────────────────────────────────────
#  🔑  PEGA TU API KEY AQUÍ
# ─────────────────────────────────────────────────────────────
API_KEY = "70cb24441a57cc0a28c2fd7dd3b76110"
BASE_URL = "https://v3.football.api-sports.io"
# ─────────────────────────────────────────────────────────────

HEADERS = {"x-apisports-key": API_KEY}
N_SIMULATIONS = 10_000
# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Football Oracle",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;700&display=swap');

  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

  .stApp { background: #080810; color: #e8e8ee; }

  /* Hero banner */
  .hero {
    background: linear-gradient(135deg, #0f0f1a 0%, #1a0a0a 100%);
    border: 1px solid #2a2a3a;
    border-radius: 16px;
    padding: 28px 32px 20px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
  }
  .hero::before {
    content: '';
    position: absolute; top:-60px; right:-60px;
    width:260px; height:260px;
    background: radial-gradient(circle, rgba(244,98,42,0.15) 0%, transparent 70%);
  }
  .hero h1 {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 3rem; color: #f4622a; margin: 0; letter-spacing: 2px;
  }
  .hero p { color: #7070a0; font-size: 0.85rem; margin: 4px 0 0; }

  /* Metric cards */
  .metric-card {
    background: #13131f; border: 1px solid #2a2a3a;
    border-radius: 12px; padding: 16px 18px; text-align: center;
  }
  .metric-val { font-family: 'Bebas Neue', sans-serif; font-size: 2.2rem; color: #f5c842; }
  .metric-lbl { font-size: 0.7rem; color: #555568; letter-spacing: 2px; text-transform: uppercase; margin-top: 2px; }

  /* Prob bar */
  .prob-row { margin: 8px 0; }
  .prob-label { font-size: 0.8rem; color: #9090b0; margin-bottom: 3px; }
  .prob-bar-bg { background: #1e1e2e; border-radius: 99px; height: 10px; overflow: hidden; }
  .prob-bar-fill { height: 100%; border-radius: 99px; }

  /* Section titles */
  .sec-title {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.4rem; color: #f4622a; letter-spacing: 2px;
    border-bottom: 1px solid #2a2a3a; padding-bottom: 6px; margin: 20px 0 14px;
  }

  /* Team vs display */
  .matchup {
    background: #13131f; border: 1px solid #2a2a3a; border-radius: 14px;
    padding: 20px; text-align: center; margin-bottom: 20px;
  }
  .team-name { font-family: 'Bebas Neue', sans-serif; font-size: 1.8rem; color: #e8e8ee; }
  .vs-badge  { font-family: 'Bebas Neue', sans-serif; font-size: 2.5rem; color: #f4622a; }

  /* Result badge */
  .result-badge {
    display: inline-block;
    padding: 6px 18px; border-radius: 8px;
    font-weight: 700; font-size: 0.9rem; letter-spacing: 1px;
  }
  .win  { background: rgba(62,207,142,0.15); color: #3ecf8e; }
  .draw { background: rgba(245,200,66,0.12); color: #f5c842; }
  .lose { background: rgba(244,98,42,0.12);  color: #f4622a; }

  /* Tables */
  .styled-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  .styled-table th {
    background: #1e1e2e; color: #555568;
    font-size: 0.7rem; letter-spacing: 2px; text-transform: uppercase;
    padding: 8px 12px; text-align: left;
  }
  .styled-table td { padding: 8px 12px; color: #c0c0d8; border-bottom: 1px solid #1e1e2e; }
  .styled-table tr:hover td { background: #16162a; }

  /* Buttons */
  .stButton > button {
    background: #f4622a !important; color: white !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 700 !important; font-size: 1rem !important;
    padding: 12px 24px !important; width: 100% !important;
    letter-spacing: 1px !important;
  }
  .stButton > button:hover { background: #c04a1e !important; }

  /* Selectbox / inputs */
  .stSelectbox label, .stTextInput label { color: #9090b0 !important; font-size: 0.8rem !important; }

  /* Spinner */
  .stSpinner > div { border-top-color: #f4622a !important; }

  /* Alert */
  .stAlert { border-radius: 10px !important; }

  /* Hide streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  API HELPERS
# ══════════════════════════════════════════════════════════════

def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("response", [])
    except Exception as e:
        st.error(f"Error de API: {e}")
        return []


@st.cache_data(ttl=3600)
def get_leagues():
    data = api_get("leagues", {"current": "true"})
    leagues = []
    for item in data:
        lg = item.get("league", {})
        ct = item.get("country", {})
        leagues.append({
            "id": lg.get("id"),
            "name": lg.get("name"),
            "country": ct.get("name", ""),
            "display": f"{ct.get('name','?')} — {lg.get('name','?')}",
        })
    return sorted(leagues, key=lambda x: x["display"])


@st.cache_data(ttl=1800)
def get_fixtures(league_id, season=2024):
    data = api_get("fixtures", {"league": league_id, "season": season, "status": "NS", "next": 20})
    matches = []
    for f in data:
        fix = f.get("fixture", {})
        teams = f.get("teams", {})
        matches.append({
            "id": fix.get("id"),
            "date": fix.get("date", "")[:10],
            "home": teams.get("home", {}).get("name", "?"),
            "away": teams.get("away", {}).get("name", "?"),
            "home_id": teams.get("home", {}).get("id"),
            "away_id": teams.get("away", {}).get("id"),
            "display": f"{fix.get('date','')[:10]}  |  {teams.get('home',{}).get('name','?')}  vs  {teams.get('away',{}).get('name','?')}",
        })
    return matches


@st.cache_data(ttl=3600)
def get_team_stats(team_id, league_id, season=2024):
    data = api_get("teams/statistics", {"team": team_id, "league": league_id, "season": season})
    return data if data else {}


@st.cache_data(ttl=3600)
def get_last_fixtures(team_id, league_id, n=10):
    data = api_get("fixtures", {"team": team_id, "league": league_id, "season": 2024,
                                 "status": "FT", "last": n})
    return data


# ══════════════════════════════════════════════════════════════
#  STATISTICS EXTRACTORS
# ══════════════════════════════════════════════════════════════

def safe_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except:
        return default


def extract_team_profile(stats, last_fixtures, is_home=True):
    """Extract rich statistical profile from API responses."""
    venue = "home" if is_home else "away"

    # Goals
    goals_for_avg  = safe_float(stats.get("goals", {}).get("for",  {}).get("average", {}).get(venue, 1.3))
    goals_ag_avg   = safe_float(stats.get("goals", {}).get("against", {}).get("average", {}).get(venue, 1.1))

    # Shots
    shots_total = safe_float(stats.get("shots", {}).get("total",  {}).get("average", 12))
    shots_on    = safe_float(stats.get("shots", {}).get("on",     {}).get("average", 4.5))

    # Cards (from fixtures history)
    yellows, reds, fouls, corners = [], [], [], []
    clean_sheets = 0

    for f in last_fixtures:
        teams    = f.get("teams", {})
        fix_id   = f.get("fixture", {}).get("id")
        score    = f.get("score", {}).get("fulltime", {})
        home_sc  = score.get("home", 0) or 0
        away_sc  = score.get("away", 0) or 0

        is_team_home = teams.get("home", {}).get("id") == (stats.get("team", {}).get("id"))
        team_goals = home_sc if is_team_home else away_sc
        opp_goals  = away_sc if is_team_home else home_sc

        if opp_goals == 0:
            clean_sheets += 1

    # Fallback league averages if stats incomplete
    yellows_avg  = safe_float(stats.get("cards",  {}).get("yellow", {}).get("average", 1.8))
    reds_avg     = safe_float(stats.get("cards",  {}).get("red",    {}).get("average", 0.1))
    fouls_avg    = safe_float(stats.get("fouls",  {}).get("committed", {}).get("average", 12.0))
    corners_avg  = safe_float(stats.get("corners",{}).get("total",     {}).get("average",  5.2))

    cs_pct = clean_sheets / max(len(last_fixtures), 1)

    return {
        "goals_for":    goals_for_avg,
        "goals_against":goals_ag_avg,
        "shots_total":  shots_total,
        "shots_on":     shots_on,
        "yellows":      yellows_avg  if yellows_avg  > 0 else 1.8,
        "reds":         reds_avg     if reds_avg     > 0 else 0.1,
        "fouls":        fouls_avg    if fouls_avg    > 0 else 12.0,
        "corners":      corners_avg  if corners_avg  > 0 else 5.2,
        "clean_sheet_pct": cs_pct,
        "btts_scored":  1.0,  # placeholder, computed below
    }


# ══════════════════════════════════════════════════════════════
#  MONTE CARLO ENGINE
# ══════════════════════════════════════════════════════════════

def run_monte_carlo(home_profile, away_profile):
    """10,000 Monte Carlo simulations of a football match."""
    rng = np.random.default_rng(42)

    # ── Goal simulation (Dixon-Coles inspired) ──
    home_attack = home_profile["goals_for"]
    away_attack = away_profile["goals_for"]
    home_defence= home_profile["goals_against"]
    away_defence= away_profile["goals_against"]

    league_avg = 1.35  # typical league average
    home_advantage = 1.12

    lambda_home = max(0.3, home_attack * (away_defence / league_avg) * home_advantage)
    lambda_away = max(0.3, away_attack * (home_defence / league_avg))

    home_goals_sim = rng.poisson(lambda_home, N_SIMULATIONS)
    away_goals_sim = rng.poisson(lambda_away, N_SIMULATIONS)

    home_wins = np.sum(home_goals_sim > away_goals_sim)
    draws     = np.sum(home_goals_sim == away_goals_sim)
    away_wins = np.sum(home_goals_sim < away_goals_sim)

    # ── Over 2.5 ──
    total_goals = home_goals_sim + away_goals_sim
    over25 = np.sum(total_goals > 2.5)

    # ── BTTS ──
    btts = np.sum((home_goals_sim > 0) & (away_goals_sim > 0))

    # ── Corners ──
    home_corners_sim = rng.poisson(home_profile["corners"], N_SIMULATIONS)
    away_corners_sim = rng.poisson(away_profile["corners"],  N_SIMULATIONS)
    total_corners    = home_corners_sim + away_corners_sim

    # ── Cards ──
    home_yellows_sim = rng.poisson(home_profile["yellows"], N_SIMULATIONS)
    away_yellows_sim = rng.poisson(away_profile["yellows"], N_SIMULATIONS)
    total_yellows    = home_yellows_sim + away_yellows_sim

    home_reds_sim    = rng.poisson(home_profile["reds"], N_SIMULATIONS)
    away_reds_sim    = rng.poisson(away_profile["reds"], N_SIMULATIONS)
    total_reds       = home_reds_sim + away_reds_sim

    # ── Fouls ──
    home_fouls_sim   = rng.poisson(home_profile["fouls"], N_SIMULATIONS)
    away_fouls_sim   = rng.poisson(away_profile["fouls"],  N_SIMULATIONS)
    total_fouls      = home_fouls_sim + away_fouls_sim

    # ── Shots on target ──
    home_shots_sim   = rng.poisson(home_profile["shots_on"], N_SIMULATIONS)
    away_shots_sim   = rng.poisson(away_profile["shots_on"],  N_SIMULATIONS)

    # ── Scoreline probabilities (top 9) ──
    scores = {}
    for h, a in zip(home_goals_sim[:], away_goals_sim[:]):
        k = f"{h}-{a}"
        scores[k] = scores.get(k, 0) + 1
    top_scores = sorted(scores.items(), key=lambda x: -x[1])[:9]

    def pct(n): return round(n / N_SIMULATIONS * 100, 1)

    return {
        # 1X2
        "prob_home_win": pct(home_wins),
        "prob_draw":     pct(draws),
        "prob_away_win": pct(away_wins),
        # Goals
        "lambda_home": round(lambda_home, 2),
        "lambda_away": round(lambda_away, 2),
        "over25_pct":  pct(over25),
        "btts_pct":    pct(btts),
        # Corners
        "home_corners_avg": round(np.mean(home_corners_sim), 2),
        "away_corners_avg": round(np.mean(away_corners_sim), 2),
        "total_corners_avg":round(np.mean(total_corners), 2),
        "corners_over85_pct": pct(np.sum(total_corners > 8.5)),
        # Cards
        "home_yellows_avg":  round(np.mean(home_yellows_sim), 2),
        "away_yellows_avg":  round(np.mean(away_yellows_sim), 2),
        "total_yellows_avg": round(np.mean(total_yellows), 2),
        "total_reds_avg":    round(np.mean(total_reds), 2),
        "home_reds_avg":     round(np.mean(home_reds_sim), 2),
        "away_reds_avg":     round(np.mean(away_reds_sim), 2),
        # Fouls
        "home_fouls_avg":   round(np.mean(home_fouls_sim), 2),
        "away_fouls_avg":   round(np.mean(away_fouls_sim), 2),
        "total_fouls_avg":  round(np.mean(total_fouls), 2),
        # Shots
        "home_shots_avg":  round(np.mean(home_shots_sim), 2),
        "away_shots_avg":  round(np.mean(away_shots_sim), 2),
        # Scorelines
        "top_scores": [(s, pct(c)) for s, c in top_scores],
    }


# ══════════════════════════════════════════════════════════════
#  UI HELPERS
# ══════════════════════════════════════════════════════════════

def prob_bar(label, pct, color="#f4622a"):
    st.markdown(f"""
    <div class="prob-row">
      <div class="prob-label">{label} — <b style="color:{color}">{pct}%</b></div>
      <div class="prob-bar-bg">
        <div class="prob-bar-fill" style="width:{min(pct,100)}%;background:{color}"></div>
      </div>
    </div>""", unsafe_allow_html=True)


def metric_card(val, label, col):
    col.markdown(f"""
    <div class="metric-card">
      <div class="metric-val">{val}</div>
      <div class="metric-lbl">{label}</div>
    </div>""", unsafe_allow_html=True)


def section(title):
    st.markdown(f'<div class="sec-title">{title}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
#  MAIN APP
# ══════════════════════════════════════════════════════════════

# Hero
st.markdown("""
<div class="hero">
  <h1>⚽ FOOTBALL ORACLE</h1>
  <p>Monte Carlo · 10,000 Simulaciones · Análisis Estadístico Avanzado</p>
</div>
""", unsafe_allow_html=True)

# API Key override in sidebar
with st.sidebar:
    st.markdown("### 🔑 API Key")
    key_input = st.text_input("RapidAPI Key (API-Football)", value=API_KEY, type="password")
    if key_input and key_input != "TU_API_KEY_AQUI":
        API_KEY = key_input
        HEADERS["x-rapidapi-key"] = API_KEY
    st.markdown("---")
    st.markdown("**Modelo:** Poisson + Monte Carlo")
    st.markdown("**Sims:** 10,000")
    st.markdown("**Temporada:** 2024")

# ── Step 1: Choose league ─────────────────────────────────────
section("① ELIGE LA LIGA")

if API_KEY == "TU_API_KEY_AQUI":
    st.warning("⚠️ Pega tu API Key en el sidebar izquierdo (ícono ≡) o en el código (línea 15) para comenzar.")
    st.stop()

with st.spinner("Cargando ligas disponibles..."):
    leagues = get_leagues()

if not leagues:
    st.error("No se pudieron cargar las ligas. Verifica tu API Key.")
    st.stop()

league_options = {lg["display"]: lg for lg in leagues}
selected_league_display = st.selectbox("Liga", list(league_options.keys()), label_visibility="collapsed")
selected_league = league_options[selected_league_display]

# ── Step 2: Choose match ──────────────────────────────────────
section("② ELIGE EL PARTIDO")

with st.spinner("Cargando próximos partidos..."):
    fixtures = get_fixtures(selected_league["id"])

if not fixtures:
    st.warning("No hay partidos próximos para esta liga en la temporada 2024.")
    st.stop()

match_options = {f["display"]: f for f in fixtures}
selected_match_display = st.selectbox("Partido", list(match_options.keys()), label_visibility="collapsed")
selected_match = match_options[selected_match_display]

# Matchup display
st.markdown(f"""
<div class="matchup">
  <span class="team-name">{selected_match['home']}</span>
  &nbsp;&nbsp;<span class="vs-badge">VS</span>&nbsp;&nbsp;
  <span class="team-name">{selected_match['away']}</span>
  <br><span style="color:#555568;font-size:0.8rem">{selected_match['date']}</span>
</div>
""", unsafe_allow_html=True)

# ── Step 3: Analyze ───────────────────────────────────────────
if st.button("🔮 ANALIZAR CON MONTE CARLO"):

    with st.spinner("Recopilando estadísticas y ejecutando 10,000 simulaciones..."):

        home_stats_raw = get_team_stats(selected_match["home_id"], selected_league["id"])
        away_stats_raw = get_team_stats(selected_match["away_id"], selected_league["id"])

        home_last = get_last_fixtures(selected_match["home_id"], selected_league["id"])
        away_last = get_last_fixtures(selected_match["away_id"], selected_league["id"])

        home_profile = extract_team_profile(home_stats_raw, home_last, is_home=True)
        away_profile = extract_team_profile(away_stats_raw, away_last, is_home=False)

        results = run_monte_carlo(home_profile, away_profile)

    st.success("✅ Análisis completado — 10,000 simulaciones ejecutadas")

    # ── 1X2 ──────────────────────────────────────────────────
    section("📊 RESULTADO 1X2")
    c1, c2, c3 = st.columns(3)
    metric_card(f"{results['prob_home_win']}%", f"Victoria {selected_match['home'][:12]}", c1)
    metric_card(f"{results['prob_draw']}%",     "Empate", c2)
    metric_card(f"{results['prob_away_win']}%", f"Victoria {selected_match['away'][:12]}", c3)

    st.markdown("<br>", unsafe_allow_html=True)
    prob_bar(f"Victoria {selected_match['home']}", results['prob_home_win'], "#3ecf8e")
    prob_bar("Empate", results['prob_draw'], "#f5c842")
    prob_bar(f"Victoria {selected_match['away']}", results['prob_away_win'], "#f4622a")

    # ── Goals ────────────────────────────────────────────────
    section("⚽ GOLES PROYECTADOS")
    c1, c2, c3, c4 = st.columns(4)
    metric_card(results['lambda_home'], f"Goles esperados\n{selected_match['home'][:10]}", c1)
    metric_card(results['lambda_away'], f"Goles esperados\n{selected_match['away'][:10]}", c2)
    metric_card(f"{results['over25_pct']}%", "Más de 2.5 Goles", c3)
    metric_card(f"{results['btts_pct']}%",   "Ambos Anotan (BTTS)", c4)

    # ── Scorelines ───────────────────────────────────────────
    section("🎯 MARCADORES MÁS PROBABLES")
    score_data = pd.DataFrame(results["top_scores"], columns=["Marcador", "Probabilidad (%)"])
    score_data = score_data.sort_values("Probabilidad (%)", ascending=False)
    st.dataframe(
        score_data.style
            .background_gradient(subset=["Probabilidad (%)"], cmap="Oranges")
            .format({"Probabilidad (%)": "{:.1f}%"}),
        use_container_width=True, hide_index=True
    )

    # ── Corners ──────────────────────────────────────────────
    section("🚩 CÓRNERS")
    c1, c2, c3, c4 = st.columns(4)
    metric_card(results['home_corners_avg'],    f"Córners\n{selected_match['home'][:10]}", c1)
    metric_card(results['away_corners_avg'],    f"Córners\n{selected_match['away'][:10]}", c2)
    metric_card(results['total_corners_avg'],   "Total Córners", c3)
    metric_card(f"{results['corners_over85_pct']}%", "Más de 8.5 Córners", c4)

    prob_bar(f"Más Córners: {selected_match['home']}", round(results['home_corners_avg'] / max(results['total_corners_avg'],1) * 100, 1), "#4f8ef7")

    # ── Cards ────────────────────────────────────────────────
    section("🟨 TARJETAS")
    c1, c2, c3, c4 = st.columns(4)
    metric_card(results['home_yellows_avg'],  f"Amarillas\n{selected_match['home'][:10]}", c1)
    metric_card(results['away_yellows_avg'],  f"Amarillas\n{selected_match['away'][:10]}", c2)
    metric_card(results['total_yellows_avg'], "Total Amarillas", c3)
    metric_card(results['total_reds_avg'],    "Rojas Totales", c4)

    st.markdown("<br>", unsafe_allow_html=True)
    cards_df = pd.DataFrame({
        "Equipo": [selected_match["home"], selected_match["away"]],
        "Amarillas esperadas": [results["home_yellows_avg"], results["away_yellows_avg"]],
        "Rojas esperadas":     [results["home_reds_avg"],    results["away_reds_avg"]],
    })
    st.dataframe(cards_df, use_container_width=True, hide_index=True)

    # ── Fouls & Shots ────────────────────────────────────────
    section("⚡ FALTAS & TIROS A PUERTA")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Faltas Cometidas**")
        fouls_df = pd.DataFrame({
            "Equipo": [selected_match["home"], selected_match["away"], "TOTAL"],
            "Faltas esperadas": [
                results["home_fouls_avg"],
                results["away_fouls_avg"],
                results["total_fouls_avg"]
            ]
        })
        st.dataframe(fouls_df, use_container_width=True, hide_index=True)

    with c2:
        st.markdown("**Tiros a Puerta**")
        shots_df = pd.DataFrame({
            "Equipo": [selected_match["home"], selected_match["away"]],
            "Tiros a puerta": [results["home_shots_avg"], results["away_shots_avg"]]
        })
        st.dataframe(shots_df, use_container_width=True, hide_index=True)

    # ── Summary ──────────────────────────────────────────────
    section("✅ RESUMEN DE APUESTAS SUGERIDAS")

    best_1x2 = max(
        [("Victoria " + selected_match["home"], results["prob_home_win"]),
         ("Empate", results["prob_draw"]),
         ("Victoria " + selected_match["away"], results["prob_away_win"])],
        key=lambda x: x[1]
    )

    bets = [
        ("1X2", best_1x2[0], f"{best_1x2[1]}%", "alta" if best_1x2[1] > 50 else "media"),
        ("Goles", "Más de 2.5" if results["over25_pct"] > 50 else "Menos de 2.5",
         f"{max(results['over25_pct'], 100-results['over25_pct'])}%",
         "alta" if max(results["over25_pct"], 100-results["over25_pct"]) > 60 else "media"),
        ("BTTS", "Sí" if results["btts_pct"] > 50 else "No",
         f"{max(results['btts_pct'], 100-results['btts_pct'])}%",
         "alta" if max(results["btts_pct"], 100-results["btts_pct"]) > 60 else "media"),
        ("Córners", f"{'Más' if results['corners_over85_pct'] > 50 else 'Menos'} de 8.5",
         f"{max(results['corners_over85_pct'], 100-results['corners_over85_pct'])}%",
         "alta" if max(results["corners_over85_pct"], 100-results["corners_over85_pct"]) > 60 else "media"),
    ]

    bets_df = pd.DataFrame(bets, columns=["Mercado", "Selección", "Confianza", "Nivel"])
    st.dataframe(bets_df, use_container_width=True, hide_index=True)

    st.info("⚠️ Este análisis es estadístico y educativo. Las apuestas deportivas implican riesgo. Juega con responsabilidad.")
