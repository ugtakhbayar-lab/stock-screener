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
        hist = yf.Ticker(ticker).history(period="1mo")
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
        if rsi < 40:
            if strategy == "1. Төгс боломж" and (0 < pe < 20) and (growth > 0.10): passed = True
            elif strategy == "2. Тренд дагах (Уян хатан)" and ((target - current) / current) >= 0.20: passed = True
            elif strategy == "3. Ирээдүйн өсөлт (Turnaround)" and (0 < fpe < 25) and (growth > 0.15): passed = True
        
        if not passed: return None
        
        radar_data = [
            {"Үзүүлэлт": "P/E", "Оноо": max(0, min(100, 100 - pe))},
            {"Үзүүлэлт": "Өсөлт", "Оноо": min(100, growth * 100)},
            {"Үзүүлэлт": "Боломж", "Оноо": min(100, ((target - current) / current) * 100)},
            {"Үзүүлэлт": "RSI (Inverse)", "Оноо": max(0, min(100, 100 - rsi))}
        ]
        radar_df = pd.DataFrame(radar_data)

        return {
            "Тикер": ticker,
            "Компани": info.get('longName', ticker),
            "rsi": round(rsi, 1),
            "price": current,
            "growth_pot": round(((target - current) / current) * 100, 1),
            "radar_df": radar_df,
            "signal_color": "green" if target > current else "orange"
        }
    except:
        return None

# Sidebar
st.sidebar.title("⚙️ Стратеги сонгох")
strategy = st.sidebar.radio("Сонгох:", ("1. Төгс боломж", "2. Тренд дагах (Уян хатан)", "3. Ирээдүйн өсөлт (Turnaround)"))

if st.button("🚀 ШҮҮЛТҮҮРИЙГ АЖИЛЛУУЛАХ"):
    tickers = get_all_us_tickers()
    st.info("🔍 Шинжилж байна...")
    results = []
    progress_bar = st.progress(0)
    
    for i, t in enumerate(tickers):
        data = get_stock_data(t, strategy)
        if data: results.append(data)
        progress_bar.progress((i + 1) / len(tickers))
        
    st.session_state.results = results
    st.success(f"✅ Нийт {len(results)} хувьцаа тэнцлээ.")

# Үр дүн харуулах
if 'results' in st.session_state and st.session_state.results:
    df_results = pd.DataFrame(st.session_state.results)
    display_df = df_results[["Тикер", "Компани", "rsi", "price", "growth_pot"]].copy()
    display_df['Цаг'] = datetime.datetime.now().strftime("%H:%M")
    
    selected = st.dataframe(display_df, use_container_width=True, on_select="rerun", selection_mode="single-row")
    
    # Аюулгүй CSV татах
    st.subheader("💾 Үр дүн татах")
    csv_df = df_results.copy()
    if 'radar_df' in csv_df.columns: csv_df = csv_df.drop(columns=['radar_df'])
    csv = csv_df.to_csv(index=False).encode('utf-8')
    st.download_button("CSV-ээр татах", csv, f"results_{datetime.datetime.now().strftime('%Y%m%d')}.csv")
    
    if selected.selection["rows"]:
        idx = selected.selection["rows"][0]
        stock = st.session_state.results[idx]
        st.divider()
        st.subheader(f"📊 {stock['Тикер']} - {stock['Компани']}")
        st.markdown(f":{stock['signal_color']}[Сигнал: ХУДАЛДАЖ АВАХ]")
        st.success(f"📈 Өсөх боломж: {stock['growth_pot']}%")
        
        if 'radar_df' in stock and not stock['radar_df'].empty:
            fig = px.line_polar(stock['radar_df'], r='Оноо', theta='Үзүүлэлт', line_close=True, range_r=[0,100])
            st.plotly_chart(fig, use_container_width=True)
