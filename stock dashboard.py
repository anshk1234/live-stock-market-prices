import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import altair as alt
import time
import json
from streamlit_lottie import st_lottie
from datetime import datetime

# Page config
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

st.header('''📈 Live Stock Dashboard''')
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

# Logo URLs
logos = {
    "Apple": "https://upload.wikimedia.org/wikipedia/commons/f/fa/Apple_logo_black.svg",
    "Microsoft": "https://upload.wikimedia.org/wikipedia/commons/4/44/Microsoft_logo.svg",
    "Amazon": "https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg",
    "Tesla": "https://upload.wikimedia.org/wikipedia/commons/b/bd/Tesla_Motors.svg",
    "Google": "https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg",
    "NVIDIA": "https://www.logo.wine/a/logo/Nvidia/Nvidia-Light-Vertical-Dark-Background-Logo.wine.svg",
    "Meta": "https://tse2.mm.bing.net/th/id/OIP.UuE5-qQHGzojP7JoW2jRzwHaGB?cb=ucfimg2ucfimg=1&rs=1&pid=ImgDetMain&o=7&rm=3"
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

# Fetch news
def fetch_news(ticker):
    try:
        stock = yf.Ticker(ticker)
        return stock.news
    except Exception as e:
        st.error(f"Error fetching news: {e}")
        return []


# Peer comparison dashboard
def show_peer_analysis():
    STOCKS = [
    "AAPL", "ABBV", "ACN", "ADBE", "ADP", "AMD", "AMGN", "AMT", "AMZN", "APD",
    "AVGO", "AXP", "BA", "BK", "BKNG", "BMY", "BRK.B", "BSX", "C", "CAT", "CI",
    "CL", "CMCSA", "COST", "CRM", "CSCO", "CVX", "DE", "DHR", "DIS", "DUK",
    "ELV", "EOG", "EQR", "FDX", "GD", "GE", "GILD", "GOOG", "GOOGL", "HD",
    "HON", "HUM", "IBM", "ICE", "INTC", "ISRG", "JNJ", "JPM", "KO", "LIN",
    "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "META", "MMC", "MO", "MRK",
    "MSFT", "NEE", "NFLX", "NKE", "NOW", "NVDA", "ORCL", "PEP", "PFE", "PG",
    "PLD", "PM", "PSA", "REGN", "RTX", "SBUX", "SCHW", "SLB", "SO", "SPGI",
    "T", "TJX", "TMO", "TSLA", "TXN", "UNH", "UNP", "UPS", "V", "VZ", "WFC",
    "WM", "WMT", "XOM"
]
    horizon_map = {
        "1 Month": "1mo",
        "3 Months": "3mo",
        "6 Months": "6mo",
        "1 Year": "1y",
        "5 Years": "5y",
        "10 Years": "10y",
        "20 Years": "20y",
    }

    DEFAULT_TICKERS = ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "TSLA", "META"]
    tickers = st.multiselect("Select stocks to compare", STOCKS, default=DEFAULT_TICKERS)
    horizon = st.selectbox("Select time horizon", list(horizon_map.keys()), index=2)

    if not tickers:
        st.info("Pick some stocks to compare")
        st.stop()

    @st.cache_data(ttl=21600)
    def load_data(tickers, period):
        frames = []
        for ticker in tickers:
            try:
                df = yf.Ticker(ticker).history(period=period)[["Close"]]
                if not df.empty:
                    df.columns = [ticker]
                    frames.append(df)
            except:
                continue
        if frames:
            return pd.concat(frames, axis=1)
        else:
            return pd.DataFrame()

    data = load_data(tickers, horizon_map[horizon])
    if data.empty or data.isna().all().all():
        st.error("No valid price data to normalize.")
        st.stop()

    clean_data = data.dropna(axis=0, how="any")
    if clean_data.empty or clean_data.shape[0] < 2:
        st.error("Not enough clean data to normalize.")
        st.stop()

    normalized = clean_data.div(clean_data.iloc[0])
    normalized.index.name = "Date"

    st.altair_chart(
        alt.Chart(
            normalized.reset_index().melt(
                id_vars=["Date"], var_name="Stock", value_name="Normalized price"
            )
        )
        .mark_line()
        .encode(
            alt.X("Date:T"),
            alt.Y("Normalized price:Q").scale(zero=False),
            alt.Color("Stock:N"),
        )
        .properties(height=400),
        use_container_width=True
    )

    if len(tickers) > 1:
        st.markdown("### Individual vs Peer Average")
        cols = st.columns(4)
        for i, ticker in enumerate(tickers):
            peers = normalized.drop(columns=[ticker])
            peer_avg = peers.mean(axis=1)

            plot_data = pd.DataFrame({
                "Date": normalized.index,
                ticker: normalized[ticker],
                "Peer average": peer_avg,
            }).melt(id_vars=["Date"], var_name="Series", value_name="Price")

            chart = alt.Chart(plot_data).mark_line().encode(
                alt.X("Date:T"),
                alt.Y("Price:Q").scale(zero=False),
                alt.Color("Series:N", scale=alt.Scale(domain=[ticker, "Peer average"], range=["red", "gray"])),
                alt.Tooltip(["Date", "Series", "Price"]),
            ).properties(title=f"{ticker} vs peer average", height=300)

            cell = cols[(i * 2) % 4].container(border=True)
            cell.altair_chart(chart, use_container_width=True)

            delta_data = pd.DataFrame({
                "Date": normalized.index,
                "Delta": normalized[ticker] - peer_avg,
            })

            chart = alt.Chart(delta_data).mark_area().encode(
                alt.X("Date:T"),
                alt.Y("Delta:Q").scale(zero=False),
            ).properties(title=f"{ticker} minus peer average", height=300)

            cell = cols[(i * 2 + 1) % 4].container(border=True)
            cell.altair_chart(chart, use_container_width=True)

