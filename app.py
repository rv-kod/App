import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from groq import Groq
import datetime

# --- KONFIGURATION ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_ID = st.secrets["TELEGRAM_CHAT_ID"]
except:
    st.error("Secrets saknas i Streamlit Cloud (GROQ_API_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)!")
    st.stop()

# --- FUNKTIONER ---
def get_ai_analysis(home, away, league, deep_search=False):
    """Genererar analys med Llama-3.1. Deep search simulerar en djupare research-agent."""
    
    context_prompt = "Du är en professionell betting-analytiker med tillgång till realtidsstatistik."
    if deep_search:
        context_prompt += " Gör en extra djup analys av startelvor, väderförhållanden, skador och historiska möten (H2H)."

    prompt = f"""
    {context_prompt}
    Analysera matchen: {home} vs {away} i {league}.
    Datum för analys: {datetime.date.today()}
    
    Strukturera svaret så här:
    1. **Formkollen**: Senaste 5 matcherna för båda lagen.
    2. **Nyckelinfo**: Skador eller avstängningar.
    3. **Speltips**: Rekommenderat spel med motivering (t.ex. 'Över 2.5 mål' eller 'Asian Handicap').
    4. **Sannolikhet**: Ge din uppskattade procentchans för 1, X och 2.
    """
    
    try:
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Analysera sportdata objektivt."},
                      {"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content
    except Exception as e:
        return f"Kunde inte generera analys: {e}"

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {"chat_id": TG_ID, "text": text, "parse_mode": "Markdown"}
    return requests.post(url, json=payload)

# --- UI DESIGN ---
st.set_page_config(page_title="Sport Intel Terminal Pro", layout="wide", page_icon="⚽")

# CSS för terminal-känsla
st.markdown("""
    <style>
    .report-box { background-color: #0e1117; border: 1px solid #30363d; padding: 20px; border-radius: 10px; }
    .stButton>button { width: 100%; }
    </style>
""", unsafe_allow_html=True)

st.title("⚽ Sport Intelligence Terminal v3")
st.caption(f"Status: Ansluten till Llama-3.1 API | {datetime.date.today()}")

tabs = st.tabs(["🎯 Manuell Deep-Analysis", "⭐ Sparade Strategier"])

# --- TAB 1: AVANCERAD ANALYS ---
with tabs[0]:
    c1, c2, c3 = st.columns(3)
    with c1:
        home_team = st.text_input("Hemmalag", placeholder="t.ex. Arsenal")
    with c2:
        away_team = st.text_input("Bortalag", placeholder="t.ex. Liverpool")
    with c3:
        league = st.selectbox("Liga", ["Premier League", "Serie A", "La Liga", "Bundesliga", "Ligue 1", "Champions League", "Allsvenskan"])

    col_btn1, col_btn2 = st.columns(2)
    
    run_standard = col_btn1.button("📊 Standard Analys")
    run_deep = col_btn2.button("🔥 Deep Intelligence Search", type="primary")

    if run_standard or run_deep:
        if home_team and away_team:
            with st.spinner("Hämtar data och genererar rapport..."):
                analysis = get_ai_analysis(home_team, away_team, league, deep_search=run_deep)
                
                st.markdown("---")
                st.markdown(f"### 📋 Analysrapport: {home_team} - {away_team}")
                st.markdown(f"<div class='report-box'>{analysis}</div>", unsafe_allow_html=True)
                
                # Action buttons
                st.write("")
                ca, cb = st.columns(2)
                if ca.button("✈️ Skicka till Telegram"):
                    tg_msg = f"⚽ *NY ANALYS*\n\n{analysis}"
                    send_to_telegram(tg_msg)
                    st.success("Skickat till Telegram!")
                
                if cb.button("💾 Spara Analys"):
                    if 'history' not in st.session_state: st.session_state.history = []
                    st.session_state.history.append(f"{home_team}-{away_team} ({datetime.date.today()})")
                    st.toast("Sparad i historik!")
        else:
            st.warning("Vänligen fyll i båda lagen för att starta analysen.")

# --- TAB 2: HISTORIK ---
with tabs[1]:
    st.subheader("Tidigare analyserade matcher")
    if 'history' in st.session_state and st.session_state.history:
        for item in st.session_state.history:
            st.write(f"• {item}")
        if st.button("Rensa historik"):
            st.session_state.history = []
            st.rerun()
    else:
        st.info("Din historik är tom.")
