import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro Max", layout="wide")

@st.cache_data(ttl=86400)
def get_all_us_tickers():
    # Бүх хувьцааг татах функц
    tickers = []
    try:
        url_500 = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tickers.extend(pd.read_html(url_500)[0]['Symbol'].str.replace('.', '-', regex=False).tolist())
        url_600 = 'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies'
        tickers.extend(pd.read_html(url_600)[0]['Ticker symbol'].str.replace('.', '-', regex=False).tolist())
    except:
        tickers = ['AAPL', 'MSFT', 'AMD', 'NVDA', 'TSLA', 'GOOGL', 'AMZN']
    return list(set(tickers))

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def process_stock_data(ticker, info, history):
    close = history['Close'].dropna()
    rsi = calculate_rsi(close).iloc[-1] if len(close) > 14 else 50
    pe = info.get('trailingPE', 20)
    target = info.get('targetMeanPrice', 0)
    current = info.get('currentPrice', 1)
    growth_pot = max(0, min(100, ((target - current) / current) * 100))
    
    # Зөв бичиглэл
    if rsi < 35: signal, color = "🚨 ХҮЧТЭЙ ХУДАЛДАЖ АВАХ", "green"
    elif rsi < 55: signal, color = "✅ ХУДАЛДАЖ АВАХ", "lightgreen"
    else: signal, color = "🔲 СУУЖ БАЙХ", "orange"
    
    pe_score = max(0, 100 - (pe * 2))
    radar_df = pd.DataFrame({
        "Үзүүлэлт": ["RSI (Хүч)", "Үнэлгээ (P/E)", "Өсөлт"], 
        "Оноо": [max(0, 100 - rsi), pe_score, growth_pot]
    })
    return {"Тикер": ticker, "Компани": info.get('longName', ticker), "Салбар": info.get('sector', 'Unknown'), "RSI": round(rsi, 1), "Сигнал": signal, "signal_color": color, "history_df": history, "radar": radar_df}

def get_screened_data(strat, sector_sel):
    screened = []
    # Энд [:] нь бүх 3100 хувьцааг шүүнэ гэсэн үг
    for t in get_all_us_tickers()[:]: 
        try:
            s = yf.Ticker(t)
            hist = s.history(period="1y")
            if len(hist) < 30: continue
            data = process_stock_data(t, s.info, hist)
            if strat == "1. Төгс боломж (Хатуу шалгуур)" and data['RSI'] < 40: screened.append(data)
            elif strat == "2. Тренд дагах (Уян хатан шалгуур)" and data['RSI'] < 65: screened.append(data)
        except: continue
    return screened

st.sidebar.title("⚙️ Удирдах Цэс")
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж (Хатуу шалгуур)", "2. Тренд дагах (Уян хатан шалгуур)"))
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
        with tab2:
            st.plotly_chart(px.line(stock['history_df'], y='Close'), use_container_width=True)
        with tab3:
            fig = px.line_polar(stock['radar'], r='Оноо', theta='Үзүүлэлт', line_close=True)
            fig.update_traces(fill='toself')
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Стратегиа сонгоод 'Хувьцааг Шүүх' товчийг дарна уу.")
