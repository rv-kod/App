import streamlit as st
import google.generativeai as genai
import requests
import datetime
import math

# --- KONFIGURATION ---
# Vi sätter upp modellen direkt utan att "slösa" anrop i starten
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    # Vi använder 1.5-flash som är mest stabil för gratis-konton
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception as config_error:
    st.error(f"Kunde inte ladda konfiguration: {config_error}")
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
st.set_page_config(page_title="Gemini Betting Pro", layout="wide", page_icon="⚽")

st.title("⚽ Gemini Sports Intel")
st.caption(f"Datum: {datetime.date.today()}")

# --- STEG 1: HÄMTA MATCHER ---
st.header("1. Hitta Matcher")
league = st.selectbox("Välj liga", ["Europa League", "Champions League", "Premier League", "Serie A", "La Liga", "Allsvenskan"])

if st.button(f"🔍 Visa matcher i {league}"):
    with st.spinner("Söker... (Vänta ca 10 sek om det laggar)"):
        try:
            prompt = f"Vilka fotbollsmatcher spelas idag {datetime.date.today()} i {league}? Svara ENDAST med 'Hemmalag - Bortalag', en per rad."
            response = model.generate_content(prompt)
            
            if response.text:
                matches = [line.strip() for line in response.text.split('\n') if "-" in line]
                if matches:
                    st.session_state.found_matches = matches
                    st.success(f"Hittade {len(matches)} matcher!")
                else:
                    st.warning("Inga matcher hittades för idag. Skriv in manuellt nedan.")
        except Exception as e:
            if "429" in str(e):
                st.error("Kvoten är full! Vänta 60 sekunder innan du klickar igen.")
            else:
                st.error(f"Ett fel uppstod: {e}")

# Val av match
if "found_matches" in st.session_state and st.session_state.found_matches:
    selected_match = st.selectbox("Välj match:", st.session_state.found_matches)
else:
    selected_match = st.text_input("Skriv match manuellt (Hemma - Borta):")

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
        
        st.metric("1", f"{h_p}%")
        st.metric("X", f"{d_p}%")
        st.metric("2", f"{a_p}%")

    with col2:
        st.subheader("🧠 AI Research")
        if st.button("Hämta Tips & Odds"):
            with st.spinner("Gemini analyserar..."):
                try:
                    analysis_prompt = f"Gör en snabb bettinganalys av {selected_match}. Ge odds-förslag och kolla skador/form. Ge ett konkret speltips baserat på {h_p}% hemmavinst."
                    res = model.generate_content(analysis_prompt)
                    st.session_state.full_report = res.text
                    st.markdown(res.text)
                except Exception as e:
                    st.error("Kunde inte hämta analys (troligen kvot-begränsning). Vänta lite.")

    # --- STEG 3: TELEGRAM ---
    if "full_report" in st.session_state:
        st.divider()
        if st.button("🚀 Skicka till Telegram"):
            try:
                msg = f"⚽ *ANALYS*\n\n{st.session_state.full_report}"
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                              json={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"})
                st.success("Skickat!")
            except:
                st.error("Kunde inte skicka.")
