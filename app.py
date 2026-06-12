import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro", layout="wide")

# КЭШ-ийг 1 секунд болгож цэвэрлэв
@st.cache_data(ttl=1)
def get_all_us_tickers():
    tickers = set()
    # S&P 500
    try:
        url_sp = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df_sp = pd.read_csv(url_sp)
        tickers.update(df_sp['Symbol'].astype(str).tolist())
    except: pass
    
    # Russell 2000
    try:
        url_r2k = "https://en.wikipedia.org/wiki/List_of_Russell_2000_component_companies"
        df_r2k = pd.read_html(url_r2k)[0]
        tickers.update(df_r2k['Ticker'].astype(str).tolist())
    except: pass
    
    return [t.replace('.', '-') for t in list(tickers)]

def get_stock_data(ticker, strategy):
    s = yf.Ticker(ticker)
    try:
        info = s.info
        hist = s.history(period="1y")
        if hist.empty: return None
        pe = info.get('trailingPE') or 0
        fpe = info.get('forwardPE') or 0
        growth = info.get('revenueGrowth') or 0
        target = info.get('targetMeanPrice') or 0
        current = info.get('currentPrice') or 1
        if strategy == "1. Төгс боломж" and not (0 < pe < 20 and growth > 0.1): return None
        if strategy == "2. Тренд дагах (Уян хатан)" and ((target - current) / current) < 0.1: return None
        if strategy == "3. Ирээдүйн өсөлт (Turnaround)" and not (0 < fpe < 25 and growth > 0.2): return None
        radar_df = pd.DataFrame({"Үзүүлэлт": ["RSI", "P/E", "Өсөлт"], "Оноо": [50, max(0, 100 - (pe*2)), min(100, growth*1000)]})
        return {"Тикер": ticker, "Компани": info.get('longName', ticker), "info": info, "hist": hist, "radar": radar_df, "growth_pot": round(((target - current) / current) * 100, 1), "signal_color": "green"}
    except: return None

st.sidebar.title("⚙️ Удирдах Цэс")
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж", "2. Тренд дагах (Уян хатан)", "3. Ирээдүйн өсөлт (Turnaround)"))

if st.button("🚀 БҮХ ХУВЬЦААГ ШҮҮХ"):
    all_tickers = get_all_us_tickers()
    st.write(f"🌐 {len(all_tickers)} хувьцаа шүүж эхэллээ...")
    data = []
    progress_bar = st.progress(0)
    for i, t in enumerate(all_tickers):
        res = get_stock_data(t, strategy)
        if res: data.append(res)
        progress_bar.progress((i + 1) / len(all_tickers))
    st.session_state.data = data
    st.success(f"✅ Дууслаа! {len(data)} хувьцаа тэнцлээ.")

if 'data' in st.session_state and st.session_state.data:
    df = pd.DataFrame(st.session_state.data)
    event = st.dataframe(df[["Тикер", "Компани"]], use_container_width=True, on_select="rerun", selection_mode="single-row")
    if event.selection["rows"]:
        st.session_state.selected_ticker = df.iloc[event.selection["rows"][0]]["Тикер"]
    if st.session_state.selected_ticker:
        stock = next(item for item in st.session_state.data if item["Тикер"] == st.session_state.selected_ticker)
        st.subheader(f"📊 {stock['Тикер']} - {stock['Компани']}")
        tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "🕸️ Радар", "📉 График"])
        with tab1:
            st.markdown(f"**Сигнал:** :{stock['signal_color']}[ХУДАЛДАЖ АВАХ]")
            st.success(f"📈 Өсөх боломж: **{stock['growth_pot']}%**")
        with tab2:
            st.plotly_chart(px.line_polar(stock['radar'], r='Оноо', theta='Үзүүлэлт', line_close=True), use_container_width=True)
        with tab3:
            st.plotly_chart(px.line(stock['hist'], y='Close'), use_container_width=True)
