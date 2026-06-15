import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ─── Хуудасны тохиргоо ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="Ухаалаг Хувьцаа Шүүгч Pro",
    layout="wide",
    page_icon="📈"
)

# ─── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 60%, #1c2333 100%);
        border: 1px solid #30363d;
        padding: 2rem 2.5rem;
        border-radius: 14px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 { color: #58a6ff; font-size: 2.2rem; font-weight: 800; margin: 0; }
    .main-header p  { color: #8b949e; margin: 0.4rem 0 0; font-size: 1rem; }
    .badge-buy   { background:#1a7f64; color:#fff; padding:4px 14px; border-radius:20px; font-weight:700; }
    .badge-watch { background:#9a6700; color:#fff; padding:4px 14px; border-radius:20px; font-weight:700; }
    .badge-hold  { background:#6e3c14; color:#fff; padding:4px 14px; border-radius:20px; font-weight:700; }
    .score-label { font-size:0.85rem; color:#8b949e; }
    [data-testid="stSidebar"] { background: #0d1117; border-right: 1px solid #21262d; }
    [data-testid="stSidebar"] .stRadio label { color: #c9d1d9 !important; }
    .stDataFrame tbody tr:hover { background: rgba(88,166,255,0.07) !important; }
    [data-testid="stMetricDelta"] svg { display:none; }
</style>
""", unsafe_allow_html=True)


# ─── Өгөгдөл авах ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_sp500_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df = pd.read_csv(url)
        return df['Symbol'].astype(str).tolist()
    except:
        return ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","JPM","V","JNJ",
                "UNH","XOM","PG","HD","MA","MRK","ABBV","CVX","PEP","KO"]


@st.cache_data(ttl=3600)
def get_russell2000_tickers():
    sources = [
        "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/russell2000/russell2000_tickers.txt",
        "https://raw.githubusercontent.com/datasets/russell-2000/master/data/constituents.csv",
    ]
    for url in sources:
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=10) as r:
                content = r.read().decode("utf-8")
            if url.endswith(".txt"):
                tickers = [t.strip() for t in content.splitlines() if t.strip()]
            else:
                df = pd.read_csv(pd.io.common.StringIO(content))
                tickers = df.iloc[:, 0].astype(str).tolist()
            if len(tickers) > 100:
                return tickers
        except:
            continue
    return [
        "SMCI","KRYS","CRVS","PRCT","ACAD","PRLB","BLFS","HIMS","RXO","CARG",
        "IRTC","NVST","FRSH","IIPR","RGEN","STAA","NSIT","LPSN","OMCL","BRKL",
        "CLBT","CALX","SFNC","MGNI","ASTS","JOBY","IONQ","ARQT","WOLF","MRUS",
        "VERX","SPNT","INVA","AMRC","FXNC","HAFC","AMPH","CCSI","CLOV","MNTV",
        "TNDM","FLNC","NVCR","CBRL","PLAY","WING","FAT","SHAK","DNUT","CAVA",
        "BROS","ARCO","PTGX","FLGT","AXSM","ACLS","FORM","AMBA","AEHR","SMPL",
        "EOLS","HALO","INMD","TGTX","RCUS","IMVT","NRIX","PRAX","KROS","DAWN",
        "LSCC","OSIS","ICHR","NOVT","DIOD","ONTO","COHU","AEIS","RMBS","POWI",
        "MGRC","PLXS","IIVI","BEL","CTS","KLIC","MKSI","AMAT","CREE","IMOS",
    ]


@st.cache_data(ttl=3600)
def get_tickers_for_universe(universe):
    if universe == "S&P 500 (~500)":
        return get_sp500_tickers(), 2_000_000_000
    elif universe == "Russell 2000 (~2000)":
        return get_russell2000_tickers(), 200_000_000
    else:
        sp  = get_sp500_tickers()
        r2k = get_russell2000_tickers()
        combined = list(dict.fromkeys(sp + r2k))
        return combined, 200_000_000


# ─── Техник шинжилгээ ─────────────────────────────────────────────────────────
def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    delta = prices.diff()
    gain  = delta.where(delta > 0, 0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs    = gain / loss.replace(0, 1e-9)
    return round(float(100 - 100 / (1 + rs.iloc[-1])), 1)


def calc_macd_hist(prices):
    if len(prices) < 26:
        return 0.0
    ema12  = prices.ewm(span=12, adjust=False).mean()
    ema26  = prices.ewm(span=26, adjust=False).mean()
    macd   = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1] - signal.iloc[-1])


def calc_momentum(prices, days=22):
    if len(prices) < days:
        return 0.0
    return round((prices.iloc[-1] / prices.iloc[-days] - 1) * 100, 2)


# ─── Оноо тооцоолол ──────────────────────────────────────────────────────────
def calc_score(pe, fpe, growth, rsi, upside, macd_hist, analyst_rec, strategy):
    s = 0
    if strategy == "1. Төгс боломж":
        if 0 < pe < 12:   s += 25
        elif 0 < pe < 20: s += 15
        if growth > 0.15:   s += 20
        elif growth > 0.08: s += 10
        if rsi < 30:   s += 25
        elif rsi < 40: s += 15
        if upside > 30:  s += 20
        elif upside > 15: s += 10
        if macd_hist > 0: s += 10
    elif strategy == "2. Тренд дагах (Уян хатан)":
        if 55 < rsi < 68:   s += 30
        elif 50 < rsi < 72: s += 18
        if macd_hist > 0:  s += 25
        if upside > 20:   s += 20
        elif upside > 12: s += 10
        if growth > 0.15:   s += 15
        elif growth > 0.08: s += 8
        if 0 < fpe < 30: s += 10
    elif strategy == "3. Ирээдүйн өсөлт (Turnaround)":
        if growth > 0.25:   s += 30
        elif growth > 0.12: s += 18
        if 0 < fpe < 18:   s += 25
        elif 0 < fpe < 28: s += 14
        if upside > 25:   s += 20
        elif upside > 15: s += 10
        if 35 < rsi < 60: s += 15
        if macd_hist > 0:  s += 10
    if analyst_rec and 0 < analyst_rec < 2.0: s += 10
    elif analyst_rec and analyst_rec < 2.5:   s += 5
    return min(100, s)


def get_signal(score, upside):
    if score >= 68 and upside > 15:
        return "🟢 ХУДАЛДАЖ АВ", "#1a7f64"
    elif score >= 48:
        return "🟡 АЖИГЛА", "#9a6700"
    else:
        return "🔴 БОЛГООМЖИЛ", "#6e3c14"


# ─── Нэг хувьцааны өгөгдөл ───────────────────────────────────────────────────
def get_stock_data(ticker, strategy, min_cap=2_000_000_000):
    try:
        s    = yf.Ticker(ticker)
        info = s.info
        if not info or info.get('quoteType') not in ('EQUITY',):
            return None
        pe            = info.get('trailingPE')    or 0
        fpe           = info.get('forwardPE')     or 0
        growth        = info.get('revenueGrowth') or 0
        earn_growth   = info.get('earningsGrowth') or 0
        target        = info.get('targetMeanPrice') or 0
        current       = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        market_cap    = info.get('marketCap')    or 0
        analyst_rec   = info.get('recommendationMean') or 3
        analyst_count = info.get('numberOfAnalystOpinions') or 0
        beta          = info.get('beta') or 1
        if current <= 0 or market_cap < min_cap:
            return None
        hist = s.history(period="6mo")
        if len(hist) < 30:
            return None
        rsi       = calc_rsi(hist['Close'])
        macd_hist = calc_macd_hist(hist['Close'])
        mom_1m    = calc_momentum(hist['Close'], 22)
        mom_3m    = calc_momentum(hist['Close'], 66)
        upside    = round(((target - current) / current * 100), 1) if target > 0 else 0
        avg_vol    = hist['Volume'].mean()
        recent_vol = hist['Volume'].iloc[-5:].mean()
        vol_ratio  = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 1
        passed = False
        if strategy == "1. Төгс боломж":
            passed = (rsi < 40 and 0 < pe < 20 and growth > 0.08 and upside > 15)
        elif strategy == "2. Тренд дагах (Уян хатан)":
            passed = (50 < rsi < 72 and macd_hist > 0 and upside > 15 and mom_1m > 0)
        elif strategy == "3. Ирээдүйн өсөлт (Turnaround)":
            passed = (rsi < 60 and 0 < fpe < 28 and growth > 0.12 and upside > 15)
        if not passed:
            return None
        score =
