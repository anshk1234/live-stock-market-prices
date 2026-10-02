import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import altair as alt
import time
import json
from streamlit_lottie import st_lottie
from datetime import datetime, timedelta, time as dt_time
from zoneinfo import ZoneInfo
import io
from streamlit_echarts import st_echarts
import plotly.graph_objects as go
import streamlit.components.v1 as components

# Page config
st.set_page_config(page_title="📈 Live Stock Dashboard", layout="wide")

# --- Capitalized Tickers & Enter-to-Select Behavior ---
st.markdown(
    """
    <style>
    /* Force all selectbox and multiselect search inputs to display in uppercase */
    div[data-baseweb="select"] input,
    div[data-testid="stSelectbox"] input,
    div[data-testid="stMultiSelect"] input,
    input[aria-autocomplete="list"] {
        text-transform: uppercase !important;
    }
    div[data-baseweb="select"] input::placeholder {
        text-transform: none !important;
    }
    /* Completely eliminate any script carrier containers or iframe artifacts */
    div.ticker-script-carrier,
    div[data-testid="stHtml"]:has(div.ticker-script-carrier),
    iframe.stIFrame,
    iframe[title="st.iframe"],
    iframe[height="1"],
    div[data-testid="stIFrame"],
    div[data-testid="stIframe"],
    div[data-testid="stCustomComponentV1"],
    div:has(> iframe.stIFrame),
    div:has(> div[data-testid="stIFrame"]) {
        display: none !important;
        position: fixed !important;
        top: -9999px !important;
        left: -9999px !important;
        width: 0 !important;
        height: 0 !important;
        max-width: 0 !important;
        max-height: 0 !important;
        opacity: 0 !important;
        pointer-events: none !important;
        border: none !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

enter_select_js = """
<div class="ticker-script-carrier" style="display:none;position:fixed;top:-9999px;left:-9999px;width:0;height:0;overflow:hidden;opacity:0;">
<script>
(function() {
    function setupEnterKey() {
        try {
            const doc = window.parent ? window.parent.document : document;
            if (!doc || doc._autoSelectTopTickerSetup) return;
            doc._autoSelectTopTickerSetup = true;

            doc.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    const target = e.target;
                    if (target && (
                        target.closest('div[data-baseweb="select"]') || 
                        target.getAttribute('aria-autocomplete') === 'list' ||
                        target.closest('div[data-testid="stSelectbox"]') ||
                        target.closest('div[data-testid="stMultiSelect"]')
                    )) {
                        const popovers = doc.querySelectorAll('div[data-baseweb="popover"], ul[role="listbox"], div[role="listbox"]');
                        for (let pop of popovers) {
                            if (pop && pop.offsetParent !== null) {
                                const highlighted = pop.querySelector('li[aria-selected="true"], div[aria-selected="true"], [data-highlighted="true"]');
                                const optionToClick = highlighted || pop.querySelector('li[role="option"], div[role="option"], ul[role="listbox"] li, div[data-baseweb="menu"] li');
                                if (optionToClick) {
                                    optionToClick.click();
                                    e.preventDefault();
                                    e.stopPropagation();
                                    break;
                                }
                            }
                        }
                    }
                }
            }, true);

            doc.addEventListener('input', function(e) {
                const target = e.target;
                if (target && (target.closest('div[data-baseweb="select"]') || target.getAttribute('aria-autocomplete') === 'list')) {
                    target.style.textTransform = 'uppercase';
                }
            }, true);
        } catch (err) {
            console.error('Ticker auto-select error:', err);
        }
    }

    setupEnterKey();
    setInterval(setupEnterKey, 1000);
})();
</script>
</div>
"""

try:
    st.html(enter_select_js, unsafe_allow_javascript=True)
except Exception:
    components.html(
        f"""<!DOCTYPE html><html><head><style>html,body{{margin:0;padding:0;overflow:hidden;background:transparent;}}</style></head><body>{enter_select_js}</body></html>""",
        height=1,
    )

# --- Splash Animation ---
def load_lottiefile(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

if "show_intro" not in st.session_state:
    st.session_state.show_intro = True

if st.session_state.show_intro:
    lottie_intro = load_lottiefile("Money Investment.json")
    if lottie_intro:
        st.markdown("<h1 style='text-align:center;'>Welcome to Stock Market Dashboard !</h1>", unsafe_allow_html=True)
        st_lottie(lottie_intro, height=280, speed=1.0, loop=False)
        time.sleep(3)
    st.session_state.show_intro = False
    st.rerun()

#app title
st.header('''📈 Live Stock Dashboard''')

# Fetch live data
def _fetch_stock_details_impl(ticker, period="1mo"):
    stock = yf.Ticker(ticker)
    try:
        info = stock.info or {}
    except Exception:
        info = {}

    price = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"
    change_pct = info.get("regularMarketChangePercent", 0)

    # Request full OHLC data with multi-layer fallback
    history = pd.DataFrame()
    try:
        hist = stock.history(period=period, interval="1d")
        if hist.empty or not {"Open", "High", "Low", "Close"}.issubset(hist.columns):
            # Fallback 1: yf.download with period
            hist = yf.download(ticker, period=period, interval="1d", progress=False)
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.get_level_values(0)

        if hist.empty or not {"Open", "High", "Low", "Close"}.issubset(hist.columns):
            # Fallback 2: explicit start date (prevents 3mo / crumb DNS glitches)
            period_days = {
                "1mo": 35, "3mo": 95, "6mo": 185, "1y": 370,
                "5y": 1835, "10y": 3660, "20y": 7320
            }
            days = period_days.get(period, 95)
            start_date = datetime.today() - timedelta(days=days)
            hist = yf.download(ticker, start=start_date, interval="1d", progress=False)
            if isinstance(hist.columns, pd.MultiIndex):
                hist.columns = hist.columns.get_level_values(0)

        if not hist.empty and {"Open", "High", "Low", "Close"}.issubset(hist.columns):
            history = hist[["Open", "High", "Low", "Close"]]
            if price == "N/A" and not history.empty:
                price = history["Close"].iloc[-1]
    except Exception:
        history = pd.DataFrame()

    details = {
        "price": price,
        "change_pct": change_pct if change_pct is not None else 0,
        "market_cap": info.get("marketCap", "N/A"),
        "pe_ratio": info.get("trailingPE", "N/A"),
        "eps": info.get("trailingEps", "N/A"),
        "high_52w": info.get("fiftyTwoWeekHigh", "N/A"),
        "low_52w": info.get("fiftyTwoWeekLow", "N/A"),
        "volume": info.get("volume", "N/A"),
        "dividend_yield": info.get("dividendYield", "N/A"),
        "company_name": info.get("longName", ticker),
        "sector": info.get("sector", "N/A")
    }

    return details, history


@st.cache_data(ttl=3600)   # cache for 1 hour
def _fetch_stock_details_cached(ticker, period="1mo"):
    details, history = _fetch_stock_details_impl(ticker, period)
    if history.empty:
        # Avoid caching transient errors
        raise ValueError(f"No price data found for {ticker} ({period})")
    return details, history


def fetch_stock_details(ticker, period="1mo"):
    try:
        return _fetch_stock_details_cached(ticker, period)
    except Exception:
        return _fetch_stock_details_impl(ticker, period)



# Define symbols globally for metric tab
symbols = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Tesla": "TSLA",
    "NVIDIA": "NVDA",
    "Amazon": "AMZN",
    "Google": "GOOG",
    "Meta": "META"
}

@st.cache_data(ttl=36000) # cache for 10 hours
def fetch_metrics():
    metrics = []
    for name, symbol in symbols.items():
        try:
            info = yf.Ticker(symbol).info or {}
            metrics.append({
                "Company": name,
                "PE Ratio": info.get("trailingPE", "N/A"),
                "EPS": info.get("trailingEps", "N/A"),
                "Analyst Rating": info.get("recommendationMean", "N/A")  # 1=Strong Buy, 5=Sell
            })
        except Exception:
            metrics.append({
                "Company": name,
                "PE Ratio": "N/A",
                "EPS": "N/A",
                "Analyst Rating": "N/A"
            })
    return pd.DataFrame(metrics)


# Fetch news
@st.cache_data(ttl=21600) # cache for 6 hours
def fetch_news(ticker):
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        if not news:
            try:
                search = yf.Search(ticker, news_count=5)
                news = getattr(search, "news", [])
            except Exception:
                news = []
        return news or []
    except Exception:
        return []


# Peer comparison dashboard
def show_peer_analysis():
    STOCKS = [
        "AAPL","ABBV","ACN","ADBE","ADP","AMD","AMGN","AMT","AMZN","APD",
        "AVGO","AXP","BA","BK","BKNG","BMY","BRK.B","BSX","C","CAT","CI",
        "CL","CMCSA","COST","CRM","CSCO","CVX","DE","DHR","DIS","DUK",
        "ELV","EOG","EQR","FDX","GD","GE","GILD","GOOG","GOOGL","HD",
        "HON","HUM","IBM","ICE","INTC","ISRG","JNJ","JPM","KO","LIN",
        "LLY","LMT","LOW","MA","MCD","MDLZ","META","MMC","MO","MRK",
        "MSFT","NEE","NFLX","NKE","NOW","NVDA","ORCL","PEP","PFE","PG",
        "PLD","PM","PSA","REGN","RTX","SBUX","SCHW","SLB","SO","SPGI",
        "T","TJX","TMO","TSLA","TXN","UNH","UNP","UPS","V","VZ","WFC",
        "WM","WMT","XOM"
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
    tickers = st.multiselect("Select stocks to compare", STOCKS, default=DEFAULT_TICKERS, key="peer_stocks_multiselect")
    horizon = st.selectbox("Select time horizon", list(horizon_map.keys()), index=2, key="peer_horizon_select")

    if not tickers:
        st.info("Pick some stocks to compare")
        st.stop()

    @st.cache_data(ttl=21600) # cache for 6 hours
    def load_data(tickers, period):
        try:
            download_df = yf.download(tickers, period=period, progress=False)
            if not download_df.empty and "Close" in download_df:
                close_df = download_df["Close"]
                if isinstance(close_df, pd.Series):
                    close_df = close_df.to_frame(name=tickers[0])
                if not close_df.empty:
                    return close_df
        except Exception:
            pass

        frames = []
        for ticker in tickers:
            try:
                df = yf.Ticker(ticker).history(period=period)
                if not df.empty and "Close" in df.columns:
                    col = df[["Close"]].rename(columns={"Close": ticker})
                    frames.append(col)
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

    # --- Peer comparison chart ---
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
        width="stretch"
    )

    @st.cache_data(ttl=3600)
    def fetch_sparkline_card(ticker):
        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            price = info.get("currentPrice") or info.get("regularMarketPrice") or "N/A"
            change_pct = info.get("regularMarketChangePercent", 0.0)
            hist = stock.history(period="1mo")
            close_series = hist["Close"] if not hist.empty and "Close" in hist.columns else pd.Series()
            return price, change_pct, close_series
        except Exception:
            return "N/A", 0.0, pd.Series()

    # --- Price cards inside expander only ---
    with st.expander("💵 Current Prices of Selected Companies", expanded=True):
        for i in range(0, len(tickers), 4):  # 4 cards per row
            row = st.columns(min(4, len(tickers) - i))
            for j, ticker in enumerate(tickers[i:i+4]):
                try:
                    price, change_pct, hist = fetch_sparkline_card(ticker)

                    with row[j].container(border=True):
                        price_str = f"${price:,.2f}" if isinstance(price, (int, float)) else str(price)
                        delta_str = f"{change_pct:+.2f}%" if isinstance(change_pct, (int, float)) else "0.00%"
                        st.metric(label=ticker, value=price_str, delta=delta_str)

                        # Sparkline with dynamic y-scale and better height
                        if not hist.empty and len(hist) >= 2:
                            color = "green" if hist.iloc[-1] >= hist.iloc[0] else "red"
                            sparkline_data = pd.DataFrame({"Date": hist.index, "Price": hist.values})
                            sparkline = (
                                alt.Chart(sparkline_data)
                                .mark_line(color=color)
                                .encode(
                                    x=alt.X("Date:T", axis=None),
                                    y=alt.Y("Price:Q", scale=alt.Scale(domain=[float(hist.min()), float(hist.max())]), axis=None)
                                )
                                .properties(height=100)
                            )
                            st.altair_chart(sparkline, width="stretch")

                except:
                    with row[j].container(border=True):
                        st.metric(label=ticker, value="N/A", delta="N/A")

    # --- Peer average comparison charts ---
    if len(tickers) > 1:
        st.markdown("### Individual vs Peer Average")
        cols = st.columns(4)
        for i, ticker in enumerate(tickers):
            if ticker not in normalized.columns:
                continue
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
            cell.altair_chart(chart, width="stretch")

            delta_data = pd.DataFrame({
                "Date": normalized.index,
                "Delta": normalized[ticker] - peer_avg,
            })

            chart = alt.Chart(delta_data).mark_area().encode(
                alt.X("Date:T"),
                alt.Y("Delta:Q").scale(zero=False),
            ).properties(title=f"{ticker} minus peer average", height=300)

            cell = cols[(i * 2 + 1) % 4].container(border=True)
            cell.altair_chart(chart, width="stretch")

    # raw data display
    st.markdown("## Raw data")
    st.dataframe(data)


# Tabs layout
tab1, tab2, tab3, tab4, tab5, tab6= st.tabs(["📈 Live Prices", "📉 Peer Trends", "📊 Metrics",  "📰 News", "⚡ portfolio", "⚙️ Settings & Info"])

with tab1:
    st.subheader("🔍 Stock Explorer")

    # --- Stock selector ---
    STOCKS = [
        "AAPL","ABBV","ACN","ADBE","ADP","AMD","AMGN","AMT","AMZN","APD",
        "AVGO","AXP","BA","BK","BKNG","BMY","BRK.B","BSX","C","CAT","CI",
        "CL","CMCSA","COST","CRM","CSCO","CVX","DE","DHR","DIS","DUK",
        "ELV","EOG","EQR","FDX","GD","GE","GILD","GOOG","GOOGL","HD",
        "HON","HUM","IBM","ICE","INTC","ISRG","JNJ","JPM","KO","LIN",
        "LLY","LMT","LOW","MA","MCD","MDLZ","META","MMC","MO","MRK",
        "MSFT","NEE","NFLX","NKE","NOW","NVDA","ORCL","PEP","PFE","PG",
        "PLD","PM","PSA","REGN","RTX","SBUX","SCHW","SLB","SO","SPGI",
        "T","TJX","TMO","TSLA","TXN","UNH","UNP","UPS","V","VZ","WFC",
        "WM","WMT","XOM"
    ]
    selected_ticker = st.selectbox("Choose a company", STOCKS, key="live_stock_company_select")

    # --- Company name display ---
    try:
        stock = yf.Ticker(selected_ticker)
        company_name = (stock.info or {}).get("longName", selected_ticker)
    except Exception:
        company_name = selected_ticker
    st.markdown(f"## {company_name} ({selected_ticker})")

    # --- Time horizon selector ABOVE chart ---
    horizon_map = {
        "1 Month": "1mo",
        "3 Months": "3mo",
        "6 Months": "6mo",
        "1 Year": "1y",
        "5 Years": "5y",
        "10 Years": "10y",
        "20 Years": "20y",
    }
    
    time_range = st.selectbox(
        "Select time horizon",
        list(horizon_map.keys()),
        index=1,  # default to "3 Months"
        key="live_stock_horizon_select"
    )
    # --- Trend chart ---
    details, history = fetch_stock_details(selected_ticker, horizon_map[time_range])
    if not history.empty and {"Open", "High", "Low", "Close"}.issubset(history.columns):
    # Split layout: chart on left, key metrics (Price, PE, EPS) on right
        col_chart, col_metrics = st.columns([4, 1])

        with col_chart:
            fig = go.Figure()

        # Candlestick
            fig.add_trace(go.Candlestick(
                x=history.index,
                open=history["Open"],
                high=history["High"],
                low=history["Low"],
                close=history["Close"],
                name="Candlestick",
                increasing_line_color='green',
                decreasing_line_color='red'
            ))

        # Line chart overlay
            fig.add_trace(go.Scatter(
                x=history.index,
                y=history["Close"],
                mode="lines",
                name="Close Price",
                line=dict(color="cyan", width=2)
            ))

            fig.update_layout(
                xaxis_title="Date",
                yaxis_title="Price",
                xaxis_rangeslider_visible=False,
                template="plotly_dark",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, width="stretch")

    # Right-side metrics (card style)
        price_val = details.get('price')
        price_str = f"${price_val:,.2f}" if isinstance(price_val, (int, float)) else str(price_val)
        chg_val = details.get('change_pct')
        chg_str = f"{chg_val:+.2f}%" if isinstance(chg_val, (int, float)) else "0.00%"

        pe_val = details.get('pe_ratio')
        pe_str = f"{pe_val:.2f}" if isinstance(pe_val, (int, float)) else str(pe_val)

        eps_val = details.get('eps')
        eps_str = f"{eps_val:.2f}" if isinstance(eps_val, (int, float)) else str(eps_val)

        with col_metrics.container(border=True):
            st.metric("💵 Price", price_str, chg_str)
        with col_metrics.container(border=True):
            st.metric("📊 PE Ratio", pe_str)
        with col_metrics.container(border=True):
            st.metric("📈 EPS", eps_str)
    else:
        st.info("Candlestick data not available for this range.")

    # --- Other snapshot cards BELOW chart ---
    vol_val = details.get('volume')
    vol_str = f"{vol_val:,}" if isinstance(vol_val, (int, float)) else str(vol_val)

    mcap_val = details.get('market_cap')
    mcap_str = f"${mcap_val:,}" if isinstance(mcap_val, (int, float)) else str(mcap_val)

    sector_str = str(details.get("sector", "N/A"))

    high_val = details.get('high_52w')
    high_str = f"${high_val:,.2f}" if isinstance(high_val, (int, float)) else str(high_val)

    low_val = details.get('low_52w')
    low_str = f"${low_val:,.2f}" if isinstance(low_val, (int, float)) else str(low_val)

    div_val = details.get('dividend_yield')
    div_str = f"{div_val:.2%}" if isinstance(div_val, (int, float)) else "N/A"

    row1 = st.columns(3)
    with row1[0].container(border=True):
        st.metric("📦 Volume", vol_str)
    with row1[1].container(border=True):
        st.metric("🏦 Market Cap", mcap_str)
    with row1[2].container(border=True):
        st.metric("🏷️ Sector", sector_str)

    row2 = st.columns(3)
    with row2[0].container(border=True):
        st.metric("📉 52W High", high_str)
    with row2[1].container(border=True):
        st.metric("📉 52W Low", low_str)
    with row2[2].container(border=True):
        st.metric("💸 Dividend Yield", div_str)
    
    

with tab2:
    show_peer_analysis()


with tab3:
    st.subheader("📊 Financial Metrics & Analyst Insights")
    metrics_df = fetch_metrics()

    # Force Analyst Rating to numeric (convert strings like "3" to 3.0, invalid → NaN)
    metrics_df["Analyst Rating"] = pd.to_numeric(metrics_df["Analyst Rating"], errors="coerce")
    plot_df = metrics_df.copy()
    plot_df["PE Ratio"] = pd.to_numeric(plot_df["PE Ratio"], errors="coerce")
    plot_df["EPS"] = pd.to_numeric(plot_df["EPS"], errors="coerce")

    # Line chart: PE Ratio and EPS
    fig_pe_eps = px.line(
        plot_df.sort_values("EPS", na_position="last"),
        x="Company", y=["PE Ratio", "EPS"],
        title="PE Ratio and EPS by Company", markers=True
    )
    st.plotly_chart(fig_pe_eps, width="stretch")

    # Analyst Rating Chart (bar)
    fig_rating = px.bar(
        metrics_df.sort_values("Analyst Rating", na_position="last"),
        x="Analyst Rating", y="Company",
        orientation="h",
        color="Analyst Rating",
        color_continuous_scale="RdYlGn_r",
        title="Analyst Recommendation Score (1=Strong Buy, 5=Sell)"
    )
    st.plotly_chart(fig_rating, width="stretch")

    # Analyst Rating Gauges in card UI (max 4 per row)
    st.subheader("🔮 Analyst Rating Gauges")
    with st.expander("⚡View Analyst Ratings", expanded=True):
        for i in range(0, len(metrics_df), 4):
            cols = st.columns(4)  # up to 4 cards per row
            for j, (_, row) in enumerate(metrics_df.iloc[i:i+4].iterrows()):
                with cols[j]:
                    with st.container(border=True):  # card-style border
                        st.markdown(f"### {row['Company']}")
                        rating_val = row["Analyst Rating"]
                        has_rating = pd.notna(rating_val) and isinstance(rating_val, (int, float))
                        fig = go.Figure(go.Indicator(
                            mode="gauge+number" if has_rating else "number",
                            value=float(rating_val) if has_rating else 0,
                            number={"valueformat": ".2f"} if has_rating else {"prefix": "N/A", "valueformat": ""},
                            title={"text": "Analyst Rating"},
                            gauge={
                                "axis": {"range": [1, 5]},
                                "steps": [
                                    {"range": [1, 2], "color": "green"},
                                    {"range": [2, 3], "color": "lightgreen"},
                                    {"range": [3, 4], "color": "orange"},
                                    {"range": [4, 5], "color": "red"}
                                ]
                            }
                        ))
                        fig.update_layout(height=250, margin=dict(t=20, b=20, l=10, r=10))
                        # Add a unique key using company name + index
                        st.plotly_chart(fig, width="stretch", key=f"rating_{i}_{j}_{row['Company']}")


    # Full Data Table
    st.dataframe(metrics_df.set_index("Company"))

with tab4:
    st.subheader("📰 General Stock Market News")

    # Collect news from multiple tickers
    tickers = ["MSFT", "TSLA", "NVDA", "AMZN", "GOOG", "META"]
    all_news = []
    for ticker in tickers:
        items = fetch_news(ticker)
        if items:
            all_news.extend(items)

    # Show combined news feed (no ticker headings)
    if all_news:
        for item in all_news[:8]:
            content = item.get("content") or {}
            title = content.get("title") or item.get("title") or "No title available"
            summary = content.get("summary") or item.get("summary") or ""
            pubDate = content.get("pubDate") or item.get("pubDate") or item.get("providerPublishTime")
            if isinstance(pubDate, (int, float)):
                try:
                    pubDate = datetime.fromtimestamp(pubDate).strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            link = (content.get("canonicalUrl") or {}).get("url") or item.get("link")
            thumbnail = (content.get("thumbnail") or {}).get("originalUrl")
            if not thumbnail and isinstance(item.get("thumbnail"), dict):
                resolutions = item.get("thumbnail", {}).get("resolutions", [])
                if resolutions and isinstance(resolutions, list) and len(resolutions) > 0:
                    thumbnail = resolutions[0].get("url")
            provider = (content.get("provider") or {}).get("displayName") or item.get("publisher") or "Unknown"

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


with tab5:
    # Session state to store portfolio
    if "portfolio" not in st.session_state:
        st.session_state.portfolio = []

    st.subheader("📁 Portfolio Tracker")
    st.caption("Track your investments and performance in real-time")

    # upload portfolio from CSV
    uploaded_file = st.file_uploader("📥 Import Portfolio CSV", type=["csv"])
    if uploaded_file is not None:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.get("last_imported_file") != file_id:
            try:
                imported_df = pd.read_csv(uploaded_file)
                new_portfolio = []
                for _, row in imported_df.iterrows():
                    # Handle exported format (ASSET, DETAIL)
                    if "ASSET" in row and "DETAIL" in row and "@ $" in str(row["DETAIL"]):
                        parts = str(row["DETAIL"]).split("@ $")
                        qty_str = parts[0].replace("shares", "").strip()
                        qty = float(qty_str)
                        price = float(parts[1].strip())
                        new_portfolio.append({
                            "ticker": str(row["ASSET"]).strip().upper(),
                            "quantity": int(qty) if qty.is_integer() else qty,
                            "buy_price": price
                        })
                    # Handle standard column names
                    elif any(c in row for c in ["ticker", "Ticker", "ASSET", "Symbol"]):
                        ticker_col = next(c for c in ["ticker", "Ticker", "ASSET", "Symbol"] if c in row)
                        qty_col = next((c for c in ["quantity", "Quantity", "shares", "Shares"] if c in row), None)
                        price_col = next((c for c in ["buy_price", "Buy Price", "price", "Price", "PRICE"] if c in row), None)
                        if qty_col and price_col and pd.notna(row[qty_col]) and pd.notna(row[price_col]):
                            qty = float(row[qty_col])
                            new_portfolio.append({
                                "ticker": str(row[ticker_col]).strip().upper(),
                                "quantity": int(qty) if qty.is_integer() else qty,
                                "buy_price": float(row[price_col])
                            })
                if new_portfolio:
                    st.session_state.portfolio = new_portfolio
                    st.session_state.last_imported_file = file_id
                    st.success("Portfolio imported successfully!")
                else:
                    st.warning("Could not parse portfolio rows from CSV.")
            except Exception as e:
                st.error(f"Error importing CSV: {e}")
        
    #input form to add new asset
    # --- Input Section ---
    st.write("➕ Add New Asset to Portfolio")

    tickers = [
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

    with st.form("add_asset_form"):
        col1, col2, col3 = st.columns([2, 1, 1])

        # 🔽 Replace text_input with selectbox (searchable dropdown)
        ticker_input = col1.selectbox("Search Stock", tickers, key="portfolio_stock_select")

        quantity_input = col2.number_input("Quantity", min_value=1, step=1)
        buy_price_input = col3.number_input("Buy Price", min_value=0.0, format="%.2f")

        submitted = st.form_submit_button("➕ Add Asset")

        if submitted and ticker_input:
            st.session_state.portfolio.append({
                "ticker": ticker_input,   # already uppercase from list
                "quantity": quantity_input,
                "buy_price": buy_price_input
            })

    # --- Portfolio Table ---
    def get_portfolio_df(portfolio):
        rows = []
        for asset in portfolio:
            ticker = yf.Ticker(asset["ticker"])
            try:
                hist = ticker.history(period="1d")
                current_price = hist["Close"].iloc[-1] if not hist.empty else 0.0
            except:
                current_price = 0.0
            quantity = asset["quantity"]
            buy_price = asset["buy_price"]
            invested = quantity * buy_price
            value = quantity * current_price
            gain = value - invested
            gain_pct = (gain / invested) * 100 if invested else 0
            rows.append({
                "ASSET": asset["ticker"],
                "PRICE": current_price,   # numeric
                "BALANCE": value,         # numeric
                "GAIN": gain,             # numeric
                "GAIN_PCT": gain_pct,     # numeric
                "DETAIL": f"{quantity} shares @ ${buy_price:.2f}"
            })
        return pd.DataFrame(rows)

    df = get_portfolio_df(st.session_state.portfolio)

    # --- Summary Cards ---
    total_invested = sum(asset["quantity"] * asset["buy_price"] for asset in st.session_state.portfolio)
    total_value = df["BALANCE"].sum() if not df.empty else 0
    total_gain = total_value - total_invested
    gain_pct = (total_gain / total_invested) * 100 if total_invested else 0

    colA, colB, colC = st.columns(3)

    with colA.container(border=True):
        st.metric("💰 Total Balance", f"${total_value:.2f}")

    with colB.container(border=True):
        st.metric("📈 Total Profit/Loss", f"${total_gain:.2f}", f"{gain_pct:.2f}% All Time")

    with colC.container(border=True):
        st.metric("🏦 Invested Capital", f"${total_invested:.2f}")
    
    # --- Charts Section ---
    if not df.empty:
        st.markdown("### 📊 Portfolio Charts")

    # Build data for echarts pie chart
    pie_data = [
        {"value": row["BALANCE"], "name": row["ASSET"]}
        for _, row in df.iterrows()
    ]

    options = {
        "title": {
            "text": "Portfolio Allocation",
            "left": "center",
            "textStyle": {"color": "#fff"},
        },
        "tooltip": {"trigger": "item"},
        "legend": {
            "orient": "vertical",
            "left": "left",
            "textStyle": {"color": "#fff"}  # legend text white
        },
        "series": [
            {
                "name": "Allocation",
                "type": "pie",
                "radius": "90%",
                "data": pie_data,
                "label": {
                    "show": True,
                    "position": "inside",
                    "formatter": "{b}: {d}%",
                    "color": "#fff",           # label text white
                    "fontWeight": "bold",
                    "fontSize": 12
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)"
                    }
                }
            }
        ]
    }

    st_echarts(options=options, height="300px")



    # --- Bar chart for returns ---
    if not df.empty and "GAIN_PCT" in df.columns:
        fig2 = px.bar(
            df,
            x="ASSET",
            y="GAIN",
            color="GAIN",
            text=df["GAIN_PCT"].apply(lambda x: f"{x:.2f}%"),
            title="Gain/Loss by Asset"
        )
        st.plotly_chart(fig2, width="stretch")
    else:
        st.info("No portfolio data available to display returns chart.")


    # --- Holdings Table ---
    st.markdown("### Your Holdings")
    st.dataframe(df.style.format({
        "PRICE": "${:.2f}",
        "BALANCE": "${:.2f}",
        "GAIN": "${:.2f}",
        "GAIN_PCT": "{:.2f}%"
    }), width="stretch")
    
    # Download portfolio as CSV
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📤 Export Portfolio as CSV",
        data=csv,
        file_name="portfolio.csv",
        mime="text/csv"
    )


with tab6:
    st.subheader("⚙️ Settings & Info")

    # --- Live Market Hours & Trading Sessions (Full-width 4-column row) ---
    st.markdown("### 🕒 Global Market Hours & Sessions")

    # Helper to calculate exchange status
    def get_market_status(tz_name, open_time, close_time, pre_open=None, post_close=None, lunch_break=None):
        now = datetime.now(ZoneInfo(tz_name))
        is_weekend = now.weekday() >= 5
        t = now.time()
        time_str = now.strftime("%I:%M %p")
        if is_weekend:
            return "🔴 Closed (Weekend)", time_str
        if lunch_break and lunch_break[0] <= t < lunch_break[1]:
            return "🟡 Lunch Break", time_str
        if open_time <= t <= close_time:
            return "🟢 OPEN", time_str
        if pre_open and pre_open <= t < open_time:
            return "🟡 Pre-Market", time_str
        if post_close and close_time < t <= post_close:
            return "🟣 After-Hours", time_str
        return "🔴 Closed", time_str

    ny_status, ny_time = get_market_status("America/New_York", dt_time(9, 30), dt_time(16, 0), dt_time(4, 0), dt_time(20, 0))
    lon_status, lon_time = get_market_status("Europe/London", dt_time(8, 0), dt_time(16, 30))
    tky_status, tky_time = get_market_status("Asia/Tokyo", dt_time(9, 0), dt_time(15, 30), lunch_break=(dt_time(11, 30), dt_time(12, 30)))
    in_status, in_time = get_market_status("Asia/Kolkata", dt_time(9, 15), dt_time(15, 30))

    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1.container(border=True):
        st.markdown("**🗽 New York**")
        st.caption("NYSE / NASDAQ")
        st.markdown(f"**Status:** {ny_status}")
        st.caption(f"Time: {ny_time} ET")
        st.caption("Regular: 09:30 AM – 04:00 PM ET")

    with m_col2.container(border=True):
        st.markdown("**🏛️ London**")
        st.caption("LSE")
        st.markdown(f"**Status:** {lon_status}")
        st.caption(f"Time: {lon_time} GMT")
        st.caption("Regular: 08:00 AM – 04:30 PM GMT")

    with m_col3.container(border=True):
        st.markdown("**🗼 Tokyo**")
        st.caption("TSE")
        st.markdown(f"**Status:** {tky_status}")
        st.caption(f"Time: {tky_time} JST")
        st.caption("Regular: 09:00 AM – 03:30 PM JST")

    with m_col4.container(border=True):
        st.markdown("**🪷 Mumbai**")
        st.caption("NSE / BSE")
        st.markdown(f"**Status:** {in_status}")
        st.caption(f"Time: {in_time} IST")
        st.caption("Regular: 09:15 AM – 03:30 PM IST")

    st.caption("💡 *Market sessions automatically update in real-time based on local exchange time zones.*")

    st.markdown("---")

    # --- Bottom Row: Future Updates, App Status, Collaboration ---
    b_col1, b_col2, b_col3 = st.columns(3)

    with b_col1:
        with st.container(border=True):
            st.markdown("### 🚀 Future Updates")
            st.markdown("""
            - 🧠 Advanced AI stock predictions & sentiment:  
              [**Stockly.ai**](https://stockly-ai.streamlit.app)
            - 📊 Real-time portfolio rebalancing alerts coming soon!
            """)

    with b_col2:
        with st.container(border=True):
            st.markdown("### ⚡ App Status")
            st.markdown("""
            <div style="height:120px; display:flex; justify-content:center; align-items:center;">
                <a href="https://live-stock.betteruptime.com/" target="_blank">
                    <img src="https://uptime.betterstack.com/status-badges/v1/monitor/196o6.svg" 
                         alt="Uptime Badge" 
                         style="transform: scale(2.4); transform-origin: center;">
                </a>
            </div>
            """, unsafe_allow_html=True)

    with b_col3:
        with st.container(border=True):
            st.markdown("### 🤝 Collaboration")
            st.markdown("""
            Interested in collaborating or hiring?  
            - 📧 Contact: anshkunwar3009@gmail.com  
            - 🧠 Projects: [streamlit](https://share.streamlit.io/user/anshk1234)  
            - 🌐 GitHub: [github](https://github.com/anshk1234)         
            """)

#sidebar
symbols = {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Tesla": "TSLA",
    "NVIDIA": "NVDA",
    "Amazon": "AMZN",
    "Google": "GOOG",
    "Meta": "META"
}


@st.cache_data(ttl=3600)  # cache for 1 hour
def get_daily_details(symbols):
    details = {}
    for name, ticker in symbols.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            if not hist.empty:
                if len(hist) >= 2:
                    prev_close = hist["Close"].iloc[-2]
                    close_price = hist["Close"].iloc[-1]
                    change_pct = ((close_price - prev_close) / prev_close) * 100 if prev_close else 0.0
                else:
                    open_price = hist["Open"].iloc[0]
                    close_price = hist["Close"].iloc[0]
                    change_pct = ((close_price - open_price) / open_price) * 100 if open_price else 0.0
                details[name] = {
                    "price": close_price,
                    "change_pct": change_pct
                }
        except Exception:
            pass
    return details

with st.sidebar:
    st.header("📈 Daily Snapshot")

    details = get_daily_details(symbols)

    if details:
        # Find best and worst
        best_stock = max(details, key=lambda x: details[x]["change_pct"])
        worst_stock = min(details, key=lambda x: details[x]["change_pct"])

        best_price = details[best_stock]['price']
        best_pct = details[best_stock]['change_pct']
        best_price_str = f"${best_price:.2f}" if isinstance(best_price, (int, float)) else str(best_price)
        best_pct_str = f"{best_pct:+.2f}%" if isinstance(best_pct, (int, float)) else "0.00%"

        worst_price = details[worst_stock]['price']
        worst_pct = details[worst_stock]['change_pct']
        worst_price_str = f"${worst_price:.2f}" if isinstance(worst_price, (int, float)) else str(worst_price)
        worst_pct_str = f"{worst_pct:+.2f}%" if isinstance(worst_pct, (int, float)) else "0.00%"

        # Best stock card
        with st.container(border=True):
            st.markdown("### Today’s Best Stock")
            st.markdown(f"**{best_stock}**")
            st.metric("💵 Price", best_price_str, best_pct_str)

        # Worst stock card
        with st.container(border=True):
            st.markdown("### Today’s Worst Stock")
            st.markdown(f"**{worst_stock}**")
            st.metric("💵 Price", worst_price_str, worst_pct_str)
    else:
        st.info("No performance data available today.")


st.sidebar.markdown("---")
st.sidebar.markdown("### 🙌 Credits")
st.sidebar.markdown("""
- 👨‍💻 **Developed by**: Ansh Kunwar
- 📊 **Data Source**: [Yahoo Finance](https://finance.yahoo.com)  
- 🖼️ **Logos**: Wikimedia Commons  
- ⚙️ **Tech Stack**: Streamlit + Plotly  
- 🧠 **Source Code**: [Github](https://github.com/anshk1234/live-stock-market-prices)  
- 🌐 **see other projects**: [streamlit.io/ansh kunwar](https://share.streamlit.io/user/anshk1234)  
- 📧 **Contact**: anshkunwar3009@gmail.com     
-  This App is Licensed Under **Apache License 2.0**
    
""") 

st.sidebar.markdown("<br><center>© 2025 Live Stock Dashboard</center>", unsafe_allow_html=True)
    
# ---- Footer ----
st.markdown("<p style='text-align:center; color:white;'>© 2025 Live Stock Dashboard | Powered by Yahoo Finance</p>", unsafe_allow_html=True)

