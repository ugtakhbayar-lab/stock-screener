import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Хувьцаа Шүүгч Pro", layout="wide")
st.title("📈 АНУ-ын Зах зээлийг Бүрэн Шүүгч (3,100+ Хувьцаа)")

st.write("S&P 500, S&P 600 болон Russell 2000 нийт 3,100 гаруй компанийн датаг татаж байна. Түр хүлээнэ үү...")

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
    except Exception as e:
        return ['AAPL', 'MSFT', 'VALE', 'F', 'GM', 'AMD', 'BAC', 'JPM', 'OSCR']

TICKERS = get_all_us_tickers()

@st.cache_data(ttl=3600)
def get_screened_data():
    screened = []
    progress_bar = st.progress(0)
    total = len(TICKERS)
    
    for index, ticker in enumerate(TICKERS):
        progress_bar.progress((index + 1) / total)
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            pe = info.get('trailingPE')
            pb = info.get('priceToBook')
            
            # ШАЛГУУРЫГ УЯН ХАТАН БОЛГОВ (Жижиг компаниудад зориулж)
            if pb and pb < 6:
                history = stock.history(period="1mo")
                if len(history) >= 20:
                    sma_5 = history['Close'].tail(5).mean()
                    sma_20 = history['Close'].tail(20).mean()
                    
                    # Богино хугацааны өсөлтийн тренд
                    if sma_5 > sma_20:
                        # P/E байхгүй бол оноог 50 гэж үзнэ
                        current_pe = pe if pe else 40
                        val_score = max(10, min(100, int((60 - current_pe) * 2)))
                        mom_score = 95 if sma_5 > sma_20 * 1.02 else 75
                        growth = max(10, min(100, int(info.get('revenueGrowth', 0) * 100)))
                        health = max(10, min(100, int(100 - info.get('debtToEquity', 100) / 2)))
                        
                        screened.append({
                            "Тикер": ticker,
                            "Компани": info.get('longName', ticker),
                            "Үнэ": f"${info.get('currentPrice')}",
                            "P/E": round(pe, 2) if pe else "N/A",
                            "P/B": round(pb, 2),
                            "radar": [
                                {"Үзүүлэлт": "Үнэлгээ", "Оноо": val_score},
                                {"Үзүүлэлт": "Өсөлт", "Оноо": mom_score},
                                {"Үзүүлэлт": "Орлого", "Оноо": growth},
                                {"Үзүүлэлт": "Эрүүл мэнд", "Оноо": health}
                            ]
                        })
        except:
            continue
            
    progress_bar.empty()
    return screened

data = get_screened_data()

if not data:
    st.warning("Яг одоо энэ уян хатан шалгуурт ч тэнцэх хувьцаа олдсонгүй.")
else:
    df = pd.DataFrame(data)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader(f"Шалгуурт тэнцсэн хувьцаанууд ({len(df)} олдлоо)")
        selected_ticker = st.selectbox("Шинжлэх хувьцааг сонгоно уу:", df["Тикер"].tolist())
        st.dataframe(df[["Тикер", "Компани", "Үнэ", "P/E", "P/B"]], use_container_width=True)
        
    with col2:
        st.subheader("СТРАТЕГИЙН НӨЛӨӨЛӨЛ (Радар график)")
        selected_stock = next(item for item in data if item["Тикер"] == selected_ticker)
        radar_df = pd.DataFrame(selected_stock["radar"])
        fig = px.line_polar(radar_df, r='Оноо', theta='Үзүүлэлт', line_close=True)
        fig.update_traces(fill='toself')
        st.plotly_chart(fig, use_container_width=True)
