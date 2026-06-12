import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

# 1. Хуудасны тохиргоо
st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro", layout="wide")

# 2. Хувьцааны жагсаалт татах (S&P 500)
@st.cache_data(ttl=3600)
def get_all_us_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df = pd.read_csv(url)
        return df['Symbol'].astype(str).tolist()
    except:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]

# 3. Дата боловсруулах ба ХАТУУ ШҮҮЛТҮҮР
def get_stock_data(ticker, strategy):
    try:
        s = yf.Ticker(ticker)
        info = s.info
        if not info: return None
        
        # Датаг авах (Байхгүй бол 0 гэж үзнэ)
        pe = info.get('trailingPE') or 0
        fpe = info.get('forwardPE') or 0
        growth = info.get('revenueGrowth') or 0
        target = info.get('targetMeanPrice') or 0
        current = info.get('currentPrice') or 1
        
        # --- СТРАТЕГИЙН ХАТУУ ШҮҮЛТҮҮРҮҮД ---
        passed = False
        if strategy == "1. Төгс боломж":
            # P/E 25-аас бага БОЛОН өсөлт 5%-иас их байх ёстой
            if (0 < pe < 25) and (growth > 0.05):
                passed = True
                
        elif strategy == "2. Тренд дагах (Уян хатан)":
            # Зорилтот үнэ нь одоогийн үнээс дор хаяж 10% өндөр байх ёстой
            if ((target - current) / current) >= 0.10:
                passed = True
                
        elif strategy == "3. Ирээдүйн өсөлт (Turnaround)":
            # Forward P/E 30-аас бага БОЛОН өсөлт 10%-иас их байх ёстой
            if (0 < fpe < 30) and (growth > 0.10):
                passed = True
        
        # Хэрэв шалгуур хангаагүй бол None буцаана (Жагсаалтад оруулахгүй)
        if not passed:
            return None
        
        # Диаграммд зориулсан оноо
        radar_df = pd.DataFrame({
            "Үзүүлэлт": ["P/E", "Өсөлт", "Боломж"],
            "Оноо": [max(0, min(100, 100 - pe)), min(100, growth * 100), min(100, ((target-current)/current)*100)]
        })
        
        return {
            "Тикер": ticker,
            "Компани": info.get('longName', ticker),
            "radar": radar_df,
            "growth_pot": round(((target - current) / current) * 100, 1),
            "price": current,
            "signal_color": "green" if target > current else "orange"
        }
    except:
        return None

# 4. Sidebar (Удирдах хэсэг)
st.sidebar.title("⚙️ Стратеги сонгох")
strategy = st.sidebar.radio("Сонгох:", ("1. Төгс боломж", "2. Тренд дагах (Уян хатан)", "3. Ирээдүйн өсөлт (Turnaround)"))

# 5. Үндсэн хэсэг
if st.button("🚀 ШҮҮЛТҮҮРИЙГ АЖИЛЛУУЛАХ"):
    tickers = get_all_us_tickers()
    # Туршилтын журмаар эхний 150 хувьцааг шүүж байна (Хугацаа хэмнэх)
    st.info(f"🔍 {len(tickers)} хувьцааг шинжилж байна. Түр хүлээнэ үү...")
    
    results = []
    progress_bar = st.progress(0)
    
    test_limit = tickers[:150] # Хэрэв бүгдийг шүүх бол [:150]-ийг арилгаарай
    for i, t in enumerate(test_limit):
        data = get_stock_data(t, strategy)
        if data:
            results.append(data)
        progress_bar.progress((i + 1) / len(test_limit))
        
    st.session_state.results = results
    st.success(f"✅ Нийт {len(results)} хувьцаа таны шалгуурт тэнцлээ.")

# 6. Үр дүнг харуулах
if 'results' in st.session_state and st.session_state.results:
    df_results = pd.DataFrame(st.session_state.results)
    
    # Хувьцаа сонгох хүснэгт
    selected = st.dataframe(
        df_results[["Тикер", "Компани", "price"]], 
        use_container_width=True, 
        on_select="rerun", 
        selection_mode="single-row"
    )
    
    # Сонгосон хувьцааны нарийн мэдээлэл
    if selected.selection["rows"]:
        idx = selected.selection["rows"][0]
        stock = st.session_state.results[idx]
        
        st.divider()
        st.subheader(f"📊 {stock['Тикер']} - {stock['Компани']}")
        
        col1, col2 = st.columns(2)
        with col1:
            # Өнгө гаргах хамгийн найдвартай стандарт бичиглэл
            color_text = stock['signal_color']
            st.markdown(f":{color_text}[Сигнал: ХУДАЛДАЖ АВАХ]")
            
            st.success(f"📈 Өсөх боломж: **{stock['growth_pot']}%**")
            st.metric("Одоогийн үнэ", f"${stock['price']}")
            
        with col2:
            fig = px.line_polar(stock['radar'], r='Оноо', theta='Үзүүлэлт', line_close=True)
            st.plotly_chart(fig, use_container_width=True)
