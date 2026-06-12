import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 🖥️ ДЭЛГЭЦИЙГ ӨРГӨНӨӨР НЬ БҮРЭН ДҮҮРГЭХ
st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro Max", layout="wide")

# --- 1. ФУНКЦУУД ---
@st.cache_data(ttl=86400)
def get_all_us_tickers():
    return ['AAPL', 'MSFT', 'VALE', 'F', 'GM', 'AMD', 'BAC', 'JPM', 'OSCR', 'TSLA', 'NVDA']

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def process_stock_data(ticker, info, history):
    current_price = info.get('currentPrice')
    close_prices = history['Close'].dropna()
    rsi = calculate_rsi(close_prices).iloc[-1]
    
    val_score = max(10, min(100, int((60 - (info.get('trailingPE') or 40)) * 2)))
    mom_score = max(10, min(100, int((75 - rsi) * 1.5)))
    growth = max(10, min(100, int(info.get('revenueGrowth', 0) * 100)))
    health = max(10, min(100, int(100 - info.get('debtToEquity', 100) / 2)))
    
    return {
        "Тикер": ticker,
        "Компани": info.get('longName', ticker),
        "Салбар": info.get('sector', 'N/A'),
        "Өнөөгийн Үнэ": current_price,
        "history_df": history,
        "signal_color": "green" if rsi < 55 else "orange",
        "Сигнал": "Худалдаж авах" if rsi < 55 else "Сууж байх",
        "RSI": round(rsi, 1),
        "Шинжээчдийн Таамаг": info.get('targetMeanPrice', 0),
        "Өсөх Боломж (%)": round(((info.get('targetMeanPrice', 0) - current_price) / current_price) * 100, 1) if current_price and info.get('targetMeanPrice') else 0,
        "high_target": info.get('targetHighPrice', current_price),
        "low_target": info.get('targetLowPrice', current_price),
        "radar": [
            {"Үзүүлэлт": "Үнэлгээ", "Оноо": val_score},
            {"Үзүүлэлт": "Өсөлт", "Оноо": mom_score},
            {"Үзүүлэлт": "Орлого", "Оноо": growth},
            {"Үзүүлэлт": "Эрүүл мэнд", "Оноо": health}
        ]
    }

# --- 2. SIDEBAR ---
st.sidebar.title("⚙️ Удирдах Цэс")
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж", "2. Тренд дагах"))
sector_choice = st.sidebar.selectbox("Салбар:", ("Бүх салбар", "Technology", "Healthcare"))
search_ticker = st.sidebar.text_input("🔍 Хувьцаа хайх:").upper().strip()

# --- 3. ДАТА ТАТАХ ---
st.title("📈 Хувьцаа Шүүгч Pro")
tickers = get_all_us_tickers()

if search_ticker:
    stock = yf.Ticker(search_ticker)
    show_data = [process_stock_data(search_ticker, stock.info, stock.history(period="1y"))]
    selected_ticker = search_ticker
else:
    # Энгийн болгохын тулд эхний 5-ыг авлаа, та өөрийн логикоо энд бүрэн оруулна уу
    show_data = [process_stock_data(t, yf.Ticker(t).info, yf.Ticker(t).history(period="1y")) for t in tickers[:5]]
    selected_ticker = st.selectbox("Хувьцаа сонгох:", [d["Тикер"] for d in show_data])

# --- 4. UI ---
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Жагсаалт")
    st.dataframe(pd.DataFrame(show_data)[["Тикер", "Компани", "Өнөөгийн Үнэ"]], use_container_width=True)

with col2:
    selected_stock = next(item for item in show_data if item["Тикер"] == selected_ticker)
    st.subheader(f"📊 {selected_ticker} Хянах Самбар")
    
    tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "📉 Ханш", "🕸️ Радар"])
    
    with tab1:
        st.markdown(f"**Дохио:** :{selected_stock['signal_color']}[{selected_stock['Сигнал']}]")
        st.write(f"RSI: {selected_stock['RSI']}")
        
    with tab2:
        fig = px.line(selected_stock["history_df"], y='Close')
        st.plotly_chart(fig, use_container_width=True)
        
    with tab3:
        radar_df = pd.DataFrame(selected_stock["radar"])
        fig_radar = px.line_polar(radar_df, r='Оноо', theta='Үзүүлэлт', line_close=True)
        fig_radar.update_traces(fill='toself')
        fig_radar.update_layout(height=400, margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig_radar, use_container_width=True)
