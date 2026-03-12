import streamlit as st
import google.generativeai as genai
import requests
import datetime
import math

# --- KONFIGURATION ---
try:
    # Hämta API-nyckel
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    # VIKTIGT: Vi använder 'gemini-1.5-flash' eller 'gemini-1.5-flash-latest'
    # 'gemini-pro' fungerar också som fallback
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception as e:
    st.error(f"Konfigurationsfel: {e}")
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
st.caption(f"Status: Live | Datum: {datetime.date.today()}")

# --- STEG 1: HÄMTA MATCHER ---
st.header("1. Live Match-Scanner")
league = st.selectbox("Välj liga", ["Europa League", "Champions League", "Premier League", "Serie A", "La Liga", "Allsvenskan"])

if st.button(f"🔍 Fråga Gemini om matcher i {league}"):
    with st.spinner("Söker efter matcher..."):
        try:
            # Vi lägger till en tydligare instruktion för att undvika tomma svar
            prompt = f"Lista alla fotbollsmatcher som spelas idag {datetime.date.today()} i {league}. Svara endast med namnen på lagen i formatet: Hemmalag - Bortalag. En match per rad."
            response = model.generate_content(prompt)
            
            if response and response.text:
                matches = [line.strip() for line in response.text.split('\n') if "-" in line]
                if matches:
                    st.session_state.found_matches = matches
                else:
                    st.warning("Hittade inga matcher i texten. Prova att söka igen eller skriv manuellt.")
            else:
                st.error("Inget svar från Gemini. Prova igen.")
        except Exception as e:
            st.error(f"Ett fel uppstod vid sökning: {e}")

# Visa resultat
if "found_matches" in st.session_state and st.session_state.found_matches:
    selected_match = st.selectbox("Välj match att analysera:", st.session_state.found_matches)
else:
    selected_match = st.text_input("Eller skriv match manuellt (t.ex. Roma - Brighton):")

st.divider()

# --- STEG 2: DJUPANALYS ---
if selected_match:
    st.header(f"2. Analys: {selected_match}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📊 Sannolikhet")
        h_goal = st.slider("Förväntade mål (Hemma)", 0.0, 5.0, 1.5, 0.1)
        a_goal = st.slider("Förväntade mål (Borta)", 0.0, 5.0, 1.2, 0.1)
        h_p, d_p, a_p = calculate_poisson(h_goal, a_goal)
        
        st.metric("Hemmavinst", f"{h_p}%")
        st.metric("Oavgjort", f"{d_p}%")
        st.metric("Bortavinst", f"{a_p}%")

    with col2:
        st.subheader("🧠 Gemini Research")
        if st.button("Generera Speltips"):
            with st.spinner("Hämtar senaste infon..."):
                try:
                    analysis_prompt = f"Gör en snabb analys av {selected_match} i {league}. Vilka är oddsen? Finns det skador? Baserat på sannolikheten H:{h_p}% X:{d_p}% B:{a_p}%, vad är det bästa spelet?"
                    res = model.generate_content(analysis_prompt)
                    st.session_state.full_report = res.text
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Kunde inte generera analys: {e}")

    # --- STEG 3: TELEGRAM ---
    if "full_report" in st.session_state:
        st.divider()
        if st.button("🚀 Skicka till Telegram"):
            try:
                msg = f"♊ *GEMINI TIPS*\n\n*Match:* {selected_match}\n*Chans:* {h_p}% / {d_p}% / {a_p}%\n\n{st.session_state.full_report}"
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              json={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"})
                st.success("Analysen skickad!")
            except:
                st.error("Telegram-felet: Kontrollera dina Bot-inställningar.")
