import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro Max", layout="wide")

@st.cache_data(ttl=86400)
def get_all_us_tickers():
    tickers = set()
    try:
        urls = ['https://en.wikipedia.org/wiki/List_of_S%26P_500_companies', 
                'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies',
                'https://en.wikipedia.org/wiki/Nasdaq-100']
        for url in urls:
            df = pd.read_html(url)[0]
            col = 'Symbol' if 'Symbol' in df.columns else 'Ticker' if 'Ticker' in df.columns else 'Ticker symbol'
            tickers.update(df[col].str.replace('.', '-', regex=False).tolist())
    except:
        tickers = {'AAPL', 'MSFT', 'AMD', 'NVDA', 'TSLA', 'GOOGL', 'AMZN'}
    return list(tickers)

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def process_stock_data(ticker, info, history):
    close = history['Close'].dropna()
    rsi = calculate_rsi(close).iloc[-1] if len(close) > 14 else 50
    pe = info.get('trailingPE', 0) or 0
    target = info.get('targetMeanPrice', 0)
    current = info.get('currentPrice', 1)
    growth_pot = round(((target - current) / current) * 100, 1) if target and current else 0

    if rsi < 40: signal, color = "🚨 ХҮЧТЭЙ ХУДАЛДАЖ АВАХ", "green"
    elif rsi < 60: signal, color = "✅ ХУДАЛДАЖ АВАХ", "lightgreen"
    else: signal, color = "🔲 СУУЖ БАЙХ", "orange"

    radar_df = pd.DataFrame({
        "Үзүүлэлт": ["RSI (Хүч)", "Үнэлгээ (P/E)", "Өсөлт"], 
        "Оноо": [max(0, 100 - rsi), max(0, 100 - (pe * 2)), max(0, min(100, growth_pot))]
    })
    return {
        "Тикер": ticker, "Компани": info.get('longName', ticker), 
        "Салбар": info.get('sector', 'Unknown'), "RSI": round(rsi, 1), 
        "Сигнал": signal, "signal_color": color, 
        "Өсөх Боломж": f"{growth_pot}%", "history_df": history, "radar": radar_df
    }

def get_screened_data(strat, sector_sel):
    screened = []
    for t in get_all_us_tickers(): 
        try:
            s = yf.Ticker(t)
            info = s.info
            hist = s.history(period="1y")
            if len(hist) < 30: continue
            
            pe = info.get('trailingPE', 0) or 0
            forward_pe = info.get('forwardPE', 0) or 0
            rev_growth = info.get('revenueGrowth', 0) or 0
            rsi = calculate_rsi(hist['Close']).iloc[-1]
            
            if strat == "1. Төгс боломж (Хатуу)" and 0 < pe < 30 and rsi < 50:
                screened.append(process_stock_data(t, info, hist))
            elif strat == "2. Тренд дагах (Уян хатан)" and rsi < 75:
                screened.append(process_stock_data(t, info, hist))
            elif strat == "3. Ирээдүйн өсөлт (Turnaround)" and forward_pe > 0 and forward_pe < 25 and rev_growth > 0.15:
                screened.append(process_stock_data(t, info, hist))
        except: continue
    return screened

st.sidebar.title("⚙️ Удирдах Цэс")
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж (Хатуу)", "2. Тренд дагах (Уян хатан)", "3. Ирээдүйн өсөлт (Turnaround)"))
sector = st.sidebar.selectbox("Салбар:", ["Бүх салбар", "Technology", "Healthcare"])

if st.sidebar.button("🚀 Хувьцааг Шүүх"):
    with st.spinner("Хувьцаануудыг шүүж байна..."):
        st.session_state.data = get_screened_data(strategy, sector)

if 'data' in st.session_state and st.session_state.data:
    df = pd.DataFrame(st.session_state.data)
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("🔍 Жагсаалт")
        selected = st.selectbox("Хувьцаа сонгох:", df["Тикер"].tolist())
        st.dataframe(df[["Тикер", "Сигнал", "RSI"]], use_container_width=True)
    with col2:
        stock = next(item for item in st.session_state.data if item["Тикер"] == selected)
        st.subheader(f"📊 {stock['Тикер']} Хянах Самбар")
        tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "📉 График", "🕸️ Радар"])
        with tab1:
            st.info(f"Салбар: {stock['Салбар']} | RSI: {stock['RSI']}")
            # ЗАЙГҮЙ БИЧИХ ДҮРЭМ
            st.markdown(f"**Сигнал:** :{stock['signal_color']}[{stock['Сигнал']}]")
            st.success(f"📈 Шинжээчдийн таамгаар өсөх боломж: **{stock['Өсөх Боломж']}**")
        with tab2:
            st.plotly_chart(px.line(stock['history_df'], y='Close'), use_container_width=True)
        with tab3:
            fig = px.line_polar(stock['radar'], r='Оноо', theta='Үзүүлэлт', line_close=True)
            fig.update_traces(fill='toself')
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Стратегиа сонгоод 'Хувьцааг Шүүх' товчийг дарна уу.")
