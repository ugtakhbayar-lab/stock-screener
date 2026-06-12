import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro", layout="wide")
st.title("📈 Үнийн Таамаглалтай Ухаалаг Хувьцаа Шүүгч")

st.write("3,100+ компанийг шинжилж, цаашдын өсөх магадлалыг тооцоолж байна...")

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

def calculate_rsi(series, periods=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

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
            current_price = info.get('currentPrice')
            
            if pb and pb < 5 and current_price:
                history = stock.history(period="3mo")
                if len(history) >= 30:
                    close_prices = history['Close']
                    rsi_series = calculate_rsi(close_prices)
                    current_rsi = rsi_series.iloc[-1]
                    
                    # Ханш хэт өсөөгүй (RSI < 55) үед
                    if pd.notna(current_rsi) and current_rsi < 55:
                        last_3_days = close_prices.tail(3).tolist()
                        
                        # Богино хугацааны дээшээ эргэсэн дохио
                        if last_3_days[2] > last_3_days[1] and last_3_days[1] > last_3_days[0]:
                            
                            # УОЛЛ СТРИТИЙН ТААМАГЛАЛЫГ ТАТАХ
                            target_price = info.get('targetMeanPrice')
                            potential_growth = "N/A"
                            
                            if target_price:
                                # Цаашид өсөх боломжтой хувийг бодох
                                potential_growth = round(((target_price - current_price) / current_price) * 100, 1)
                            
                            current_pe = pe if pe else 35
                            val_score = max(10, min(100, int((50 - current_pe) * 2.5)))
                            mom_score = max(10, min(100, int((70 - current_rsi) * 2))) 
                            growth = max(10, min(100, int(info.get('revenueGrowth', 0) * 100)))
                            health = max(10, min(100, int(100 - info.get('debtToEquity', 100) / 2)))
                            
                            screened.append({
                                "Тикер": ticker,
                                "Компани": info.get('longName', ticker),
                                "Өнөөгийн Үнэ": f"${current_price}",
                                "Шинжээчдийн Таамаг": f"${target_price}" if target_price else "N/A",
                                "Өсөх Боломж (%)": f"{potential_growth}%" if potential_growth != "N/A" else "N/A",
                                "P/E": round(pe, 2) if pe else "N/A",
                                "RSI": round(current_rsi, 1),
                                "potential_raw": potential_growth if potential_growth != "N/A" else -999,
                                "high_target": info.get('targetHighPrice', current_price),
                                "low_target": info.get('targetLowPrice', current_price),
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
    st.warning("Яг одоо энэ шалгуурт тэнцэх хувьцаа олдсонгүй.")
else:
    df = pd.DataFrame(data)
    # Өсөх магадлал өндөртэйг нь хамгийн дээр гаргаж эрэмбэлнэ
    df = df.sort_values(by="potential_raw", ascending=False)
    
    col1, col2 = st.columns([1.2, 0.8])
    
    with col1:
        st.subheader(f"🔍 Олдсон хувьцаанууд ({len(df)} компани)")
        selected_ticker = st.selectbox("Шинжлэх хувьцааг сонгоно уу:", df["Тикер"].tolist())
        st.dataframe(df[["Тикер", "Компани", "Өнөөгийн Үнэ", "Шинжээчдийн Таамаг", "Өсөх Боломж (%)", "P/E"]], use_container_width=True)
        
    with col2:
        selected_stock = next(item for item in data if item["Тикер"] == selected_ticker)
        
        # ҮНЭ ХЭД ХҮРЭХ ТУХАЙ МЭДЭЭЛЛИЙГ ХАРУУЛАХ ХЭСЭГ
        st.subheader(f"📊 {selected_ticker} Үнийн Таамаглал")
        st.metric(label="Шинжээчдийн дундаж бай (Target)", value=selected_stock["Шинжээчдийн Таамаг"], delta=f"{selected_stock['Өсөх Боломж (%)']} Өсөх зай")
        
        st.info(f"""
        * **Хамгийн өндөр таамаг:** ${selected_stock['high_target']}
        * **Хамгийн бага таамаг:** ${selected_stock['low_target']}
        """)
        
        st.write("---")
        st.subheader("СТРАТЕГИЙН НӨЛӨӨЛӨЛ (Радар график)")
        radar_df = pd.DataFrame(selected_stock["radar"])
        fig = px.line_polar(radar_df, r='Оноо', theta='Үзүүлэлт', line_close=True)
        fig.update_traces(fill='toself')
        st.plotly_chart(fig, use_container_width=True)
