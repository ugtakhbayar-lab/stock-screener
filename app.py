import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro", layout="wide")

if 'watchlist' not in st.session_state: 
    st.session_state.watchlist = set()

@st.cache_data(ttl=86400)
def get_all_us_tickers():
    return ['AAPL', 'MSFT', 'AMD', 'NVDA', 'TSLA', 'OSCR', 'HIMS', 'PLTR', 'SOFI']

def get_stock_details(ticker):
    s = yf.Ticker(ticker)
    try:
        info = s.info
        hist = s.history(period="1y")
        # KeyError гаргахгүйгээр мэдээлэл авах
        return {
            "Тикер": ticker, 
            "Компани": info.get('longName', ticker),
            "info": info, 
            "hist": hist, 
            "news": s.news[:3] if hasattr(s, 'news') else [],
            "signal_color": "green"
        }
    except:
        return None

st.sidebar.title("⚙️ Удирдах Цэс")
if st.sidebar.button("🚀 Хувьцаануудыг Шүүх"):
    data = []
    for t in get_all_us_tickers():
        res = get_stock_details(t)
        if res: data.append(res)
    st.session_state.data = data

if 'data' in st.session_state and st.session_state.data:
    df = pd.DataFrame(st.session_state.data)
    st.subheader("🔍 Жагсаалт (Сонгоно уу)")
    
    selected_ticker = st.selectbox("Хувьцаа сонгох:", df["Тикер"].tolist())
    stock = next(item for item in st.session_state.data if item["Тикер"] == selected_ticker)
    
    if st.button("⭐ Watchlist-д нэмэх"):
        st.session_state.watchlist.add(selected_ticker)
        st.success(f"{selected_ticker} нэмэгдлээ!")

    st.subheader(f"📊 {stock['Тикер']} - {stock['Компани']}")
    tab1, tab2, tab3 = st.tabs(["💡 Зөвлөх", "📰 Мэдээ", "📉 График"])
    
    with tab1:
        # KeyError-аас хамгаалсан дуудлага
        sector = stock['info'].get('sector', 'N/A')
        st.write(f"Салбар: {sector}")
        # Зайгүй бичих дүрэм (Өнгө зөв гарна)
        st.markdown(f"**Сигнал:** :{stock['signal_color']}[ХУДАЛДАЖ АВАХ]")
    
    with tab2:
        news_list = stock.get('news', [])
        if news_list:
            for news in news_list:
                st.write(f"[{news.get('title', 'Мэдээгүй')}]({news.get('link', '#')})")
        else:
            st.write("Мэдээ олдсонгүй.")
            
    with tab3:
        if not stock['hist'].empty:
            st.plotly_chart(px.line(stock['hist'], y='Close'), use_container_width=True)
        else:
            st.warning("График байхгүй байна.")

st.sidebar.subheader("⭐ Миний Watchlist")
if st.session_state.watchlist:
    st.sidebar.write(", ".join(list(st.session_state.watchlist)))
else:
    st.sidebar.write("Жагсаалт хоосон байна.")
