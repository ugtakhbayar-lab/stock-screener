import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import datetime

# 1. Хуудасны тохиргоо
st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro", layout="wide")

@st.cache_data(ttl=3600)
def get_all_us_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df = pd.read_csv(url)
        return df['Symbol'].astype(str).tolist()
    except:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]

def get_rsi(ticker, period=14):
    try:
        # Сүүлийн 3 сарын өдөр тутмын дата ашиглах
        hist = yf.Ticker(ticker).history(period="3mo")
        if len(hist) < period: return 50
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs.iloc[-1]))
    except:
        return 50

def get_stock_data(ticker, strategy):
    try:
        s = yf.Ticker(ticker)
        info = s.info
        if not info: return None
        pe = info.get('trailingPE') or 0
        fpe = info.get('forwardPE') or 0
        growth = info.get('revenueGrowth') or 0
        target = info.get('targetMeanPrice') or 0
        current = info.get('currentPrice') or 1
        rsi = get_rsi(ticker)
        
        passed = False
        # Шалгуур (RSI < 40)
        if rsi < 40: 
            if strategy == "1. Төгс боломж" and (0 < pe < 20) and (growth > 0.10): passed = True
            elif strategy == "2. Тренд дагах (Уян хатан)" and ((target - current) / current) >= 0.20: passed = True
            elif strategy == "3. Ирээдүйн өсөлт (Turnaround)" and (0 < fpe < 25) and (growth > 0.15): passed = True
        
        if not passed: return None
        
        radar_df = pd.DataFrame({
            "Үзүүлэлт": ["P/E", "Өсөлт", "Боломж", "RSI (Inv)"],
            "Оноо": [max(0, min(100, 100 - pe)), min(100, growth * 100), min(100, ((target - current)/current)*100), max(0, min(100, 100 - rsi))]
        })

        return {
            "Тикер": ticker, "Компани": info.get('longName', ticker), "rsi": round(rsi, 1),
            "price": current, "growth_pot": round(((target - current) / current) * 100, 1),
            "radar_df": radar_df, "signal_color": "green" if target > current else "orange"
        }
    except: return None

# UI
strategy = st.sidebar.radio("Стратеги:", ("1. Төгс боломж", "2. Тренд дагах (Уян хатан)", "3. Ирээдүйн өсөлт (Turnaround)"))

if st.button("🚀 ШИНЖИЛГЭЭГ АЖИЛЛУУЛАХ"):
    tickers = get_all_us_tickers()
    st.write(f"📊 Нийт {len(tickers)} хувьцааг шинжилж эхэллээ...")
    results = []
    bar = st.progress(0)
    for i, t in enumerate(tickers):
        data = get_stock_data(t, strategy)
        if data: results.append(data)
        bar.progress((i + 1) / len(tickers))
    st.session_state.results = results
    st.success(f"✅ Шинжилгээ дууслаа! Олдсон: {len(results)}")

# Үр дүн харуулах
if 'results' in st.session_state and len(st.session_state.results) > 0:
    df = pd.DataFrame(st.session_state.results)
    display_df = df[["Тикер", "Компани", "rsi", "price", "growth_pot"]]
    
    selected = st.dataframe(display_df, use_container_width=True, on_select="rerun", selection_mode="single-row")
    
    # CSV татах
    csv = df.drop(columns=['radar_df'], errors='ignore').to_csv(index=False).encode('utf-8')
    st.download_button("💾 CSV татах", csv, "results.csv")
    
    # Сонгосон хувьцааны дэлгэрэнгүй
    if selected.selection.rows:
        idx = selected.selection.rows[0]
        if idx < len(st.session_state.results):
            stock = st.session_state.results[idx]
            st.divider()
            st.subheader(f"📊 {stock['Тикер']} - {stock['Компани']}")
            st.markdown(f":{stock['signal_color']}[Сигнал: ХУДАЛДАЖ АВАХ]")
            
            col1, col2 = st.columns(2)
            col1.metric("Үнэ", f"${stock['price']}")
            col2.metric("📈 Өсөх боломж", f"{stock['growth_pot']}%")
            
            # 3 сарын үнийн график
            st.subheader("📈 Сүүлийн 3 сарын үнийн хэлбэлзэл")
            hist = yf.Ticker(stock['Тикер']).history(period="3mo")
            if not hist.empty:
                st.line_chart(hist['Close'])
            
            # Радар график
            if 'radar_df' in stock:
                st.plotly_chart(px.line_polar(stock['radar_df'], r='Оноо', theta='Үзүүлэлт', line_close=True, range_r=[0,100]), use_container_width=True)
else:
    st.warning("⚠️ Тэнцэх хувьцаа одоогоор алга.")
