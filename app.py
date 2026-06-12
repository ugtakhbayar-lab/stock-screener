import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro", layout="wide")

if 'watchlist' not in st.session_state: st.session_state.watchlist = set()

@st.cache_data(ttl=86400)
def get_all_us_tickers():
    tickers = {'AAPL', 'MSFT', 'AMD', 'NVDA', 'TSLA', 'OSCR', 'HIMS', 'PLTR', 'SOFI'}
    return list(tickers)

def get_stock_details(ticker):
    s = yf.Ticker(ticker)
    info = s.info
    hist = s.history(period="1y")
    rsi = 50 
    return {
        "Тикер": ticker, "Компани": info.get('longName', ticker),
        "RSI": round(rsi, 1), "info": info, "hist": hist, 
        "news": s.news[:3], "signal_color": "green"
    }

st.sidebar.title("⚙️ Удирдах Цэс")
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж", "2. Тренд дагах", "3. Ирээдүйн өсөлт"))

if st.sidebar.button("🚀 Шүүх"):
    st.session_state.data = [get_stock_details(t) for t in get_all_us_tickers()]

if 'data' in st.session_state:
    df = pd.DataFrame(st.session_state.data)
    st.subheader("🔍 Жагсаалт (Сонгоно уу)")
    
    # Хүснэгтээс сонгох
    selected_ticker = st.selectbox("Хувьцаа сонгох:", df["Тикер"].tolist())
    stock = next(item for item in st.session_state.data if item["Тикер"] == selected_ticker)
    
    if st.button("⭐ Watchlist-д нэмэх"):
        st.session_state.watchlist.add(selected_ticker)
        st.success(f"{selected_ticker} нэмэгдлээ!")

    st.subheader(f"📊 {stock['Тикер']} - {stock['Компани']}")
    tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "📰 Мэдээ", "📉 График"])
    
    with tab1:
        st.write(f"Салбар: {stock['info'].get('sector', 'N/A')}")
        # ЭНД ЗАЙГҮЙ БИЧИВ (Өнгө заавал гарна)
        st.markdown(f"**Сигнал:** :{stock['signal_color']}[ХУДАЛДАЖ АВАХ]")
    
    with tab2:
        for news in stock['news']:
            st.write(f"[{news['title']}]({news['link']})")
            
    with tab3:
        st.plotly_chart(px.line(stock['hist'], y='Close'), use_container_width=True)

st.sidebar.subheader("⭐ Миний Watchlist")
st.sidebar.write(", ".join(list(st.session_state.watchlist)))
