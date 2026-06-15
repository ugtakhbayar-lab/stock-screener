import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

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
    border-radius: 14px; margin-bottom: 1.5rem; text-align: center;
}
.main-header h1 { color: #58a6ff; font-size: 2rem; font-weight: 800; margin: 0; }
.main-header p  { color: #8b949e; margin: 0.4rem 0 0; }
[data-testid="stSidebar"] { background: #0d1117 !important; border-right: 1px solid #21262d; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #58a6ff !important; }
[data-testid="stSidebar"] strong { color: #ffffff !important; }
[data-testid="stMetricDelta"] svg { display: none; }
.risk-low   { color: #3fb950; font-weight: 700; }
.risk-mid   { color: #d29922; font-weight: 700; }
.risk-high  { color: #f85149; font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ── Стратегийн тодорхойлолт ───────────────────────────────────────────────────
STRATEGIES = {
    "📊 GARP — Тогтвортой өсөлт": {
        "horizon": "Дунд-урт хугацаа (3–12 сар)",
        "about": (
            "**Growth at Reasonable Price** — Питер Линчийн арга.\n\n"
            "Өсөлтийн хурдтайгаа харьцуулахад зохистой үнэтэй компани олно.\n\n"
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
        import urllib.request
        headers = {"User-Agent": "Mozilla/5.0 (compatible; stockscreener/1.0)"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        tables = pd.read_html(html)
        for df in tables:
            cols = [str(c).lower() for c in df.columns]
            for kw in ("ticker", "symbol", "stock"):
                matches = [i for i, c in enumerate(cols) if kw in c]
                if matches:
                    col = df.columns[matches[0]]
                    tickers = (
                        df[col].astype(str).str.strip()
                        .str.replace(".", "-", regex=False).tolist()
                    )
                    tickers = [t for t in tickers if 1 <= len(t) <= 6 and t.replace("-", "").isalpha()]
                    if len(tickers) > 50:
                        return tickers
    except Exception:
        pass
    return []


@st.cache_data(ttl=3600)
def get_sp400_tickers():
    for url in [
        "https://en.wikipedia.org/wiki/List_of_S%26P_Mid-Cap_400_companies",
        "https://en.wikipedia.org/wiki/List_of_S%26P_400_companies",
    ]:
        result = get_wiki_tickers(url)
        if result:
            return result
    return []


@st.cache_data(ttl=3600)
def get_sp600_tickers():
    for url in [
        "https://en.wikipedia.org/wiki/List_of_S%26P_Small-Cap_600_companies",
        "https://en.wikipedia.org/wiki/List_of_S%26P_600_companies",
    ]:
        result = get_wiki_tickers(url)
        if result:
            return result
    return []


@st.cache_data(ttl=3600)
def get_russell2000_tickers():
    import urllib.request
    try:
        url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/russell2000/russell2000_tickers.txt"
        with urllib.request.urlopen(url, timeout=12) as r:
            content = r.read().decode("utf-8")
        tickers = [t.strip() for t in content.splitlines() if t.strip()]
        if len(tickers) > 100:
            return tickers
    except Exception:
        pass
    return [
        "SMCI","KRYS","HIMS","CARG","IRTC","NVST","FRSH","IIPR","RGEN","ASTS",
        "JOBY","IONQ","WOLF","VERX","TNDM","FLNC","PLAY","WING","SHAK","CAVA",
        "BROS","AXSM","FORM","AMBA","HALO","INMD","TGTX","LSCC","ONTO","COHU",
        "RMBS","POWI","CALX","MGNI","ACLS","PRCT","BLFS","STAA","OMCL","NSIT",
        "AGIO","FOLD","ACAD","CARA","CDXS","CNXC","CORT","DCPH","ECPG","ENVA",
        "EXAS","EXPI","FCFS","FIVN","FND","FRPT","GCMG","GKOS","GNRC","GPRO",
        "GSHD","HCAT","HLNE","HMST","HRMY","HTBK","HTLD","IBTX","ICFI","IDCC",
        "INFU","INVA","IOSP","IPAR","IRMD","ISBC","ITCI","JBSS","JELD","JJSF",
        "KELYA","KFRC","KIDS","KMPR","KNSA","KTOS","LAKE","LANC","LCII","LGND",
        "LKFN","LMAT","LNTH","LOCO","LOPE","LPRO","LUNA","MBIN","MBUU","MDGL",
        "MEDP","MGLN","MGRC","MIRM","MKSI","MMSI","MNKD","MODV","MOFG","MPWR",
        "MRCY","MRTN","MSEX","MSTR","MTRN","NABL","NARI","NATH","NBTB","NCBS",
        "NMIH","NNOX","NOMD","NOVT","NPCE","NTCT","NVEE","NVRO","NWBI","OCFC",
        "OCUL","OFIX","OMCL","ONTO","OPRX","ORGO","OSBC","OSIS","OSPN","OTRK",
        "PAHC","PCVX","PDCO","PDFS","PFIS","PGNY","PHAT","PINC","PIPR","PKOH",
        "PLCE","PLMR","PLUS","PMVP","PODD","POWI","PPBI","PRDO","PRFT","PRGS",
        "PRTA","PTCT","PTGX","PUMP","PVBC","PWSC","PYCR","QDEL","QNST","QTWO",
        "RAMP","RCKT","RCUS","RDUS","REAL","REEF","REXR","RFIL","RGEN","RLAY",
        "RMBS","RNST","ROAD","RRGB","RRTS","RUSHA","RUTH","SABR","SAFE","SAGE",
        "SAMG","SANM","SASR","SBCF","SBGI","SBRA","SCHL","SCSC","SDGR","SEER",
        "SFBS","SFNC","SHYF","SIBN","SIGI","SILK","SKYW","SLCA","SLGN","SMBC",
        "SMCI","SMED","SMPL","SNBR","SNCY","SNDR","SNEX","SPFI","SPOK","SPWR",
        "SQSP","SRCE","SRDX","SRGA","SRRK","SSYS","STBA","STFC","STKS","STRA",
        "STRL","SWIM","SYBT","SYNA","SYNH","TBBK","TBPH","TCBK","TCMD","TCRR",
        "TENB","TGTX","TILE","TITN","TMDX","TNXP","TPIC","TRIN","TRMK","TRNS",
        "TRUP","TRVN","TTEC","TTGT","TUSK","TZOO","UBCP","UCBI","UCTT","UEIC",
        "UFCS","UFPT","UMBF","UNFI","UNIT","UPBD","UPWK","URBN","USAK","USPH",
        "UVSP","VBTX","VCNX","VCRA","VCYT","VECO","VERI","VIAV","VIRT","VIVO",
        "VNDA","VNET","VOXX","VRCA","VRRM","VRTS","VSCO","VSTO","VTRS","WABC",
        "WAFD","WASH","WDFC","WETF","WEYS","WIRE","WLDN","WOOF","WRLD","WSBC",
        "WSFS","WTBA","WTFC","XNCR","XPEL","XRAY","YEXT","ZGNX","ZIXI","ZUMZ",
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
    if peg < 0.6:     s += 30
    elif peg < 1.0:   s += 22
    elif peg < 1.3:   s += 14
    else:             s += 7
    if growth > 0.25: s += 25
    elif growth > 0.18: s += 18
    elif growth > 0.12: s += 10
    else:             s += 5
    if roe > 0.25:    s += 20
    elif roe > 0.18:  s += 14
    elif roe > 0.12:  s += 8
    else:             s += 4
    if 55 <= rsi <= 65: s += 15
    elif 48 <= rsi <= 68: s += 8
    if macd_hist > 0: s += 10
    if analyst_rec and analyst_rec < 2.0: s += 10
    elif analyst_rec and analyst_rec < 2.5: s += 5
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
    if rsi < 28:      s += 30
    elif rsi < 33:    s += 22
    elif rsi < 37:    s += 14
    else:             s += 7
    if roe > 0.30:    s += 25
    elif roe > 0.22:  s += 18
    elif roe > 0.15:  s += 12
    else:             s += 6
    if upside > 40:   s += 25
    elif upside > 30: s += 18
    elif upside > 25: s += 12
    else:             s += 6
    if growth > 0.20: s += 12
    elif growth > 0.12: s += 8
    else:             s += 4
    if debt_ratio < 0.3: s += 5
    if vol_ratio > 1.4:  s += 3
    if analyst_rec and analyst_rec < 2.0: s += 10
    elif analyst_rec and analyst_rec < 2.5: s += 5
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
    if 62 <= rsi <= 70:   s += 25
    elif 58 <= rsi <= 75: s += 15
    if mom_1m > 10:  s += 25
    elif mom_1m > 7: s += 18
    elif mom_1m > 5: s += 12
    else:            s += 6
    if mom_3m > 20:  s += 20
    elif mom_3m > 14: s += 14
    elif mom_3m > 8: s += 8
    else:            s += 4
    if macd_hist > 0: s += 15
    if vol_ratio > 2.0:   s += 10
    elif vol_ratio > 1.5: s += 6
    else:                 s += 3
    if upside > 25: s += 5
    if analyst_rec and analyst_rec < 2.0: s += 10
    elif analyst_rec and analyst_rec < 2.5: s += 5
    return True, min(100, s)


# ── Нэг хувьцааны өгөгдөл ────────────────────────────────────────────────────
def get_stock_data(ticker, strategy, min_cap=0):
    try:
        s = yf.Ticker(ticker)
        info = s.info
        if not info or info.get("quoteType") != "EQUITY":
            return None
        current = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        market_cap = info.get("marketCap") or 0
        if current <= 0 or (min_cap > 0 and market_cap < min_cap):
            return None

        pe          = info.get("trailingPE") or 0
        fpe         = info.get("forwardPE") or 0
        peg         = info.get("pegRatio") or 0
        growth      = info.get("revenueGrowth") or 0
        earn_growth = info.get("earningsGrowth") or 0
        roe_raw     = info.get("returnOnEquity") or 0
        roe         = roe_raw if abs(roe_raw) < 5 else roe_raw / 100
        debt_eq_raw = info.get("debtToEquity") or 0
        debt_ratio  = debt_eq_raw / 100 if debt_eq_raw > 5 else debt_eq_raw
        target      = info.get("targetMeanPrice") or 0
        analyst_rec = info.get("recommendationMean") or 3
        analyst_cnt = info.get("numberOfAnalystOpinions") or 0
        beta        = info.get("beta") or 1
        high_52w    = info.get("fiftyTwoWeekHigh") or 0

        upside = round((target - current) / current * 100, 1) if target > 0 else 0

        hist = s.history(period="6mo")
        if len(hist) < 30:
            return None

        rsi       = calc_rsi(hist["Close"])
        macd_hist_v = calc_macd_hist(hist["Close"])
        mom_1m    = calc_momentum(hist["Close"], 22)
        mom_3m    = calc_momentum(hist["Close"], 66)
        avg_vol   = hist["Volume"].mean()
        recent_vol = hist["Volume"].iloc[-5:].mean()
        vol_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        if strategy == "📊 GARP — Тогтвортой өсөлт":
            passed, sc = score_garp(peg, growth, roe, rsi, macd_hist_v, upside, analyst_rec)
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
            passed, sc = score_momentum(rsi, mom_1m, mom_3m, macd_hist_v, vol_ratio, upside, analyst_rec, current, high_52w)
            radar = {
                "RSI моментум": max(0, min(100, rsi)),
                "1M өсөлт": min(100, mom_1m * 6),
                "3M өсөлт": min(100, mom_3m * 3),
                "Volume": min(100, vol_ratio * 40),
                "MACD": 80 if macd_hist_v > 0 else 20,
            }

        if not passed or sc < 35:
            return None

        signal = "🟢 ХУДАЛДАЖ АВ" if sc >= 70 else ("🟡 АЖИГЛА" if sc >= 50 else "🔴 БОЛГООМЖИЛ")

        # Эрсдэлийн түвшин
        risk_score = 0
        if beta > 1.5:       risk_score += 2
        elif beta > 1.1:     risk_score += 1
        if debt_ratio > 1.5: risk_score += 2
        elif debt_ratio > 0.8: risk_score += 1
        if risk_score >= 3:  risk_level = "🔴 Өндөр"
        elif risk_score >= 1: risk_level = "🟡 Дунд"
        else:                risk_level = "🟢 Бага"

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
            "macd_hist": round(macd_hist_v, 4),
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
            "risk_level": risk_level,
            "radar_df": radar_df,
        }
    except Exception:
        return None



def get_entry_advice(ticker):
    """Stage 3: яг хэзээ авах талаар техник дүн шинжилгээ"""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        hist = tk.history(period="3mo")
        if len(hist) < 20:
            return None
        current = hist["Close"].iloc[-1]
        rsi = calc_rsi(hist["Close"])
        macd = calc_macd_hist(hist["Close"])
        support = float(hist["Low"].rolling(10).min().iloc[-1])
        resist  = float(hist["High"].rolling(10).max().iloc[-1])
        dist_sup_pct = (current - support) / current * 100
        target = info.get("targetMeanPrice") or 0
        upside = round((target - current) / current * 100, 1) if target > 0 else 0
        stop_loss = round(max(current * 0.92, support * 0.97), 2)
        entry_low  = round(support * 1.01, 2)
        entry_high = round(support * 1.04, 2)

        if rsi < 35 and macd > 0:
            advice = "Одоо авах цаг таарч байна"
            color  = "success"
            detail = f"RSI ({rsi}) хэт зарагдсан бүс — MACD эергийн хослол идэальд"
        elif rsi < 45 and dist_sup_pct < 4:
            advice = "Дэмжлэгийн бүсэд — авах боломжтой"
            color  = "success"
            detail = f"Дэмжлэгийн ${support:.2f}-ийн ойролцоо байна ({dist_sup_pct:.1f}%)"
        elif rsi > 68:
            advice = "Хямдрал хүлээнэ"
            color  = "warning"
            detail = f"RSI ({rsi}) өндөр — ойрын зарлага болзошгүй"
        elif macd < 0 and rsi > 55:
            advice = "MACD сул — дараагийн дохиог хүлээнэ"
            color  = "warning"
            detail = "MACD сөрөг тренд — RSI буурч дэмжлэгт хүрхийг хүлээнэ"
        elif dist_sup_pct > 8:
            advice = f"${entry_low}–${entry_high} буурахийг хүлээнэ"
            color  = "info"
            detail = f"Дэмжлэгийн түвшнээс {dist_sup_pct:.1f}% дээш — илүү сайн оролтын боломж байна"
        else:
            advice = "Тренд нотлогдохийг хүлээнэ"
            color  = "info"
            detail = "Тодорхой чиглэл одоохондоо илрэхгүй байна"

        return {
            "advice": advice,
            "color": color,
            "detail": detail,
            "rsi": rsi,
            "macd": round(macd, 4),
            "support": round(support, 2),
            "resist": round(resist, 2),
            "current": round(current, 2),
            "stop_loss": stop_loss,
            "entry_low": entry_low,
            "entry_high": entry_high,
            "upside": upside,
            "dist_sup_pct": round(dist_sup_pct, 1),
            "hist": hist,
        }
    except Exception:
        return None


def fmt_cap(cap):
    if cap >= 1e12: return f"${cap/1e12:.1f}T"
    if cap >= 1e9:  return f"${cap/1e9:.1f}B"
    return f"${cap/1e6:.0f}M"


# ── Session state эхлүүлэх ───────────────────────────────────────────────────
for key, default in [("history", []), ("watchlist", []), ("results", None), ("strategy", ""),
                        ("stage1", []), ("stage2", []), ("stage3", [])]:
    if key not in st.session_state:
        st.session_state[key] = default


def save_to_history(results, strategy):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    for r in results:
        st.session_state.history.append({
            "Огноо": ts,
            "Тикер": r["Тикер"],
            "Компани": r["Компани"][:22],
            "Стратеги": strategy[:18],
            "Оноо": r["score"],
            "Сигнал": r["signal"],
            "Зорилт %": r["upside"],
            "Эрсдэл": r["risk_level"],
            "Салбар": r["Салбар"],
            "Үнэ $": r["price"],
        })


def get_score_delta(ticker, current_score):
    """Өмнөх шинжилгээтэй оноог харьцуулна"""
    prev = [h for h in st.session_state.history if h["Тикер"] == ticker]
    if len(prev) >= 2:
        return current_score - prev[-2]["Оноо"]
    return None


def sector_warning(results):
    """Нэг салбараас хэт олон хувьцаа байвал анхааруулна"""
    from collections import Counter
    counts = Counter(r["Салбар"] for r in results if r["Салбар"] != "—")
    warnings = [f"**{sec}** ({n} хувьцаа)" for sec, n in counts.items() if n >= 3]
    return warnings


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Тохиргоо")

    mode = st.radio("Горим:", ["🔍 Автомат шүүлт", "✍️ Гараар тикер"], horizontal=True)

    if mode == "🔍 Автомат шүүлт":
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
        custom_tickers = []
    else:
        custom_raw = st.text_area(
            "Тикерүүд (таслал эсвэл зайгаар):",
            placeholder="AAPL, TSLA, NVDA\nMSFT GOOGL META",
            height=90,
        )
        custom_tickers = [t.strip().upper() for t in custom_raw.replace(",", " ").split() if t.strip()]
        if custom_tickers:
            st.caption(f"✅ {len(custom_tickers)} тикер бэлэн")
        universe = "S&P 500 — Том (~500)"

    strategy = st.radio("Стратеги:", list(STRATEGIES.keys()))
    st.markdown("---")
    st.info(STRATEGIES[strategy]["about"])
    st.caption(f"⏱️ Хугацаа: **{STRATEGIES[strategy]['horizon']}**")
    st.markdown("---")
    max_results = st.slider("Харуулах тоо", 5, 20, 10)
    run_btn = st.button("🚀 ШИНЖИЛГЭЭ ЭХЛЭХ", type="primary", use_container_width=True)

    # ── Watchlist ──
    if st.session_state.watchlist:
        st.markdown("---")
        st.markdown("### ⭐ Watchlist")
        for t in list(st.session_state.watchlist):
            c1, c2 = st.columns([4, 1])
            c1.caption(f"**{t}**")
            if c2.button("✕", key=f"rm_{t}", help="Устгах"):
                st.session_state.watchlist.remove(t)
                st.rerun()
        if st.button("⚡ Watchlist шинжилнэ", use_container_width=True):
            st.session_state._run_watchlist = True
            st.rerun()


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>📈 Ухаалаг Хувьцаа Шүүгч Pro</h1>
  <p>Ашиг олох боломжтой хувьцааг олох мэргэжлийн хэрэгсэл</p>
</div>
""", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────────────────────
tab_screen, tab_hist, tab_watch, tab_pipeline = st.tabs(["📊 Шинжилгээ", "📋 Түүх & Харьцуулалт", "⭐ Watchlist", "🎯 Шийдвэрийн үе шат"])

# ═══════════════════════════════════════════════════════════════════════════════
with tab_screen:

    # Watchlist шинжилгээ хийх
    run_watchlist = st.session_state.pop("_run_watchlist", False)

    if run_btn or run_watchlist:
        if run_watchlist:
            scan_tickers = list(st.session_state.watchlist)
            min_cap = 0
            label = f"⭐ Watchlist — {len(scan_tickers)} хувьцаа"
        elif mode == "✍️ Гараар тикер":
            scan_tickers = custom_tickers
            min_cap = 0
            label = f"✍️ Гараар оруулсан — {len(scan_tickers)} тикер"
        else:
            scan_tickers, min_cap = get_tickers_for_universe(universe)
            label = f"📊 {universe} — нийт {len(scan_tickers)} хувьцаа"

        if not scan_tickers:
            st.warning("Тикер оруулаагүй байна.")
        else:
            st.markdown(f"**{label} шинжилж байна...**")
            bar    = st.progress(0)
            status = st.empty()
            results = []
            for i, t in enumerate(scan_tickers):
                status.caption(f"🔍 {t}  —  {i+1}/{len(scan_tickers)}  |  Олдсон: {len(results)}")
                data = get_stock_data(t, strategy, min_cap)
                if data:
                    results.append(data)
                bar.progress((i + 1) / len(scan_tickers))
            results.sort(key=lambda x: x["score"], reverse=True)
            results = results[:max_results]
            bar.empty()
            status.empty()
            st.session_state.results  = results
            st.session_state.strategy = strategy
            # Түүхэнд хадгална
            if results:
                save_to_history(results, strategy)
                # 2+ удаа гарсан өндөр оноотой хувьцааг Stage1-д санал болгох
                from collections import Counter
                hist_tickers = [h["Тикер"] for h in st.session_state.history]
                counts = Counter(hist_tickers)
                s1 = st.session_state.stage1
                for r in results:
                    if counts[r["Тикер"]] >= 2 and r["score"] >= 60 and r["Тикер"] not in s1:
                        s1.append(r["Тикер"])
            st.rerun()

    # ── Үр дүн харуулах ──
    results = st.session_state.results
    strat   = st.session_state.strategy

    if results:
        # Дээд мэдээлэл
        avg_upside = round(sum(r["upside"] for r in results) / len(results), 1)
        best = results[0]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("✅ Олдсон", len(results))
        c2.metric("🏆 Шилдэг оноо", f"{best['score']}/100")
        c3.metric("📈 Дундаж зорилт", f"{avg_upside}%")
        c4.metric("⏱️ Хугацаа", STRATEGIES.get(strat, {}).get("horizon", "—")[:18])

        # Салбарын анхааруулга
        warns = sector_warning(results)
        if warns:
            st.warning(f"⚠️ Нэг салбараас хэт олон: {', '.join(warns)} — портфолиог диверсификаци хийхийг анхаарна уу.")

        st.markdown("### 🏆 Үр дүн — мөрийг сонгоод дэлгэрэнгүй харна уу")

        rows = []
        for r in results:
            delta = get_score_delta(r["Тикер"], r["score"])
            delta_str = (f"↑{delta}" if delta and delta > 0 else (f"↓{abs(delta)}" if delta and delta < 0 else "—"))
            row = {
                "Тикер": r["Тикер"],
                "Компани": r["Компани"][:24],
                "Оноо": r["score"],
                "Δ Оноо": delta_str,
                "Сигнал": r["signal"],
                "Эрсдэл": r["risk_level"],
                "Зорилт %": r["upside"],
                "RSI": r["rsi"],
            }
            if "GARP" in strat:
                row["PEG"] = r["peg"]
                row["ROE %"] = r["roe"]
                row["Өсөлт %"] = r["growth"]
            elif "Чанар" in strat:
                row["ROE %"] = r["roe"]
                row["Өр"] = r["debt_ratio"]
                row["Өсөлт %"] = r["growth"]
            else:
                row["1M %"] = r["mom_1m"]
                row["3M %"] = r["mom_3m"]
                row["Vol x"] = r["vol_ratio"]
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
                "Зорилт %": st.column_config.NumberColumn(format="%.1f%%"),
                "1M %": st.column_config.NumberColumn(format="%.1f%%"),
                "3M %": st.column_config.NumberColumn(format="%.1f%%"),
                "Өсөлт %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

        # Салбарын хуваарилалт
        sector_counts = {}
        for r in results:
            sec = r["Салбар"]
            sector_counts[sec] = sector_counts.get(sec, 0) + 1
        if len(sector_counts) > 1:
            df_sec = pd.DataFrame({"Салбар": list(sector_counts.keys()), "Тоо": list(sector_counts.values())})
            df_sec = df_sec.sort_values("Тоо", ascending=True)
            fig_sec = px.bar(
                df_sec, x="Тоо", y="Салбар", orientation="h",
                color="Тоо", color_continuous_scale=["#1c2333", "#58a6ff"],
                title="📂 Салбарын хуваарилалт",
            )
            fig_sec.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                showlegend=False, coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=35, b=0), height=max(180, len(sector_counts) * 32),
                xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                title_font_color="#8b949e", title_font_size=13,
            )
            st.plotly_chart(fig_sec, use_container_width=True)

        # ── Дэлгэрэнгүй харах ──
        if selected.selection.rows:
            idx   = selected.selection.rows[0]
            stock = results[idx]
            st.divider()

            h1, h2, h3 = st.columns([3, 1, 1])
            with h1:
                st.markdown(f"## {stock['Тикер']} — {stock['Компани']}")
                st.caption(f"📂 {stock['Салбар']}  |  {fmt_cap(stock['market_cap'])}  |  Beta: {stock['beta']}")
            with h2:
                st.markdown(f"### {stock['signal']}")
                st.markdown(f"**Оноо: `{stock['score']} / 100`**")
            with h3:
                st.markdown(f"### Эрсдэл: {stock['risk_level']}")
                st.info(STRATEGIES.get(strat, {}).get("horizon", ""))

            # Watchlist + Stage товчнууд
            wl = st.session_state.watchlist
            s1 = st.session_state.stage1
            s2 = st.session_state.stage2
            s3 = st.session_state.stage3
            tk_btn = stock["Тикер"]
            btn1, btn2, btn3, btn4 = st.columns(4)
            with btn1:
                if tk_btn not in wl:
                    if st.button(f"⭐ Watchlist", key='wl_add'):
                        wl.append(tk_btn); st.rerun()
                else:
                    st.success('✅ Watchlist-д байна')
            with btn2:
                if tk_btn not in s1:
                    if st.button('👁️ Анхааруулахад нэмэх', key='s1_add'):
                        s1.append(tk_btn); st.success(f'{tk_btn} → Stage 1')
                else:
                    st.info('👁️ Stage 1-д байна')
            with btn3:
                if tk_btn not in s2:
                    if st.button('📋 Судалж байнад нэмэх', key='s2_add'):
                        s2.append(tk_btn)
                        if tk_btn not in s1: s1.append(tk_btn)
                        st.success(f'{tk_btn} → Stage 2')
                else:
                    st.info('📋 Stage 2-д байна')
            with btn4:
                if tk_btn not in s3:
                    if st.button('💰 Авахаар шийдлээ', key='s3_add'):
                        s3.append(tk_btn)
                        if tk_btn not in s2: s2.append(tk_btn)
                        if tk_btn not in s1: s1.append(tk_btn)
                        st.success(f'{tk_btn} → Stage 3')
                else:
                    st.success('💰 Stage 3-д байна')

            # Risk/Reward хэсэг
            rr_col1, rr_col2 = st.columns(2)
            with rr_col1:
                rr = round(stock["upside"] / max(stock["beta"], 0.1), 1)
                st.metric(
                    "📐 Ашиг/Эрсдэл харьцаа",
                    f"{rr}x",
                    help="Зорилт өсөлт% ÷ Beta. 15+ = маш сайн, 8-15 = сайн, 8 доош = болгоомжтой",
                )
            with rr_col2:
                conviction = "🔥 Маш өндөр" if stock["score"] >= 75 else ("✅ Өндөр" if stock["score"] >= 60 else ("⚠️ Дунд" if stock["score"] >= 50 else "❓ Бага"))
                st.metric("🎯 Итгэлийн түвшин", conviction, help="Оноо болон аналистын үнэлгээнд суурилсан")

            st.markdown("#### 💰 Үнэ ба зорилт")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Одоогийн үнэ", f"${stock['price']}")
            m2.metric("12 сарын аналист зорилт", f"{stock['upside']}%",
                      help="Аналистуудын дундаж 12 сарын зорилтот үнэтэй харьцуулсан өсөх боломж")
            m3.metric("52 долоо хоногийн дээд", f"${stock['high_52w']}")
            m4.metric('Аналистын тоо', stock['analyst_cnt'])

            st.markdown('#### Үнэлгээ')
            v1, v2, v3, v4 = st.columns(4)
            v1.metric('P/E', stock['pe'], help='15 доош=хямд')
            v2.metric('Fwd P/E', stock['fpe'])
            v3.metric('PEG', stock['peg'], help='1 доош=хямд, 0.5 доош=маш сайн')
            v4.metric('ROE', f"{stock['roe']}%", help='15%+=сайн')

            st.markdown('#### Техник үзүүлэлт')
            t1, t2, t3, t4, t5 = st.columns(5)
            t1.metric('RSI', stock['rsi'], help='30 доош=хэт зарагдсан')
            t2.metric('MACD', 'Дээш' if stock['macd_hist'] > 0 else 'Доош')
            t3.metric('1M моментум', f"{stock['mom_1m']}%")
            t4.metric('3M моментум', f"{stock['mom_3m']}%")
            t5.metric('Volume', f"{stock['vol_ratio']}x", help='1.5x+=идэвхтэй')

            st.markdown('#### Бизнесийн үзүүлэлт')
            b1, b2, b3, b4 = st.columns(4)
            b1.metric('Орлогын өсөлт', f"{stock['growth']}%")
            b2.metric('Ашгийн өсөлт', f"{stock['earn_growth']}%")
            b3.metric('Өр/хөрөнгө', stock['debt_ratio'], help='0.5 доош=тогтвортой')
            rec_map = {1: 'Хүчтэй авах', 2: 'Авах', 3: 'Хадгал', 4: 'Зарах', 5: 'Хүчтэй зарах'}
            rec_val = int(round(stock['analyst_rec'])) if isinstance(stock['analyst_rec'], float) else 3
            b4.metric('Аналист', rec_map.get(rec_val, '-'))

            ch1, ch2 = st.columns(2)
            with ch1:
                st.subheader('6 сарын үнийн хэлбэлзэл')
                hist_data = yf.Ticker(stock['Тикер']).history(period='6mo')
                if not hist_data.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=hist_data.index, y=hist_data['Close'],
                        mode='lines', fill='tozeroy',
                        line=dict(color='#58a6ff', width=2),
                        fillcolor='rgba(88,166,255,0.1)', name='Үнэ',
                    ))
                    ma20 = hist_data['Close'].rolling(20).mean()
                    fig.add_trace(go.Scatter(
                        x=hist_data.index, y=ma20, mode='lines',
                        line=dict(color='#f0883e', width=1.5, dash='dot'),
                        name='MA20',
                    ))
                    fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                        legend=dict(orientation='h', yanchor='bottom', y=1.02),
                        xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                        yaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                        margin=dict(l=0, r=0, t=5, b=0), height=260,
                    )
                    st.plotly_chart(fig, use_container_width=True)
            with ch2:
                st.subheader('Стратегийн нүүлэлт')
                fig2 = px.line_polar(
                    stock['radar_df'], r='Оноо', theta='Үзүүлэлт',
                    line_close=True, range_r=[0, 100],
                    color_discrete_sequence=['#58a6ff'],
                )
                fig2.update_traces(fill='toself', fillcolor='rgba(88,166,255,0.18)', line=dict(width=2))
                fig2.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    polar=dict(
                        bgcolor='rgba(0,0,0,0)',
                        radialaxis=dict(gridcolor='rgba(255,255,255,0.1)', tickfont_size=9),
                        angularaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
                    ),
                    margin=dict(l=20, r=20, t=20, b=20), height=260,
                )
                st.plotly_chart(fig2, use_container_width=True)

            st.subheader('Volume')
            if not hist_data.empty:
                vol_colors = [
                    '#3fb950' if c >= o else '#f85149'
                    for c, o in zip(hist_data['Close'], hist_data['Open'])
                ]
                fig3 = go.Figure(go.Bar(
                    x=hist_data.index, y=hist_data['Volume'],
                    marker_color=vol_colors, opacity=0.75,
                ))
                fig3.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                    yaxis=dict(gridcolor='rgba(255,255,255,0.06)'),
                    margin=dict(l=0, r=0, t=5, b=0), height=160,
                )
                st.plotly_chart(fig3, use_container_width=True)

    elif results is not None and len(results) == 0:
        st.warning('Шалгуур хангасан хувьцаа олдсонгүй.')
    else:
        st.markdown("""
### Тавтай морил!

Зүүн цэснээс горим болон стратеги сонгоод товчийг дарна уу.

| Стратеги | Үндэслэл | Хугацаа |
|---|---|---|
| GARP | Питер Линч PEG+ROE | 3-12 сар |
| Чанарын хямдрал | Баффет oversold | 2-8 сар |
| Моментум Breakout | O'Neil тренд | 1-4 сар |

> Энэхүү апп нь мэдээлэл өгөх зорилготой.
        """)


# =========================================================
with tab_hist:
    st.markdown('## Шинжилгээний түүх')
    if not st.session_state.history:
        st.info('Шинжилгээ хийсний дараа энд түүх харагдана.')
    else:
        df_hist = pd.DataFrame(st.session_state.history)
        df_hist['Delta'] = ''
        seen = {}
        for i, row in df_hist.iterrows():
            tk = row['Тикер']
            cur = row['Оноо']
            if tk in seen:
                diff = cur - seen[tk]
                df_hist.at[i, 'Delta'] = ('+' + str(diff)) if diff > 0 else (str(diff) if diff < 0 else '=')
            seen[tk] = cur
        st.markdown(f"Нийт {len(df_hist)} бичлэг | {df_hist['Тикер'].nunique()} тикер")
        fc1, fc2 = st.columns(2)
        with fc1:
            filter_ticker = st.text_input('Тикерээр шүүх:', placeholder='AAPL').upper().strip()
        with fc2:
            filter_signal = st.selectbox('Сигналаар:', ['Бүгд', 'ХУДАЛДАЖ АВ', 'АЖИГЛА', 'БОЛГООМЖИЛ'])
        df_show = df_hist.copy()
        if filter_ticker:
            df_show = df_show[df_show['Тикер'] == filter_ticker]
        if filter_signal != 'Бүгд':
            df_show = df_show[df_show['Сигнал'].str.contains(filter_signal, na=False)]
        show_cols = [c for c in ['Огноо','Тикер','Компани','Стратеги','Оноо','Delta','Сигнал','Эрсдэл','Зорилт %','Үнэ $','Салбар'] if c in df_show.columns]
        st.dataframe(df_show[show_cols], use_container_width=True, hide_index=True,
            column_config={'Оноо': st.column_config.ProgressColumn('Оноо', min_value=0, max_value=100, format='%d')})
        if filter_ticker and filter_ticker in df_hist['Тикер'].values:
            df_t = df_hist[df_hist['Тикер'] == filter_ticker].reset_index(drop=True)
            if len(df_t) > 1:
                fig_t = px.line(df_t, x='Огноо', y='Оноо', markers=True, color_discrete_sequence=['#58a6ff'])
                fig_t.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                    yaxis=dict(range=[0,100]), margin=dict(l=0,r=0,t=10,b=0), height=220)
                st.plotly_chart(fig_t, use_container_width=True)
        st.markdown('---')
        dl1, dl2 = st.columns(2)
        with dl1:
            csv_bytes = df_hist.drop(columns=['Delta'], errors='ignore').to_csv(index=False).encode('utf-8-sig')
            st.download_button('Түүхийг CSV татах', data=csv_bytes,
                file_name=f"history_{datetime.now().strftime('%Y%m%d')}.csv",
                mime='text/csv', use_container_width=True)
        with dl2:
            uploaded = st.file_uploader('Өмнөх түүхийг оруулах (.csv)', type=['csv'])
            if uploaded:
                try:
                    df_up = pd.read_csv(uploaded)
                    existing_keys = {(h.get('Огноо',''), h.get('Тикер','')) for h in st.session_state.history}
                    added = 0
                    for rec in df_up.to_dict('records'):
                        k = (rec.get('Огноо',''), rec.get('Тикер',''))
                        if k not in existing_keys:
                            st.session_state.history.insert(0, rec)
                            existing_keys.add(k)
                            added += 1
                    st.success(f'{added} бичлэг нэмэгдлээ.')
                    st.rerun()
                except Exception as e:
                    st.error(f'Алдаа: {e}')
        if st.button('Түүхийг цэвэрлэх', type='secondary'):
            st.session_state.history = []
            st.rerun()


# =========================================================
with tab_watch:
    st.markdown('## Watchlist')
    st.caption('Хувьцааг нэмж, дахин хурдан шинжилнэ.')
    wl = st.session_state.watchlist
    add_col, btn_col = st.columns([4, 1])
    with add_col:
        new_ticker = st.text_input('Тикер нэмэх:', placeholder='AAPL', label_visibility='collapsed').upper().strip()
    with btn_col:
        if st.button('Нэмэх', use_container_width=True) and new_ticker:
            if new_ticker not in wl:
                wl.append(new_ticker)
                st.rerun()
            else:
                st.info(f'{new_ticker} аль хэдийн байна.')
    if not wl:
        st.info('Watchlist хоосон.')
    else:
        st.markdown(f'**{len(wl)} хувьцаа** хяналтад:')
        n_cols = min(4, len(wl))
        cols4 = st.columns(n_cols)
        for i, t in enumerate(list(wl)):
            with cols4[i % n_cols]:
                c1, c2 = st.columns([3, 1])
                c1.markdown(f'### {t}')
                if c2.button('x', key=f'wl2_{t}'):
                    wl.remove(t)
                    st.rerun()
        st.markdown('---')
        wl_strat = st.selectbox('Стратеги:', list(STRATEGIES.keys()), key='wl_strat2')
        if st.button('Watchlist шинжилнэ', type='primary', use_container_width=True):
            wl_results = []
            bar_wl = st.progress(0)
            status_wl = st.empty()
            for i, t in enumerate(wl):
                status_wl.caption(f'{t} шинжилж байна... {i+1}/{len(wl)}')
                data = get_stock_data(t, wl_strat, 0)
                if data:
                    wl_results.append(data)
                bar_wl.progress((i + 1) / len(wl))
            bar_wl.empty()
            status_wl.empty()
            wl_results.sort(key=lambda x: x['score'], reverse=True)
            if wl_results:
                save_to_history(wl_results, wl_strat)
                st.session_state.results = wl_results
                st.session_state.strategy = wl_strat
                st.success(f"{len(wl_results)}/{len(wl)} хувьцаа шалгуур хангалаа.")
                st.rerun()
            else:
                st.warning('Шалгуур хангасангүй. Стратеги өөрчилж үзнэ үү.')
        if st.button('Watchlist цэвэрлэх', type='secondary'):
            st.session_state.watchlist = []
            st.rerun()

def mn_stock_summary(ticker):
    try:
        info = yf.Ticker(ticker).info
        name     = info.get("longName", ticker)
        sector   = info.get("sector", "—")
        desc     = (info.get("longBusinessSummary") or "")[:400]
        price    = info.get("currentPrice") or info.get("regularMarketPrice") or 0
        target   = info.get("targetMeanPrice") or 0
        upside   = round((target - price) / price * 100, 1) if target and price else 0
        rec      = info.get("recommendationKey", "—")
        rec_mn   = {"buy": "Авах", "strong_buy": "Хүчтэл авах", "hold": "Хадгал",
                    "sell": "Зарах", "strong_sell": "Хүчтэл зарах"}.get(rec, rec)
        n_analyst = info.get("numberOfAnalystOpinions") or 0
        pe       = round(info.get("trailingPE") or 0, 1)
        fpe      = round(info.get("forwardPE") or 0, 1)
        peg      = round(info.get("pegRatio") or 0, 2)
        roe_r    = info.get("returnOnEquity") or 0
        roe      = round((roe_r if abs(roe_r) < 5 else roe_r / 100) * 100, 1)
        rev_g    = round((info.get("revenueGrowth") or 0) * 100, 1)
        debt_r   = info.get("debtToEquity") or 0
        debt     = round(debt_r / 100 if debt_r > 5 else debt_r, 2)
        mcap     = info.get("marketCap") or 0
        beta     = round(info.get("beta") or 1, 2)
        low52    = round(info.get("fiftyTwoWeekLow") or 0, 2)
        high52   = round(info.get("fiftyTwoWeekHigh") or 0, 2)
        return dict(name=name, sector=sector, desc=desc, price=price, target=target,
                    upside=upside, rec=rec_mn, n_analyst=n_analyst, pe=pe, fpe=fpe,
                    peg=peg, roe=roe, rev_g=rev_g, debt=debt, mcap=mcap,
                    beta=beta, low52=low52, high52=high52)
    except Exception:
        return None



# =========================================================
with tab_pipeline:
    st.markdown("## 🎯 Шийдвэрийн үе шат — 3 эрэмбэлт хүүнел")
    st.caption("Шинжилгээний үр дүнгээс 2+ удаа гарсан хувьцаа автоматаар Stage 1-д нэмэгдэнэ.")

    s1 = st.session_state.stage1
    s2 = st.session_state.stage2
    s3 = st.session_state.stage3

    # Summary bar
    p1, p2, p3 = st.columns(3)
    p1.metric("👁️ Анхаарух (Stage 1)", len(s1))
    p2.metric("📋 Судалж байна (Stage 2)", len(s2))
    p3.metric("💰 Авахаар шийдлээ (Stage 3)", len(s3))
    st.divider()

    stage_tab1, stage_tab2, stage_tab3 = st.tabs([
        f"👁️ Анхаарух ({len(s1)})",
        f"📋 Судалж байна ({len(s2)})",
        f"💰 Авахаар шийдлээ ({len(s3)})",
    ])

    # ── STAGE 1 ──────────────────────────────────────────────────────
    with stage_tab1:
        st.markdown("### 👁️ Анхаарух жагсаалт")
        st.caption("Олон удаа шинжилгээнд гарсан эсвэл гараар нэмсэн хувьцаа энд харагдана.")

        manual_s1 = st.text_input("Тикер гараар нэмэх:", placeholder="AAPL", key="s1_manual").upper().strip()
        if st.button("Нэмэх", key="s1_add_btn") and manual_s1:
            if manual_s1 not in s1:
                s1.append(manual_s1)
                st.rerun()

        if not s1:
            st.info("Шинжилгээ хийсний дараа энд хувьцаа нэмэгдэнэ.")
        else:
            for tk in list(s1):
                with st.expander(f"**{tk}**", expanded=False):
                    info_data = mn_stock_summary(tk)
                    if info_data:
                        st.markdown(f"### {tk} — {info_data['name']}")
                        st.caption(f"📂 {info_data['sector']}  |  {fmt_cap(info_data['mcap'])}  |  Beta: {info_data['beta']}")
                        if info_data["desc"]:
                            st.markdown(f"**Тухай тодорхойлол:** {info_data['desc']}")
                        st.markdown("---")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Унэ", f"${info_data['price']:.2f}")
                        c2.metric("Аналистын зорилт", f"{info_data['upside']}%")
                        c3.metric(f"Аналист ({info_data['n_analyst']})", info_data["rec"])
                        c4.metric("P/E  |  Fwd P/E", f"{info_data['pe']}  |  {info_data['fpe']}")
                        d1, d2, d3, d4 = st.columns(4)
                        d1.metric("PEG", info_data["peg"])
                        d2.metric("ROE", f"{info_data['roe']}%")
                        d3.metric("Орлогын өсөлт", f"{info_data['rev_g']}%")
                        d4.metric("Өр/хөрөнгө", info_data["debt"])
                        e1, e2 = st.columns(2)
                        e1.metric("52 хоногийн дьэд", f"${info_data['high52']}")
                        e2.metric("52 хоногийн доод", f"${info_data['low52']}")
                    btn_c1, btn_c2, btn_c3 = st.columns(3)
                    with btn_c1:
                        if tk not in s2:
                            if st.button("📋 Stage 2-д шилжуүлэх", key=f"s1_to_s2_{tk}"):
                                s2.append(tk); st.rerun()
                    with btn_c2:
                        if st.button("❌ Жагсаалтаас хасах", key=f"s1_rm_{tk}"):
                            s1.remove(tk); st.rerun()

    # ── STAGE 2 ──────────────────────────────────────────────────────
    with stage_tab2:
        st.markdown("### 📋 Судалж байна — нарийвчилсан дүн шинжилгээ")
        st.caption("Хүчтэл бүх мэдээллийг үзээд нэгтгээд Stage 3-д шилжүүл.")

        if not s2:
            st.info("Stage 1-ээс хувьцаа шилжүүлээ.")
        else:
            for tk in list(s2):
                with st.expander(f"**{tk}** — дэлгэрэнгүй шинжилгээ", expanded=False):
                    info_data = mn_stock_summary(tk)
                    ea = get_entry_advice(tk)

                    if info_data:
                        st.markdown(f"### {tk} — {info_data['name']}")
                        st.caption(f"📂 {info_data['sector']}  |  {fmt_cap(info_data['mcap'])}  |  Beta: {info_data['beta']}")

                        if info_data["desc"]:
                            st.markdown(f"**Тухай тодорхойлол:** {info_data['desc']}")
                        st.markdown("---")

                        st.markdown("#### 💰 Үнэ ба зах зээлийн байдал")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Одоогийн унэ", f"${info_data['price']:.2f}")
                        c2.metric("12 сарын зорилт", f"{info_data['upside']}%",
                                  help="Аналистуудын дундаж зорилтот үнэтэй харьцуулсан өсөх боломж")
                        c3.metric(f"Аналистын дүгнэлт ({info_data['n_analyst']})", info_data["rec"])
                        c4.metric("P/E  |  PEG", f"{info_data['pe']}  |  {info_data['peg']}")

                        st.markdown("#### 📊 Фундаментал")
                        f1, f2, f3, f4 = st.columns(4)
                        f1.metric("ROE (өгөөж)", f"{info_data['roe']}%", help="15%+=сайн, 25%+=маш сайн")
                        f2.metric("Орлогын өсөлт", f"{info_data['rev_g']}%")
                        f3.metric("Өр/хөрөнгө", info_data["debt"], help="0.5 доош=тогтвортой, 2.0+=өндөр өртэй")
                        f4.metric("Beta (эрсдэл)", info_data["beta"])

                        if ea:
                            st.markdown("#### 📈 Техник үзүүлэлт")
                            e1, e2, e3 = st.columns(3)
                            e1.metric("RSI", ea["rsi"], help="30 доош=хэт зарагдсан, 70+=хэт худалдагдсан")
                            e2.metric("MACD", "📈 Дээш" if ea["macd"] > 0 else "📉 Доош")
                            e3.metric("Дэмжлэгийн түвшин", f"${ea['support']}")

                    btn_r1, btn_r2 = st.columns(2)
                    with btn_r1:
                        if tk not in s3:
                            if st.button("💰 Авахаар шийдлээ", key=f"s2_to_s3_{tk}", type="primary"):
                                s3.append(tk); st.rerun()
                        else:
                            st.success("💰 Stage 3-д байна")
                    with btn_r2:
                        if st.button("❌ Хасах", key=f"s2_rm_{tk}"):
                            s2.remove(tk); st.rerun()

    # ── STAGE 3 ──────────────────────────────────────────────────────
    with stage_tab3:
        st.markdown("### 💰 Авахаар шийдлээ — оролтын цаг шинжилгээ")
        st.caption("Яаг хэзээ худалдаж авах талаар техник дүн шинжилгээ, дэмжлэгийн түвшин, stop-loss зөвлөмж.")

        if not s3:
            st.info("Stage 2-ээс шилжүүлээ.")
        else:
            for tk in list(s3):
                with st.expander(f"**{tk}** — оролтын шинжилгээ", expanded=True):
                    ea = get_entry_advice(tk)
                    info_data = mn_stock_summary(tk)

                    if ea is None:
                        st.warning(f"{tk} өгөгдөл авахаар боломжгүй.")
                    else:
                        name = info_data["name"] if info_data else tk
                        st.markdown(f"### {tk} — {name}")

                        # Advice banner
                        if ea["color"] == "success":
                            st.success(ea["advice"] + " -- " + ea["detail"])
                        elif ea["color"] == "warning":
                            st.warning(ea["advice"] + " -- " + ea["detail"])
                        else:
                            st.info(ea["advice"] + " -- " + ea["detail"])

                        # Key metrics
                        m1, m2, m3, m4, m5 = st.columns(5)
                        m1.metric("Одоогийн унэ", f"${ea['current']}")
                        m2.metric("🟢 Оролтын үнэ ($)", f"${ea['entry_low']}–${ea['entry_high']}")
                        m3.metric("🛑 Stop-loss", f"${ea['stop_loss']}", help="Енэ унэнаас 8% буурсан цэгээх")
                        m4.metric("📊 Дэмжлэг", f"${ea['support']}", help=f"Өнөөд {ea['dist_sup_pct']}% дээш байна")
                        m5.metric("📈 12 сарын зорилт", f"{ea['upside']}%")

                        # RSI / MACD
                        t1, t2 = st.columns(2)
                        t1.metric("RSI", ea["rsi"],
                            delta="Oversold — сайн" if ea["rsi"] < 40 else ("Өндөр — хүлээх" if ea["rsi"] > 65 else "Тэнцвэрт бүс"))
                        t2.metric("MACD", "📈 Дээш (сайн)" if ea["macd"] > 0 else "📉 Доош (болгоомжил)")

                        # 3-month chart with support/resistance
                        hist = ea["hist"]
                        if not hist.empty:
                            fig_e = go.Figure()
                            fig_e.add_trace(go.Scatter(
                                x=hist.index, y=hist["Close"],
                                mode="lines", name="үнэ",
                                line=dict(color="#58a6ff", width=2),
                            ))
                            fig_e.add_hline(y=ea["support"], line_dash="dot", line_color="#3fb950",
                                            annotation_text=f"Дэмжлэг ${ea['support']}", annotation_position="left")
                            fig_e.add_hline(y=ea["resist"], line_dash="dot", line_color="#f85149",
                                            annotation_text=f"Тэсрэлт ${ea['resist']}", annotation_position="left")
                            fig_e.add_hline(y=ea["stop_loss"], line_dash="dash", line_color="#d29922",
                                            annotation_text=f"Stop-loss ${ea['stop_loss']}", annotation_position="left")
                            if ea["entry_low"]:
                                fig_e.add_hrect(y0=ea["entry_low"], y1=ea["entry_high"],
                                                fillcolor="rgba(63,185,80,0.08)",
                                                annotation_text="Оролтын бүс", annotation_position="top left")
                            fig_e.update_layout(
                                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                                xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                                yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                                margin=dict(l=60, r=20, t=20, b=0), height=320,
                                title=f"{tk} — 3 сарын үнэ — дэмжлэг/тэсрэлт/stop-loss",
                                title_font_color="#8b949e", title_font_size=12,
                            )
                            st.plotly_chart(fig_e, use_container_width=True)

                        # Risk/Reward
                        if ea["upside"] > 0 and ea["current"] > ea["stop_loss"]:
                            risk_pct  = round((ea["current"] - ea["stop_loss"]) / ea["current"] * 100, 1)
                            rr_ratio  = round(ea["upside"] / risk_pct, 1) if risk_pct > 0 else 0
                            rr_color  = "🟢 Сайн" if rr_ratio >= 2 else ("🟡 Дунд" if rr_ratio >= 1.5 else "🔴 Болгоомжил")
                            st.markdown(
                                f"**📐 Ашиг/эрсдэл харьцаа:** "
                                f"Зорилт {ea['upside']}% vs эрсдэл {risk_pct}% = **{rr_ratio}x** {rr_color}"
                            )

                    done_c, rm_c = st.columns(2)
                    with done_c:
                        if st.button("✅ Худалдаж авлаа", key=f"s3_done_{tk}"):
                            s3.remove(tk)
                            st.success(f"Аз байх байдла!")
                            st.rerun()
                    with rm_c:
                        if st.button("❌ Хасах", key=f"s3_rm_{tk}"):
                            s3.remove(tk); st.rerun()
