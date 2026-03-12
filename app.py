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
    st.error("Secrets saknas! Kontrollera GROQ_API_KEY, TELEGRAM_TOKEN och TELEGRAM_CHAT_ID.")
    st.stop()

# --- MATEMATISK MOTOR ---
def calculate_poisson_probability(exp_h, exp_a):
    home_win, draw, away_win = 0, 0, 0
    for h in range(10):
        for a in range(10):
            prob = ((exp_h**h * math.exp(-exp_h)) / math.factorial(h)) * \
                   ((exp_a**a * math.exp(-exp_a)) / math.factorial(a))
            if h > a: home_win += prob
            elif h == a: draw += prob
            else: away_win += prob
    return round(home_win*100, 1), round(draw*100, 1), round(away_win*100, 1)

# --- AI-FUNKTIONER ---
def fetch_real_fixtures(league):
    """Hämtar dagens faktiska matcher via AI-research"""
    prompt = f"Vilka matcher spelas idag {datetime.date.today()} i {league}? Svara endast med matcherna på varsin rad, t.ex: Lag A - Lag B. Om du är osäker, nämn de mest sannolika stormatcherna."
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return [line.strip() for line in res.choices[0].message.content.split('\n') if "-" in line]

def get_market_odds(match_name):
    """Hämtar uppskattade odds för vald match"""
    prompt = f"Ge aktuella marknadsodds (1, X, 2) för matchen {match_name}. Svara kort."
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content

# --- UI ---
st.set_page_config(page_title="Sport Intel Terminal", layout="wide")

st.title("🏆 Betting Terminal Pro")

# --- FLÖDE ---
step1, step2, step3 = st.tabs(["1. Välj Match", "2. Analys & Odds", "3. Skicka Tips"])

with step1:
    col1, col2 = st.columns([2, 1])
    with col1:
        league = st.selectbox("Välj Liga", ["Europa League", "Champions League", "Premier League", "Allsvenskan", "Serie A", "La Liga"])
    with col2:
        if st.button("Sök Dagens Matcher"):
            with st.spinner("Söker..."):
                st.session_state.match_list = fetch_real_fixtures(league)
    
    st.divider()
    
    if "match_list" in st.session_state and st.session_state.match_list:
        selected_m = st.radio("Välj match att analysera:", st.session_state.match_list)
        if st.button("Välj denna match"):
            st.session_state.active_match = selected_m
            st.success(f"Vald: {selected_m}. Gå till nästa flik!")
    else:
        st.info("Inga matcher laddade. Sök ovan eller skriv in manuellt nedan.")
        manual_match = st.text_input("Skriv in match manuellt (t.ex. Arsenal - Liverpool)")
        if st.button("Använd manuell inmatning"):
            st.session_state.active_match = manual_match

with step2:
    if "active_match" in st.session_state:
        st.subheader(f"Analys: {st.session_state.active_match}")
        
        if st.button("Hämta Marknadsodds & AI-Research"):
            with st.spinner("Hämtar data..."):
                odds_info = get_market_odds(st.session_state.active_match)
                st.info(f"**Marknadsodds:** {odds_info}")
        
        st.divider()
        st.write("Justera förväntade mål för att se sannolikhet:")
        c1, c2 = st.columns(2)
        h_goal = c1.number_input("Hemmalag mål-snitt", value=1.5)
        a_goal = c2.number_input("Bortalag mål-snitt", value=1.2)
        
        h_p, d_p, a_p = calculate_poisson_probability(h_goal, a_goal)
        
        st.write("### Sannolikhet enligt modellen")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("1", f"{h_p}%")
        mc2.metric("X", f"{d_p}%")
        mc3.metric("2", f"{a_p}%")
        
        if st.button("Generera Slutgiltigt Speltips"):
            prompt = f"Baserat på att {st.session_state.active_match} har sannolikheten H:{h_p}% X:{d_p}% B:{a_p}%, ge ett rekommenderat spel och motivera varför."
            tip = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user", "content":prompt}]).choices[0].message.content
            st.session_state.final_report = f"⚽ *MATCH:* {st.session_state.active_match}\n📈 *CHANS:* 1:{h_p}% X:{d_p}% 2:{a_p}%\n\n*AI ANALYS:*\n{tip}"
            st.markdown(st.session_state.final_report)
    else:
        st.warning("Välj en match i steg 1 först.")

with step3:
    if "final_report" in st.session_state:
        st.markdown(st.session_state.final_report)
        if st.button("🚀 Skicka till Telegram"):
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          json={"chat_id": TG_ID, "text": st.session_state.final_report, "parse_mode": "Markdown"})
            st.success("Skickat!")
    else:
        st.info("Generera en rapport i steg 2 först.")
