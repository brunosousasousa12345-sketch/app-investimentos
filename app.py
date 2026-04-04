import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Investidor Pro", layout="wide")

st.title("📈 Analisador de Ações PRO")

ticker_input = st.sidebar.text_input("Ticker:", "BBAS3").upper()

if not ticker_input.endswith(".SA"):
    ticker_nome = f"{ticker_input}.SA"
else:
    ticker_nome = ticker_input

try:
    acao = yf.Ticker(ticker_nome)
    hist = acao.history(period="1y")

    info = acao.info if acao.info else {}

    preco_atual = hist['Close'].iloc[-1] if not hist.empty else 0

    vpa = info.get('bookValue') or 0
    lpa = info.get('trailingEps') or 0
    pl = info.get('trailingPE') or 0
    dy = (info.get('dividendYield') or 0) * 100
    roe = (info.get('returnOnEquity') or 0) * 100
    divida = info.get('debtToEquity') or 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Preço", f"R$ {preco_atual:.2f}")
    col2.metric("P/L", f"{pl:.2f}")
    col3.metric("DY", f"{dy:.2f}%")
    col4.metric("ROE", f"{roe:.2f}%")

    st.subheader("📊 Gráfico")
    fig = px.line(hist, x=hist.index, y='Close')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("⚖️ Valuation")

    if lpa > 0 and vpa > 0:
        preco_justo = (22.5 * lpa * vpa) ** 0.5
        margem = ((preco_justo / preco_atual) - 1) * 100 if preco_atual > 0 else 0

        st.write(f"Preço Justo: R$ {preco_justo:.2f}")

        if margem > 20:
            st.success(f"🟢 Margem: {margem:.2f}% (Excelente)")
        elif margem > 0:
            st.info(f"🟡 Margem: {margem:.2f}%")
        else:
            st.error(f"🔴 Margem: {margem:.2f}%")

    st.subheader("🛡️ Saúde da Empresa")

    if roe > 15:
        st.success("ROE bom")
    else:
        st.warning("ROE baixo")

    if divida < 1:
        st.success("Dívida controlada")
    else:
        st.warning("Dívida alta")

except:
    st.error("Erro ao carregar dados. Verifique o ticker.")
