import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Investidor PRO", layout="wide")

st.title("📈 Investidor PRO - Análise Completa")

# INPUT
ticker = st.sidebar.text_input("Digite o Ticker:", "BBAS3").upper()

if not ticker.endswith(".SA"):
    ticker += ".SA"

try:
    acao = yf.Ticker(ticker)
    hist = acao.history(period="1y")
    info = acao.info if acao.info else {}

    preco = hist['Close'].iloc[-1] if not hist.empty else 0

    # INDICADORES
    vpa = info.get('bookValue') or 0
    lpa = info.get('trailingEps') or 0
    pl = info.get('trailingPE') or 0
    dy = (info.get('dividendYield') or 0) * 100
    roe = (info.get('returnOnEquity') or 0) * 100
    divida = info.get('debtToEquity') or 0

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

    # NOTA AUTOMÁTICA
    st.subheader("🧠 Nota da Ação")

    score = 0

    if roe > 15:
        score += 1
    if dy > 5:
        score += 1
    if divida < 1:
        score += 1

    if score == 3:
        st.success("🟢 Ação BOA")
    elif score == 2:
        st.warning("🟡 Ação MÉDIA")
    else:
        st.error("🔴 Ação FRACA")

    # SIMULADOR
    st.subheader("💼 Simulador de Investimento")

    valor = st.number_input("Quanto você investiu (R$):", 100.0)
    cotas = valor / preco if preco > 0 else 0
    valor_atual = cotas * preco

    st.write(f"Cotas: {cotas:.2f}")
    st.write(f"Valor atual: R$ {valor_atual:.2f}")

except:
    st.error("Erro ao carregar dados.")
