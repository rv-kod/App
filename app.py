import streamlit as st
import google.generativeai as genai
import requests
import datetime
import math

# --- KONFIGURATION ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    # Vi använder 'gemini-1.5-flash-latest' vilket är den mest robusta adressen
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception as e:
    st.error("Kunde inte starta AI-modellen. Kontrollera din API-nyckel i Secrets.")
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

# --- UI DESIGN ---
st.set_page_config(page_title="MatchAnalys Pro", layout="wide")

st.title("⚽ Dagens Matcher & Analys")
st.write(f"Datum: **{datetime.date.today()}**")

# --- STEG 1: HÄMTA MATCHER ---
st.subheader("1. Välj Liga")
league = st.selectbox("Välj liga", ["Serie A", "La Liga", "Premier League", "Europa League", "Allsvenskan"])

if st.button(f"Visa matcher i {league}"):
    with st.spinner("Hämtar dagens schema..."):
        try:
            # En väldigt specifik prompt för att få listan exakt som du vill
            prompt = f"Vilka fotbollsmatcher spelas idag {datetime.date.today()} i {league}? Svara med en enkel lista där varje match står som: Lag - Lag. Svara 'Inga matcher' om det är tomt."
            response = model.generate_content(prompt)
            
            st.session_state.match_text = response.text
            # Dela upp texten till en lista för väljaren
            st.session_state.match_list = [line.strip() for line in response.text.split('\n') if "-" in line]
        except Exception as e:
            st.error(f"Kunde inte hämta matcher: {e}")

# Här visas listan snyggt
if "match_text" in st.session_state:
    st.markdown("---")
    st.markdown("### Matcher idag:")
    st.info(st.session_state.match_text)

# --- STEG 2: VÄLJ OCH ANALYSERA ---
st.markdown("---")
st.subheader("2. Analysera vald match")

if "match_list" in st.session_state and st.session_state.match_list:
    selected = st.selectbox("Vilken match vill du spela på?", st.session_state.match_list)
else:
    selected = st.text_input("Skriv match manuellt (t.ex. Torino - Parma):")

if selected:
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.write("**Sannolikhetskalkyl**")
        h_goal = st.number_input("Hemmalag (mål-snitt)", 0.0, 5.0, 1.5)
        a_goal = st.number_input("Bortalag (mål-snitt)", 0.0, 5.0, 1.2)
        h_p, d_p, a_p = calculate_poisson(h_goal, a_goal)
        st.metric("1", f"{h_p}%")
        st.metric("X", f"{d_p}%")
        st.metric("2", f"{a_p}%")

    with c2:
        if st.button("🤖 Hämta AI-Tips & Odds"):
            with st.spinner("Analyserar..."):
                analysis_prompt = f"Ge en kort bettinganalys för {selected}. Vad är marknadens odds och vad är ett bra speltips?"
                res = model.generate_content(analysis_prompt)
                st.session_state.current_analysis = res.text
                st.markdown(res.text)

# --- STEG 3: SKICKA ---
if "current_analysis" in st.session_state:
    if st.button("🚀 Skicka analysen till Telegram"):
        msg = f"⚽ *TIPS:* {selected}\n\n{st.session_state.current_analysis}"
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      json={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"})
        st.success("Analysen skickad!")
