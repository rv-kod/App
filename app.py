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
    st.error("Secrets saknas i Streamlit Cloud!")
    st.stop()

# --- SCRAPER FUNKTION (FÖRBÄTTRAD) ---
def get_matches_safe():
    # Vi testar en annan källa som ofta är mer öppen för enkla anrop
    url = "https://www.forebet.com/en/football-tips-and-predictions-for-today"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        matches = []
        
        # Forebet-specifik skrapning
        for row in soup.select('.predict_row'):
            try:
                home = row.select_one('.homeTeam span').text.strip()
                away = row.select_one('.awayTeam span').text.strip()
                league = row.select_one('.short_league').text.strip()
                # Prediction/Procent (ex: 1, X, 2)
                pred = row.select_one('.pred_res').text.strip()
                
                matches.append({
                    "Liga": league,
                    "Match": f"{home} - {away}",
                    "Tips": pred,
                    "Home": home,
                    "Away": away
                })
            except: continue
        return matches
    except:
        return []

# --- UI DESIGN ---
st.set_page_config(page_title="Football Terminal v2", layout="wide")

if 'saved' not in st.session_state: st.session_state.saved = []

st.title("⚽ Football Intelligence Terminal")

# --- NAVIGATION ---
menu = st.tabs(["📅 Dagens Matcher", "✍️ Manuell Analys", "⭐ Sparade"])

# TAB 1: AUTOMATISK HÄMTNING
with menu[0]:
    if st.button("🔄 Hämta Matcher Nu"):
        with st.spinner("Surfar efter matcher..."):
            matches = get_matches_safe()
            st.session_state.daily_matches = matches
    
    if 'daily_matches' in st.session_state and st.session_state.daily_matches:
        for m in st.session_state.daily_matches:
            with st.container():
                c1, c2, c3 = st.columns([3, 1, 1])
                c1.write(f"**{m['Match']}** ({m['Liga']})")
                c1.caption(f"Tips: {m['Tips']}")
                
                if c2.button("🤖 Analysera", key=f"ai_{m['Match']}"):
                    prompt = f"Gör en snabb bettinganalys: {m['Match']}. Tips: {m['Tips']}. Ge ett proffstips."
                    res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user", "content":prompt}])
                    st.info(res.choices[0].message.content)
                
                if c3.button("⭐ Spara", key=f"s_{m['Match']}"):
                    st.session_state.saved.append(m['Match'])
                    st.toast("Sparad!")
                st.divider()
    else:
        st.info("Klicka på knappen ovan för att skrapa dagens matcher. Om det misslyckas, använd 'Manuell Analys'.")

# TAB 2: MANUELL INMATNING (Säkerhetsnätet)
with menu[1]:
    st.subheader("Skriv in match själv för AI-analys")
    m_home = st.text_input("Hemmalag")
    m_away = st.text_input("Bortalag")
    m_league = st.selectbox("Liga", ["Premier League", "Serie A", "La Liga", "Bundesliga", "Champions League", "Europa League"])
    
    if st.button("Generera AI-Rapport"):
        if m_home and m_away:
            with st.spinner("AI-Boten tänker..."):
                prompt = f"Analysera matchen {m_home} vs {m_away} i {m_league}. Kolla form, skador och ge ett speltips."
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user", "content":prompt}])
                analysis = res.choices[0].message.content
                st.success("Analys Klar!")
                st.markdown(analysis)
                
                if st.button("✈️ Skicka till Telegram"):
                    msg = f"⚽ *MANUELL ANALYS*\n{m_home} vs {m_away}\n\n{analysis}"
                    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"})
                    st.toast("Skickat!")
        else:
            st.warning("Fyll i båda lagen.")

# TAB 3: SPARADE
with menu[2]:
    if st.session_state.saved:
        for s in st.session_state.saved:
            st.write(f"✅ {s}")
        if st.button("Rensa listan"):
            st.session_state.saved = []
            st.rerun()
    else:
        st.write("Inga matcher sparade ännu.")
