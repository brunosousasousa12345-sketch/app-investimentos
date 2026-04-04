import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Investidor PRO", layout="wide")

# 🎨 ESTILO
st.markdown("""
<style>
body { background-color: #0E1117; }
div[data-testid="stMetric"] {
    background-color: #1E222A;
    padding: 15px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

st.title("📈 Investidor PRO")
st.caption("Sistema profissional de análise de ações")

# SIDEBAR
ticker = st.sidebar.text_input("Digite o Ticker:", "BBAS3").upper()
if not ticker.endswith(".SA"):
    ticker += ".SA"

aba1, aba2, aba3 = st.tabs(["📊 Análise", "💼 Carteira", "💰 Dividendos"])

# =========================
# 📊 ANÁLISE
# =========================
with aba1:
    try:
        acao = yf.Ticker(ticker)
        hist = acao.history(period="1y")
        info = acao.info if acao.info else {}

        preco = hist['Close'].iloc[-1] if not hist.empty else 0

        vpa = info.get('bookValue') or 0
        lpa = info.get('trailingEps') or 0
        pl = info.get('trailingPE') or 0
        roe = (info.get('returnOnEquity') or 0) * 100
        divida = info.get('debtToEquity') or 0

        # DY CORRIGIDO
        dy_raw = info.get('dividendYield')
        if dy_raw is None:
            dy = 0
        elif dy_raw < 1:
            dy = dy_raw * 100
        else:
            dy = dy_raw

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço", f"R$ {preco:.2f}")
        c2.metric("P/L", f"{pl:.2f}")
        c3.metric("DY", f"{dy:.2f}%")
        c4.metric("ROE", f"{roe:.2f}%")

        st.subheader("📊 Histórico")
        fig = px.line(hist, x=hist.index, y='Close')
        st.plotly_chart(fig, use_container_width=True)

        # PREÇO JUSTO
        if lpa > 0 and vpa > 0:
            preco_justo = (22.5 * lpa * vpa) ** 0.5
            margem = ((preco_justo / preco) - 1) * 100 if preco > 0 else 0

            st.subheader("⚖️ Preço Justo")
            st.write(f"R$ {preco_justo:.2f}")

            if margem > 20:
                st.success(f"🟢 Margem {margem:.2f}%")
            elif margem > 0:
                st.warning(f"🟡 Margem {margem:.2f}%")
            else:
                st.error(f"🔴 Margem {margem:.2f}%")

        # SCORE
        score = 0
        if roe > 20: score += 2
        elif roe > 10: score += 1

        if dy > 8: score += 2
        elif dy > 4: score += 1

        if divida < 0.5: score += 2
        elif divida < 1: score += 1

        st.subheader("🧠 Nota")
        if score >= 5:
            st.success("🟢 BOA")
        elif score >= 3:
            st.warning("🟡 MÉDIA")
        else:
            st.error("🔴 FRACA")

    except:
        st.error("Erro ao carregar dados")

# =========================
# 💼 CARTEIRA
# =========================
with aba2:
    st.subheader("💼 Minha Carteira")

    if "carteira" not in st.session_state:
        st.session_state.carteira = []

    col1, col2, col3 = st.columns(3)

    with col1:
        novo = st.text_input("Ticker").upper()

    with col2:
        valor = st.number_input("Valor investido", min_value=0.0)

    with col3:
        if st.button("Adicionar"):
            if novo:
                st.session_state.carteira.append({
                    "ticker": novo,
                    "valor": valor
                })

    total_investido = 0
    total_atual = 0
    dados = []

    for ativo in st.session_state.carteira:
        t = ativo["ticker"]

        if not t.endswith(".SA"):
            t += ".SA"

        acao = yf.Ticker(t)
        hist = acao.history(period="1d")

        preco = hist['Close'].iloc[-1] if not hist.empty else 0

        investido = ativo["valor"]
        cotas = investido / preco if preco > 0 else 0
        atual = cotas * preco
        lucro = atual - investido

        total_investido += investido
        total_atual += atual

        dados.append({
            "Ticker": t,
            "Investido": investido,
            "Atual": atual,
            "Lucro": lucro
        })

    if dados:
        df = pd.DataFrame(dados)
        st.dataframe(df, use_container_width=True)

        lucro_total = total_atual - total_investido

        c1, c2, c3 = st.columns(3)
        c1.metric("Investido", f"R$ {total_investido:.2f}")
        c2.metric("Atual", f"R$ {total_atual:.2f}")
        c3.metric("Lucro", f"R$ {lucro_total:.2f}")

        # GRÁFICO
        df_total = pd.DataFrame()

        for ativo in st.session_state.carteira:
            t = ativo["ticker"]
            if not t.endswith(".SA"):
                t += ".SA"

            hist = yf.Ticker(t).history(period="1y")['Close']

            if not hist.empty:
                df_total[t] = hist

        if not df_total.empty:
            df_total["Total"] = df_total.sum(axis=1)
            fig = px.line(df_total, x=df_total.index, y="Total")
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Adicione ativos")

# =========================
# 💰 DIVIDENDOS
# =========================
with aba3:
    st.subheader("💰 Dividendos")

    investimento = st.number_input("Valor por ação", 1000.0)

    total = 0

    for ativo in st.session_state.carteira:
        t = ativo["ticker"]

        if not t.endswith(".SA"):
            t += ".SA"

        info = yf.Ticker(t).info or {}

        dy_raw = info.get('dividendYield')

        if dy_raw is None:
            dy = 0
        elif dy_raw < 1:
            dy = dy_raw
        else:
            dy = dy_raw / 100

        dividendos = investimento * dy
        total += dividendos

        st.write(f"{t}: R$ {dividendos:.2f}/ano")

    st.success(f"Total anual: R$ {total:.2f}")
