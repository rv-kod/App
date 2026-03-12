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

# --- SCRAPER-FUNKTION (Surfar utan API) ---
def scrape_daily_matches():
    # Vi använder en sida som listar dagens tips
    url = "https://www.betshoot.com/football/predictions/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        matches = []
        
        # Hittar alla match-containrar på sidan
        for item in soup.select('.bet-item'):
            try:
                teams = item.select_one('.teams').text.strip()
                league = item.select_one('.league').text.strip()
                tip = item.select_one('.tip').text.strip()
                time = item.select_one('.time').text.strip()
                
                # Dela upp hemmalag och bortalag
                home, away = teams.split(' vs ')
                
                matches.append({
                    "Liga": league,
                    "Match": f"{home} - {away}",
                    "Tips": tip,
                    "Tid": time,
                    "Home": home,
                    "Away": away
                })
            except: continue
        return matches
    except Exception as e:
        st.error(f"Scraping-fel: {e}")
        return []

# --- UI DESIGN ---
st.set_page_config(page_title="Football Scraper Pro", layout="wide")

if 'saved' not in st.session_state: st.session_state.saved = []

st.title("⚽ Football Intelligence Scraper")
st.write(f"Hämtar data live från webben: {datetime.date.today()}")

# Sidomeny
with st.sidebar:
    st.header("⭐ Bevakningslista")
    for s in st.session_state.saved:
        st.write(f"• {s}")
    if st.button("Rensa"):
        st.session_state.saved = []
        st.rerun()

# --- HUVUDINNEHÅLL ---
if st.button("🔄 Uppdatera matcher från webben"):
    st.rerun()

matches = scrape_daily_matches()

if not matches:
    st.warning("Kunde inte hämta matcher just nu. Sidan kan vara nere eller blockera anropet.")
else:
    # Gruppera efter liga
    df = pd.DataFrame(matches)
    for league, group in df.groupby('Liga'):
        with st.expander(f"🏆 {league} ({len(group)} matcher)"):
            for _, row in group.iterrows():
                c1, c2, c3 = st.columns([3, 1, 1])
                
                with c1:
                    st.write(f"**{row['Match']}**")
                    st.caption(f"Avspark: {row['Tid']} | Tips: {row['Tips']}")
                
                with c2:
                    if st.button("⭐ Spara", key=f"s_{row['Match']}"):
                        st.session_state.saved.append(row['Match'])
                        st.toast("Sparad!")
                
                with c3:
                    if st.button("🤖 AI Analys", key=f"ai_{row['Match']}"):
                        prompt = f"Gör en kort bettinganalys för {row['Match']} i {league}. Tipset är {row['Tips']}. Är det ett bra spel?"
                        res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user", "content":prompt}])
                        analysis = res.choices[0].message.content
                        st.info(analysis)
                        
                        # Telegram-knapp dyker upp efter analys
                        if st.button("✈️ Skicka till Telegram", key=f"tg_{row['Match']}"):
                            msg = f"⚽ *MATCHTIPS*\n{row['Match']}\n🏆 {league}\n📈 Tips: {row['Tips']}\n\n{analysis}"
                            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", json={"chat_id": TG_ID, "text": msg, "parse_mode": "Markdown"})
                            st.success("Skickat!")
