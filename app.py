import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 🖥️ ДЭЛГЭЦИЙГ ӨРГӨНӨӨР НЬ БҮРЭН ДҮҮРГЭХ ТОХИРГОО
# ДЭЛГЭЦИЙГ ӨРГӨНӨӨР НЬ БҮРЭН ДҮҮРГЭХ
st.set_page_config(page_title="Ухаалаг Хувьцаа Шүүгч Pro Max", layout="wide")

# 1. ХАЖУУГИЙН ЦЭС (SIDEBAR) - ТОХИРГООНУУД
st.sidebar.title("⚙️ Удирдах Цэс")
# (Энд таны өмнөх бүх функцууд болох get_all_us_tickers, calculate_rsi, process_stock_data, get_screened_data гээд бүх код байх ёстой)
# ... [ЭНД ТАНЫ ҮНДСЭН КОД БАЙХ ЁСТОЙ] ...

strategy = st.sidebar.radio(
    "Хөрөнгө оруулалтын стратеги:",
    ("1. Төгс боломж (Хатуу шалгуур)", "2. Тренд дагах (Уян хатан шалгуур)")
)

sector_choice = st.sidebar.selectbox(
    "Салбараар шүүх:",
    ("Бүх салбар", "Technology", "Healthcare", "Financial Services", "Consumer Cyclical", "Industrials", "Energy")
)

st.sidebar.write("---")
search_ticker = st.sidebar.text_input("🔍 Шууд хувьцаа хайх (Жишээ нь: OSCR, AAPL):").upper().strip()

st.title("📈 Хос Стратегит & Автомат Зөвлөхтэй Хувьцаа Шүүгч")

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

# ХУВЬЦААНЫ МЭДЭЭЛЛИЙГ БОДДОГ СУУРЬ ФУНКЦ
def process_stock_data(ticker, info, history):
    pe = info.get('trailingPE')
    pb = info.get('priceToBook')
    current_price = info.get('currentPrice')
    sector = info.get('sector', 'Unknown')
    
    close_prices = history['Close'].dropna()
    rsi_series = calculate_rsi(close_prices)
    current_rsi = rsi_series.iloc[-1]
    
    target_price = info.get('targetMeanPrice')
    potential_growth = round(((target_price - current_price) / current_price) * 100, 1) if target_price and current_price else "N/A"
    
    # СИГНАЛ ТОХИРУУЛАХ ЛОГИК
    if current_rsi < 35:
        signal = "🚨 ХҮЧТЭЙ ХУДАТДАЖ АВАХ (Хэт унасан)"
        signal_color = "green"
    elif current_rsi < 55:
        signal = "✅ ХУДАТДАЖ АВАХ (Боломжит бүс)"
        signal_color = "lightgreen"
    elif current_rsi > 70:
        signal = "⚠️ ЗАРАХ / ТҮР ХҮЛЭЭХ (Хэт хөөссөн)"
        signal_color = "red"
    else:
        signal = "🔲 СУУЖ БАЙХ (Төвийг сахисан)"
        signal_color = "orange"
        
    current_pe = pe if pe else 40
    val_score = max(10, min(100, int((60 - current_pe) * 2)))
    mom_score = max(10, min(100, int((75 - current_rsi) * 1.5))) 
    growth = max(10, min(100, int(info.get('revenueGrowth', 0) * 100)))
    health = max(10, min(100, int(100 - info.get('debtToEquity', 100) / 2)))
    
    return {
        "Тикер": ticker,
        "Компани": info.get('longName', ticker),
        "Салбар": sector,
        "Өнөөгийн Үнэ": current_price,
        "Шинжээчдийн Таамаг": target_price if target_price else 0,
        "Өсөх Боломж (%)": f"{potential_growth}%" if potential_growth != "N/A" else "N/A",
        "P/E": round(pe, 2) if pe else "N/A",
        "P/B": round(pb, 2) if pb else "N/A",
        "RSI": round(current_rsi, 1),
        "Сигнал": signal,
        "signal_color": signal_color,
        "potential_raw": potential_growth if potential_growth != "N/A" else -999,
        "high_target": info.get('targetHighPrice', current_price),
        "low_target": info.get('targetLowPrice', current_price),
        "history_df": history, 
        "radar": [
            {"Үзүүлэлт": "Үнэлгээ", "Оноо": val_score},
            {"Үзүүлэлт": "Өсөлт", "Оноо": mom_score},
            {"Үзүүлэлт": "Орлого", "Оноо": growth},
            {"Үзүүлэлт": "Эрүүл мэнд", "Оноо": health}
        ]
    }

