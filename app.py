import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Хуудасны тохиргоо
st.set_page_config(page_title="Pro Stock Analyst v2.0", layout="wide", initial_sidebar_state="expanded")

# --- SESSION STATE ЭХЛҮҮЛЭХ ---
if 'results' not in st.session_state: st.session_state.results = []
if 'watchlist' not in st.session_state: st.session_state.watchlist = []

# 2. Дата татах функцүүд
@st.cache_data(ttl=3600)
def get_all_us_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df = pd.read_csv(url)
        return df[['Symbol', 'Sector']].astype(str)
    except:
        return pd.DataFrame({"Symbol": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"], "Sector": ["Technology"]*5})

def get_rsi(ticker, period=14):
    try:
        hist = yf.Ticker(ticker).history(period="3mo")
        if len(hist) < period: return 50
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs.iloc[-1]))
    except: return 50

def get_stock_data(ticker, strategy, sector_name):
    try:
        s = yf.Ticker(ticker)
        info = s.info
        if not info: return None
        
        # Салбараар шүүх
        current_sector = info.get('sector', 'Unknown')
        if sector_name != "All" and sector_name != current_sector: return None

        pe = info.get('trailingPE') or 0
        fpe = info.get('forwardPE') or 0
        growth = info.get('revenueGrowth') or 0
        target = info.get('targetMeanPrice') or 0
        current = info.get('currentPrice') or 1
        rsi = get_rsi(ticker)
        
        passed = False
        if rsi < 45: 
            if strategy == "1. Төгс боломж" and (0 < pe < 20) and (growth > 0.10): passed = True
            elif strategy == "2. Тренд дагах (Уян хатан)" and ((target - current) / current) >= 0.15: passed = True
            elif strategy == "3. Ирээдүйн өсөлт (Turnaround)" and (0 < fpe < 25) and (growth > 0.10): passed = True
        
        if not passed: return None
        
        radar_df = pd.DataFrame({
            "Үзүүлэлт": ["P/E", "Өсөлт", "Боломж", "RSI (Inv)"],
            "Оноо": [max(0, min(100, 100 - pe)), min(100, growth * 100), min(100, ((target - current)/current)*100), max(0, min(100, 100 - rsi))]
        })

        return {
            "Тикер": ticker, "Компани": info.get('longName', ticker), "Sector": current_sector,
            "rsi": round(rsi, 1), "price": current, "growth_pot": round(((target - current) / current) * 100, 1),
            "pe": pe, "radar_df": radar_df, "news": s.news[:5] if s.news else []
        }
    except: return None

# --- SIDEBAR ---
st.sidebar.title("🛠️ Тохиргоо")
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж", "2. Тренд дагах (Уян хатан)", "3. Ирээдүйн өсөлт (Turnaround)"))
all_sectors = ["All", "Technology", "Financials", "Healthcare", "Energy", "Industrials", "Consumer Discretionary", "Consumer Staples", "Utilities", "Real Estate", "Materials", "Communication Services"]
sector_choice = st.sidebar.selectbox("Салбар сонгох:", all_sectors)

if st.sidebar.button("🚀 ШИНЖИЛГЭЭГ АЖИЛЛУУЛАХ"):
    ticker_df = get_all_us_tickers()
    results = []
    bar = st.progress(0)
    for i, row in ticker_df.iterrows():
        data = get_stock_data(row['Symbol'], strategy, sector_choice)
        if data: results.append(data)
        bar.progress((i + 1) / len(ticker_df))
    st.session_state.results = results
    st.rerun()

# --- ҮР ДҮН ---
if st.session_state.results:
    df_res = pd.DataFrame(st.session_state.results)
    selected = st.dataframe(df_res[["Тикер", "Компани", "Sector", "rsi", "price", "growth_pot"]], use_container_width=True, on_select="rerun", selection_mode="single-row")
    
    if selected.selection.rows:
        idx = selected.selection.rows[0]
        if idx < len(st.session_state.results):
            stock = st.session_state.results[idx]
            st.divider()
            col_main, col_news = st.columns([2, 1])
            with col_main:
                st.header(f"{stock['Тикер']} - {stock['Компани']}")
                if st.button("⭐ Watchlist-д нэмэх"):
                    if stock['Тикер'] not in [s['Тикер'] for s in st.session_state.watchlist]:
                        st.session_state.watchlist.append(stock)
                st.line_chart(yf.Ticker(stock['Тикер']).history(period="3mo")['Close'])
                st.plotly_chart(px.line_polar(stock['radar_df'], r='Оноо', theta='Үзүүлэлт', line_close=True, range_r=[0,100]), use_container_width=True)
            with col_news:
                st.subheader("📰 Сүүлийн мэдээ")
                for n in stock['news']: st.markdown(f"**[{n['title']}]({n['link']})**")

if st.session_state.watchlist:
    st.divider()
    st.subheader("⭐ Миний Watchlist")
    st.table(pd.DataFrame(st.session_state.watchlist)[["Тикер", "price", "growth_pot"]])
