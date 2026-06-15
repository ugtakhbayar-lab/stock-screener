import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Ухаалаг Хувьцаа Шүүгч Pro",
    layout="wide",
    page_icon="📈"
)

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 60%, #1c2333 100%);
        border: 1px solid #30363d;
        padding: 2rem 2.5rem;
        border-radius: 14px;
        margin-bottom: 2rem;
        text-align: center;
    }
    .main-header h1 { color: #58a6ff; font-size: 2.2rem; font-weight: 800; margin: 0; }
    .main-header p  { color: #8b949e; margin: 0.4rem 0 0; font-size: 1rem; }

    /* ── Sidebar бүх текстийг цагаан болгох ── */
    [data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }
    [data-testid="stSidebar"] * { color: #e6edf3 !important; }
    [data-testid="stSidebar"] h2 { color: #58a6ff !important; font-size: 1.2rem; }
    [data-testid="stSidebar"] .stSelectbox label { color: #e6edf3 !important; }
    [data-testid="stSidebar"] .stRadio label { color: #e6edf3 !important; }
    [data-testid="stSidebar"] .stSlider label { color: #e6edf3 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #c9d1d9 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li { color: #c9d1d9 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong { color: #e6edf3 !important; }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] em { color: #8b949e !important; }
    [data-testid="baseButton-primary"] { background: linear-gradient(135deg, #1158a6, #58a6ff) !important; color: #fff !important; }

    .stDataFrame tbody tr:hover { background: rgba(88,166,255,0.07) !important; }
    [data-testid="stMetricDelta"] svg { display:none; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def get_sp500_tickers():
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        df = pd.read_csv(url)
        return df['Symbol'].astype(str).tolist()
    except:
        return ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA","META","JPM","V","JNJ",
                "UNH","XOM","PG","HD","MA","MRK","ABBV","CVX","PEP","KO"]


@st.cache_data(ttl=3600)
def get_russell2000_tickers():
    sources = [
        "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/russell2000/russell2000_tickers.txt",
        "https://raw.githubusercontent.com/datasets/russell-2000/master/data/constituents.csv",
    ]
    for url in sources:
        try:
            import urllib.request
            with urllib.request.urlopen(url, timeout=10) as r:
                content = r.read().decode("utf-8")
            if url.endswith(".txt"):
                tickers = [t.strip() for t in content.splitlines() if t.strip()]
            else:
                df = pd.read_csv(pd.io.common.StringIO(content))
                tickers = df.iloc[:, 0].astype(str).tolist()
            if len(tickers) > 100:
                return tickers
        except:
            continue
    return [
        "SMCI","KRYS","CRVS","PRCT","ACAD","PRLB","BLFS","HIMS","RXO","CARG",
        "IRTC","NVST","FRSH","IIPR","RGEN","STAA","NSIT","LPSN","OMCL","BRKL",
        "CLBT","CALX","SFNC","MGNI","ASTS","JOBY","IONQ","ARQT","WOLF","MRUS",
        "VERX","SPNT","INVA","AMRC","FXNC","HAFC","AMPH","CCSI","CLOV","MNTV",
        "TNDM","FLNC","NVCR","CBRL","PLAY","WING","FAT","SHAK","DNUT","CAVA",
        "BROS","ARCO","PTGX","FLGT","AXSM","ACLS","FORM","AMBA","AEHR","SMPL",
        "EOLS","HALO","INMD","TGTX","RCUS","IMVT","NRIX","PRAX","KROS","DAWN",
        "LSCC","OSIS","ICHR","NOVT","DIOD","ONTO","COHU","AEIS","RMBS","POWI",
        "MGRC","PLXS","IIVI","BEL","CTS","KLIC","MKSI","AMAT","CREE","IMOS",
    ]


@st.cache_data(ttl=3600)
def get_tickers_for_universe(universe):
    if universe == "S&P 500 (~500)":
        return get_sp500_tickers(), 2_000_000_000
    elif universe == "Russell 2000 (~2000)":
        return get_russell2000_tickers(), 200_000_000
    else:
        sp = get_sp500_tickers()
        r2k = get_russell2000_tickers()
        combined = list(dict.fromkeys(sp + r2k))
        return combined, 200_000_000


def calc_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50.0
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    return round(float(100 - 100 / (1 + rs.iloc[-1])), 1)


def calc_macd_hist(prices):
    if len(prices) < 26:
        return 0.0
    ema12 = prices.ewm(span=12, adjust=False).mean()
    ema26 = prices.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1] - signal.iloc[-1])


def calc_momentum(prices, days=22):
    if len(prices) < days:
        return 0.0
    return round((prices.iloc[-1] / prices.iloc[-days] - 1) * 100, 2)


def estimate_months_to_target(upside, mom_1m):
    """Аналистын зорилтод хүрэх ойролцоо хугацаа (сараар)"""
    if upside <= 0 or mom_1m <= 0:
        return None
    months = round(upside / max(mom_1m, 0.5))
    return max(1, min(months, 24))


def calc_score(pe, fpe, growth, rsi, upside, macd_hist, analyst_rec, strategy):
    s = 0
    if strategy == "1. Төгс боломж":
        if 0 < pe < 12:
            s += 25
        elif 0 < pe < 20:
            s += 15
        if growth > 0.15:
            s += 20
        elif growth > 0.08:
            s += 10
        if rsi < 30:
            s += 25
        elif rsi < 40:
            s += 15
        if upside > 30:
            s += 20
        elif upside > 15:
            s += 10
        if macd_hist > 0:
            s += 10
    elif strategy == "2. Тренд дагах (Уян хатан)":
        if 55 < rsi < 68:
            s += 30
        elif 50 < rsi < 72:
            s += 18
        if macd_hist > 0:
            s += 25
        if upside > 20:
            s += 20
        elif upside > 12:
            s += 10
        if growth > 0.15:
            s += 15
        elif growth > 0.08:
            s += 8
        if 0 < fpe < 30:
            s += 10
    elif strategy == "3. Ирээдүйн өсөлт (Turnaround)":
        if growth > 0.25:
            s += 30
        elif growth > 0.12:
            s += 18
        if 0 < fpe < 18:
            s += 25
        elif 0 < fpe < 28:
            s += 14
        if upside > 25:
            s += 20
        elif upside > 15:
            s += 10
        if 35 < rsi < 60:
            s += 15
        if macd_hist > 0:
            s += 10
    if analyst_rec and 0 < analyst_rec < 2.0:
        s += 10
    elif analyst_rec and analyst_rec < 2.5:
        s += 5
    return min(100, s)


def get_signal(score, upside):
    if score >= 68 and upside > 15:
        return "🟢 ХУДАЛДАЖ АВ", "#1a7f64"
    elif score >= 48:
        return "🟡 АЖИГЛА", "#9a6700"
    else:
        return "🔴 БОЛГООМЖИЛ", "#6e3c14"


def get_stock_data(ticker, strategy, min_cap=2_000_000_000):
    try:
        s = yf.Ticker(ticker)
        info = s.info
        if not info or info.get('quoteType') not in ('EQUITY',):
            return None
        pe = info.get('trailingPE') or 0
        fpe = info.get('forwardPE') or 0
        growth = info.get('revenueGrowth') or 0
        earn_growth = info.get('earningsGrowth') or 0
        target = info.get('targetMeanPrice') or 0
        current = info.get('currentPrice') or info.get('regularMarketPrice') or 0
        market_cap = info.get('marketCap') or 0
        analyst_rec = info.get('recommendationMean') or 3
        analyst_count = info.get('numberOfAnalystOpinions') or 0
        beta = info.get('beta') or 1
        if current <= 0 or market_cap < min_cap:
            return None
        hist = s.history(period="6mo")
        if len(hist) < 30:
            return None
        rsi = calc_rsi(hist['Close'])
        macd_hist = calc_macd_hist(hist['Close'])
        mom_1m = calc_momentum(hist['Close'], 22)
        mom_3m = calc_momentum(hist['Close'], 66)
        upside = round(((target - current) / current * 100), 1) if target > 0 else 0
        avg_vol = hist['Volume'].mean()
        recent_vol = hist['Volume'].iloc[-5:].mean()
        vol_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 1
        months_est = estimate_months_to_target(upside, mom_1m)
        passed = False
        if strategy == "1. Төгс боломж":
            passed = (rsi < 40 and 0 < pe < 20 and growth > 0.08 and upside > 15)
        elif strategy == "2. Тренд дагах (Уян хатан)":
            passed = (50 < rsi < 72 and macd_hist > 0 and upside > 15 and mom_1m > 0)
        elif strategy == "3. Ирээдүйн өсөлт (Turnaround)":
            passed = (rsi < 60 and 0 < fpe < 28 and growth > 0.12 and upside > 15)
        if not passed:
            return None
        score = calc_score(pe, fpe, growth, rsi, upside, macd_hist, analyst_rec, strategy)
        if score < 40:
            return None
        signal_text, signal_color = get_signal(score, upside)
        if strategy == "1. Төгс боломж":
            radar_scores = [
                max(0, min(100, 100 - pe * 3)) if pe > 0 else 0,
                min(100, max(0, growth * 250)),
                min(100, max(0, upside * 2)),
                max(0, min(100, 100 - rsi)),
                min(100, max(0, 50 + mom_1m)),
            ]
        elif strategy == "2. Тренд дагах (Уян хатан)":
            radar_scores = [
                min(100, max(0, rsi)),
                min(100, max(0, 50 + macd_hist * 10)),
                min(100, max(0, upside * 2)),
                min(100, max(0, 50 + mom_1m)),
                min(100, max(0, 50 + mom_3m)),
            ]
        else:
            radar_scores = [
                min(100, max(0, growth * 250)),
                max(0, min(100, 100 - fpe * 2)) if fpe > 0 else 0,
                min(100, max(0, upside * 2)),
                min(100, max(0, earn_growth * 200)),
                max(0, min(100, 100 - rsi)),
            ]
        radar_labels = {
            "1. Төгс боломж": ["P/E Хямдрал", "Өсөлт", "Зорилт", "RSI Боломж", "Моментум"],
            "2. Тренд дагах (Уян хатан)": ["RSI Тренд", "MACD", "Зорилт", "1M Моментум", "3M Моментум"],
            "3. Ирээдүйн өсөлт (Turnaround)": ["Орлогын өсөлт", "Fwd P/E", "Зорилт", "Ашгийн өсөлт", "RSI Боломж"],
        }
        radar_df = pd.DataFrame({"Үзүүлэлт": radar_labels[strategy], "Оноо": radar_scores})
        return {
            "Тикер": ticker,
            "Компани": info.get('longName', ticker),
            "Салбар": info.get('sector', '—'),
            "rsi": rsi,
            "price": round(current, 2),
            "pe": round(pe, 1) if pe else "—",
            "fpe": round(fpe, 1) if fpe else "—",
            "growth": round(growth * 100, 1),
            "earn_growth": round(earn_growth * 100, 1),
            "upside": upside,
            "mom_1m": mom_1m,
            "mom_3m": mom_3m,
            "vol_ratio": vol_ratio,
            "market_cap": market_cap,
            "analyst_rec": round(analyst_rec, 1),
            "analyst_count": analyst_count,
            "beta": round(beta, 2),
            "score": score,
            "signal": signal_text,
            "signal_color": signal_color,
            "radar_df": radar_df,
            "months_est": months_est,
            "macd_hist": round(macd_hist, 4),
        }
    except:
        return None


def fmt_cap(cap):
    if cap >= 1e12:
        return f"${cap/1e12:.1f}T"
    if cap >= 1e9:
        return f"${cap/1e9:.1f}B"
    return f"${cap/1e6:.0f}M"


# ─── SIDEBAR ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Тохиргоо")
    universe = st.selectbox(
        "Хувьцааны орчлон:",
        ("S&P 500 (~500)", "Russell 2000 (~2000)", "Хосолсон (~2500)"),
        help="Russell 2000 = жижиг капиталтай компаниуд."
    )
    strategy = st.radio(
        "Стратеги:",
        ("1. Төгс боломж", "2. Тренд дагах (Уян хатан)", "3. Ирээдүйн өсөлт (Turnaround)"),
    )
    st.markdown("---")
    desc = {
        "1. Төгс боломж": (
            "**📉 Дутуу үнэлэгдсэн хувьцаа**\n\n"
            "- RSI < 40 *(хэт их зарагдсан)*\n"
            "- P/E < 20 *(хямд үнэлгээ)*\n"
            "- Орлогын өсөлт > 8%\n"
            "- Аналист зорилт > 15% дээш\n\n"
            "*Зах зээл хэт унагасан боловч үндсэн үзүүлэлт сайн хувьцааг олно.*"
        ),
        "2. Тренд дагах (Уян хатан)": (
            "**📈 Моментум тренд**\n\n"
            "- RSI 50–72 *(өсөлтийн бүс)*\n"
            "- MACD эерэг *(дээш чиглэл)*\n"
            "- Сүүлийн 1 сард өсөлттэй\n"
            "- Аналист зорилт > 15%\n\n"
            "*Өсч байгаа хувьцааны трендийг дагана.*"
        ),
        "3. Ирээдүйн өсөлт (Turnaround)": (
            "**🚀 Хурдацтай өсөлт**\n\n"
            "- Орлогын өсөлт > 12%\n"
            "- Forward P/E < 28 *(ирээдүйн үнэлгээ)*\n"
            "- RSI < 60 *(хэт халаагүй)*\n"
            "- Аналист зорилт > 15%\n\n"
            "*Ирээдүйд хурдацтай өсөх боломжтой компани.*"
        ),
    }
    st.info(desc[strategy])
    st.markdown("---")
    max_results = st.slider("Харуулах тоо", 5, 20, 10)
    run_btn = st.button("🚀 ШИНЖИЛГЭЭ ЭХЛЭХ", type="primary", use_container_width=True)


# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>📈 Ухаалаг Хувьцаа Шүүгч Pro</h1>
  <p>S&P 500 дотроос ойрын үед өсөх боломжтой хувьцааг олох мэргэжлийн хэрэгсэл</p>
</div>
""", unsafe_allow_html=True)


# ─── ШИНЖИЛГЭЭ ────────────────────────────────────────────────────────────────
if run_btn:
    tickers, min_cap = get_tickers_for_universe(universe)
    st.markdown(f"**📊 {universe} — нийт {len(tickers)} хувьцааг шинжилж байна...**")
    progress_bar = st.progress(0)
    status_empty = st.empty()
    results = []
    for i, t in enumerate(tickers):
        status_empty.caption(f"🔍 {t}  —  {i+1} / {len(tickers)}  |  Олдсон: {len(results)}")
        data = get_stock_data(t, strategy, min_cap=min_cap)
        if data:
            results.append(data)
        progress_bar.progress((i + 1) / len(tickers))
    results.sort(key=lambda x: x['score'], reverse=True)
    results = results[:max_results]
    progress_bar.empty()
    status_empty.empty()
    st.session_state.results = results
    st.session_state.strategy = strategy
    st.rerun()


# ─── ҮР ДҮН ──────────────────────────────────────────────────────────────────
if 'results' in st.session_state and st.session_state.results:
    results = st.session_state.results
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Олдсон хувьцаа", len(results))
    c2.metric("🏆 Шилдэг оноо", f"{results[0]['score']}/100")
    c3.metric("📈 Дундаж зорилт (12 сар)", f"{round(sum(r['upside'] for r in results)/len(results),1)}%")
    c4.metric("📊 Стратеги", st.session_state.get('strategy', '—')[:20])

    st.markdown("### 🏆 Шүүгчийн үр дүн — хувьцааг сонгоод дэлгэрэнгүй харна уу")

    display_rows = []
    for r in results:
        months_str = f"~{r['months_est']} сар" if r.get('months_est') else "—"
        display_rows.append({
            "Тикер": r['Тикер'],
            "Компани": r['Компани'][:28],
            "Оноо": r['score'],
            "Сигнал": r['signal'],
            "Үнэ ($)": r['price'],
            "12 сарын зорилт %": r['upside'],
            "Хүрэх хугацаа": months_str,
            "1 сарын өсөлт %": r['mom_1m'],
            "RSI (0-100)": r['rsi'],
            "Салбар": r['Салбар'],
        })

    df_disp = pd.DataFrame(display_rows)
    selected = st.dataframe(
        df_disp,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        column_config={
            "Оноо": st.column_config.ProgressColumn("Оноо", min_value=0, max_value=100, format="%d"),
            "12 сарын зорилт %": st.column_config.NumberColumn(format="%.1f%%"),
            "1 сарын өсөлт %": st.column_config.NumberColumn(format="%.1f%%"),
        }
    )

    if selected.selection.rows:
        idx = selected.selection.rows[0]
        stock = results[idx]
        st.divider()

        hdr1, hdr2 = st.columns([3, 1])
        with hdr1:
            st.markdown(f"## {stock['Тикер']}  —  {stock['Компани']}")
            st.caption(f"📂 {stock['Салбар']}  |  Market Cap: {fmt_cap(stock['market_cap'])}  |  Beta (эрсдэл): {stock['beta']}")
        with hdr2:
            st.markdown(f"### {stock['signal']}")
            st.markdown(f"**Нийт оноо: `{stock['score']} / 100`**")
            if stock.get('months_est'):
                st.info(f"⏱️ Зорилтод хүрэх\nойролцоо хугацаа:\n**~{stock['months_est']} сар**")

        # Үндсэн метрик
        st.markdown("#### 📊 Үндсэн үзүүлэлтүүд")
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Одоогийн үнэ", f"${stock['price']}")
        m2.metric("🎯 12 сарын аналист зорилт", f"{stock['upside']}%",
                  help="Аналистуудын тавьсан 12 сарын дундаж зорилтот үнэтэй харьцуулсан өсөх боломж")
        m3.metric("⏱️ Зорилтод хүрэх хугацаа",
                  f"~{stock['months_est']} сар" if stock.get('months_est') else "—",
                  help="Сүүлийн 1 сарын моментумаар тооцсон ойролцоо хугацаа")

        m4, m5, m6 = st.columns(3)
        m4.metric(
            "📊 RSI (хэт борлуулагдсан эсэх)",
            stock['rsi'],
            help="Relative Strength Index. 0-30: хэт их зарагдсан (авах боломж), 70+: хэт их худалдагдсан (эрсдэлтэй)"
        )
        m5.metric(
            "📉 P/E (үнэ/ашгийн харьцаа)",
            stock['pe'],
            help="Price-to-Earnings. Бага байх тусам хямд үнэлгээтэй. 15 доош = хямд, 30+ = үнэтэй"
        )
        m6.metric(
            "🔮 Fwd P/E (ирээдүйн үнэлгээ)",
            stock['fpe'],
            help="Forward P/E. Ирээдүйн ашгаар тооцсон үнэлгээ. Trailing P/E-ээс бага байвал өсөлт хүлээгдэж байна"
        )

        m7, m8, m9 = st.columns(3)
        m7.metric(
            "📈 1 сарын моментум (үнийн хурд)",
            f"{stock['mom_1m']}%",
            help="Momentum: сүүлийн 1 сарын хугацаанд үнэ хэдэн % өссөн/буурсан"
        )
        m8.metric(
            "📈 3 сарын моментум",
            f"{stock['mom_3m']}%",
            help="Сүүлийн 3 сарын үнийн өөрчлөлт"
        )
        m9.metric(
            "📊 MACD (чиглэлийн үзүүлэлт)",
            "Эерэг 📈" if stock['macd_hist'] > 0 else "Сөрөг 📉",
            help="Moving Average Convergence Divergence. Эерэг = дээш чиглэл, Сөрөг = доош чиглэл"
        )

        # Графикууд
        ch1, ch2 = st.columns(2)
        with ch1:
            st.subheader("📈 6 сарын үнийн хэлбэлзэл")
            hist_data = yf.Ticker(stock['Тикер']).history(period="6mo")
            if not hist_data.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist_data.index, y=hist_data['Close'],
                    mode='lines', fill='tozeroy',
                    line=dict(color='#58a6ff', width=2),
                    fillcolor='rgba(88,166,255,0.1)',
                    name='Хаалтын үнэ'
                ))
                ma20 = hist_data['Close'].rolling(20).mean()
                fig.add_trace(go.Scatter(
                    x=hist_data.index, y=ma20, mode='lines',
                    line=dict(color='#f0883e', width=1.5, dash='dot'),
                    name='MA20 (20 өдрийн дундаж)'
                ))
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    legend=dict(orientation='h', yanchor='bottom', y=1),
                    xaxis=dict(gridcolor='rgba(255,255,255,0.06)', showgrid=True),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.06)', showgrid=True),
                    margin=dict(l=0, r=0, t=10, b=0),
                    height=280
                )
                st.plotly_chart(fig, use_container_width=True)

        with ch2:
            st.subheader("🎯 Стратегийн нүүлэлт")
            fig2 = px.line_polar(
                stock['radar_df'], r='Оноо', theta='Үзүүлэлт',
                line_close=True, range_r=[0, 100],
                color_discrete_sequence=['#58a6ff']
            )
            fig2.update_traces(fill='toself', fillcolor='rgba(88,166,255,0.18)', line=dict(width=2))
            fig2.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                polar=dict(
                    bgcolor='rgba(0,0,0,0)',
                    radialaxis=dict(gridcolor='rgba(255,255,255,0.1)', tickfont_size=9),
                    angularaxis=dict(gridcolor='rgba(255,255,255,0.1)')
                ),
                margin=dict(l=20, r=20, t=30, b=20),
                height=280
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📊 Volume — эзлэхүүн (6 сар)")
        st.caption("Ногоон = өсөлттэй өдөр, Улаан = уналттай өдөр")
        if not hist_data.empty:
            vol_colors = ['#3fb950' if c >= o else '#f85149'
                          for c, o in zip(hist_data['Close'], hist_data['Open'])]
            fig3 = go.Figure(go.Bar(
                x=hist_data.index, y=hist_data['Volume'],
                marker_color=vol_colors, opacity=0.7, name='Volume'
            ))
            fig3.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                yaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                margin=dict(l=0, r=0, t=10, b=0),
                height=180
            )
            st.plotly_chart(fig3, use_container_width=True)

        st.subheader("📋 Аналистын мэдээлэл")
        ai1, ai2, ai3 = st.columns(3)
        rec_label = {1: "Хүчтэй Худалдаж ав ⭐⭐⭐", 2: "Худалдаж ав ⭐⭐", 3: "Хадгал ➖", 4: "Зар ⚠️", 5: "Хүчтэй Зар 🚨"}
        rec_val = int(round(stock['analyst_rec'])) if isinstance(stock['analyst_rec'], float) else 3
        ai1.metric("Аналистын дундаж үнэлгээ", rec_label.get(rec_val, "—"))
        ai2.metric("Үнэлгээ өгсөн аналистын тоо", stock['analyst_count'])
        ai3.metric("Ашгийн өсөлт (орлого)", f"{stock['earn_growth']}%")

elif 'results' in st.session_state and not st.session_state.results:
    st.warning("⚠️ Шалгуур хангасан хувьцаа олдсонгүй. Өөр стратеги туршина уу.")

else:
    st.markdown("""
    ### 👋 Тавтай морил!

    Зүүн цэснээс **стратеги сонгоод** 🚀 товчийг дарна уу.

    | Стратеги | Зориулалт | Хамгийн тохиромжтой |
    |----------|-----------|---------------------|
    | 📉 Төгс боломж | Хямдарсан, дутуу үнэлэгдсэн хувьцаа | Урт хугацааны хөрөнгө оруулагч |
    | 📈 Тренд дагах | Өсч байгаа хувьцааны тренд | Идэвхтэй трейдер |
    | 🚀 Ирээдүйн өсөлт | Хурдацтай өсөлттэй компани | Өсөлтийн хөрөнгө оруулагч |

    > ⚠️ Энэхүү апп нь мэдээлэл өгөх зорилготой бөгөөд хөрөнгө оруулалтын зөвлөгөө биш болно.
    """)
