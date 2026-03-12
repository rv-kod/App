import streamlit as st
import pandas as pd
import requests
from groq import Groq
import datetime

# --- KONFIGURATION ---
# Din RapidAPI-nyckel som du skickade
RAPID_KEY = "6f284e1b80mshe8e1f0c239f60d6p1df8a1jsn818617882208"

try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    # Telegram-info från dina secrets
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_ID = st.secrets["TELEGRAM_CHAT_ID"]
except:
    st.error("GROQ_API_KEY eller Telegram-secrets saknas i Streamlit Cloud!")
    st.stop()

# --- API FUNKTIONER ---
def get_football_predictions():
    # Vi använder /predictions för att få dagens matcher
    url = "https://today-football-prediction.p.rapidapi.com/predictions/"
    headers = {
        "x-rapidapi-key": RAPID_KEY,
        "x-rapidapi-host": "today-football-prediction.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Fel: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Kunde inte ansluta: {e}")
        return None

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_ID, "text": message, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

# --- UI DESIGN ---
st.set_page_config(page_title="Football Intel Pro", layout="wide")

if 'saved_matches' not in st.session_state:
    st.session_state.saved_matches = []

st.title("⚽ Football Prediction Terminal")
st.write(f"Datum: {datetime.date.today()}")

# --- SIDOMENY ---
with st.sidebar:
    st.header("⭐ Sparade Matcher")
    if st.session_state.saved_matches:
        for m in st.session_state.saved_matches:
            st.write(f"• {m}")
        if st.button("Rensa listan"):
            st.session_state.saved_matches = []
            st.rerun()
    else:
        st.write("Inga sparade matcher.")

# --- HÄMTA DATA ---
if st.button("🔄 Uppdatera Dagens Matcher", type="primary"):
    st.rerun()

data = get_football_predictions()

if data and 'data' in data:
    # Ligor vi vill bevaka
    top_leagues = ["Premier League", "Serie A", "La Liga", "Bundesliga", "Champions League", "Europa League"]
    
    for match in data['data']:
        league = match.get('league_name', 'Unknown')
        
        # Filtrera (Valfritt: Ta bort if-satsen om du vill se ALLA ligor)
        if any(l in league for l in top_leagues):
            home = match.get('home_team')
            away = match.get('away_team')
            prediction = match.get('prediction')
            prob = match.get('probability', {})
            
            with st.expander(f"🏟 {home} vs {away} ({league})"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Tips:** {prediction}")
                    if prob:
                        st.write(f"Sannolikhet: H({prob.get('1')}% ) X({prob.get('x')}% ) B({prob.get('2')}% )")
                
                with col2:
                    if st.button("⭐ Spara", key=f"sv_{home}"):
                        st.session_state.saved_matches.append(f"{home}-{away}")
                        st.toast("Sparad till listan!")
                
                with col3:
                    if st.button("🤖 AI Analys", key=f"ai_{home}"):
                        prompt = f"Analysera matchen {home} vs {away} i {league}. Tips: {prediction}. Sannolikheter: {prob}. Ge ett kort proffstips."
                        analysis = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=[{"role": "user", "content": prompt}]
                        ).choices[0].message.content
                        
                        st.info(analysis)
                        
                        # Skicka till Telegram-knapp
                        if st.button("✈️ Skicka till Telegram", key=f"tg_{home}"):
                            msg = f"🔥 *MATCHANALYS*\n\n{home} vs {away}\nTips: {prediction}\n\n{analysis}"
                            send_telegram(msg)
                            st.success("Skickat till mobilen!")
                
                st.divider()
else:
    st.info("Inga matcher hittades för tillfället. Försök igen om en stund.")
