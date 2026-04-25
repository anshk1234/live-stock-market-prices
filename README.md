# 📈 Stockly — Live Stock Market Dashboard

A real-time stock market dashboard built with **Streamlit** and **yfinance**, offering live prices, historical comparisons, analyst ratings, financial news, and personal portfolio tracking — all in one place.

🔗 **Live App:** [live-stock-market-dashboard.streamlit.app](https://live-stock-market-dashboard.streamlit.app)

---

## Features

- **Live Stock Prices** — Fetch real-time price data for any publicly listed company using its ticker symbol.
- **Company Comparison** — Compare the historical performance of multiple companies on a single interactive chart.
- **Metrics & Analyst Ratings** — View key financial metrics and aggregated analyst buy/sell/hold recommendations.
- **Daily Market News** — Stay up to date with the latest stock market news relevant to your selected tickers.
- **Personal Portfolio** — Track your own investments, monitor gains/losses, and visualize your portfolio allocation.

---

## Tech Stack

| Library | Purpose |
|---|---|
| [Streamlit](https://streamlit.io/) | Web app framework |
| [yfinance](https://github.com/ranaroussi/yfinance) | Live & historical stock data |
| [Pandas](https://pandas.pydata.org/) | Data manipulation |
| [Plotly](https://plotly.com/python/) | Interactive charts |
| [Altair](https://altair-viz.github.io/) | Declarative visualizations |
| [streamlit-lottie](https://github.com/andfanilo/streamlit-lottie) | Lottie animations |
| [streamlit-echarts](https://github.com/andfanilo/streamlit-echarts) | ECharts-based visualizations |

---

## Getting Started

### Prerequisites

- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/anshk1234/live-stock-market-prices.git
cd live-stock-market-prices

# Install dependencies
pip install -r requirements.txt
```

### Running the App

```bash
streamlit run "stock dashboard.py"
```

The app will open in your browser at `http://localhost:8501`.

---

## Project Structure

```
live-stock-market-prices/
├── stock dashboard.py      # Main Streamlit application
├── Money Investment.json   # Portfolio / investment data
├── requirements.txt        # Python dependencies
├── .streamlit/             # Streamlit configuration
└── LICENSE                 # Apache 2.0 License
```

---

## License

This project is licensed under the [Apache 2.0 License](./LICENSE).

---

> If you find this project useful, please consider giving it a ⭐ on GitHub!
