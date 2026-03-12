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

# --- MATEMATISK MOTOR (Poisson-sannolikhet) ---
def calculate_poisson_probability(exp_goals_home, exp_goals_away):
    """Räknar ut 1X2 sannolikheter baserat på förväntade mål"""
    home_win = 0
    draw = 0
    away_win = 0
    
    for h in range(10):
        for a in range(10):
            prob = ((exp_goals_home**h * math.exp(-exp_goals_home)) / math.factorial(h)) * \
                   ((exp_goals_away**a * math.exp(-exp_goals_away)) / math.factorial(a))
            
            if h > a: home_win += prob
            elif h == a: draw += prob
            else: away_win += prob
            
    return round(home_win*100, 1), round(draw*100, 1), round(away_win*100, 1)

# --- AI-FUNKTIONER ---
def get_daily_fixtures_with_odds(league):
    prompt = f"""
    Hitta dagens matcher ({datetime.date.today()}) i {league}. 
    För varje match, uppskatta marknadsoddsen (1, X, 2) från stora bolag.
    Svara exakt så här för varje match:
    Match: Hemmalag - Bortalag | Odds: 1(odds) X(odds) 2(odds)
    """
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.split('\n')

def get_deep_analysis(match_str, league):
    prompt = f"""
    Gör en djup analys av {match_str} i {league}. 
    1. Ge förväntat antal mål för hemmalaget och bortalaget baserat på form.
    2. Vilket spel är 'Value bet' (där oddset är högre än risken)?
    3. Rekommenderat spel: (t.ex. Rak 1:a, Över 2.5, etc.)
    Svara professionellt och kortfattat.
    """
    res = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content

# --- UI DESIGN ---
st.set_page_config(page_title="Sport Intel Pro v4", layout="wide")

st.title("🏆 Betting Intelligence Terminal")
st.caption(f"Sannolikhetsberäkning & Marknadsanalys | {datetime.date.today()}")

tabs = st.tabs(["📅 Dagens Marknad", "🧮 Sannolikhets-Kalkylator", "✈️ Telegram Center"])

# TAB 1: SCHEMA OCH ODDS
with tabs[0]:
    league = st.selectbox("Välj Liga", ["Europa League", "Champions League", "Premier League", "Allsvenskan", "Serie A", "La Liga"])
    
    if st.button(f"Hämta Odds & Matcher för {league}"):
        with st.spinner("Hämtar marknadsdata..."):
            fixtures = get_daily_fixtures_with_odds(league)
            for f in fixtures:
                if "|" in f:
                    st.markdown(f"### {f}")
                    # Extrahera lagnamn för analysknappen
                    m_name = f.split("|")[0].replace("Match: ", "").strip()
                    if st.button(f"Kör Sannolikhetsanalys: {m_name}", key=f"btn_{m_name}"):
                        st.session_state.active_match = m_name
                        st.rerun()

# TAB 2: ANALYS OCH KALKYLATOR
with tabs[1]:
    active_m = st.session_state.get('active_match', "")
    match_input = st.text_input("Vald match:", value=active_m)
    
    col1, col2 = st.columns(2)
    with col1:
        exp_h = st.number_input("Förväntade mål Hemmalag (snitt)", value=1.5, step=0.1)
    with col2:
        exp_a = st.number_input("Förväntade mål Bortalag (snitt)", value=1.2, step=0.1)

    if st.button("🔥 Beräkna & Generera Rapport"):
        # 1. Räkna ut matematisk sannolikhet
        h_perc, d_perc, a_perc = calculate_poisson_probability(exp_h, exp_a)
        
        # 2. Hämta AI-insikter
        with st.spinner("AI analyserar form och nyheter..."):
            report = get_deep_analysis(match_input, league)
        
        # 3. Presentera resultatet
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric(f"Vinst {match_input.split('-')[0]}", f"{h_perc}%")
        c2.metric("Oavgjort", f"{d_perc}%")
        c3.metric(f"Vinst {match_input.split('-')[-1]}", f"{a_perc}%")
        
        st.subheader("🤖 AI Rekommendation")
        st.info(report)
        
        # Spara rapport för Telegram
        st.session_state.last_report = f"📊 *ANALYS: {match_input}*\n\nSannolikhet:\n- Hemmavinst: {h_perc}%\n- Oavgjort: {d_perc}%\n- Bortavinst: {a_perc}%\n\n*AI Analys:*\n{report}"

# TAB 3: TELEGRAM
with tabs[2]:
    st.subheader("Skicka till mobilen")
    if 'last_report' in st.session_state:
        st.markdown(st.session_state.last_report)
        if st.button("🚀 Skicka Analys till Telegram"):
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                          json={"chat_id": TG_ID, "text": st.session_state.last_report, "parse_mode": "Markdown"})
            st.success("Analysen skickad till Telegram!")
    else:
        st.write("Ingen rapport genererad än. Kör en analys i flik 2 först.")
