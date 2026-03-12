import streamlit as st
import pandas as pd
import numpy as np
import requests
from scipy.stats import poisson
import matplotlib.pyplot as plt
from groq import Groq

# --- KONFIGURATION ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("GROQ_API_KEY saknas i Secrets!")
    st.stop()

# --- DATA-HÄMTNING (Automatiserad CSV) ---
@st.cache_data(ttl=3600)
def load_football_data(league_code):
    # Vi hämtar data från Football-Data.co.uk för säsongen 25/26
    url = f"https://www.football-data.co.uk/mmz4281/2526/{league_code}.csv"
    try:
        df = pd.read_csv(url)
        # Behåll bara relevanta kolumner
        cols = ['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'B365H', 'B365D', 'B365A']
        return df[cols].dropna()
    except:
        st.error(f"Kunde inte hämta data för {league_code}")
        return pd.DataFrame()

# --- MATEMATISK MODELL (Poisson) ---
def predict_match(home_team, away_team, df):
    # Räkna ut snittmål för ligan
    avg_home_goals = df['FTHG'].mean()
    avg_away_goals = df['FTAG'].mean()

    # Hemmalagets styrka
    home_attack = df[df['HomeTeam'] == home_team]['FTHG'].mean() / avg_home_goals
    home_defense = df[df['HomeTeam'] == home_team]['FTAG'].mean() / avg_away_goals
    
    # Bortalagets styrka
    away_attack = df[df['AwayTeam'] == away_team]['FTAG'].mean() / avg_away_goals
    away_defense = df[df['AwayTeam'] == away_team]['FTHG'].mean() / avg_home_goals

    # Förväntade mål (Lambda)
    exp_home = home_attack * away_defense * avg_home_goals
    exp_away = away_attack * home_defense * avg_away_goals

    # Skapa sannolikhetsmatris (max 5 mål per lag)
    probs = np.outer(poisson.pmf(range(6), exp_home), poisson.pmf(range(6), exp_away))
    
    home_win = np.sum(np.tril(probs, -1))
    draw = np.sum(np.diag(probs))
    away_win = np.sum(np.triu(probs, 1))
    
    return round(home_win*100, 1), round(draw*100, 1), round(away_win*100, 1), exp_home, exp_away

# --- DESIGN & UI ---
st.set_page_config(page_title="Sport Terminal", layout="wide")
st.markdown("""<style>.stMetric { background-color: #1a1c24; border: 1px solid #30363d; border-radius: 10px; padding: 15px; }</style>""", unsafe_allow_html=True)

# Navigation
with st.sidebar:
    st.title("⚽ Sport Intel")
    page = st.radio("Meny", ["Marknadsanalys", "Match-Scanner", "AI Strategi"])
    st.divider()
    league = st.selectbox("Välj Liga", ["Premier League (E0)", "Bundesliga (D1)", "La Liga (SP1)", "Serie A (I1)"])
    league_code = league.split("(")[1].replace(")", "")

df_league = load_football_data(league_code)

# --- 1. MARKNADSANALYS ---
if page == "Marknadsanalys":
    st.title(f"🏛 {league.split('(')[0]} Intelligence")
    
    if not df_league.empty:
        # Visa senaste resultaten
        st.subheader("Senaste Matcherna")
        st.dataframe(df_league.tail(5), use_container_width=True)
        
        # Enkel tabell-logik
        teams = sorted(df_league['HomeTeam'].unique())
        st.subheader("Analys-verktyg")
        c1, c2 = st.columns(2)
        h_team = c1.selectbox("Hemmalag", teams)
        a_team = c2.selectbox("Bortalag", teams, index=1)
        
        if st.button("🔥 Beräkna Odds", type="primary"):
            h_p, d_p, a_p, exH, exA = predict_match(h_team, a_team, df_league)
            
            m1, m2, m3 = st.columns(3)
            m1.metric(f"Vinst {h_team}", f"{h_p}%")
            m2.metric("Oavgjort", f"{d_p}%")
            m3.metric(f"Vinst {a_team}", f"{a_p}%")
            
            st.write(f"**Förväntat resultat:** {round(exH, 1)} - {round(exA, 1)}")

# --- 2. MATCH-SCANNER (Value Finder) ---
elif page == "Match-Scanner":
    st.title("🔍 Value Scanner")
    st.info("Letar efter 'Edge' (där vår modell ger högre sannolikhet än marknadens odds)")
    
    if not df_league.empty:
        # I en riktig app skulle vi hämta kommande matcher här. 
        # Här demonstrerar vi principen på senaste matcherna:
        results = []
        teams = df_league['HomeTeam'].unique()
        
        # Exempel på scanning
        for i in range(len(df_league.tail(10))):
            row = df_league.iloc[-(i+1)]
            h_p, d_p, a_p, _, _ = predict_match(row['HomeTeam'], row['AwayTeam'], df_league)
            
            # Beräkna marknadens sannolikhet från odds (1/odds)
            mkt_h = (1/row['B365H']) * 100
            edge = h_p - mkt_h
            
            if edge > 5: # Om vi ser 5% mer chans än spelbolaget
                results.append({"Match": f"{row['HomeTeam']} - {row['AwayTeam']}", "Vår %": h_p, "Marknad %": round(mkt_h, 1), "Edge": round(edge, 1)})
        
        st.table(results)

# --- 3. AI STRATEGI ---
elif page == "AI Strategi":
    st.title("🤖 AI Sports Analyst")
    
    context = df_league.tail(20).to_string()
    q = st.chat_input("Fråga om form, skador eller betting-strategi...")
    
    if q:
        with st.chat_message("user"): st.write(q)
        prompt = f"Du är en expert på sportbetting. Här är senaste data från ligan:\n{context}\n\nAnvändare frågar: {q}"
        
        res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
        with st.chat_message("assistant"): st.write(res.choices[0].message.content)
