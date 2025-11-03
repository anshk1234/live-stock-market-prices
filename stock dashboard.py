import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import time
import json
from streamlit_lottie import st_lottie

# Set page config FIRST
st.set_page_config(page_title="📈 Live Stock Dashboard", layout="wide")

# --- Splash Animation ---
def load_lottiefile(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

if "show_intro" not in st.session_state:
    st.session_state.show_intro = True

if st.session_state.show_intro:
    lottie_intro = load_lottiefile("Money Investment.json")
    splash = st.empty()
    with splash.container():
        st.markdown("<h1 style='text-align:center;'>Welcome to Stock Market Dashboard !</h1>", unsafe_allow_html=True)
        st_lottie(lottie_intro, height=280, speed=1.0, loop=False)
        time.sleep(4)
    splash.empty()
    st.session_state.show_intro = False

# Define companies and symbols
symbols = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Amazon": "AMZN",
    "Tesla": "TSLA",
    "Google": "GOOG",
    "NVIDIA": "NVDA",
    "Meta": "META"
}

# Logo URLs (PNG-based for reliability)
logos = {
    "Apple": "https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg",
    "Microsoft": "https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg",
    "Amazon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
    "Tesla": "https://upload.wikimedia.org/wikipedia/commons/b/bd/Tesla_Motors.svg",
    "Google": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg",
    "NVIDIA": "https://upload.wikimedia.org/wikipedia/en/2/21/Nvidia_logo.svg",
    "Meta": "https://upload.wikimedia.org/wikipedia/commons/8/8d/Meta_Platforms_Inc._logo.svg"
}

# Sidebar: Select company
st.sidebar.title("🔍 Company Insights")
selected = st.sidebar.selectbox("Choose a company", list(symbols.keys()))
selected_symbol = symbols[selected]

# Display logo
try:
    st.sidebar.image(logos[selected], width=120)
except:
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/6/65/No-Image-Placeholder.svg", width=120)

# Fetch live data
def fetch_live_data():
    data = {}
    for name, symbol in symbols.items():
        stock = yf.Ticker(symbol)
        info = stock.info
        data[name] = {
            "Price": info["regularMarketPrice"],
            "Change": info["regularMarketChangePercent"]
        }
    return pd.DataFrame([
        {"Company": name, "Price (USD)": d["Price"], "Change (%)": d["Change"]}
        for name, d in data.items()
    ])

# Fetch financial metrics
def fetch_metrics():
    metrics = []
    for name, symbol in symbols.items():
        info = yf.Ticker(symbol).info
        metrics.append({
            "Company": name,
            "PE Ratio": info.get("trailingPE", "N/A"),
            "EPS": info.get("trailingEps", "N/A"),
            "Market Cap": info.get("marketCap", "N/A")
        })
    return pd.DataFrame(metrics)

# Fetch historical data
def get_history(symbol):
    stock = yf.Ticker(symbol)
    hist = stock.history(period="1mo")
    hist["Company"] = symbol
    return hist.reset_index()

# Fetch news
def fetch_news(symbol):
    try:
        return yf.Ticker(symbol).news[:5]
    except:
        return []

# Tabs layout
tab1, tab2, tab3 = st.tabs(["📈 Live Prices", "📉 Trends", "📊 Metrics"])

with tab1:
    st.subheader("📈 Live Stock Prices")
    live_df = fetch_live_data()
    fig = px.bar(live_df, x="Company", y="Price (USD)", color="Change (%)",
             color_continuous_scale="RdYlGn", title="Live Prices")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(live_df.set_index("Company"))

with tab2:
    st.subheader("📉 1-Month Price Trend")
    history_df = pd.concat([get_history(s) for s in symbols.values()])
    fig2 = px.line(history_df, x="Date", y="Close", color="Company", title="1-Month Trend")
    st.plotly_chart(fig2, use_container_width=True)

with tab3:
    st.subheader("📊 Financial Metrics")
    metrics_df = fetch_metrics()

    fig3 = px.line(metrics_df.sort_values("EPS"), x="Company", y=["PE Ratio", "EPS"],
                   title="PE Ratio and EPS by Company", markers=True)
    st.plotly_chart(fig3, use_container_width=True)  # ✅ This must be inside tab3
    
    st.dataframe(metrics_df.set_index("Company"))


# Sidebar insights
info = yf.Ticker(selected_symbol).info
st.sidebar.markdown(f"**Sector**: {info.get('sector', 'N/A')}")
st.sidebar.markdown(f"**Market Cap**: ${info.get('marketCap', 'N/A'):,}")
st.sidebar.markdown(f"**PE Ratio**: {info.get('trailingPE', 'N/A')}")
st.sidebar.markdown(f"**52-Week High**: ${info.get('fiftyTwoWeekHigh', 'N/A')}")

# Refresh options
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Manual Refresh"):
    st.experimental_rerun()


st.sidebar.markdown("---")
st.sidebar.markdown("### 🙌 Credits")
st.sidebar.markdown("""
- 👨‍💻 **Built by**: Ansh Kunwar
- 📊 **Data Source**: [Yahoo Finance](https://finance.yahoo.com)  
- 🖼️ **Logos**: Wikimedia Commons  
- ⚙️ **Tech Stack**: Streamlit + Plotly  
- 🧠 **Source Code**: [GitHub Repository](https://github.com/anshk1234/live-stock-market-prices)  
- 🌐 **see other projects**: [streamlit.io/ansh kunwar](https://share.streamlit.io/user/anshk1234)  
- 📧 **Contact**: anshkunwar3009@gmail.com                    
""") 

