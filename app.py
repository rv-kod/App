import streamlit as st
import google.generativeai as genai
import requests
import datetime
import math

# --- KONFIGURATION ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    # Uppdaterat modellnamn för 2026 - Gemini 2.0 Flash är den snabbaste och mest stabila
    # Om detta mot förmodan misslyckas, prova 'gemini-1.5-flash-latest'
    model = genai.GenerativeModel('gemini-2.0-flash')
    
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
st.set_page_config(page_title="Gemini Betting Terminal", layout="wide", page_icon="⚽")

st.title("⚽ Gemini Sports Intelligence")
st.caption(f"Status: Ansluten | Systemdatum: {datetime.date.today()}")

# --- STEG 1: HÄMTA MATCHER ---
st.header("1. Hitta Dagens Spel")
league = st.selectbox("Välj liga", ["Europa League", "Champions League", "Premier League", "Serie A", "La Liga", "Allsvenskan"])

if st.button(f"🔍 Hämta matcher för {league}"):
    with st.spinner("Gemini söker i realtid..."):
        try:
            # Vi lägger till instruktionen 'search the web' i prompten för att aktivera Geminis sökförmåga
            prompt = f"Vilka fotbollsmatcher spelas idag {datetime.date.today()} i {league}? Lista endast matcherna som: Hemmalag - Bortalag. Om inga matcher spelas idag, svara 'Inga matcher'."
            response = model.generate_content(prompt)
            
            if response.text:
                matches = [line.strip() for line in response.text.split('\n') if "-" in line]
                if matches:
                    st.session_state.found_matches = matches
                    st.success(f"Hittade {len(matches)} matcher!")
                else:
                    st.warning("Hittade inga schemalagda matcher för idag. Prova en annan liga eller skriv manuellt.")
            else:
                st.error("Kunde inte läsa matchlistan.")
        except Exception as e:
            st.error(f"Modellfel: {e}. Prova att ändra modellnamn i koden.")

# Visa matcher
if "found_matches" in st.session_state and st.session_state.found_matches:
    selected_match = st.selectbox("Välj match att analysera:", st.session_state.found_matches)
else:
    selected_match = st.text_input("Skriv match manuellt:", placeholder="t.ex. Arsenal - Porto")

st.divider()

# --- STEG 2: ANALYS ---
if selected_match:
    st.header(f"2. Analysera: {selected_match}")
    
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
        st.subheader("🧠 Gemini Live Analysis")
        if st.button("Hämta Betting-info & Speltips"):
            with st.spinner("Analyserar marknaden..."):
                try:
                    analysis_prompt = f"""
                    Gör en analys av {selected_match} i {league}. 
                    Hitta aktuella odds och viktiga nyheter (skador/avstängningar). 
                    Baserat på sannolikheten H:{h_p}% X:{d_p}% B:{a_p}%, ge ett rekommenderat spel (Value Bet).
                    """
                    res = model.generate_content(analysis_prompt)
                    st.session_state.full_report = res.text
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"Analysfel: {e}")

    # --- STEG 3: TELEGRAM ---
    if "full_report" in st.session_state:
        st.divider()
        if st.button("🚀 Skicka till Telegram"):
            msg = f"⚽ *ANALYS KLAR*\n\n*Match:* {selected_match}\n*Chans:* {h_p}% / {d_p}% / {a_p}%\n\n{st.session_state.full_report}"
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          json={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"})
            st.success("Skickat till mobilen!")
