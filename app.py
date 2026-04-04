import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import os
from datetime import datetime, timedelta

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(
    page_title="Investidor PRO",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# ==============================
# CSS PERSONALIZADO
# ==============================
st.markdown("""
<style>
    /* Fundo e tipografia geral */
    .main { background-color: #0f1117; }
    section[data-testid="stSidebar"] { background-color: #1a1d27; }

    /* Métricas */
    div[data-testid="stMetricValue"] { font-size: 22px; font-weight: 700; color: #00d4aa; }
    div[data-testid="stMetricLabel"] { font-size: 13px; color: #aaaaaa; }
    div[data-testid="stMetricDelta"] { font-size: 13px; }

    /* Cartões de ativo */
    .ativo-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border: 1px solid #2e3250;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .ativo-card h4 { color: #ffffff; margin: 0 0 4px 0; font-size: 16px; }
    .ativo-card p { color: #aaaaaa; margin: 0; font-size: 13px; }

    /* Score badge */
    .score-verde  { background:#0d3b2e; color:#00d4aa; border:1px solid #00d4aa; border-radius:8px; padding:6px 14px; font-weight:700; font-size:18px; }
    .score-amarelo{ background:#3b2e0d; color:#f0c040; border:1px solid #f0c040; border-radius:8px; padding:6px 14px; font-weight:700; font-size:18px; }
    .score-vermelho{ background:#3b0d0d; color:#ff6b6b; border:1px solid #ff6b6b; border-radius:8px; padding:6px 14px; font-weight:700; font-size:18px; }

    /* Tabela da carteira */
    .carteira-header { color:#00d4aa; font-size:14px; font-weight:700; }

    /* Tags de tipo */
    .tag-acao { background:#1a3a5c; color:#4da6ff; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
    .tag-fii  { background:#1a3a2a; color:#00d4aa; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
    .tag-etf  { background:#3a2a1a; color:#f0a040; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }
    .tag-bdr  { background:#2a1a3a; color:#c080ff; border-radius:4px; padding:2px 8px; font-size:11px; font-weight:600; }

    /* Botões */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }

    /* Separador */
    hr { border-color: #2e3250; }

    /* Título principal */
    .titulo-principal {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00d4aa, #4da6ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitulo { text-align:center; color:#888; font-size:1rem; margin-top:4px; }
</style>
""", unsafe_allow_html=True)

# ==============================
# PERSISTÊNCIA DA CARTEIRA (session_state)
# ==============================
if "carteira" not in st.session_state:
    st.session_state.carteira = {}   # {ticker: {qtd, preco_medio, tipo}}

if "lista_acoes" not in st.session_state:
    st.session_state.lista_acoes = []

if "lista_fiis" not in st.session_state:
    st.session_state.lista_fiis = []

if "lista_carregada" not in st.session_state:
    st.session_state.lista_carregada = False

# ==============================
# FUNÇÕES DE DADOS
# ==============================
@st.cache_data(ttl=3600)
def carregar_lista_ativos():
    """Carrega lista completa de ações e fundos da B3 via brapi.dev (sem token)."""
    acoes, fiis = [], []
    try:
        r = requests.get("https://brapi.dev/api/quote/list?type=stock", timeout=15)
        if r.status_code == 200:
            data = r.json()
            acoes = [
                {"ticker": x["stock"], "nome": x.get("name", x["stock"]), "setor": x.get("sector", ""), "tipo": "Ação"}
                for x in data.get("stocks", [])
                if not x["stock"].endswith("F")  # Remove fracionários
            ]
    except Exception:
        pass

    try:
        r = requests.get("https://brapi.dev/api/quote/list?type=fund", timeout=15)
        if r.status_code == 200:
            data = r.json()
            fiis = [
                {"ticker": x["stock"], "nome": x.get("name", x["stock"]), "setor": x.get("sector", ""), "tipo": "FII/ETF"}
                for x in data.get("stocks", [])
                if not x["stock"].endswith("F")
            ]
    except Exception:
        pass

    return acoes, fiis


@st.cache_data(ttl=600)
def buscar_ativo(ticker_input: str):
    """Busca dados completos de um ativo via yfinance."""
    ticker = ticker_input.upper().strip()
    tentativas = [f"{ticker}.SA", ticker]

    for t in tentativas:
        try:
            ativo = yf.Ticker(t)
            hist = ativo.history(period="1y")
            if not hist.empty:
                info = ativo.info
                divs = ativo.dividends
                return info, hist, divs, t
        except Exception:
            continue
    return None, None, None, None


def extrair_metricas(info: dict, preco: float, ticker_final: str) -> dict:
    """Extrai e normaliza métricas financeiras do ativo."""
    dy_raw = (
        info.get("dividendYield")
        or info.get("yield")
        or info.get("trailingAnnualDividendYield")
        or 0
    )
    # yfinance às vezes retorna DY já em %, às vezes em decimal
    dy = dy_raw * 100 if dy_raw < 1 else dy_raw

    book = info.get("bookValue") or 0
    pvp = round(preco / book, 2) if book and book > 0 else 0

    return {
        "nome": info.get("longName") or info.get("shortName") or ticker_final,
        "setor": info.get("sector") or info.get("industry") or "Fundo / Internacional",
        "moeda": info.get("currency", "BRL"),
        "dy": round(dy, 2),
        "pvp": pvp,
        "pl": round(info.get("trailingPE") or 0, 2),
        "roe": round((info.get("returnOnEquity") or 0) * 100, 2),
        "beta": round(info.get("beta") or 0, 2),
        "market_cap": info.get("marketCap") or 0,
        "volume": info.get("regularMarketVolume") or 0,
        "52w_high": info.get("fiftyTwoWeekHigh") or 0,
        "52w_low": info.get("fiftyTwoWeekLow") or 0,
        "media_50d": info.get("fiftyDayAverage") or 0,
        "media_200d": info.get("twoHundredDayAverage") or 0,
        "ultimo_div": info.get("lastDividendValue") or 0,
        "resumo": info.get("longBusinessSummary", "Descrição não disponível."),
        "quote_type": info.get("quoteType", ""),
    }


def calcular_score(m: dict, ticker: str) -> tuple[int, list]:
    """Calcula score de 0 a 10 com justificativas."""
    score = 0
    detalhes = []
    is_fii = ticker.endswith("11.SA") or ticker.endswith("11")

    # Dividend Yield
    if m["dy"] > 10:
        score += 4
        detalhes.append(("✅ DY excelente (>10%)", "+4"))
    elif m["dy"] > 6:
        score += 3
        detalhes.append(("✅ DY bom (>6%)", "+3"))
    elif m["dy"] > 3:
        score += 1
        detalhes.append(("🟡 DY moderado (>3%)", "+1"))
    else:
        detalhes.append(("❌ DY baixo ou zero", "+0"))

    # P/VP
    if 0 < m["pvp"] <= 1.0:
        score += 3
        detalhes.append(("✅ P/VP abaixo do patrimônio (≤1)", "+3"))
    elif 1.0 < m["pvp"] <= 1.3:
        score += 2
        detalhes.append(("✅ P/VP razoável (1–1.3)", "+2"))
    elif 1.3 < m["pvp"] <= 2.0:
        score += 1
        detalhes.append(("🟡 P/VP elevado (1.3–2)", "+1"))
    else:
        detalhes.append(("❌ P/VP muito alto ou indisponível", "+0"))

    # ROE / P/L (apenas ações)
    if not is_fii:
        if m["roe"] > 20:
            score += 2
            detalhes.append(("✅ ROE excelente (>20%)", "+2"))
        elif m["roe"] > 10:
            score += 1
            detalhes.append(("🟡 ROE bom (>10%)", "+1"))
        else:
            detalhes.append(("❌ ROE baixo", "+0"))

        if 0 < m["pl"] < 15:
            score += 1
            detalhes.append(("✅ P/L atrativo (<15)", "+1"))
        elif 15 <= m["pl"] < 25:
            detalhes.append(("🟡 P/L moderado (15–25)", "+0"))
        else:
            detalhes.append(("❌ P/L alto ou negativo", "+0"))
    else:
        # FIIs recebem bônus por estrutura
        score += 2
        detalhes.append(("✅ Bônus FII (estrutura de distribuição)", "+2"))

    return min(score, 10), detalhes


def formatar_market_cap(valor: float) -> str:
    if valor >= 1e12:
        return f"R$ {valor/1e12:.2f} T"
    elif valor >= 1e9:
        return f"R$ {valor/1e9:.2f} B"
    elif valor >= 1e6:
        return f"R$ {valor/1e6:.2f} M"
    elif valor > 0:
        return f"R$ {valor:,.0f}"
    return "N/D"


def calcular_rentabilidade_carteira():
    """Calcula rentabilidade atual da carteira."""
    rows = []
    total_investido = 0
    total_atual = 0

    for ticker, dados in st.session_state.carteira.items():
        info, hist, _, _ = buscar_ativo(ticker)
        if hist is not None and not hist.empty:
            preco_atual = hist["Close"].iloc[-1]
            qtd = dados["qtd"]
            pm = dados["preco_medio"]
            valor_investido = qtd * pm
            valor_atual = qtd * preco_atual
            rentabilidade = ((preco_atual - pm) / pm) * 100 if pm > 0 else 0
            total_investido += valor_investido
            total_atual += valor_atual

            rows.append({
                "Ticker": ticker.replace(".SA", ""),
                "Tipo": dados.get("tipo", "Ação"),
                "Qtd": qtd,
                "Preço Médio (R$)": round(pm, 2),
                "Preço Atual (R$)": round(preco_atual, 2),
                "Valor Investido (R$)": round(valor_investido, 2),
                "Valor Atual (R$)": round(valor_atual, 2),
                "Rentabilidade (%)": round(rentabilidade, 2),
            })

    return pd.DataFrame(rows), total_investido, total_atual


# ==============================
# SIDEBAR — NAVEGAÇÃO
# ==============================
with st.sidebar:
    st.markdown("## 📈 Investidor PRO")
    st.markdown("---")
    pagina = st.radio(
        "Navegação",
        ["🔍 Analisar Ativo", "📊 Minha Carteira", "🔎 Explorar Mercado", "📋 Comparar Ativos"],
        label_visibility="collapsed"
    )
    st.markdown("---")

    # Carregar listas de ativos
    if not st.session_state.lista_carregada:
        with st.spinner("Carregando lista de ativos..."):
            acoes, fiis = carregar_lista_ativos()
            st.session_state.lista_acoes = acoes
            st.session_state.lista_fiis = fiis
            st.session_state.lista_carregada = True

    total_a = len(st.session_state.lista_acoes)
    total_f = len(st.session_state.lista_fiis)
    st.markdown(f"**Ações disponíveis:** {total_a}")
    st.markdown(f"**FIIs/ETFs disponíveis:** {total_f}")
    st.markdown("---")
    st.caption("Dados: Yahoo Finance · brapi.dev")
    st.caption("Investidor PRO © 2026")


# ==============================
# PÁGINA 1: ANALISAR ATIVO
# ==============================
if "Analisar" in pagina:
    st.markdown("<h1 class='titulo-principal'>🔍 Analisar Ativo</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo'>Análise completa de ações, FIIs, ETFs e BDRs</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Busca com autocomplete
    todos_ativos = st.session_state.lista_acoes + st.session_state.lista_fiis
    opcoes_busca = [f"{a['ticker']} — {a['nome']}" for a in todos_ativos]

    col_input, col_btn = st.columns([4, 1])
    with col_input:
        busca_texto = st.text_input(
            "Digite o código ou nome do ativo:",
            placeholder="Ex: MXRF11, PETR4, VALE3, AAPL...",
            label_visibility="collapsed"
        )
    with col_btn:
        btn_analisar = st.button("🔍 Analisar", use_container_width=True, type="primary")

    # Sugestões de autocomplete
    if busca_texto and len(busca_texto) >= 2:
        sugestoes = [o for o in opcoes_busca if busca_texto.upper() in o.upper()][:8]
        if sugestoes:
            ticker_selecionado = st.selectbox(
                "Sugestões:", [""] + sugestoes, label_visibility="collapsed"
            )
            if ticker_selecionado:
                busca_texto = ticker_selecionado.split(" — ")[0]

    if busca_texto and (btn_analisar or True):
        ticker_limpo = busca_texto.split(" — ")[0].strip()
        with st.spinner(f"Buscando dados de **{ticker_limpo}**..."):
            info, hist, divs, ticker_confirmado = buscar_ativo(ticker_limpo)

        if ticker_confirmado and hist is not None and not hist.empty:
            preco_atual = hist["Close"].iloc[-1]
            m = extrair_metricas(info, preco_atual, ticker_confirmado)
            score, detalhes_score = calcular_score(m, ticker_confirmado)

            # Cabeçalho do ativo
            col_nome, col_score = st.columns([3, 1])
            with col_nome:
                tipo_tag = "fii" if ticker_confirmado.endswith("11.SA") else "acao"
                st.markdown(f"## {m['nome']}")
                st.markdown(f"`{ticker_confirmado}` · **{m['setor']}** · {m['moeda']}")
            with col_score:
                if score >= 7:
                    st.markdown(f"<div style='text-align:center'><span class='score-verde'>Score: {score}/10<br>🟢 FORTE COMPRA</span></div>", unsafe_allow_html=True)
                elif score >= 5:
                    st.markdown(f"<div style='text-align:center'><span class='score-amarelo'>Score: {score}/10<br>🟡 NEUTRO</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='text-align:center'><span class='score-vermelho'>Score: {score}/10<br>🔴 EVITAR</span></div>", unsafe_allow_html=True)

            st.markdown("---")

            # Métricas principais
            prefixo = "$" if m["moeda"] != "BRL" else "R$"
            var_dia = info.get("regularMarketChangePercent", 0) or 0
            var_dia_str = f"{var_dia:.2f}%"

            col1, col2, col3, col4, col5, col6 = st.columns(6)
            col1.metric("Preço Atual", f"{prefixo} {preco_atual:.2f}", var_dia_str)
            col2.metric("Dividend Yield", f"{m['dy']:.2f}%")
            col3.metric("P/VP", f"{m['pvp']:.2f}" if m["pvp"] > 0 else "N/D")
            col4.metric("P/L", f"{m['pl']:.2f}" if m["pl"] > 0 else "N/D")
            col5.metric("ROE", f"{m['roe']:.2f}%" if m["roe"] != 0 else "N/D")
            col6.metric("Beta", f"{m['beta']:.2f}" if m["beta"] != 0 else "N/D")

            # Segunda linha de métricas
            col7, col8, col9, col10 = st.columns(4)
            col7.metric("Mín. 52 sem.", f"{prefixo} {m['52w_low']:.2f}" if m["52w_low"] > 0 else "N/D")
            col8.metric("Máx. 52 sem.", f"{prefixo} {m['52w_high']:.2f}" if m["52w_high"] > 0 else "N/D")
            col9.metric("Market Cap", formatar_market_cap(m["market_cap"]))
            col10.metric("Último Dividendo", f"{prefixo} {m['ultimo_div']:.4f}" if m["ultimo_div"] > 0 else "N/D")

            st.markdown("---")

            # Abas de conteúdo
            tab1, tab2, tab3, tab4 = st.tabs(["📈 Histórico de Preços", "💰 Dividendos", "🎯 Score Detalhado", "📖 Sobre"])

            with tab1:
                periodo = st.select_slider(
                    "Período:",
                    options=["1mo", "3mo", "6mo", "1y", "2y", "5y"],
                    value="1y",
                    label_visibility="collapsed"
                )
                _, hist_p, _, _ = buscar_ativo(ticker_limpo)
                if hist_p is not None and not hist_p.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=hist_p.index,
                        open=hist_p["Open"],
                        high=hist_p["High"],
                        low=hist_p["Low"],
                        close=hist_p["Close"],
                        name=ticker_confirmado,
                        increasing_line_color="#00d4aa",
                        decreasing_line_color="#ff6b6b"
                    ))
                    # Médias móveis
                    if len(hist_p) >= 50:
                        hist_p["MM50"] = hist_p["Close"].rolling(50).mean()
                        fig.add_trace(go.Scatter(x=hist_p.index, y=hist_p["MM50"], name="MM50", line=dict(color="#4da6ff", width=1.5)))
                    if len(hist_p) >= 200:
                        hist_p["MM200"] = hist_p["Close"].rolling(200).mean()
                        fig.add_trace(go.Scatter(x=hist_p.index, y=hist_p["MM200"], name="MM200", line=dict(color="#f0c040", width=1.5)))

                    fig.update_layout(
                        template="plotly_dark",
                        height=420,
                        xaxis_rangeslider_visible=False,
                        margin=dict(l=0, r=0, t=20, b=0),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02)
                    )
                    st.plotly_chart(fig, use_container_width=True)

            with tab2:
                if divs is not None and len(divs) > 0:
                    divs_df = divs.reset_index()
                    divs_df.columns = ["Data", "Dividendo (R$)"]
                    divs_df["Data"] = divs_df["Data"].dt.strftime("%d/%m/%Y")

                    fig_div = px.bar(
                        divs_df.tail(24),
                        x="Data", y="Dividendo (R$)",
                        color_discrete_sequence=["#00d4aa"],
                        template="plotly_dark",
                        title="Histórico de Dividendos (últimos 24 pagamentos)"
                    )
                    fig_div.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0))
                    st.plotly_chart(fig_div, use_container_width=True)

                    total_12m = divs[divs.index >= (pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(months=12))].sum()
                    col_d1, col_d2, col_d3 = st.columns(3)
                    col_d1.metric("Total pago (12 meses)", f"R$ {total_12m:.4f}")
                    col_d2.metric("Último pagamento", f"R$ {divs.iloc[-1]:.4f}")
                    col_d3.metric("Nº pagamentos (12m)", len(divs[divs.index >= (pd.Timestamp.now(tz=divs.index.tz) - pd.DateOffset(months=12))]))

                    st.dataframe(divs_df.tail(24).sort_values("Data", ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum dividendo encontrado para este ativo.")

            with tab3:
                st.markdown(f"### Score: **{score}/10**")
                for desc, pts in detalhes_score:
                    st.markdown(f"- {desc} `{pts}`")

                # Gráfico radar do score
                categorias = ["DY", "P/VP", "ROE/FII", "P/L", "Geral"]
                valores = [
                    min(m["dy"] / 12 * 10, 10),
                    max(0, 10 - abs(m["pvp"] - 1) * 5) if m["pvp"] > 0 else 0,
                    min(m["roe"] / 25 * 10, 10) if m["roe"] > 0 else 5,
                    max(0, 10 - m["pl"] / 3) if 0 < m["pl"] < 30 else 3,
                    score
                ]
                fig_radar = go.Figure(go.Scatterpolar(
                    r=valores + [valores[0]],
                    theta=categorias + [categorias[0]],
                    fill="toself",
                    fillcolor="rgba(0, 212, 170, 0.2)",
                    line=dict(color="#00d4aa")
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 10])),
                    template="plotly_dark",
                    height=350,
                    margin=dict(l=40, r=40, t=20, b=20)
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            with tab4:
                st.markdown(f"**Setor:** {m['setor']}")
                st.markdown(f"**Moeda:** {m['moeda']}")
                st.markdown(f"**Tipo:** {m['quote_type']}")
                st.info(m["resumo"])

            # Adicionar à carteira
            st.markdown("---")
            st.markdown("### ➕ Adicionar à Carteira")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                qtd_add = st.number_input("Quantidade", min_value=1, value=1, step=1, key="qtd_add")
            with col_b:
                pm_add = st.number_input("Preço Médio (R$)", min_value=0.01, value=float(round(preco_atual, 2)), step=0.01, key="pm_add")
            with col_c:
                tipo_add = st.selectbox("Tipo", ["Ação", "FII", "ETF", "BDR", "Internacional"], key="tipo_add")

            if st.button("✅ Adicionar à Carteira", type="primary"):
                ticker_key = ticker_confirmado
                if ticker_key in st.session_state.carteira:
                    # Preço médio ponderado
                    dados_existentes = st.session_state.carteira[ticker_key]
                    qtd_total = dados_existentes["qtd"] + qtd_add
                    pm_novo = (dados_existentes["qtd"] * dados_existentes["preco_medio"] + qtd_add * pm_add) / qtd_total
                    st.session_state.carteira[ticker_key] = {"qtd": qtd_total, "preco_medio": pm_novo, "tipo": tipo_add}
                    st.success(f"✅ Posição de **{ticker_key}** atualizada! Preço médio: R$ {pm_novo:.2f}")
                else:
                    st.session_state.carteira[ticker_key] = {"qtd": qtd_add, "preco_medio": pm_add, "tipo": tipo_add}
                    st.success(f"✅ **{ticker_key}** adicionado à carteira!")

        elif busca_texto:
            st.error(f"❌ Ativo **'{ticker_limpo}'** não encontrado. Verifique o ticker e tente novamente.")


# ==============================
# PÁGINA 2: MINHA CARTEIRA
# ==============================
elif "Carteira" in pagina:
    st.markdown("<h1 class='titulo-principal'>📊 Minha Carteira</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo'>Acompanhe a performance dos seus investimentos</p>", unsafe_allow_html=True)
    st.markdown("---")

    if not st.session_state.carteira:
        st.info("📭 Sua carteira está vazia. Vá para **Analisar Ativo** e adicione seus investimentos.")
    else:
        with st.spinner("Atualizando cotações da carteira..."):
            df_carteira, total_investido, total_atual = calcular_rentabilidade_carteira()

        if not df_carteira.empty:
            rentabilidade_total = ((total_atual - total_investido) / total_investido * 100) if total_investido > 0 else 0
            lucro_prejuizo = total_atual - total_investido

            # Resumo geral
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Investido", f"R$ {total_investido:,.2f}")
            col2.metric("Valor Atual", f"R$ {total_atual:,.2f}", f"{rentabilidade_total:+.2f}%")
            col3.metric("Lucro / Prejuízo", f"R$ {lucro_prejuizo:+,.2f}")
            col4.metric("Nº de Ativos", len(df_carteira))

            st.markdown("---")

            # Tabela da carteira
            st.markdown("### 📋 Posições")
            df_display = df_carteira.copy()
            df_display["Rentabilidade (%)"] = df_display["Rentabilidade (%)"].apply(
                lambda x: f"{'🟢' if x >= 0 else '🔴'} {x:+.2f}%"
            )
            st.dataframe(df_display, use_container_width=True, hide_index=True)

            st.markdown("---")

            # Gráficos
            col_g1, col_g2 = st.columns(2)

            with col_g1:
                st.markdown("#### Distribuição por Ativo")
                fig_pie = px.pie(
                    df_carteira,
                    values="Valor Atual (R$)",
                    names="Ticker",
                    color_discrete_sequence=px.colors.sequential.Teal,
                    template="plotly_dark"
                )
                fig_pie.update_layout(height=320, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_pie, use_container_width=True)

            with col_g2:
                st.markdown("#### Rentabilidade por Ativo (%)")
                cores = ["#00d4aa" if v >= 0 else "#ff6b6b" for v in df_carteira["Rentabilidade (%)"]]
                fig_bar = go.Figure(go.Bar(
                    x=df_carteira["Ticker"],
                    y=df_carteira["Rentabilidade (%)"],
                    marker_color=cores,
                    text=[f"{v:+.2f}%" for v in df_carteira["Rentabilidade (%)"]],
                    textposition="outside"
                ))
                fig_bar.update_layout(
                    template="plotly_dark",
                    height=320,
                    margin=dict(l=0, r=0, t=20, b=0),
                    yaxis_title="%"
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            # Distribuição por tipo
            if "Tipo" in df_carteira.columns:
                st.markdown("#### Distribuição por Tipo de Ativo")
                df_tipo = df_carteira.groupby("Tipo")["Valor Atual (R$)"].sum().reset_index()
                fig_tipo = px.pie(
                    df_tipo,
                    values="Valor Atual (R$)",
                    names="Tipo",
                    color_discrete_sequence=["#00d4aa", "#4da6ff", "#f0c040", "#c080ff"],
                    template="plotly_dark"
                )
                fig_tipo.update_layout(height=280, margin=dict(l=0, r=0, t=20, b=0))
                st.plotly_chart(fig_tipo, use_container_width=True)

            st.markdown("---")

            # Gerenciar posições
            st.markdown("### 🗑️ Remover Ativo da Carteira")
            ticker_remover = st.selectbox(
                "Selecione o ativo para remover:",
                list(st.session_state.carteira.keys()),
                label_visibility="collapsed"
            )
            if st.button("🗑️ Remover", type="secondary"):
                del st.session_state.carteira[ticker_remover]
                st.success(f"✅ **{ticker_remover}** removido da carteira.")
                st.rerun()


# ==============================
# PÁGINA 3: EXPLORAR MERCADO
# ==============================
elif "Explorar" in pagina:
    st.markdown("<h1 class='titulo-principal'>🔎 Explorar Mercado</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo'>Navegue por todas as ações e FIIs da B3</p>", unsafe_allow_html=True)
    st.markdown("---")

    tipo_filtro = st.radio("Tipo de ativo:", ["Ações", "FIIs / ETFs / Fundos"], horizontal=True)
    busca_mercado = st.text_input("🔍 Buscar por ticker ou nome:", placeholder="Ex: Petro, Banco, MXRF...")

    if tipo_filtro == "Ações":
        lista = st.session_state.lista_acoes
    else:
        lista = st.session_state.lista_fiis

    # Filtrar por busca
    if busca_mercado:
        lista_filtrada = [
            a for a in lista
            if busca_mercado.upper() in a["ticker"].upper() or busca_mercado.upper() in a["nome"].upper()
        ]
    else:
        lista_filtrada = lista

    # Filtro por setor
    setores = sorted(set(a["setor"] for a in lista if a["setor"]))
    setor_selecionado = st.selectbox("Filtrar por setor:", ["Todos"] + setores)
    if setor_selecionado != "Todos":
        lista_filtrada = [a for a in lista_filtrada if a["setor"] == setor_selecionado]

    st.markdown(f"**{len(lista_filtrada)} ativos encontrados**")

    # Exibir em tabela
    if lista_filtrada:
        df_lista = pd.DataFrame(lista_filtrada)
        df_lista.columns = ["Ticker", "Nome", "Setor", "Tipo"]
        st.dataframe(df_lista, use_container_width=True, hide_index=True, height=500)
    else:
        st.warning("Nenhum ativo encontrado com os filtros aplicados.")


# ==============================
# PÁGINA 4: COMPARAR ATIVOS
# ==============================
elif "Comparar" in pagina:
    st.markdown("<h1 class='titulo-principal'>📋 Comparar Ativos</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitulo'>Compare até 5 ativos lado a lado</p>", unsafe_allow_html=True)
    st.markdown("---")

    todos_tickers = [a["ticker"] for a in st.session_state.lista_acoes + st.session_state.lista_fiis]

    tickers_comp = st.multiselect(
        "Selecione os ativos para comparar (máx. 5):",
        options=todos_tickers,
        max_selections=5,
        placeholder="Digite ou selecione os tickers..."
    )

    if tickers_comp:
        with st.spinner("Buscando dados para comparação..."):
            dados_comp = []
            hists_comp = {}
            for t in tickers_comp:
                info, hist, divs, ticker_c = buscar_ativo(t)
                if ticker_c and hist is not None and not hist.empty:
                    preco = hist["Close"].iloc[-1]
                    m = extrair_metricas(info, preco, ticker_c)
                    score, _ = calcular_score(m, ticker_c)
                    dados_comp.append({
                        "Ticker": t,
                        "Nome": m["nome"][:30],
                        "Preço (R$)": round(preco, 2),
                        "DY (%)": m["dy"],
                        "P/VP": m["pvp"],
                        "P/L": m["pl"] if m["pl"] > 0 else "N/D",
                        "ROE (%)": m["roe"] if m["roe"] != 0 else "N/D",
                        "Beta": m["beta"] if m["beta"] != 0 else "N/D",
                        "Market Cap": formatar_market_cap(m["market_cap"]),
                        "Score": f"{score}/10",
                    })
                    hists_comp[t] = hist

        if dados_comp:
            df_comp = pd.DataFrame(dados_comp)
            st.dataframe(df_comp, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### 📈 Evolução de Preços Normalizada (base 100)")

            fig_comp = go.Figure()
            cores_comp = ["#00d4aa", "#4da6ff", "#f0c040", "#c080ff", "#ff6b6b"]
            for i, (ticker_c, hist_c) in enumerate(hists_comp.items()):
                preco_base = hist_c["Close"].iloc[0]
                normalizado = (hist_c["Close"] / preco_base) * 100
                fig_comp.add_trace(go.Scatter(
                    x=hist_c.index,
                    y=normalizado,
                    name=ticker_c,
                    line=dict(color=cores_comp[i % len(cores_comp)], width=2)
                ))

            fig_comp.update_layout(
                template="plotly_dark",
                height=420,
                yaxis_title="Retorno base 100",
                margin=dict(l=0, r=0, t=20, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig_comp, use_container_width=True)

            # Comparação de DY
            st.markdown("### 💰 Comparação de Dividend Yield")
            df_dy = pd.DataFrame([{"Ticker": d["Ticker"], "DY (%)": d["DY (%)"]} for d in dados_comp])
            fig_dy = px.bar(
                df_dy, x="Ticker", y="DY (%)",
                color="DY (%)",
                color_continuous_scale="teal",
                template="plotly_dark",
                text="DY (%)"
            )
            fig_dy.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_dy, use_container_width=True)
    else:
        st.info("Selecione pelo menos um ativo para iniciar a comparação.")