@st.cache_data(ttl=3600)
def get_screened_data(strat_selection, sector_sel):
    screened = []
    progress_bar = st.progress(0)
    total = len(TICKERS)
# ХАМГИЙН ЧУХАЛ ХЭСЭГ (Таны асуудалтай байгаа баруун талын багана):
with col2:
    selected_stock = next(item for item in show_data if item["Тикер"] == selected_ticker)
    st.subheader(f"📊 {selected_ticker} Хянах Самбар")

    for index, ticker in enumerate(TICKERS):
        progress_bar.progress((index + 1) / total)
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            pb = info.get('priceToBook')
            current_price = info.get('currentPrice')
            sector = info.get('sector', 'Unknown')
            
            if sector_sel != "Бүх салбар" and sector != sector_sel:
                continue
                
            if pb and pb < 5 and current_price:
                # 📅 ЗАСВАР: Ханшны графикийг урт хугацаагаар өдөр тутам харахын тулд 1 жилээр татна
                history = stock.history(period="1y") 
                if len(history) >= 30:
                    close_prices = history['Close'].dropna()
                    rsi_series = calculate_rsi(close_prices)
                    current_rsi = rsi_series.iloc[-1]
                    
                    is_match = False
                    if strat_selection == "1. Төгс боломж (Хатуу шалгуур)":
                        if pd.notna(current_rsi) and current_rsi < 55:
                            trading_days_3 = close_prices.tail(3).tolist()
                            if len(trading_days_3) == 3 and trading_days_3[2] > trading_days_3[1] and trading_days_3[1] > trading_days_3[0]:
                                is_match = True
                    else:
                        if pd.notna(current_rsi) and 30 <= current_rsi <= 65:
                            sma_5 = close_prices.tail(5).mean()
                            sma_20 = close_prices.tail(20).mean()
                            if sma_5 > sma_20:
                                is_match = True

                    if is_match:
                        stock_data = process_stock_data(ticker, info, history)
                        screened.append(stock_data)
        except:
            continue
            
    progress_bar.empty()
    return screened

# Хайлтын систем
single_stock_view = None
if search_ticker:
    try:
        s_stock = yf.Ticker(search_ticker)
        s_info = s_stock.info
        s_history = s_stock.history(period="1y") 
        if 'Close' in s_history.columns and len(s_history) >= 30:
            single_stock_view = process_stock_data(search_ticker, s_info, s_history)
            st.success(f"🔍 Хайсан хувьцаа '{search_ticker}' амжилттай олдлоо!")
    except:
        st.error(f"❌ '{search_ticker}' тикер олдсонгүй.")

if single_stock_view:
    show_data = [single_stock_view]
    selected_ticker = search_ticker
else:
    show_data = get_screened_data(strategy, sector_choice)
    selected_ticker = None

if not show_data:
    st.warning(f"Яг одоо сонгосон стратеги болон салбарт ({sector_choice}) тэнцэх хувьцаа олдсонгүй.")
