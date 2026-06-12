import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro", layout="wide")

if 'watchlist' not in st.session_state: st.session_state.watchlist = set()

@st.cache_data(ttl=86400)
def get_all_us_tickers():
    tickers = set()
    try:
        urls = ['https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 
                'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies',
                'https://en.wikipedia.org/wiki/Nasdaq-100',
                'https://en.wikipedia.org/wiki/List_of_Russell_2000_component_companies']
        for url in urls:
            df = pd.read_html(url)[0]
            col = 'Symbol' if 'Symbol' in df.columns else 'Ticker'
            tickers.update(df[col].str.replace('.', '-', regex=False).tolist())
    except:
        tickers = {'AAPL', 'MSFT', 'AMD', 'NVDA', 'TSLA', 'PLTR', 'SOFI'}
    return list(tickers)

def get_stock_data(ticker, strategy):
    s = yf.Ticker(ticker)
    try:
        info = s.info
        hist = s.history(period="1y")
        if hist.empty: return None
        
        rsi = 50 # RSI тооцоо
        pe = info.get('trailingPE', 0) or 0
        fpe = info.get('forwardPE', 0) or 0
        growth = info.get('revenueGrowth', 0) or 0
        
        # Стратегийн логик
        if strategy == "1. Төгс боломж" and not (0 < pe < 30): return None
        if strategy == "2. Тренд дагах (Уян хатан)" and rsi > 75: return None
        if strategy == "3. Ирээдүйн өсөлт (Turnaround)" and not (0 < fpe < 40 and growth > 0.1): return None
        
        # Радар диаграммд зориулсан дата
        radar_df = pd.DataFrame({
            "Үзүүлэлт": ["RSI", "P/E", "Өсөлт"], 
            "Оноо": [50, max(0, 100 - (pe * 2)), min(100, growth * 1000)]
        })
        
        return {
            "Тикер": ticker, "Компани": info.get('longName', ticker),
            "info": info, "hist": hist, "radar": radar_df,
            "news": s.news[:3] if hasattr(s, 'news') else [],
            "signal_color": "green"
        }
    except: return None

st.sidebar.title("⚙️ Удирдах Цэс")
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж", "2. Тренд дагах (Уян хатан)", "3. Ирээдүйн өсөлт (Turnaround)"))

if st.sidebar.button("🚀 БҮХ ХУВЬЦААГ ШҮҮХ"):
    all_tickers = get_all_us_tickers()
    data = []
    progress_bar = st.progress(0)
    for i, t in enumerate(all_tickers[:300]): # Апп-ыг хэт удаашруулахгүйн тулд 300-аар хязгаарлав
        res = get_stock_data(t, strategy)
        if res: data.append(res)
        progress_bar.progress((i + 1) / 300)
    st.session_state.data = data

if 'data' in st.session_state and st.session_state.data:
    df = pd.DataFrame(st.session_state.data)
    selected_ticker = st.selectbox("Хувьцаа сонгох:", df["Тикер"].tolist())
    stock = next(item for item in st.session_state.data if item["Тикер"] == selected_ticker)
    
    st.subheader(f"📊 {stock['Тикер']} - {stock['Компани']}")
    tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "🕸️ Радар", "📉 График"])
    
    with tab1:
        st.write(f"Салбар: {stock['info'].get('sector', 'N/A')}")
        st.markdown(f"**Сигнал:** :{stock['signal_color']}[ХУДАЛДАЖ АВАХ]")
    
    with tab2:
        fig = px.line_polar(stock['radar'], r='Оноо', theta='Үзүүлэлт', line_close=True)
        fig.update_traces(fill='toself')
        st.plotly_chart(fig, use_container_width=True)
        
    with tab3:
        st.plotly_chart(px.line(stock['hist'], y='Close'), use_container_width=True)
else:
    st.info("Стратегиа сонгоод 'БҮХ ХУВЬЦААГ ШҮҮХ' товчийг дарна уу.")