# raw data display
    st.markdown("## Raw data")
    st.dataframe(data)
            

# Tabs layout
tab1, tab2, tab3, tab4 = st.tabs(["📈 Live Prices", "📉 Peer Trends", "📊 Metrics",  "📰 News"])

with tab1:
    st.subheader("📈 Live Stock Prices")
    live_df = fetch_live_data()
    fig = px.bar(live_df, x="Company", y="Price (USD)", color="Change (%)",
                 color_continuous_scale="RdYlGn", title="Live Prices")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(live_df.set_index("Company"))

with tab2:
    show_peer_analysis()

with tab3:
    st.subheader("📊 Financial Metrics")
    metrics_df = fetch_metrics()
    fig3 = px.line(metrics_df.sort_values("EPS"), x="Company", y=["PE Ratio", "EPS"],
                   title="PE Ratio and EPS by Company", markers=True)
    st.plotly_chart(fig3, use_container_width=True)
    st.dataframe(metrics_df.set_index("Company"))

with tab4:
    st.subheader(f"📰 Latest News for {selected}")
    news_items = fetch_news(selected_symbol)

    if news_items:
        for item in news_items[:4]:
            content = item.get("content", {})
            title = content.get("title", "No title available")
            summary = content.get("summary", "")
            pubDate = content.get("pubDate", None)
            link = content.get("canonicalUrl", {}).get("url", None)
            thumbnail = content.get("thumbnail", {}).get("originalUrl", None)
            provider = content.get("provider", {}).get("displayName", "Unknown")

            # Show headline
            st.markdown(f"### {title}")

            # Show thumbnail if available
            if thumbnail:
                st.image(thumbnail, width=400)

            # Show summary
            if summary:
                st.write(summary)

            # Show source + publish time
            if pubDate:
                st.caption(f"Source: {provider} | Published: {pubDate}")
            else:
                st.caption(f"Source: {provider}")

            # Show link
            if link:
                st.markdown(f"[Read more]({link})")

            st.markdown("---")
    else:
        st.info("No news available at the moment.")

# Sidebar insights
info = yf.Ticker(selected_symbol).info
st.sidebar.markdown(f"**Sector**: {info.get('sector', 'N/A')}")
st.sidebar.markdown(f"**Market Cap**: ${info.get('marketCap', 'N/A'):,}")
st.sidebar.markdown(f"**PE Ratio**: {info.get('trailingPE', 'N/A')}")
st.sidebar.markdown(f"**52-Week High**: ${info.get('fiftyTwoWeekHigh', 'N/A')}")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🙌 Credits")
st.sidebar.markdown("""
- 👨‍💻 **Developed by**: Ansh Kunwar
- 📊 **Data Source**: [Yahoo Finance](https://finance.yahoo.com)  
- 🖼️ **Logos**: Wikimedia Commons  
- ⚙️ **Tech Stack**: Streamlit + Plotly  
- 🧠 **Source Code**: [GitHub Repository](https://github.com/anshk1234/live-stock-market-prices)  
- 🌐 **see other projects**: [streamlit.io/ansh kunwar](https://share.streamlit.io/user/anshk1234)  
- 📧 **Contact**: anshkunwar3009@gmail.com     
-  This App is Licensed Under **Apache License 2.0**
    
     
""") 

st.sidebar.markdown("<br><center>© 2025 Live Stock Dashboard</center>", unsafe_allow_html=True)
    
# ---- Footer ----
st.markdown("<p style='text-align:center; color:white;'>© 2025 Live Stock Dashboard | Powered by Yahoo Finance</p>", unsafe_allow_html=True)