else:
    df = pd.DataFrame(show_data)
    df = df.sort_values(by="potential_raw", ascending=False)
    tab1, tab2, tab3 = st.tabs(["💡 Автомат Зөвлөх", "📉 Ханшны График", "🕸️ Суурь Радар"])

    # 🖥️ ЗАСВАР: Дэлгэцийг бүтэн дүүргэхийн тулд зүүн баруун талыг [1.0, 1.0] буюу 50%:50% болгов
    col1, col2 = st.columns([1.0, 1.0])
    
    with col1:
        st.subheader(f"🔍 Жагсаалт ({len(df)} компани)")
        if not selected_ticker:
            selected_ticker = st.selectbox("Шинжлэх хувьцааг сонгоно уу:", df["Тикер"].tolist())
            
        display_df = df.copy()
        display_df["Өнөөгийн Үнэ"] = display_df["Өнөөгийн Үнэ"].apply(lambda x: f"${x}")
        display_df["Шинжээчдийн Таамаг"] = display_df["Шинжээчдийн Таамаг"].apply(lambda x: f"${x}" if x > 0 else "N/A")
        st.dataframe(display_df[["Тикер", "Компани", "Салбар", "Өнөөгийн Үнэ", "Шинжээчдийн Таамаг", "Өсөх Боломж (%)", "Сигнал"]], use_container_width=True)
        
        # CSV татах товчлуур
        csv = df[["Тикер", "Компани", "Салбар", "Өнөөгийн Үнэ", "Шинжээчдийн Таамаг", "Өсөх Боломж (%)", "P/E", "P/B", "RSI", "Сигнал"]].to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Шүүсэн жагсаалтыг CSV файл болгож татах",
            data=csv,
            file_name='screener_results.csv',
            mime='text/csv',
        )
        
    with col2:
        selected_stock = next(item for item in show_data if item["Тикер"] == selected_ticker)
        
        st.subheader(f"📊 {selected_ticker} Хянах Самбар")
        
        tab1, tab2, tab3 = st.tabs(["💡 Автомат Зөвлөх", "📉 Ханшны График (Daily)", "🕸️ Суурь Радар"])
        
        with tab1:
            st.markdown(f"**Арилжааны Дохио:** :{selected_stock['signal_color']}[{selected_stock['Сигнал']}]")
            st.metric(
                label="Шинжээчдийн дундаж бай (Target)", 
                value=f"${selected_stock['Шинжээчдийн Таамаг']}" if selected_stock['Шинжээчдийн Таамаг'] > 0 else "N/A", 
                delta=f"{selected_stock['Өсөх Боломж (%)']} Өсөх зай"
            )
            st.info(f"""
            * **Салбар:** {selected_stock['Салбар']}
            * **Одоогийн RSI:** {selected_stock['RSI']}
            * **Хамгийн өндөр таамаг:** ${selected_stock['high_target']} 
            * **Хамгийн бага таамаг:** ${selected_stock['low_target']}
            """)
            
        with tab2:
            # 📈 ЗАСВАР: ӨДӨР ТУТМЫН ҮНИЙН ХӨДӨЛГӨӨН
            hist_df = selected_stock["history_df"].reset_index()
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(
                x=hist_df['Date'], 
                y=hist_df['Close'],
                mode='lines',
                name='Өдрийн хаалтын үнэ',
                line=dict(color='#00FF00', width=2)
            ))
            fig_line.update_layout(
                title=f"{selected_ticker} Өдөр тутмын ханшны түүх",
                xaxis_title="Огноо",
                yaxis_title="Үнэ ($)",
                height=450,
                template="plotly_dark",
                margin=dict(l=10, r=10, t=40, b=10)
            )
            st.plotly_chart(fig_line, use_container_width=True)
            
     with tab3:
    # РАДАР ГРАФИКИЙГ ЗӨВ ХАРУУЛАХ ТОХИРГОО
    radar_df = pd.DataFrame(selected_stock["radar"])
    fig_radar = px.line_polar(radar_df, r='Оноо', theta='Үзүүлэлт', line_close=True)
    fig_radar.update_traces(fill='toself')
    # Өндөр өргөнийг хатуу зааж өгөхөд график ил гарна
    fig_radar.update_layout(height=400, margin=dict(l=40, r=40, t=40, b=40))
    st.plotly_chart(fig_radar, use_container_width=True)
