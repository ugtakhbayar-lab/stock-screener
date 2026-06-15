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
    border: 1px solid #30363d; padding: 2rem 2.5rem;
    border-radius: 14px; margin-bottom: 2rem; text-align: center;
}
.main-header h1 { color: #58a6ff; font-size: 2.2rem; font-weight: 800; margin: 0; }
.main-header p  { color: #8b949e; margin: 0.4rem 0 0; }
[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
[data-testid="stSidebar"] h2 { color: #58a6ff !important; }
[data-testid="stSidebar"] strong { color: #ffffff !important; }
[data-testid="stMetricDelta"] svg { display: none; }
</style>
""", unsafe_allow_html=True)


# ── Стратегийн тодорхойлолт ───────────────────────────────────────────────────
STRATEGIES = {
    "📊 GARP — Тогтвортой өсөлт": {
        "horizon": "Дунд-урт хугацаа (3–12 сар)",
        "about": (
            "**Growth at Reasonable Price** — Питер Линчийн арга.\n\n"
            "Өсөлтийн хурдтайгаа харьцуулахад зохистой үнэтэй компани олно. "
            "Спекулятив биш, тогтвортой.\n\n"
            "- PEG < 1.5 *(үнэ/өсөлтийн харьцаа)*\n"
            "- Орлогын өсөлт > 10%\n"
            "- ROE > 10% *(өгөөжтэй бизнес)*\n"
            "- RSI 45–68 *(тэнцвэртэй бүс)*\n"
            "- MACD эерэг *(дээш чиглэл)*"
        ),
    },
    "💎 Чанарын хямдрал — Quality Dip": {
        "horizon": "Дунд хугацаа (2–8 сар)",
        "about": (
            "**Quality on Sale** — Баффетийн зарчимд суурилсан.\n\n"
            "Зах зээлийн айдсаар хямдарсан боловч бизнес нь хүчтэй компани олно.\n\n"
            "- RSI < 40 *(хэт зарагдсан)*\n"
            "- ROE > 12% *(чанартай бизнес)*\n"
            "- Орлогын өсөлт > 5%\n"
            "- Аналист зорилт > 20%\n"
            "- Өр/хөрөнгө тогтвортой"
        ),
    },
    "🚀 Моментум Breakout": {
        "horizon": "Богино-дунд хугацаа (1–4 сар)",
        "about": (
            "**Momentum Breakout** — O'Neil CANSLIM арга.\n\n"
            "Өсөлтийн тренд эхэлж буй хувьцааг эрт илрүүлнэ.\n\n"
            "- RSI 58–75 *(моментум бүс)*\n"
            "- 1 сарын өсөлт > 3%\n"
            "- 3 сарын өсөлт > 6%\n"
            "- Volume 1.2x дээш *(идэвхжилт)*\n"
            "- 52 долоо хоногийн өндрийн 80%+ дээр"
        ),
    },
}


# ── Тикер татах ───────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def get_sp500_tickers():
    try:
        df = pd.read_csv(
            "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv"
        )
        return df["Symbol"].astype(str).tolist()
    except Exception:
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"]


@st.cache_data(ttl=3600)
def get_wiki_tickers(url):
    try:
        tables = pd.read_html(url)
        for df in tables:
            cols = [str(c).lower() for c in df.columns]
            for kw in ("ticker", "symbol"):
                matches = [i for i, c in enumerate(cols) if kw in c]
                if matches:
                    col = df.columns[matches[0]]
                    tickers = (
                        df[col]
                        .astype(str)
                        .str.strip()
                        .str.replace(".", "-", regex=False)
                        .tolist()
                    )
                    tickers = [t for t in tickers if 1 <= len(t) <= 6 and t.replace("-", "").isalpha()]
                    if len(tickers) > 50:
                        return tickers
    except Exception:
        pass
    return []


@st.cache_data(ttl=3600)
def get_sp400_tickers():
    result = get_wiki_tickers("https://en.wikipedia.org/wiki/List_of_S%26P_400_companies")
    return result if result else []


@st.cache_data(ttl=3600)
def get_sp600_tickers():
    result = get_wiki_tickers("https://en.wikipedia.org/wiki/List_of_S%26P_600_companies")
    return result if result else []


@st.cache_data(ttl=3600)
def get_russell2000_tickers():
    try:
        import urllib.request
        url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/russell2000/russell2000_tickers.txt"
        with urllib.request.urlopen(url, timeout=10) as r:
            content = r.read().decode("utf-8")
        tickers = [t.strip() for t in content.splitlines() if t.strip()]
        if len(tickers) > 100:
            return tickers
    except Exception:
        pass
    return [
        "SMCI", "KRYS", "HIMS", "CARG", "IRTC", "NVST", "FRSH", "IIPR", "RGEN", "ASTS",
        "JOBY", "IONQ", "WOLF", "VERX", "TNDM", "FLNC", "PLAY", "WING", "SHAK", "CAVA",
        "BROS", "AXSM", "FORM", "AMBA", "HALO", "INMD", "TGTX", "LSCC", "ONTO", "COHU",
        "RMBS", "POWI", "CALX", "MGNI", "ACLS", "PRCT", "BLFS", "STAA", "OMCL", "NSIT",
    ]


@st.cache_data(ttl=3600)
def get_tickers_for_universe(universe):
    sp500 = get_sp500_tickers()
    sp400 = get_sp400_tickers()
    sp600 = get_sp600_tickers()
    r2000 = get_russell2000_tickers()
    mapping = {
        "S&P 500 — Том (~500)":      (sp500, 8_000_000_000),
        "S&P 400 — Дунд (~400)":     (sp400 if sp400 else sp500, 1_500_000_000),
        "S&P 600 — Жижиг (~600)":    (sp600 if sp600 else r2000, 200_000_000),
        "Russell 2000 (~2000)":       (r2000, 150_000_000),
        "S&P 1500 (500+400+600)":     (list(dict.fromkeys(sp500 + sp400 + sp600)), 200_000_000),
        "Бүгд (~3500)":               (list(dict.fromkeys(sp500 + sp400 + sp600 + r2000)), 150_000_000),
    }
    return mapping.get(universe, (sp500, 8_000_000_000))


# ── Техник үзүүлэлт ───────────────────────────────────────────────────────────
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


def calc_momentum(prices, days):
    if len(prices) < days:
        return 0.0
    return round((prices.iloc[-1] / prices.iloc[-days] - 1) * 100, 2)


# ── Стратегийн шүүлтүүр + оноо ───────────────────────────────────────────────
def score_garp(peg, growth, roe, rsi, macd_hist, upside, analyst_rec):
    passed = (
        0 < peg < 1.5
        and growth > 0.10
        and roe > 0.10
        and 45 <= rsi <= 68
        and macd_hist > 0
        and upside > 15
    )
    if not passed:
        return False, 0
    s = 0
    if peg < 0.6:
        s += 30
    elif peg < 1.0:
        s += 22
    elif peg < 1.3:
        s += 14
    else:
        s += 7
    if growth > 0.25:
        s += 25
    elif growth > 0.18:
        s += 18
    elif growth > 0.12:
        s += 10
    else:
        s += 5
    if roe > 0.25:
        s += 20
    elif roe > 0.18:
        s += 14
    elif roe > 0.12:
        s += 8
    else:
        s += 4
    if 55 <= rsi <= 65:
        s += 15
    elif 48 <= rsi <= 68:
        s += 8
    if macd_hist > 0:
        s += 10
    if analyst_rec and analyst_rec < 2.0:
        s += 10
    elif analyst_rec and analyst_rec < 2.5:
        s += 5
    return True, min(100, s)


def score_quality_dip(rsi, roe, growth, upside, debt_ratio, vol_ratio, analyst_rec):
    passed = (
        rsi < 40
        and roe > 0.12
        and growth > 0.05
        and upside > 20
        and debt_ratio < 2.0
    )
    if not passed:
        return False, 0
    s = 0
    if rsi < 28:
        s += 30
    elif rsi < 33:
        s += 22
    elif rsi < 37:
        s += 14
    else:
        s += 7
    if roe > 0.30:
        s += 25
    elif roe > 0.22:
        s += 18
    elif roe > 0.15:
        s += 12
    else:
        s += 6
    if upside > 40:
        s += 25
    elif upside > 30:
        s += 18
    elif upside > 25:
        s += 12
    else:
        s += 6
    if growth > 0.20:
        s += 12
    elif growth > 0.12:
        s += 8
    else:
        s += 4
    if debt_ratio < 0.3:
        s += 5
    if vol_ratio > 1.4:
        s += 3
    if analyst_rec and analyst_rec < 2.0:
        s += 10
    elif analyst_rec and analyst_rec < 2.5:
        s += 5
    return True, min(100, s)


def score_momentum(rsi, mom_1m, mom_3m, macd_hist, vol_ratio, upside, analyst_rec, price, high_52w):
    near_high = (price / high_52w >= 0.80) if high_52w > 0 else False
    passed = (
        58 <= rsi <= 75
        and mom_1m > 3
        and mom_3m > 6
        and macd_hist > 0
        and vol_ratio > 1.2
        and upside > 12
        and near_high
    )
    if not passed:
        return False, 0
    s = 0
    if 62 <= rsi <= 70:
        s += 25
    elif 58 <= rsi <= 75:
        s += 15
    if mom_1m > 10:
        s += 25
    elif mom_1m > 7:
        s += 18
    elif mom_1m > 5:
        s += 12
    else:
        s += 6
    if mom_3m > 20:
        s += 20
    elif mom_3m > 14:
        s += 14
    elif mom_3m > 8:
        s += 8
    else:
        s += 4
    if macd_hist > 0:
        s += 15
    if vol_ratio > 2.0:
        s += 10
    elif vol_ratio > 1.5:
        s += 6
    else:
        s += 3
    if upside > 25:
        s += 5
    if analyst_rec and analyst_rec < 2.0:
        s += 10
    elif analyst_rec and analyst_rec < 2.5:
        s += 5
    return True, min(100, s)


# ── Нэг хувьцааны өгөгдөл ────────────────────────────────────────────────────
def get_stock_data(ticker, strategy, min_cap):
    try:
        s = yf.Ticker(ticker)
        info = s.info
        if not info or info.get("quoteType") != "EQUITY":
            return None
        current = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        market_cap = info.get("marketCap") or 0
        if current <= 0 or market_cap < min_cap:
            return None

        pe = info.get("trailingPE") or 0
        fpe = info.get("forwardPE") or 0
        peg = info.get("pegRatio") or 0
        growth = info.get("revenueGrowth") or 0
        earn_growth = info.get("earningsGrowth") or 0
        roe_raw = info.get("returnOnEquity") or 0
        roe = roe_raw if abs(roe_raw) < 5 else roe_raw / 100
        debt_eq_raw = info.get("debtToEquity") or 0
        debt_ratio = debt_eq_raw / 100 if debt_eq_raw > 5 else debt_eq_raw
        target = info.get("targetMeanPrice") or 0
        analyst_rec = info.get("recommendationMean") or 3
        analyst_cnt = info.get("numberOfAnalystOpinions") or 0
        beta = info.get("beta") or 1
        high_52w = info.get("fiftyTwoWeekHigh") or 0

        upside = round(((target - current) / current * 100), 1) if target > 0 else 0

        hist = s.history(period="6mo")
        if len(hist) < 30:
            return None

        rsi = calc_rsi(hist["Close"])
        macd_hist = calc_macd_hist(hist["Close"])
        mom_1m = calc_momentum(hist["Close"], 22)
        mom_3m = calc_momentum(hist["Close"], 66)
        avg_vol = hist["Volume"].mean()
        recent_vol = hist["Volume"].iloc[-5:].mean()
        vol_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        if strategy == "📊 GARP — Тогтвортой өсөлт":
            passed, sc = score_garp(peg, growth, roe, rsi, macd_hist, upside, analyst_rec)
            radar = {
                "PEG": max(0, min(100, (1.5 - peg) / 1.5 * 100)) if peg > 0 else 0,
                "Өсөлт": min(100, growth * 300),
                "ROE": min(100, roe * 300),
                "RSI тэнцвэр": max(0, min(100, 100 - abs(rsi - 57) * 3)),
                "Аналист зорилт": min(100, upside * 2.5),
            }
        elif strategy == "💎 Чанарын хямдрал — Quality Dip":
            passed, sc = score_quality_dip(rsi, roe, growth, upside, debt_ratio, vol_ratio, analyst_rec)
            radar = {
                "RSI боломж": max(0, min(100, (40 - rsi) * 3.5)),
                "ROE чанар": min(100, roe * 300),
                "Зорилт": min(100, upside * 2),
                "Бага өр": max(0, min(100, 100 - debt_ratio * 40)),
                "Өсөлт": min(100, growth * 400),
            }
        else:
            passed, sc = score_momentum(rsi, mom_1m, mom_3m, macd_hist, vol_ratio, upside, analyst_rec, current, high_52w)
            radar = {
                "RSI моментум": max(0, min(100, rsi)),
                "1M өсөлт": min(100, mom_1m * 6),
                "3M өсөлт": min(100, mom_3m * 3),
                "Volume": min(100, vol_ratio * 40),
                "MACD": 80 if macd_hist > 0 else 20,
            }

        if not passed or sc < 35:
            return None

        signal = "🟢 ХУДАЛДАЖ АВ" if sc >= 70 else ("🟡 АЖИГЛА" if sc >= 50 else "🔴 БОЛГООМЖИЛ")
        radar_df = pd.DataFrame({"Үзүүлэлт": list(radar.keys()), "Оноо": list(radar.values())})

        return {
            "Тикер": ticker,
            "Компани": info.get("longName", ticker),
            "Салбар": info.get("sector", "—"),
            "price": round(current, 2),
            "pe": round(pe, 1) if pe else "—",
            "fpe": round(fpe, 1) if fpe else "—",
            "peg": round(peg, 2) if peg else "—",
            "growth": round(growth * 100, 1),
            "earn_growth": round(earn_growth * 100, 1),
            "roe": round(roe * 100, 1),
            "debt_ratio": round(debt_ratio, 2),
            "upside": upside,
            "rsi": rsi,
            "macd_hist": round(macd_hist, 4),
            "mom_1m": mom_1m,
            "mom_3m": mom_3m,
            "vol_ratio": vol_ratio,
            "market_cap": market_cap,
            "analyst_rec": round(analyst_rec, 1),
            "analyst_cnt": analyst_cnt,
            "beta": round(beta, 2),
            "high_52w": round(high_52w, 2),
            "score": sc,
            "signal": signal,
            "radar_df": radar_df,
        }
    except Exception:
        return None


def fmt_cap(cap):
    if cap >= 1e12:
        return f"${cap/1e12:.1f}T"
    if cap >= 1e9:
        return f"${cap/1e9:.1f}B"
    return f"${cap/1e6:.0f}M"


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Тохиргоо")
    universe = st.selectbox(
        "Хувьцааны орчлон:",
        [
            "S&P 500 — Том (~500)",
            "S&P 400 — Дунд (~400)",
            "S&P 600 — Жижиг (~600)",
            "Russell 2000 (~2000)",
            "S&P 1500 (500+400+600)",
            "Бүгд (~3500)",
        ],
    )
    strategy = st.radio("Стратеги:", list(STRATEGIES.keys()))
    st.markdown("---")
    st.info(STRATEGIES[strategy]["about"])
    st.caption(f"⏱️ Хугацаа: **{STRATEGIES[strategy]['horizon']}**")
    st.markdown("---")
    max_results = st.slider("Харуулах тоо", 5, 20, 10)
    run_btn = st.button("🚀 ШИНЖИЛГЭЭ ЭХЛЭХ", type="primary", use_container_width=True)


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>📈 Ухаалаг Хувьцаа Шүүгч Pro</h1>
  <p>Ашиг олох боломжтой хувьцааг олох мэргэжлийн хэрэгсэл</p>
</div>
""", unsafe_allow_html=True)


# ── ШИНЖИЛГЭЭ ────────────────────────────────────────────────────────────────
if run_btn:
    tickers, min_cap = get_tickers_for_universe(universe)
    st.markdown(f"**📊 {universe} — нийт {len(tickers)} хувьцааг шинжилж байна...**")
    bar = st.progress(0)
    status = st.empty()
    results = []
    for i, t in enumerate(tickers):
        status.caption(f"🔍 {t}  —  {i+1}/{len(tickers)}  |  Олдсон: {len(results)}")
        data = get_stock_data(t, strategy, min_cap)
        if data:
            results.append(data)
        bar.progress((i + 1) / len(tickers))
    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:max_results]
    bar.empty()
    status.empty()
    st.session_state.results = results
    st.session_state.strategy = strategy
    st.rerun()


# ── ҮР ДҮН ───────────────────────────────────────────────────────────────────
if "results" in st.session_state and st.session_state.results:
    results = st.session_state.results
    strat = st.session_state.get("strategy", "")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("✅ Олдсон", len(results))
    c2.metric("🏆 Шилдэг оноо", f"{results[0]['score']}/100")
    c3.metric("📈 Дундаж зорилт (12 сар)", f"{round(sum(r['upside'] for r in results)/len(results), 1)}%")
    c4.metric("⏱️ Хугацаа", STRATEGIES.get(strat, {}).get("horizon", "—")[:18])

    st.markdown("### 🏆 Үр дүн — мөрийг сонгоод дэлгэрэнгүй харна уу")

    rows = []
    for r in results:
        row = {
            "Тикер": r["Тикер"],
            "Компани": r["Компани"][:26],
            "Оноо": r["score"],
            "Сигнал": r["signal"],
            "Үнэ ($)": r["price"],
            "12 сарын зорилт %": r["upside"],
            "RSI": r["rsi"],
        }
        if "GARP" in strat:
            row["PEG"] = r["peg"]
            row["ROE %"] = r["roe"]
            row["Өсөлт %"] = r["growth"]
        elif "Чанар" in strat:
            row["ROE %"] = r["roe"]
            row["Өр харьцаа"] = r["debt_ratio"]
            row["Өсөлт %"] = r["growth"]
        else:
            row["1M өсөлт %"] = r["mom_1m"]
            row["3M өсөлт %"] = r["mom_3m"]
            row["Volume x"] = r["vol_ratio"]
        row["Салбар"] = r["Салбар"]
        rows.append(row)

    df_disp = pd.DataFrame(rows)
    selected = st.dataframe(
        df_disp,
        use_container_width=True,
        on_select="rerun",
        selection_mode="single-row",
        hide_index=True,
        column_config={
            "Оноо": st.column_config.ProgressColumn("Оноо", min_value=0, max_value=100, format="%d"),
            "12 сарын зорилт %": st.column_config.NumberColumn(format="%.1f%%"),
            "1M өсөлт %": st.column_config.NumberColumn(format="%.1f%%"),
            "3M өсөлт %": st.column_config.NumberColumn(format="%.1f%%"),
            "Өсөлт %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    if selected.selection.rows:
        idx = selected.selection.rows[0]
        stock = results[idx]
        st.divider()

        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown(f"## {stock['Тикер']} — {stock['Компани']}")
            st.caption(f"📂 {stock['Салбар']}  |  {fmt_cap(stock['market_cap'])}  |  Beta (эрсдэл): {stock['beta']}")
        with h2:
            st.markdown(f"### {stock['signal']}")
            st.markdown(f"**Оноо: `{stock['score']} / 100`**")
            st.info(STRATEGIES.get(strat, {}).get("horizon", ""))

        st.markdown("#### 💰 Үнэ ба зорилт")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Одоогийн үнэ", f"${stock['price']}")
        m2.metric(
            "12 сарын аналист зорилт",
            f"{stock['upside']}%",
            help="Аналистуудын дундаж 12 сарын зорилтот үнэтэй харьцуулсан өсөх боломж",
        )
        m3.metric("52 долоо хоногийн дээд", f"${stock['high_52w']}", help="Сүүлийн 1 жилийн хамгийн өндөр үнэ")
        m4.metric("Аналистын тоо", stock["analyst_cnt"])

        st.markdown("#### 📊 Үнэлгээ (Valuation)")
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("P/E (үнэ/ашгийн харьцаа)", stock["pe"], help="Бага байх тусам хямд. 15 доош=хямд, 30+=үнэтэй")
        v2.metric("Fwd P/E (ирээдүйн үнэлгээ)", stock["fpe"], help="Ирээдүйн ашигт суурилсан. Trailing P/E-ээс бага=өсөлт хүлээгдэж байна")
        v3.metric("PEG (үнэ/өсөлтийн харьцаа)", stock["peg"], help="1 доош=өсөлттэй харьцуулахад хямд. Питер Линч: 0.5 доош=маш сайн")
        v4.metric("ROE (өөрийн хөрөнгийн өгөөж)", f"{stock['roe']}%", help="15%+=сайн, 25%+=маш сайн")

        st.markdown("#### 📈 Техник үзүүлэлт")
        t1, t2, t3, t4, t5 = st.columns(5)
        t1.metric("RSI (хэт борлуулагдсан эсэх)", stock["rsi"], help="30 доош=хэт зарагдсан (авах боломж), 70+=хэт худалдагдсан")
        t2.metric("MACD (чиглэлийн үзүүлэлт)", "📈 Дээш" if stock["macd_hist"] > 0 else "📉 Доош", help="Эерэг=дээш тренд, Сөрөг=доош тренд")
        t3.metric("1 сарын моментум (үнийн хурд)", f"{stock['mom_1m']}%", help="Сүүлийн 22 арилжааны өдрийн үнийн өөрчлөлт")
        t4.metric("3 сарын моментум", f"{stock['mom_3m']}%")
        t5.metric("Volume хэтрэлт", f"{stock['vol_ratio']}x", help="1.5x+=идэвхтэй арилжаа")

        st.markdown("#### 🏢 Бизнесийн үзүүлэлт")
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Орлогын өсөлт", f"{stock['growth']}%")
        b2.metric("Ашгийн өсөлт", f"{stock['earn_growth']}%")
        b3.metric("Өр/хөрөнгийн харьцаа", stock["debt_ratio"], help="0.5 доош=тогтвортой санхүү, 2.0+=өндөр өртэй")
        rec_map = {1: "⭐⭐⭐ Хүчтэй авах", 2: "⭐⭐ Авах", 3: "➖ Хадгал", 4: "⚠️ Зарах", 5: "🚨 Хүчтэй зарах"}
        rec_val = int(round(stock["analyst_rec"])) if isinstance(stock["analyst_rec"], float) else 3
        b4.metric("Аналистын үнэлгээ", rec_map.get(rec_val, "—"))

        ch1, ch2 = st.columns(2)
        with ch1:
            st.subheader("📈 6 сарын үнийн хэлбэлзэл")
            hist_data = yf.Ticker(stock["Тикер"]).history(period="6mo")
            if not hist_data.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=hist_data.index, y=hist_data["Close"],
                    mode="lines", fill="tozeroy",
                    line=dict(color="#58a6ff", width=2),
                    fillcolor="rgba(88,166,255,0.1)", name="Үнэ",
                ))
                ma20 = hist_data["Close"].rolling(20).mean()
                fig.add_trace(go.Scatter(
                    x=hist_data.index, y=ma20, mode="lines",
                    line=dict(color="#f0883e", width=1.5, dash="dot"),
                    name="MA20 (20 өдрийн дундаж)",
                ))
                fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                    xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                    yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                    margin=dict(l=0, r=0, t=5, b=0), height=260,
                )
                st.plotly_chart(fig, use_container_width=True)

        with ch2:
            st.subheader("🎯 Стратегийн нүүлэлт")
            fig2 = px.line_polar(
                stock["radar_df"], r="Оноо", theta="Үзүүлэлт",
                line_close=True, range_r=[0, 100],
                color_discrete_sequence=["#58a6ff"],
            )
            fig2.update_traces(fill="toself", fillcolor="rgba(88,166,255,0.18)", line=dict(width=2))
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                polar=dict(
                    bgcolor="rgba(0,0,0,0)",
                    radialaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont_size=9),
                    angularaxis=dict(gridcolor="rgba(255,255,255,0.1)"),
                ),
                margin=dict(l=20, r=20, t=20, b=20), height=260,
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.subheader("📊 Volume — арилжааны эзлэхүүн (6 сар)")
        if not hist_data.empty:
            vol_colors = [
                "#3fb950" if c >= o else "#f85149"
                for c, o in zip(hist_data["Close"], hist_data["Open"])
            ]
            fig3 = go.Figure(go.Bar(
                x=hist_data.index, y=hist_data["Volume"],
                marker_color=vol_colors, opacity=0.75,
            ))
            fig3.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                margin=dict(l=0, r=0, t=5, b=0), height=160,
            )
            st.plotly_chart(fig3, use_container_width=True)

elif "results" in st.session_state and not st.session_state.results:
    st.warning("⚠️ Шалгуур хангасан хувьцаа олдсонгүй. Өөр стратеги эсвэл орчлон сонгоно уу.")

else:
    st.markdown("""
    ### 👋 Тавтай морил!

    Зүүн цэснээс **орчлон** болон **стратеги** сонгоод 🚀 товчийг дарна уу.

    | Стратеги | Үндэслэл | Хугацаа |
    |---|---|---|
    | 📊 GARP | Питер Линч — PEG + ROE + өсөлт | 3–12 сар |
    | 💎 Чанарын хямдрал | Баффет — oversold чанарын компани | 2–8 сар |
    | 🚀 Моментум Breakout | O'Neil — тренд эхэлж буй хувьцаа | 1–4 сар |

    > ⚠️ Энэхүү апп нь мэдээлэл өгөх зорилготой бөгөөд хөрөнгө оруулалтын зөвлөгөө биш болно.
    """)
