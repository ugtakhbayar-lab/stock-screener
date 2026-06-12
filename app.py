import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Тохиргоо
st.set_page_config(page_title="Pro Stock Analyst", layout="wide")

# 2. Session State
if 'results' not in st.session_state: st.session_state.results = []
if 'selected_stock' not in st.session_state: st.session_state.selected_stock = None

# 3. Дата татах функц
@st.cache_data(ttl=3600)
def get_all_us_tickers():
    return pd.DataFrame({"Symbol": ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "AMD", "META"], "Sector": ["Technology"]*8})

def get_stock_data(ticker, strategy):
    try:
        s = yf.Ticker(ticker)
        info = s.info
        pe = info.get('trailingPE') or 0
        target = info.get('targetMeanPrice') or 0
        current = info.get('currentPrice') or 1
        
        # Шүүлтүүр
        if strategy == "1. Төгс боломж" and (0 < pe < 25): passed = True
        elif strategy == "2. Тренд дагах" and (target > current): passed = True
        else: passed = False
        
        if not passed: return None
        return {"Тикер": ticker, "Компани": info.get('longName', ticker), "price": current, "news": s.news[:3] if s.news else []}
    except: return None

# 4. Sidebar
st.sidebar.title("🛠️ Тохиргоо")
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж", "2. Тренд дагах"))
if st.sidebar.button("🚀 ШИНЖИЛГЭЭГ АЖИЛЛУУЛАХ"):
    ticker_df = get_all_us_tickers()
    results = []
    bar = st.progress(0)
    for i, row in ticker_df.iterrows():
        data = get_stock_data(row['Symbol'], strategy)
        if data: results.append(data)
        bar.progress((i + 1) / len(ticker_df))
    st.session_state.results = results
    st.session_state.selected_stock = None
    st.rerun()

# 5. Үр дүн харуулах
if st.session_state.results:
    st.subheader("📊 Олдсон хувьцаанууд")
    for idx, stock in enumerate(st.session_state.results):
        c1, c2, c3 = st.columns([1, 2, 1])
        c1.write(stock['Тикер'])
        c2.write(stock['Компани'])
        if c3.button("🔍 Харах", key=f"btn_{idx}"):
            st.session_state.selected_stock = stock
            st.rerun()

# 6. Сонгосон хувьцааг харуулах
if st.session_state.selected_stock:
    stock = st.session_state.selected_stock
    st.divider()
    st.header(f"📊 {stock['Тикер']} - {stock['Компани']}")
    st.metric("Одоогийн үнэ", f"${stock['price']}")
    
    hist = yf.Ticker(stock['Тикер']).history(period="3mo")
    if not hist.empty:
        st.line_chart(hist['Close'])
        
    st.subheader("📰 Сүүлийн мэдээ")
    for n in stock.get('news', []):
        st.write(f"• {n.get('title')}")
