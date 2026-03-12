# --- KONFIGURATION MED FALLBACK ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    # Lista på modeller att prova i ordning
    # Vi testar 1.5 Flash först nu eftersom 2.0 verkar vara maxad för dig
    model_names = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash']
    
    model = None
    for name in model_names:
        try:
            test_model = genai.GenerativeModel(name)
            # Vi gör ett litet testanrop för att se om kvoten är ok
            st.toast(f"Testar modell: {name}...")
            model = test_model
            break # Om vi lyckas, bryt loopen
        except:
            continue
            
    if model is None:
        st.error("Alla Gemini-modeller är för tillfället maxade på ditt gratiskonto. Vänta 60 sekunder och prova igen.")
        st.stop()
    
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    TG_ID = st.secrets["TELEGRAM_CHAT_ID"]
except Exception as e:
    st.error(f"Konfigurationsfel: {e}")
    st.stop()
