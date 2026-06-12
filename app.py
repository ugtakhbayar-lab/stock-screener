import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Хувьцаа Шүүгч", layout="wide")
st.title("📈 Богино хугацааны өсөлттэй Хямд хувьцаа шүүгч")

TICKERS = ['AAPL', 'TSLA', 'NVDA', 'INTC', 'VALE', 'F', 'GM', 'XOM', 'T', 'VZ', 'MSFT', 'GOOGL']

st.write("Зах зээлийн датаг бодит цагаар шүүж байна...")

@st.cache_data(ttl=3600)
def get_screened_data():
    screened = []
    for ticker in TICKERS:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            pe = info.get('trailingPE')
            pb = info.get('priceToBook')
            
            if pe and pb and pe < 25 and pb < 3:
                history = stock.history(period="1mo")
                if len(history) >= 20:
                    sma_5 = history['Close'].tail(5).mean()
                    sma_20 = history['Close'].tail(20).mean()
                    
                    if sma_5 > sma_20:
                        val_score = max(10, min(100, int((25 - pe) * 4)))
                        mom_score = 90 if sma_5 > sma_20 * 1.02 else 70
                        growth = max(10, min(100, int(info.get('revenueGrowth', 0) * 100)))
                        health = max(10, min(100, int(100 - info.get('debtToEquity', 100) / 2)))
                        
                        screened.append({
                            "Тикер": ticker,
                            "Компани": info.get('longName', ticker),
                            "Үнэ": f"${info.get('currentPrice')}",
                            "P/E": round(pe, 2),
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
    return screened

data = get_screened_data()

if not data:
    st.warning("Яг одоо шалгуурт тэнцэх хувьцаа олдсонгүй.")
else:
    df = pd.DataFrame(data)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Шалгуурт тэнцсэн хувьцаанууд")
        selected_ticker = st.selectbox("Шинжлэх хувьцааг сонгоно уу:", df["Тикер"].tolist())
        st.dataframe(df[["Тикер", "Компани", "Үнэ", "P/E", "P/B"]], use_container_width=True)
        
    with col2:
        st.subheader("СТРАТЕГИЙН НӨЛӨӨЛӨЛ (Радар график)")
        selected_stock = next(item for item in data if item["Тикер"] == selected_ticker)
        radar_df = pd.DataFrame(selected_stock["radar"])
        fig = px.line_polar(radar_df, r='Оноо', theta='Үзүүлэлт', line_close=True)
        fig.update_traces(fill='subsection')
        st.plotly_chart(fig, use_container_width=True)
