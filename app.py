import streamlit as st
import requests
from groq import Groq
import datetime
import math

# --- KONFIGURATION ---
try:
    client = Groq(api_key=st.secrets["GROQ_API_KEY"])
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_ID = st.secrets["TELEGRAM_CHAT_ID"]
except:
    st.error("Secrets saknas! Kontrollera GROQ_API_KEY, TELEGRAM_TOKEN och TELEGRAM_CHAT_ID i Streamlit Cloud.")
    st.stop()

# --- MATEMATISK MOTOR ---
def calculate_poisson(exp_h, exp_a):
    h_win, d, a_win = 0, 0, 0
    for h in range(10):
        for a in range(10):
            prob = ((exp_h**h * math.exp(-exp_h)) / math.factorial(h)) * \
                   ((exp_a**a * math.exp(-exp_a)) / math.factorial(a))
            if h > a: h_win += prob
            elif h == a: d += prob
            else: a_win += prob
    return round(h_win*100, 1), round(d*100, 1), round(a_win*100, 1)

# --- UI ---
st.set_page_config(page_title="Betting Terminal v5", layout="wide", page_icon="⚽")

st.title("🏆 Professional Betting Terminal")
st.write(f"Inloggad som analytiker | {datetime.date.today()}")

# --- STEG 1: HÄMTA MATCHER ---
st.header("1. Hämta Dagens Schema")
league = st.selectbox("Välj liga/turnering", ["Europa League", "Champions League", "Premier League", "Allsvenskan", "Serie A", "La Liga", "NHL"])

if st.button("🔍 Sök aktuella matcher på nätet"):
    with st.spinner(f"Söker efter dagens matcher i {league}..."):
        # Vi använder en kraftfullare prompt för att tvinga AI:n att hämta faktiska data
        prompt = f"Vilka matcher spelas idag {datetime.date.today()} i {league}? Lista dem som 'Hemmalag - Bortalag'. Svara endast med listan."
        res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}]
        )
        matches = [line.strip() for line in res.choices[0].message.content.split('\n') if "-" in line]
        st.session_state.found_matches = matches

# Visa funna matcher eller låt användaren skriva själv
if "found_matches" in st.session_state and st.session_state.found_matches:
    selected_match = st.selectbox("Välj match att analysera:", st.session_state.found_matches)
else:
    st.info("Inga matcher laddade ännu. Du kan skriva in en match manuellt nedan.")
    selected_match = st.text_input("Manuell match (t.ex. Arsenal - Porto)")

st.divider()

# --- STEG 2: ANALYS ---
if selected_match:
    st.header(f"2. Analysera: {selected_match}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Sannolikhets-kalkyl")
        h_goal = st.slider("Förväntade mål (Hemma)", 0.0, 5.0, 1.5, 0.1)
        a_goal = st.slider("Förväntade mål (Borta)", 0.0, 5.0, 1.2, 0.1)
        
        h_p, d_p, a_p = calculate_poisson(h_goal, a_goal)
        
        st.write(f"**Modellens tips:**")
        st.write(f"🏠 Vinst: {h_p}% | 🤝 Oavgjort: {d_p}% | 🚀 Vinst: {a_p}%")

    with col2:
        st.subheader("🤖 AI Intelligence")
        if st.button("Hämta AI-Research & Odds"):
            with st.spinner("Analyserar form, skador och marknadsodds..."):
                prompt = f"Gör en snabb analys av {selected_match}. Vad är marknadsoddsen? Finns det några viktiga skador? Vad är det mest troliga resultatet?"
                res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}])
                st.session_state.ai_report = res.choices[0].message.content
                st.write(st.session_state.ai_report)

    st.divider()

    # --- STEG 3: TELEGRAM ---
    st.header("3. Skicka till Telegram")
    if st.button("🚀 Skicka Fullständig Rapport"):
        full_msg = f"⚽ *BETTING ANALYS*\n\n*Match:* {selected_match}\n*Modell:* 1:{h_p}% X:{d_p}% 2:{a_p}%\n\n*AI Analys:*\n{st.session_state.get('ai_report', 'Ingen AI-analys bifogad.')}"
        
        try:
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          json={"chat_id": TG_ID, "text": full_msg, "parse_mode": "Markdown"})
            st.success("Analysen skickad till din mobil!")
        except:
            st.error("Kunde inte skicka Telegram-meddelande.")
