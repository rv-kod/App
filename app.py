import streamlit as st
import google.generativeai as genai
import requests
import datetime
import math

# --- KONFIGURATION ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_ID = st.secrets["TELEGRAM_CHAT_ID"]
except:
    st.error("Secrets saknas! Kontrollera GEMINI_API_KEY och Telegram-info i Streamlit.")
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
st.set_page_config(page_title="Gemini Betting Intel", layout="wide", page_icon="♊")

st.title("♊ Gemini AI Sports Terminal")
st.caption(f"Drivs av Google Gemini | {datetime.date.today()}")

# --- STEG 1: HÄMTA MATCHER ---
st.header("1. Live Match-Scanner")
league = st.selectbox("Välj liga", ["Europa League", "Champions League", "Premier League", "Serie A", "La Liga", "Allsvenskan"])

if st.button(f"🔍 Fråga Gemini om dagens matcher i {league}"):
    with st.spinner("Gemini söker på nätet..."):
        prompt = f"Vilka matcher spelas idag {datetime.date.today()} i {league}? Svara med en enkel lista: 'Hemmalag - Bortalag'. Om inga matcher spelas, säg det."
        response = model.generate_content(prompt)
        matches = [line.strip() for line in response.text.split('\n') if "-" in line]
        st.session_state.found_matches = matches

if "found_matches" in st.session_state and st.session_state.found_matches:
    selected_match = st.selectbox("Välj match att analysera:", st.session_state.found_matches)
else:
    selected_match = st.text_input("Eller skriv match manuellt:", placeholder="Lag A - Lag B")

st.divider()

# --- STEG 2: DJUPANALYS ---
if selected_match:
    st.header(f"2. Intelligens-analys: {selected_match}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📊 Sannolikhet")
        h_goal = st.slider("Förväntade mål (Hemma)", 0.0, 5.0, 1.5)
        a_goal = st.slider("Förväntade mål (Borta)", 0.0, 5.0, 1.2)
        h_p, d_p, a_p = calculate_poisson(h_goal, a_goal)
        
        st.metric("Hemmavinst", f"{h_p}%")
        st.metric("Oavgjort", f"{d_p}%")
        st.metric("Bortavinst", f"{a_p}%")

    with col2:
        st.subheader("🧠 Gemini Live Research")
        if st.button("Hämta Live-analys & Odds"):
            with st.spinner("Gemini analyserar marknaden..."):
                analysis_prompt = f"""
                Gör en professionell betting-analys för {selected_match} ({league}) idag.
                1. Sök efter aktuella marknadsodds (1X2).
                2. Kolla senaste skador och startelvor.
                3. Beräkna 'Value': Om vår modell säger {h_p}% vinst för hemmalaget, är oddset spelvärt?
                4. Ge ett konkret speltips.
                """
                res = model.generate_content(analysis_prompt)
                st.session_state.full_report = res.text
                st.markdown(res.text)

    # --- STEG 3: TELEGRAM ---
    if "full_report" in st.session_state:
        st.divider()
        if st.button("🚀 Skicka rapport till Telegram"):
            msg = f"♊ *GEMINI ANALYS*\n\n*Match:* {selected_match}\n*Modell:* 1:{h_p}% X:{d_p}% 2:{a_p}%\n\n{st.session_state.full_report}"
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          json={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"})
            st.success("Skickat!")
