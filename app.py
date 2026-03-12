import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from groq import Groq
import datetime

# --- KONFIGURATION ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("GROQ_API_KEY saknas i Secrets!")
    st.stop()

# --- DATA-FUNKTIONER ---
@st.cache_data(ttl=3600)
def load_data(league):
    # Källor för historisk data (för att räkna ut styrka)
    sources = {
        "Premier League": "https://www.football-data.co.uk/mmz4281/2425/E0.csv",
        "SHL": "https://raw.githubusercontent.com/frenberg/shl-stats/master/data/shl_results.csv", # Historik
        "Champions League": "https://www.football-data.co.uk/mmz4281/2425/E0.csv" # Placeholder
    }
    
    try:
        df = pd.read_csv(sources.get(league))
        # Standardisera SHL-kolumner om det är hockey
        if league == "SHL":
            df = df.rename(columns={'home_team': 'HomeTeam', 'away_team': 'AwayTeam', 'home_goals': 'FTHG', 'away_goals': 'FTAG'})
        return df
    except:
        return pd.DataFrame()

def get_poisson_probs(home_team, away_team, df):
    # Beräkna genomsnitt
    avg_home_g = df['FTHG'].mean()
    avg_away_g = df['FTAG'].mean()
    
    # Styrka (baserat på senaste 20 matcherna för bättre form-koll)
    def team_strength(team, is_home):
        side = 'HomeTeam' if is_home else 'AwayTeam'
        goal_col = 'FTHG' if is_home else 'FTAG'
        against_col = 'FTAG' if is_home else 'FTHG'
        
        team_df = df[(df[side] == team)].tail(10)
        if team_df.empty: return 1.0, 1.0
        
        att = team_df[goal_col].mean() / (avg_home_g if is_home else avg_away_g)
        defen = team_df[against_col].mean() / (avg_away_g if is_home else avg_home_g)
        return att, defen

    h_att, h_def = team_strength(home_team, True)
    a_att, a_def = team_strength(away_team, False)
    
    exp_h = h_att * a_def * avg_home_g
    exp_a = a_att * h_def * avg_away_g
    
    # Sannolikheter
    h_probs = [poisson.pmf(i, exp_h) for i in range(10)]
    a_probs = [poisson.pmf(i, exp_a) for i in range(10)]
    
    matrix = np.outer(h_probs, a_probs)
    
    win = np.sum(np.tril(matrix, -1))
    draw = np.sum(np.diag(matrix))
    loss = np.sum(np.triu(matrix, 1))
    
    return win, draw, loss, exp_h, exp_a

# --- UI DESIGN ---
st.set_page_config(page_title="Sport Terminal Pro", layout="wide")
st.title("🏆 Betting Intelligence Terminal")

with st.sidebar:
    st.header("Inställningar")
    valda_ligor = st.multiselect("Välj ligor att bevaka", 
                                ["Premier League", "SHL", "Champions League"],
                                default=["Premier League", "SHL"])
    st.divider()
    st.write("Dagens datum:", datetime.date.today())

# --- HUVUDSIDA ---
tabs = st.tabs(["📅 Dagens Matcher", "📊 Djupanalys", "🤖 AI Strategi"])

# TAB 1: DAGENS MATCHER (Simulerad lista baserat på data)
with tabs[0]:
    st.subheader("Dagens Spelförslag & Analys")
    
    all_predictions = []
    
    for league in valda_ligor:
        data = load_data(league)
        if not data.empty:
            teams = sorted(data['HomeTeam'].unique())
            # Vi slumpar fram 2 "kommande" matcher för demo-syfte 
            # (Riktiga API:er krävs för exakt dagsschema)
            m1, m2 = teams[0], teams[-1]
            m3, m4 = teams[1], teams[-2]
            
            for h, a in [(m1, m2), (m3, m4)]:
                w, d, l, eh, ea = get_poisson_probs(h, a, data)
                all_predictions.append({
                    "Liga": league,
                    "Match": f"{h} vs {a}",
                    "Vinst %": f"{round(w*100,1)}%",
                    "Oavgjort %": f"{round(d*100,1)}%",
                    "Förlust %": f"{round(l*100,1)}%",
                    "Väntat mål": f"{round(eh,1)}-{round(ea,1)}"
                })
    
    st.table(all_predictions)

# TAB 2: DJUPANALYS
with tabs[1]:
    league_choice = st.selectbox("Välj liga för analys", valda_ligor)
    data = load_data(league_choice)
    
    if not data.empty:
        teams = sorted(list(set(data['HomeTeam'].unique())))
        c1, c2 = st.columns(2)
        home = c1.selectbox("Hemmalag", teams, key="h1")
        away = c2.selectbox("Bortalag", teams, key="a1")
        
        if st.button("Generera Full Analys"):
            w, d, l, eh, ea = get_poisson_probs(home, away, data)
            
            col1, col2, col3 = st.columns(3)
            col1.metric(home, f"{round(w*100,1)}%", "Hemmaseger")
            col2.metric("Oavgjort", f"{round(d*100,1)}%")
            col3.metric(away, f"{round(l*100,1)}%", "Bortaseger")
            
            # AI-Analys
            prompt = f"""Analysera matchen {home} mot {away} i {league_choice}. 
            Våra beräkningar säger: {home} vinner med {round(w*100)}% sannolikhet. 
            Väntat resultat: {round(eh,1)} - {round(ea,1)}. 
            Ge ett kort, professionellt speltips baserat på sannolikheten."""
            
            with st.spinner("AI Analyserar..."):
                response = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
                st.info(response.choices[0].message.content)

# TAB 3: AI STRATEGI
with tabs[2]:
    st.subheader("Fråga AI om Betting")
    user_q = st.chat_input("T.ex: Hur ska jag spela på SHL ikväll?")
    if user_q:
        st.write(f"USER: {user_q}")
        res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": user_q}])
        st.write(f"AI: {res.choices[0].message.content}")
