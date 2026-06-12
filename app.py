import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 🖥️ ДЭЛГЭЦИЙГ ӨРГӨНӨӨР НЬ БҮРЭН ДҮҮРГЭХ
st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro Max", layout="wide")

# 1. ХАЖУУГИЙН ЦЭС
st.sidebar.title("⚙️ Удирдах Цэс")
strategy = st.sidebar.radio("Хөрөнгө оруулалтын стратеги:", ("1. Төгс боломж (Хатуу шалгуур)", "2. Тренд дагах (Уян хатан шалгуур)"))
sector_choice = st.sidebar.selectbox("Салбараар шүүх:", ("Бүх салбар", "Technology", "Healthcare", "Financial Services", "Consumer Cyclical", "Industrials", "Energy"))
st.sidebar.write("---")
# Шүүх товч нэмсэн
if st.sidebar.button("🚀 Хувьцааг Шүүх"):
    st.session_state.run_screen = True
else:
    if 'run_screen' not in st.session_state: st.session_state.run_screen = False

search_ticker = st.sidebar.text_input("🔍 Шууд хувьцаа хайх (Жишээ нь: OSCR, AAPL):").upper().strip()

st.title("📈 Хос Стратегит & Автомат Зөвлөхтэй Хувьцаа Шүүгч")

@st.cache_data(ttl=86400)
def get_all_us_tickers():
    return ['AAPL', 'MSFT', 'VALE', 'F', 'GM', 'AMD', 'BAC', 'JPM', 'OSCR', 'TSLA', 'NVDA']

TICKERS = get_all_us_tickers()

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def process_stock_data(ticker, info, history):
    pe = info.get('trailingPE')
    pb = info.get('priceToBook')
    current_price = info.get('currentPrice')
    sector = info.get('sector', 'Unknown')
    close_prices = history['Close'].dropna()
    current_rsi = calculate_rsi(close_prices).iloc[-1] if len(close_prices) > 14 else 50
    target_price = info.get('targetMeanPrice')
    potential_growth = round(((target_price - current_price) / current_price) * 100, 1) if target_price and current_price else "N/A"
    
    if current_rsi < 35:
        signal = "🚨 ХҮЧТЭЙ ХУДАТДАЖ АВАХ"
        signal_color = "green"
    elif current_rsi < 55:
        signal = "✅ ХУДАТДАЖ АВАХ"
        signal_color = "lightgreen"
    else:
        signal = "🔲 СУУЖ БАЙХ"
        signal_color = "orange"
        
    return {
        "Тикер": ticker, "Компани": info.get('longName', ticker), "Салбар": sector,
        "Өнөөгийн Үнэ": current_price, "Шинжээчдийн Таамаг": target_price or 0,
        "Өсөх Боломж (%)": f"{potential_growth}%", "RSI": round(current_rsi, 1),
        "Сигнал": signal, "signal_color": signal_color, "potential_raw": potential_growth if potential_growth != "N/A" else -999,
        "history_df": history, "radar": [{"Үзүүлэлт": "RSI", "Оноо": current_rsi}]
    }

def get_screened_data(strat_selection, sector_sel):
    screened = []
    for ticker in TICKERS[:20]: # Түргэн ажиллахын тулд цөөн тикер сонгов
        try:
            stock = yf.Ticker(ticker)
            history = stock.history(period="1y")
            if len(history) >= 30:
                screened.append(process_stock_data(ticker, stock.info, history))
        except: continue
    return screened

# Логик
if search_ticker:
    s_stock = yf.Ticker(search_ticker)
    show_data = [process_stock_data(search_ticker, s_stock.info, s_stock.history(period="1y"))]
elif st.session_state.run_screen:
    show_data = get_screened_data(strategy, sector_choice)
else:
    show_data = []

# Дэлгэц
if show_data:
    df = pd.DataFrame(show_data).sort_values(by="potential_raw", ascending=False)
    col1, col2 = st.columns([1.0, 1.0])
    with col1:
        st.subheader("🔍 Жагсаалт")
        selected_ticker = st.selectbox("Хувьцаа сонгох:", df["Тикер"].tolist())
        st.dataframe(df[["Тикер", "Сигнал", "RSI"]], use_container_width=True)
    with col2:
        selected_stock = next(item for item in show_data if item["Тикер"] == selected_ticker)
        st.subheader(f"📊 {selected_ticker} Хянах Самбар")
        tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "📉 График", "🕸️ Радар"])
        with tab1: st.info(f"Салбар: {selected_stock['Салбар']}")
        with tab2: st.plotly_chart(px.line(selected_stock['history_df'], y='Close'), use_container_width=True)
        with tab3: st.plotly_chart(px.line_polar(pd.DataFrame(selected_stock['radar']), r='Оноо', theta='Үзүүлэлт'), use_container_width=True)
else:
    st.info("Хувьцааг шүүх товчийг дарна уу.")
