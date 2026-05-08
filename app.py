import streamlit as st
import requests
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from scipy.stats import nbinom
import math, json, warnings

warnings.filterwarnings("ignore")

# ================================================================
#  KEYS & CONFIG
# ================================================================
FD_KEY    = "a2aef808a68d4cd6ba2ad97f9953ec81"
APISPORTS = "70cb24441a57cc0a28c2fd7dd3b76110"
ODDS_KEY  = "f028e4d3689b54c609ce7137fc6a40ba"

# Headers
FD_HDR = {"X-Auth-Token": FD_KEY}
AS_HDR = {"x-apisports-key": APISPORTS}

N_SIM      = 10_000
DAYS_AHEAD = 45
KELLY_FRAC = 0.25

# ================================================================
#  MODULO ADN MUNDIALISTA (Datos 2014-2022)
# ================================================================
ADN_MUNDIALISTA = {
    "Brasil":    {"gf": 1.9, "gc": 0.8, "corners": 6.1},
    "Argentina": {"gf": 1.7, "gc": 0.9, "corners": 5.8},
    "Colombia":  {"gf": 1.6, "gc": 1.0, "corners": 4.5},
    "Alemania":  {"gf": 2.1, "gc": 1.1, "corners": 6.5},
    "Francia":   {"gf": 2.0, "gc": 0.9, "corners": 5.5},
    "DEFAULT":   {"gf": 1.3, "gc": 1.3, "corners": 5.0}
}

# ================================================================
#  DICCIONARIO DE LIGAS (ID API-SPORTS)
# ================================================================
LIGAS_TOP = {
    "Colombia - Liga BetPlay": {"id": 72, "season": 2025, "odds": "soccer_colombia_primera_a"},
    "Argentina - LFP":         {"id": 128, "season": 2025, "odds": "soccer_argentina_primera_division"},
    "Brasil - Serie A":        {"id": 71, "season": 2025, "odds": "soccer_brazil_campeonato"},
    "Chile - Primera":         {"id": 265, "season": 2025, "odds": "soccer_chile_primera_division"},
    "Copa Libertadores":       {"id": 13, "season": 2025, "odds": "soccer_conmebol_copa_libertadores"},
    "Copa Sudamericana":       {"id": 11, "season": 2025, "odds": "soccer_conmebol_copa_sudamericana"},
    "Premier League":          {"id": 39, "season": 2024, "odds": "soccer_england_league1"},
    "La Liga":                 {"id": 140, "season": 2024, "odds": "soccer_spain_la_liga"},
    "Bundesliga":              {"id": 78, "season": 2024, "odds": "soccer_germany_bundesliga"},
    "Serie A (ITA)":           {"id": 135, "season": 2024, "odds": "soccer_italy_serie_a"},
    "Ligue 1 (FRA)":           {"id": 61, "season": 2024, "odds": "soccer_france_ligue_one"},
    "Champions League":        {"id": 2, "season": 2024, "odds": "soccer_uefa_champs_league"},
    "Mundial 2026":            {"id": 1, "season": 2026, "odds": "soccer_fifa_world_cup"}
}

# ================================================================
#  SISTEMA HÍBRIDO (CAPA 2: WEB SCRAPING FBREF)
# ================================================================
def scrape_fbref_backup(league_name):
    """Fallback si las APIs devuelven 0 resultados."""
    try:
        # Intentamos leer tablas de resultados generales (Ejemplo simplificado)
        url = "https://fbref.com/en/comps/9/schedule/Premier-League-Scores-and-Fixtures"
        tables = pd.read_html(url)
        df = tables[0]
        # Aquí procesaríamos el dataframe para devolver partidos
        return [] # Simulación de retorno
    except:
        return []

# ================================================================
#  MOTOR ESTADÍSTICO: BINOMIAL NEGATIVA
# ================================================================
def run_monte_carlo_v6(lambda_h, lambda_a, is_world_cup=False, team_h="", team_a=""):
    # Ajuste ADN Mundialista
    if is_world_cup:
        adn_h = ADN_MUNDIALISTA.get(team_h, ADN_MUNDIALISTA["DEFAULT"])
        adn_a = ADN_MUNDIALISTA.get(team_a, ADN_MUNDIALISTA["DEFAULT"])
        lambda_h = (lambda_h * 0.7) + (adn_h["gf"] * 0.3)
        lambda_a = (lambda_a * 0.7) + (adn_a["gf"] * 0.3)

    rng = np.random.default_rng()
    
    # Parámetros para Binomial Negativa (alpha controla la sobre-dispersión)
    # alpha alto = más varianza (fútbol irregular)
    alpha = 0.25 
    
    def simulate_nbinom(mu, size):
        if mu <= 0: mu = 0.1
        n = 1/alpha
        p = n/(n + mu)
        return rng.negative_binomial(n, p, size)

    hg = simulate_nbinom(lambda_h, N_SIM)
    ag = simulate_nbinom(lambda_a, N_SIM)
    
    return hg, ag

# ================================================================
#  INTERFACE & VALUE BET DETECTOR
# ================================================================
def calculate_ev(prob, odds):
    if not odds or odds == 0: return 0
    return (prob / 100) * odds

def display_investment_panel(prob_h, prob_d, prob_a, odds_h, odds_d, odds_a, bankroll):
    st.markdown("<div class='sec'>ANALISIS DE PROBABILIDAD DE INVERSIÓN</div>", unsafe_allow_html=True)
    
    cols = st.columns(3)
    outcomes = [
        ("LOCAL", prob_h, odds_h),
        ("EMPATE", prob_d, odds_d),
        ("VISITA", prob_a, odds_a)
    ]
    
    for i, (label, prob, odd) in enumerate(outcomes):
        ev = calculate_ev(prob, odd)
        is_value = ev > 1.05
        bg_color = "rgba(62,207,142,0.2)" if is_value else "transparent"
        border = "2px solid #3ecf8e" if is_value else "1px solid #1c1c32"
        
        # Kelly Criterion
        stake = 0
        if is_value:
            b = odd - 1
            p = prob / 100
            q = 1 - p
            f_star = (b * p - q) / b
            stake = f_star * bankroll * KELLY_FRAC

        cols[i].markdown(f"""
        <div style="background:{bg_color}; border:{border}; padding:15px; border-radius:10px; text-align:center;">
            <div style="font-size:0.8rem; color:#606080;">{label}</div>
            <div style="font-size:1.5rem; font-family:'Bebas Neue'; color:#f5c842;">{prob}%</div>
            <div style="font-size:0.9rem; margin-top:5px;">EV: {ev:.2f}</div>
            {f'<div style="color:#3ecf8e; font-weight:bold; font-size:0.8rem;">VALUE BET!</div>' if is_value else ''}
            <div style="font-size:0.7rem; color:#f4622a; margin-top:10px;">STAKE SUGERIDO: ${max(0, stake):.2f}</div>
        </div>
        """, unsafe_allow_html=True)

# [El resto del código integraría la carga de partidos y la interfaz Streamlit]
