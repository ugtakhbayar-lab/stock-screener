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
search_ticker = st.sidebar.text_input("🔍 Шууд хувьцаа хайх (Жишээ нь: OSCR, AAPL):").upper().strip()

st.title("📈 Хос Стратегит & Автомат Зөвлөхтэй Хувьцаа Шүүгч")

@st.cache_data(ttl=86400)
def get_all_us_tickers():
    tickers = []
    try:
        url_500 = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        tickers_500 = pd.read_html(url_500)[0]['Symbol'].str.replace('.', '-', regex=False).tolist()
        tickers.extend(tickers_500)
        url_600 = 'https://en.wikipedia.org/wiki/List_of_S%26P_600_companies'
        tickers_600 = pd.read_html(url_600)[0]['Ticker symbol'].str.replace('.', '-', regex=False).tolist()
        tickers.extend(tickers_600)
        url_2000 = 'https://en.wikipedia.org/wiki/List_of_Russell_2000_companies'
        tickers_2000 = pd.read_html(url_2000)[0]['Ticker'].str.replace('.', '-', regex=False).tolist()
        tickers.extend(tickers_2000)
        return list(set(tickers))
    except:
        return ['AAPL', 'MSFT', 'VALE', 'F', 'GM', 'AMD', 'BAC', 'JPM', 'OSCR']

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
        signal = "🚨 ХҮЧТЭЙ ХУДАТДАЖ АВАХ (Хэт унасан)"
        signal_color = "green"
    elif current_rsi < 55:
        signal = "✅ ХУДАТДАЖ АВАХ (Боломжит бүс)"
        signal_color = "lightgreen"
    elif current_rsi > 70:
        signal = "⚠️ ЗАРАХ / ТҮР ХҮЛЭЭХ (Хэт хөөссөн)"
        signal_color = "red"
    else:
        signal = "🔲 СУУЖ БАЙХ (Төвийг сахисан)"
        signal_color = "orange"
        
    return {
        "Тикер": ticker, "Компани": info.get('longName', ticker), "Салбар": sector,
        "Өнөөгийн Үнэ": current_price, "Шинжээчдийн Таамаг": target_price or 0,
        "Өсөх Боломж (%)": f"{potential_growth}%" if potential_growth != "N/A" else "N/A",
        "RSI": round(current_rsi, 1), "Сигнал": signal, "signal_color": signal_color,
        "potential_raw": potential_growth if potential_growth != "N/A" else -999,
        "high_target": info.get('targetHighPrice', current_price),
        "low_target": info.get('targetLowPrice', current_price),
        "history_df": history, "radar": [{"Үзүүлэлт": "RSI", "Оноо": current_rsi}]
    }

def get_screened_data(strat_selection, sector_sel):
    screened = []
    for ticker in TICKERS:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            pb = info.get('priceToBook')
            current_price = info.get('currentPrice')
            sector = info.get('sector', 'Unknown')
            if sector_sel != "Бүх салбар" and sector != sector_sel: continue
            if pb and pb < 5 and current_price:
                history = stock.history(period="1y")
                if len(history) >= 30:
                    stock_data = process_stock_data(ticker, info, history)
                    screened.append(stock_data)
        except: continue
    return screened

# Логик
if search_ticker:
    s_stock = yf.Ticker(search_ticker)
    show_data = [process_stock_data(search_ticker, s_stock.info, s_stock.history(period="1y"))]
    selected_ticker = search_ticker
else:
    show_data = get_screened_data(strategy, sector_choice)
    selected_ticker = show_data[0]['Тикер'] if show_data else None

# Дэлгэц
if not show_data:
    st.warning("Сонгосон шалгуурт тэнцэх хувьцаа олдсонгүй.")
else:
    df = pd.DataFrame(show_data).sort_values(by="potential_raw", ascending=False)
    col1, col2 = st.columns([1.0, 1.0])
    with col1:
        st.subheader(f"🔍 Жагсаалт ({len(df)} компани)")
        if not selected_ticker:
            selected_ticker = st.selectbox("Сонгоно уу:", df["Тикер"].tolist())
        st.dataframe(df[["Тикер", "Сигнал", "RSI"]], use_container_width=True)
    with col2:
        if selected_ticker:
            selected_stock = next(item for item in show_data if item["Тикер"] == selected_ticker)
            st.subheader(f"📊 {selected_ticker} Хянах Самбар")
            tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "📉 График", "🕸️ Радар"])
            with tab1:
                st.info(f"Салбар: {selected_stock['Салбар']} | RSI: {selected_stock['RSI']}")
            with tab2:
                st.plotly_chart(px.line(selected_stock['history_df'], y='Close'), use_container_width=True)
            with tab3:
                st.plotly_chart(px.line_polar(pd.DataFrame(selected_stock['radar']), r='Оноо', theta='Үзүүлэлт'), use_container_width=True)
