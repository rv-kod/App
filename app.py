import streamlit as st
import pandas as pd
import numpy as np
from scipy.stats import poisson
from groq import Groq

# --- KONFIGURATION ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
except:
    st.error("GROQ_API_KEY saknas i Secrets!")
    st.stop()

# --- DATA-HÄMTNING ---
@st.cache_data(ttl=3600)
def load_data(league_id):
    if league_id == "SHL":
        # Hämtar historisk SHL-data (exempelkälla för hockey)
        url = "https://raw.githubusercontent.com/frenberg/shl-stats/master/data/shl_results.csv"
        try:
            df = pd.read_csv(url)
            # Anpassa kolumner för hockey-format
            df = df.rename(columns={'home_team': 'HomeTeam', 'away_team': 'AwayTeam', 'home_goals': 'FTHG', 'away_goals': 'FTAG'})
            return df
        except:
            return pd.DataFrame()
    else:
        # Fotbollsdata (Europa-cuperna ligger ofta i egna filer, här kör vi de stora ligorna + placeholder för cup)
        urls = {
            "CL": "https://www.football-data.co.uk/mmz4281/2425/E0.csv", # Placeholder: CL kräver ofta betal-API, vi använder PL som demo
            "EL": "https://www.football-data.co.uk/mmz4281/2425/E1.csv",
            "E0": "https://www.football-data.co.uk/mmz4281/2425/E0.csv"
        }
        url = urls.get(league_id, urls["E0"])
        try:
            df = pd.read_csv(url)
            return df[['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']].dropna()
        except:
            return pd.DataFrame()

# --- ANALYS-MOTOR ---
def predict_match(home_team, away_team, df):
    avg_home_goals = df['FTHG'].mean()
    avg_away_goals = df['FTAG'].mean()

    def get_strength(team, col_goals, col_opp, is_home):
        games = df[(df['HomeTeam'] == team) if is_home else (df['AwayTeam'] == team)]
        if games.empty: return 1.0
        return games[col_goals].mean() / (avg_home_goals if is_home else avg_away_goals)

    h_att = get_strength(home_team, 'FTHG', 'FTAG', True)
    h_def = get_strength(home_team, 'FTAG', 'FTHG', True)
    a_att = get_strength(away_team, 'FTAG', 'FTHG', False)
    a_def = get_strength(away_team, 'FTHG', 'FTAG', False)

    exp_home = h_att * a_def * avg_home_goals
    exp_away = a_att * h_def * avg_away_goals

    probs = np.outer(poisson.pmf(range(10), exp_home), poisson.pmf(range(10), exp_away))
    return round(np.sum(np.tril(probs, -1))*100, 1), round(np.sum(np.diag(probs))*100, 1), round(np.sum(np.triu(probs, 1))*100, 1), exp_home, exp_away

# --- UI ---
st.set_page_config(page_title="Sport Terminal Pro", layout="wide")

with st.sidebar:
    st.title("🏆 Sport Terminal")
    category = st.selectbox("Välj Liga/Turnering", [
        "SHL (Sverige)", 
        "Champions League", 
        "Europa League", 
        "Conference League",
        "Premier League"
    ])
    
    # Mappa val till kod
    mapping = {"SHL (Sverige)": "SHL", "Champions League": "CL", "Europa League": "EL", "Premier League": "E0"}
    league_code = mapping.get(category, "E0")

df = load_data(league_code)

if not df.empty:
    st.title(f"Analys: {category}")
    
    teams = sorted(list(set(df['HomeTeam'].unique()) | set(df['AwayTeam'].unique())))
    
    col1, col2 = st.columns(2)
    t1 = col1.selectbox("Hemmalag", teams)
    t2 = col2.selectbox("Bortalag", teams, index=1)
    
    if st.button("Kör Sannolikhetsanalys", type="primary"):
        hw, d, aw, exH, exA = predict_match(t1, t2, df)
        
        cols = st.columns(3)
        cols[0].metric(t1, f"{hw}%")
        cols[1].metric("Oavgjort", f"{d}%")
        cols[2].metric(t2, f"{aw}%")
        
        st.subheader(f"🤖 AI Kommentar")
        prompt = f"Analysera en match i {category} mellan {t1} och {t2}. Sannolikhet: {t1} {hw}%, Oavgjort {d}%, {t2} {aw}%. Förväntat antal mål: {round(exH+exA, 2)}. Ge ett kort speltips."
        
        try:
            res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
            st.info(res.choices[0].message.content)
        except:
            st.write("AI-tjänsten är upptagen, försök igen senare.")
else:
    st.warning("Kunde inte hämta data för denna kategori just nu.")
