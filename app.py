import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Investidor PRO", layout="wide")

# 🎨 ESTILO PROFISSIONAL
st.markdown("""
<style>
body {
    background-color: #0E1117;
}
div[data-testid="stMetric"] {
    background-color: #1E222A;
    padding: 15px;
    border-radius: 12px;
    border: 1px solid #2A2F3A;
}
h1, h2, h3 {
    color: #E6E6E6;
}
section[data-testid="stSidebar"] {
    background-color: #11151C;
}
</style>
""", unsafe_allow_html=True)

st.title("📈 Investidor PRO")
st.caption("Sistema profissional de análise de ações | Desenvolvido por Bruno 📊")

# SIDEBAR
ticker = st.sidebar.text_input("Digite o Ticker:", "BBAS3").upper()

if not ticker.endswith(".SA"):
    ticker += ".SA"

# ABAS
aba1, aba2, aba3 = st.tabs(["📊 Análise", "💼 Carteira", "💰 Dividendos"])

# =========================
# 📊 ABA 1 - ANÁLISE
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

        # 🔥 CORREÇÃO DO DY
        dy_raw = info.get('dividendYield')
        if dy_raw is None:
            dy = 0
        elif dy_raw < 1:
            dy = dy_raw * 100
        else:
            dy = dy_raw

        # DASHBOARD
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Preço", f"R$ {preco:.2f}")
        c2.metric("P/L", f"{pl:.2f}")
        c3.metric("DY", f"{dy:.2f}%")
        c4.metric("ROE", f"{roe:.2f}%")

        # GRÁFICO
        st.subheader("📊 Histórico")
        fig = px.line(hist, x=hist.index, y='Close')
        st.plotly_chart(fig, use_container_width=True)

        # VALUATION
        st.subheader("⚖️ Preço Justo")
        if lpa > 0 and vpa > 0:
            preco_justo = (22.5 * lpa * vpa) ** 0.5
            margem = ((preco_justo / preco) - 1) * 100 if preco > 0 else 0

            st.write(f"Preço Justo: R$ {preco_justo:.2f}")

            if margem > 20:
                st.success(f"🟢 Margem {margem:.2f}%")
            elif margem > 0:
                st.info(f"🟡 Margem {margem:.2f}%")
            else:
                st.error(f"🔴 Margem {margem:.2f}%")

        # 🧠 SCORE INTELIGENTE
        score = 0

        if roe > 20:
            score += 2
        elif roe > 10:
            score += 1

        if dy > 8:
            score += 2
        elif dy > 4:
            score += 1

        if divida < 0.5:
            score += 2
        elif divida < 1:
            score += 1

        st.subheader("🧠 Nota da Ação")
        if score >= 5:
            st.success("🟢 BOA")
        elif score >= 3:
            st.warning("🟡 MÉDIA")
        else:
            st.error("🔴 FRACA")

        # 🤖 RECOMENDAÇÃO
        st.subheader("🤖 Recomendação")
        if score >= 5:
            st.success("🟢 FORTE COMPRA")
        elif score >= 3:
            st.warning("🟡 NEUTRO")
        else:
            st.error("🔴 EVITAR")

        if dy > 20:
            st.warning("⚠️ DY muito alto (cuidado!)")

        # 💰 SIMULADOR
        st.subheader("💼 Simulador")
        valor = st.number_input("💰 Quanto você investiu (R$):", min_value=0.0, value=1000.0)

        cotas = valor / preco if preco > 0 else 0
        valor_atual = cotas * preco

        st.write(f"Cotas: {cotas:.2f}")
        st.write(f"Valor atual: R$ {valor_atual:.2f}")

    except:
        st.error("Erro ao carregar dados.")

# =========================
# 💼 ABA 2 - CARTEIRA
# =========================
with aba2:
    st.subheader("📊 Minha Carteira")

    carteira = ["BBAS3", "GOAU4", "CMIG3", "CPLE4", "PETR4"]

    dados = []

    for t in carteira:
        t_sa = f"{t}.SA"
        a = yf.Ticker(t_sa)
        i = a.info if a.info else {}

        preco = a.history(period="1d")['Close']
        preco = preco.iloc[-1] if not preco.empty else 0

        dy_raw = i.get('dividendYield')
        if dy_raw is None:
            dy = 0
        elif dy_raw < 1:
            dy = dy_raw * 100
        else:
            dy = dy_raw

        roe = (i.get('returnOnEquity') or 0) * 100
        divida = i.get('debtToEquity') or 0

        score = 0
        if roe > 20:
            score += 2
        elif roe > 10:
            score += 1

        if dy > 8:
            score += 2
        elif dy > 4:
            score += 1

        if divida < 0.5:
            score += 2
        elif divida < 1:
            score += 1

        dados.append({
            "Ticker": t,
            "Preço": preco,
            "DY (%)": dy,
            "ROE (%)": roe,
            "Score": score
        })

    df = pd.DataFrame(dados)

    st.dataframe(df.sort_values(by="Score", ascending=False), use_container_width=True)

    top = df.sort_values(by="Score", ascending=False).iloc[0]
    st.success(f"🏆 Melhor ação: {top['Ticker']}")

    # 📈 GRÁFICO
    st.subheader("📈 Evolução da Carteira")

    df_total = pd.DataFrame()

    for t in carteira:
        dados_hist = yf.Ticker(f"{t}.SA").history(period="1y")['Close']
        if not dados_hist.empty:
            df_total[t] = dados_hist

    if not df_total.empty:
        df_total['Total'] = df_total.sum(axis=1)
        fig2 = px.line(df_total, x=df_total.index, y='Total')
        st.plotly_chart(fig2, use_container_width=True)

# =========================
# 💰 ABA 3 - DIVIDENDOS
# =========================
with aba3:
    st.subheader("💰 Previsão de Dividendos")

    carteira = ["BBAS3", "GOAU4", "CMIG3", "CPLE4", "PETR4"]

    investimento = st.number_input("Valor investido por ação (R$):", 1000.0)

    total = 0

    for t in carteira:
        a = yf.Ticker(f"{t}.SA")
        i = a.info if a.info else {}

        dy_raw = i.get('dividendYield')

        if dy_raw is None:
            dy = 0
        elif dy_raw < 1:
            dy = dy_raw
        else:
            dy = dy_raw / 100

        dividendos = investimento * dy
        total += dividendos

        st.write(f"{t}: R$ {dividendos:.2f}/ano")

    st.success(f"💵 Total anual: R$ {total:.2f}")
