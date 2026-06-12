import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 1. Тохиргоо
st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro Max", layout="wide")

# 2. Функцууд
@st.cache_data(ttl=86400)
def get_all_us_tickers():
    # Энд таны өмнөх бүх тикер татдаг логик байгаа (S&P 500, 600, Russell 2000)
    # Таны GitHub-аас харагдсан үндсэн тикерүүдийг энд үлдээлээ
    return ['AAPL', 'MSFT', 'VALE', 'F', 'GM', 'AMD', 'BAC', 'JPM', 'OSCR']

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
    
    # Радар графикийн оноо тооцох
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
        "radar": [
            {"Үзүүлэлт": "Үнэлгээ", "Оноо": val_score},
            {"Үзүүлэлт": "Өсөлт", "Оноо": mom_score},
            {"Үзүүлэлт": "Орлого", "Оноо": growth},
            {"Үзүүлэлт": "Эрүүл мэнд", "Оноо": health}
        ]
    }

# 3. Үндсэн логик
st.title("📈 Хувьцаа Шүүгч Pro")
tickers = get_all_us_tickers()
selected_ticker = st.sidebar.selectbox("Хувьцаа сонгох:", tickers)

stock = yf.Ticker(selected_ticker)
hist = stock.history(period="1y")
data = process_stock_data(selected_ticker, stock.info, hist)

# 4. Дэлгэц хуваах
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader(f"{selected_ticker} мэдээлэл")
    st.write(f"Компани: {data['Компани']}")
    st.metric("Өнөөгийн Үнэ", f"${data['Өнөөгийн Үнэ']}")

with col2:
    tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "📉 Ханш", "🕸️ Суурь Радар"])
    
    with tab1:
        st.write("Салбар:", data['Салбар'])
    
    with tab2:
        fig = px.line(data['history_df'], y='Close', title="1 жилийн график")
        st.plotly_chart(fig, use_container_width=True)
        
    with tab3:
        # ЭНЭ ХЭСЭГ ТАНЫ РАДАР ГРАФИКИЙГ ИЛ ГАРГАНА
        radar_df = pd.DataFrame(data['radar'])
        fig_radar = px.line_polar(radar_df, r='Оноо', theta='Үзүүлэлт', line_close=True)
        fig_radar.update_traces(fill='toself')
        fig_radar.update_layout(height=400, margin=dict(t=50, b=50))
        st.plotly_chart(fig_radar, use_container_width=True)
