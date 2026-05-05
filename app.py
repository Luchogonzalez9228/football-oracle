import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json

# ─────────────────────────────────────────────────────────────
#  🔑  PEGA TU API KEY AQUÍ  (de dashboard.api-sports.io)
# ─────────────────────────────────────────────────────────────
API_KEY  = "70cb24441a57cc0a28c2fd7dd3b76110"  # No escribas tu key aqui. Usala desde el sidebar o Streamlit Secrets
BASE_URL = "https://v3.football.api-sports.io"
# ─────────────────────────────────────────────────────────────

N_SIMULATIONS = 10_000

def get_headers():
    # Try: 1) sidebar input, 2) Streamlit Secrets, 3) hardcoded fallback
    key = (st.session_state.get("api_key") or
           st.secrets.get("API_KEY", "") if hasattr(st, "secrets") else "" or
           API_KEY)
    return {"x-apisports-key": key}

st.set_page_config(page_title="Football Oracle", page_icon="⚽", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Sans:wght@300;400;500;700&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:#080810;color:#e8e8ee;}
.hero{background:linear-gradient(135deg,#0f0f1a,#1a0a0a);border:1px solid #2a2a3a;border-radius:16px;padding:28px 32px 20px;margin-bottom:24px;}
.hero h1{font-family:'Bebas Neue',sans-serif;font-size:3rem;color:#f4622a;margin:0;letter-spacing:2px;}
.hero p{color:#7070a0;font-size:.85rem;margin:4px 0 0;}
.metric-card{background:#13131f;border:1px solid #2a2a3a;border-radius:12px;padding:16px 18px;text-align:center;margin-bottom:8px;}
.metric-val{font-family:'Bebas Neue',sans-serif;font-size:2.2rem;color:#f5c842;}
.metric-lbl{font-size:.7rem;color:#555568;letter-spacing:2px;text-transform:uppercase;margin-top:2px;}
.sec-title{font-family:'Bebas Neue',sans-serif;font-size:1.4rem;color:#f4622a;letter-spacing:2px;border-bottom:1px solid #2a2a3a;padding-bottom:6px;margin:20px 0 14px;}
.matchup{background:#13131f;border:1px solid #2a2a3a;border-radius:14px;padding:20px;text-align:center;margin-bottom:20px;}
.team-name{font-family:'Bebas Neue',sans-serif;font-size:1.8rem;color:#e8e8ee;}
.vs-badge{font-family:'Bebas Neue',sans-serif;font-size:2.5rem;color:#f4622a;}
.pred-card{background:#13131f;border:1px solid #2a2a3a;border-radius:12px;padding:16px 20px;margin-bottom:10px;}
.pred-card-low{background:#1a0d0d;border:1px solid #f4622a55;border-radius:12px;padding:16px 20px;margin-bottom:10px;}
.pred-card-med{background:#13130a;border:1px solid #f5c84244;border-radius:12px;padding:16px 20px;margin-bottom:10px;}
.pred-market{font-size:.7rem;color:#555568;letter-spacing:2px;text-transform:uppercase;}
.pred-pick{font-weight:700;font-size:.95rem;margin:4px 0;}
.pred-detail{font-size:.75rem;color:#555568;}
.cbar-wrap{background:#1e1e2e;border-radius:99px;height:8px;overflow:hidden;margin:5px 0;}
.prob-row{margin:8px 0;}
.prob-label{font-size:.8rem;color:#9090b0;margin-bottom:3px;}
.prob-bar-bg{background:#1e1e2e;border-radius:99px;height:10px;overflow:hidden;}
.prob-bar-fill{height:100%;border-radius:99px;}
.stButton>button{background:#f4622a!important;color:white!important;border:none!important;border-radius:10px!important;font-weight:700!important;font-size:1rem!important;padding:14px 24px!important;width:100%!important;letter-spacing:1px!important;}
.stButton>button:hover{background:#c04a1e!important;}
#MainMenu,footer,header{visibility:hidden;}
</style>
""", unsafe_allow_html=True)

POPULAR_LEAGUES = {
    "ENG England — Premier League":  {"id":39,  "season":2024},
    "ESP Spain — La Liga":              {"id":140, "season":2024},
    "GER Germany — Bundesliga":         {"id":78,  "season":2024},
    "ITA Italy — Serie A":              {"id":135, "season":2024},
    "FRA France — Ligue 1":             {"id":61,  "season":2024},
    "POR Portugal — Primeira Liga":      {"id":94,  "season":2024},
    "NED Netherlands — Eredivisie":      {"id":88,  "season":2024},
    "TUR Turkey — Süper Lig":           {"id":203, "season":2024},
    "KSA Saudi Arabia — Pro League":     {"id":307, "season":2024},
    "MEX Mexico — Liga MX":             {"id":262, "season":2024},
    "BRA Brazil — Série A":              {"id":71,  "season":2025},
    "ARG Argentina — Liga Profesional":  {"id":128, "season":2024},
    "COL Colombia — Liga BetPlay":       {"id":239, "season":2025},
    "USA — MLS":                    {"id":253, "season":2025},
    "UCL UEFA Champions League":         {"id":2,   "season":2024},
    "UEL UEFA Europa League":            {"id":3,   "season":2024},
}

def api_get(endpoint, params=None):
    try:
        r = requests.get(f"{BASE_URL}/{endpoint}", headers=get_headers(), params=params, timeout=15)
        if r.status_code == 401:
            st.error("❌ API Key inválida.")
            return []
        if r.status_code == 429:
            st.warning("⚠️ Límite de requests alcanzado. Espera 1 minuto.")
            return []
        return r.json().get("response", [])
    except Exception as e:
        st.error(f"Error: {e}")
        return []

@st.cache_data(ttl=900)
def get_fixtures_for_league(league_id, season):
    today  = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d")
    for params in [
        {"league": league_id, "season": season, "status": "NS", "next": 20},
        {"league": league_id, "season": season, "from": today, "to": future},
        {"league": league_id, "season": season, "next": 20},
    ]:
        data = api_get("fixtures", params)
        if data:
            matches = []
            for f in data:
                fix   = f.get("fixture", {})
                teams = f.get("teams",   {})
                if fix.get("status", {}).get("short","") in ("FT","AET","PEN","CANC","ABD","PST"):
                    continue
                matches.append({
                    "id":      fix.get("id"),
                    "date":    fix.get("date","")[:10],
                    "home":    teams.get("home",{}).get("name","?"),
                    "away":    teams.get("away",{}).get("name","?"),
                    "home_id": teams.get("home",{}).get("id"),
                    "away_id": teams.get("away",{}).get("id"),
                    "season":  season,
                    "display": f"📅 {fix.get('date','')[:10]}  |  {teams.get('home',{}).get('name','?')}  vs  {teams.get('away',{}).get('name','?')}",
                })
            if matches:
                return matches
    return []

@st.cache_data(ttl=3600)
def get_team_stats(team_id, league_id, season):
    for s in [season, season-1]:
        data = api_get("teams/statistics", {"team": team_id, "league": league_id, "season": s})
        if data:
            return data
    return {}

@st.cache_data(ttl=3600)
def get_last_fixtures(team_id, season):
    for s in [season, season-1]:
        data = api_get("fixtures", {"team": team_id, "season": s, "status": "FT", "last": 10})
        if data:
            return data
    return []

def safe_float(v, d=0.0):
    try: return float(v) if v is not None else d
    except: return d

def extract_profile(stats, is_home=True):
    v = "home" if is_home else "away"
    def g(path, d=0.0):
        try:
            x = stats
            for k in path: x = x[k]
            return safe_float(x, d)
        except: return d
    gf = g(["goals","for","average",v]) or g(["goals","for","average","total"]) or 1.3
    ga = g(["goals","against","average",v]) or g(["goals","against","average","total"]) or 1.1
    def card_avg(color):
        d = stats.get("cards",{}).get(color,{}) if stats else {}
        vals = [safe_float(vv) for vv in d.values() if safe_float(vv) > 0]
        return round(sum(vals)/len(vals),2) if vals else (1.8 if color=="yellow" else 0.1)
    return {
        "goals_for":     max(0.3, gf),
        "goals_against": max(0.3, ga),
        "shots_on":      g(["shots","on","average"], 4.5),
        "yellows":       card_avg("yellow"),
        "reds":          card_avg("red"),
        "fouls":         g(["fouls","committed","average"], 12.0),
        "corners":       g(["corners","total","average"], 5.2),
    }

def run_mc(hp, ap):
    rng = np.random.default_rng(42)
    lh = max(0.3, hp["goals_for"] * (ap["goals_against"]/1.35) * 1.12)
    la = max(0.3, ap["goals_for"] * (hp["goals_against"]/1.35))
    hg  = rng.poisson(lh, N_SIMULATIONS)
    ag  = rng.poisson(la, N_SIMULATIONS)
    tot = hg + ag
    def p(n): return round(n/N_SIMULATIONS*100, 1)
    hc  = rng.poisson(hp["corners"], N_SIMULATIONS)
    ac  = rng.poisson(ap["corners"],  N_SIMULATIONS)
    hy  = rng.poisson(hp["yellows"], N_SIMULATIONS)
    ay  = rng.poisson(ap["yellows"], N_SIMULATIONS)
    hr  = rng.poisson(hp["reds"],    N_SIMULATIONS)
    ar  = rng.poisson(ap["reds"],    N_SIMULATIONS)
    hf  = rng.poisson(hp["fouls"],   N_SIMULATIONS)
    af  = rng.poisson(ap["fouls"],   N_SIMULATIONS)
    hs  = rng.poisson(hp["shots_on"],N_SIMULATIONS)
    as_ = rng.poisson(ap["shots_on"],N_SIMULATIONS)
    scores = {}
    for h,a in zip(hg,ag):
        k=f"{h}-{a}"; scores[k]=scores.get(k,0)+1
    return {
        "phw": p(np.sum(hg>ag)), "pd": p(np.sum(hg==ag)), "paw": p(np.sum(hg<ag)),
        "lh": round(lh,2), "la": round(la,2),
        "o25": p(np.sum(tot>2.5)),  "u25": p(np.sum(tot<=2.5)),
        "btts": p(np.sum((hg>0)&(ag>0))), "no_btts": p(np.sum(~((hg>0)&(ag>0)))),
        "hc": round(np.mean(hc),2), "ac": round(np.mean(ac),2), "tc": round(np.mean(hc+ac),2),
        "co85": p(np.sum(hc+ac>8.5)),  "cu85": p(np.sum(hc+ac<=8.5)),
        "hy": round(np.mean(hy),2), "ay": round(np.mean(ay),2), "ty": round(np.mean(hy+ay),2),
        "hr": round(np.mean(hr),2), "ar": round(np.mean(ar),2), "tr": round(np.mean(hr+ar),2),
        "hf": round(np.mean(hf),2), "af": round(np.mean(af),2), "tf": round(np.mean(hf+af),2),
        "hs": round(np.mean(hs),2), "as_": round(np.mean(as_),2),
        "top": [(s,p(c)) for s,c in sorted(scores.items(),key=lambda x:-x[1])[:9]],
    }

def conf_style(c):
    if c >= 80:   return ("#3ecf8e", "✅ ALTA",   "pred-card",     "rgba(62,207,142,0.15)")
    elif c >= 60: return ("#f5c842", "⚡ MEDIA",  "pred-card-med", "rgba(245,200,66,0.12)")
    else:         return ("#f4622a", "⚠️ BAJA",   "pred-card-low", "rgba(244,98,42,0.12)")

def build_predictions(R, hn, an):
    rows = []
    # 1X2
    best = max([(R["phw"], f"🏠 Victoria {hn}"), (R["pd"],"🤝 Empate"), (R["paw"],f"✈️ Victoria {an}")], key=lambda x:x[0])
    rows.append({"mercado":"Resultado 1X2","pick":best[1],"conf":best[0],"detalle":f"Local {R['phw']}% / Empate {R['pd']}% / Visita {R['paw']}%"})
    # O/U 2.5
    if R["o25"]>=R["u25"]: rows.append({"mercado":"Goles O/U 2.5","pick":"⚽ Más de 2.5 goles","conf":R["o25"],"detalle":f"Goles esperados: {round(R['lh']+R['la'],2)}"})
    else:                   rows.append({"mercado":"Goles O/U 2.5","pick":"🔒 Menos de 2.5 goles","conf":R["u25"],"detalle":f"Goles esperados: {round(R['lh']+R['la'],2)}"})
    # BTTS
    if R["btts"]>=R["no_btts"]: rows.append({"mercado":"Ambos Marcan (BTTS)","pick":"✅ Sí — Ambos anotan","conf":R["btts"],"detalle":f"λ local {R['lh']} / λ visita {R['la']}"})
    else:                        rows.append({"mercado":"Ambos Marcan (BTTS)","pick":"❌ No — Alguno no anota","conf":R["no_btts"],"detalle":f"λ local {R['lh']} / λ visita {R['la']}"})
    # Corners
    if R["co85"]>=R["cu85"]: rows.append({"mercado":"Córners O/U 8.5","pick":"🚩 Más de 8.5 córners","conf":R["co85"],"detalle":f"Total esperado: {R['tc']}"})
    else:                     rows.append({"mercado":"Córners O/U 8.5","pick":"🔒 Menos de 8.5 córners","conf":R["cu85"],"detalle":f"Total esperado: {R['tc']}"})
    # Doble oportunidad
    dc1 = min(round(R["phw"]+R["pd"],1), 99.0); dc2 = min(round(R["paw"]+R["pd"],1), 99.0)
    if dc1>=dc2: rows.append({"mercado":"Doble Oportunidad","pick":f"🏠 {hn} o Empate","conf":dc1,"detalle":"Dos resultados posibles cubiertos"})
    else:        rows.append({"mercado":"Doble Oportunidad","pick":f"✈️ {an} o Empate","conf":dc2,"detalle":"Dos resultados posibles cubiertos"})
    # Tarjetas
    ty = R["ty"]; line = max(1, round(ty)-1)
    prob_y = min(95.0, max(5.0, round(50+(ty-line-0.5)*18, 1)))
    rows.append({"mercado":f"Amarillas O {line}.5","pick":f"🟨 Más de {line}.5 amarillas","conf":prob_y,"detalle":f"Total amarillas esperadas: {ty}"})
    # Marcador exacto
    top = R["top"][0]
    rows.append({"mercado":"Marcador Exacto","pick":f"🎯 Resultado {top[0]}","conf":top[1],"detalle":"Marcador más frecuente en simulaciones"})
    return sorted(rows, key=lambda x: -x["conf"])

def render_pred(pred):
    color, badge, card_cls, bg = conf_style(pred["conf"])
    c = pred["conf"]
    warn = ""
    if c < 60:
        warn = f'<div style="background:rgba(244,98,42,0.1);border-radius:8px;padding:6px 12px;margin-top:8px;font-size:.78rem;color:#f4622a">⚠️ <b>RIESGO ALTO</b> — Confianza baja ({c}%). Evita apostar en este mercado.</div>'
    elif c < 80:
        warn = f'<div style="background:rgba(245,200,66,0.08);border-radius:8px;padding:6px 12px;margin-top:8px;font-size:.78rem;color:#f5c842">⚡ <b>CONFIANZA MEDIA</b> ({c}%) — Analiza antes de apostar.</div>'

    st.markdown(f"""
    <div class="{card_cls}">
      <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
        <div style="min-width:130px">
          <div class="pred-market">{pred['mercado']}</div>
        </div>
        <div style="flex:1">
          <div class="pred-pick">{pred['pick']}</div>
          <div class="pred-detail">{pred['detalle']}</div>
        </div>
        <div style="text-align:center;min-width:100px">
          <div style="font-family:'Bebas Neue',sans-serif;font-size:2rem;line-height:1;color:{color}">{c}%</div>
          <div class="cbar-wrap">
            <div style="width:{int(min(c,100))}%;height:100%;background:{color};border-radius:99px"></div>
          </div>
          <span style="display:inline-block;background:{bg};color:{color};border:1px solid {color}44;border-radius:6px;padding:2px 8px;font-size:.72rem;font-weight:700;margin-top:3px">{badge}</span>
        </div>
      </div>
      {warn}
    </div>""", unsafe_allow_html=True)

def prob_bar(label, val, color):
    st.markdown(f"""<div class="prob-row">
      <div class="prob-label">{label} — <b style="color:{color}">{val}%</b></div>
      <div class="prob-bar-bg"><div class="prob-bar-fill" style="width:{min(val,100)}%;background:{color}"></div></div>
    </div>""", unsafe_allow_html=True)

def metric_card(val, label, col):
    col.markdown(f'<div class="metric-card"><div class="metric-val">{val}</div><div class="metric-lbl">{label}</div></div>', unsafe_allow_html=True)

def section(title):
    st.markdown(f'<div class="sec-title">{title}</div>', unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔑 API Key")
    ki = st.text_input("api-sports.io key", value=st.session_state.get("api_key", API_KEY), type="password")
    if ki: st.session_state["api_key"] = ki
    st.markdown("---")
    if st.button("🔍 Probar API Key"):
        with st.spinner("Probando..."):
            try:
                r = requests.get(f"{BASE_URL}/status", headers=get_headers(), timeout=10)
                d = r.json().get("response", {})
                acct = d.get("account",{}); sub = d.get("subscription",{}); req = d.get("requests",{})
                if r.status_code==200 and acct:
                    st.success("✅ Conectado!")
                    st.markdown(f"**Email:** {acct.get('email','?')}")
                    st.markdown(f"**Plan:** {sub.get('plan','?')}")
                    st.markdown(f"**Activa:** {'Sí ✅' if sub.get('active') else 'No ❌'}")
                    st.markdown(f"**Requests hoy:** {req.get('current',0)}/{req.get('limit_day',100)}")
                else:
                    st.error(f"HTTP {r.status_code}: {r.text[:200]}")
            except Exception as e: st.error(f"{e}")
    st.markdown("---")
    st.markdown("**Modelo:** Poisson + Monte Carlo")
    st.markdown("**Simulaciones:** 10,000")
    st.markdown("---")
    st.markdown("**Leyenda:**")
    st.markdown("✅ **ALTA** ≥ 80% — Apostar")
    st.markdown("⚡ **MEDIA** 60–79% — Con cuidado")
    st.markdown("⚠️ **BAJA** < 60% — Evitar")

# ── MAIN ──────────────────────────────────────────────────────
st.markdown('<div class="hero"><h1>⚽ FOOTBALL ORACLE</h1><p>Monte Carlo · 10,000 Simulaciones · Sistema de Confiabilidad por Mercado</p></div>', unsafe_allow_html=True)

active_key = (st.session_state.get("api_key") or (st.secrets.get("API_KEY","") if hasattr(st,"secrets") else ""))
if not active_key:
    st.warning("⚠️ Abre el sidebar (≡) y pega tu API Key para comenzar.")
    st.stop()

section("① ELIGE LA LIGA")
league_name = st.selectbox("Liga", list(POPULAR_LEAGUES.keys()), label_visibility="collapsed")
lg = POPULAR_LEAGUES[league_name]

section("② ELIGE EL PARTIDO")
with st.spinner("Buscando partidos próximos..."):
    fixtures = get_fixtures_for_league(lg["id"], lg["season"])

if not fixtures:
    st.warning(f"No se encontraron partidos próximos para **{league_name}**.")
    st.info("Prueba otra liga o verifica tu API Key.")
    with st.expander("🛠️ Respuesta cruda de la API"):
        try:
            r = requests.get(f"{BASE_URL}/fixtures", headers=get_headers(),
                             params={"league":lg["id"],"season":lg["season"],"next":5}, timeout=15)
            st.code(f"HTTP {r.status_code}\n\n{json.dumps(r.json(),indent=2)[:2000]}", language="json")
        except Exception as e: st.error(str(e))
    st.stop()

M = {f["display"]: f for f in fixtures}
sel = st.selectbox("Partido", list(M.keys()), label_visibility="collapsed")
match = M[sel]

st.markdown(f"""<div class="matchup">
  <span class="team-name">{match['home']}</span>
  &nbsp;&nbsp;<span class="vs-badge">VS</span>&nbsp;&nbsp;
  <span class="team-name">{match['away']}</span>
  <br><span style="color:#555568;font-size:.85rem">📅 {match['date']}  ·  Temporada {match['season']}</span>
</div>""", unsafe_allow_html=True)

if st.button("🔮 ANALIZAR CON MONTE CARLO"):
    with st.spinner("Ejecutando 10,000 simulaciones..."):
        s   = match["season"]
        hp  = extract_profile(get_team_stats(match["home_id"], lg["id"], s), True)
        ap  = extract_profile(get_team_stats(match["away_id"], lg["id"], s), False)
        R   = run_mc(hp, ap)
        preds = build_predictions(R, match["home"], match["away"])

    st.success("✅ 10,000 simulaciones completadas")

    # ── PREDICCIONES CON CONFIANZA ────────────────────────────
    section("🎯 PREDICCIONES — NIVEL DE CONFIANZA")

    high = [p for p in preds if p["conf"] >= 80]
    med  = [p for p in preds if 60 <= p["conf"] < 80]
    low  = [p for p in preds if p["conf"] < 60]

    c1,c2,c3 = st.columns(3)
    metric_card(str(len(high)), "Alta Confianza ✅ ≥80%",  c1)
    metric_card(str(len(med)),  "Confianza Media ⚡ 60-79%", c2)
    metric_card(str(len(low)),  "Baja Confianza ⚠️ <60%",   c3)

    st.markdown("<br>", unsafe_allow_html=True)

    if high:
        st.markdown("#### ✅ Predicciones de ALTA confianza (≥ 80%)")
        for p in high: render_pred(p)
    if med:
        st.markdown("#### ⚡ Predicciones de confianza MEDIA (60–79%)")
        for p in med: render_pred(p)
    if low:
        st.markdown("#### ⚠️ Predicciones de BAJA confianza (< 60%) — Alto riesgo")
        for p in low: render_pred(p)

    # ── 1X2 ──────────────────────────────────────────────────
    section("📊 PROBABILIDADES 1X2")
    prob_bar(f"🏠 {match['home']}", R["phw"], "#3ecf8e")
    prob_bar("🤝 Empate",            R["pd"],  "#f5c842")
    prob_bar(f"✈️ {match['away']}", R["paw"], "#f4622a")

    # ── Goles ─────────────────────────────────────────────────
    section("⚽ GOLES PROYECTADOS")
    c1,c2,c3,c4 = st.columns(4)
    metric_card(R["lh"],           f"Goles esp. {match['home'][:12]}", c1)
    metric_card(R["la"],           f"Goles esp. {match['away'][:12]}", c2)
    metric_card(f"{R['o25']}%",    "Más de 2.5 Goles",   c3)
    metric_card(f"{R['btts']}%",   "Ambos Anotan BTTS",  c4)

    # ── Top Marcadores ────────────────────────────────────────
    section("🔢 MARCADORES MÁS PROBABLES")
    st.dataframe(
        pd.DataFrame(R["top"], columns=["Marcador","Prob %"])
          .style.background_gradient(subset=["Prob %"], cmap="Oranges")
          .format({"Prob %":"{:.1f}%"}),
        use_container_width=True, hide_index=True
    )

    # ── Corners ───────────────────────────────────────────────
    section("🚩 CÓRNERS")
    c1,c2,c3,c4 = st.columns(4)
    metric_card(R["hc"], f"Córners {match['home'][:12]}", c1)
    metric_card(R["ac"], f"Córners {match['away'][:12]}", c2)
    metric_card(R["tc"], "Total Córners",                  c3)
    metric_card(f"{R['co85']}%", "Más de 8.5 Córners",   c4)

    # ── Cards ─────────────────────────────────────────────────
    section("🟨 TARJETAS")
    c1,c2,c3,c4 = st.columns(4)
    metric_card(R["hy"], f"Amarillas {match['home'][:12]}", c1)
    metric_card(R["ay"], f"Amarillas {match['away'][:12]}", c2)
    metric_card(R["ty"], "Total Amarillas",                  c3)
    metric_card(R["tr"], "Rojas Totales",                    c4)

    # ── Fouls & Shots ─────────────────────────────────────────
    section("⚡ FALTAS & TIROS A PUERTA")
    c1,c2 = st.columns(2)
    with c1:
        st.dataframe(pd.DataFrame({
            "Equipo":  [match["home"], match["away"], "TOTAL"],
            "Faltas":  [R["hf"], R["af"], R["tf"]],
        }), use_container_width=True, hide_index=True)
    with c2:
        st.dataframe(pd.DataFrame({
            "Equipo":          [match["home"], match["away"]],
            "Tiros a puerta":  [R["hs"],       R["as_"]],
        }), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("⚠️ Análisis estadístico y educativo. Las apuestas implican riesgo real. ✅ ALTA confianza = mayor probabilidad estadística, NO garantía de resultado.")
