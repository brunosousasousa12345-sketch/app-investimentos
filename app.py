import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Investidor PRO", layout="wide")

st.title("📈 Investidor PRO")

# SIDEBAR
ticker = st.sidebar.text_input("Digite o Ticker:", "BBAS3").upper()

if not ticker.endswith(".SA"):
    ticker += ".SA"

# ABAS
aba1, aba2, aba3 = st.tabs(["📊 Análise", "💼 Carteira", "💰 Dividendos"])

# =========================
# ABA 1 - ANÁLISE
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

        # SCORE
        score = 0
        if roe > 15:
            score += 1
        if dy > 5:
            score += 1
        if divida < 1:
            score += 1

        st.subheader("🧠 Nota da Ação")
        if score == 3:
            st.success("🟢 BOA")
        elif score == 2:
            st.warning("🟡 MÉDIA")
        else:
            st.error("🔴 FRACA")

        # RECOMENDAÇÃO
        st.subheader("🤖 Recomendação")
        if score == 3:
            st.success("🟢 COMPRAR")
        elif score == 2:
            st.warning("🟡 SEGURAR")
        else:
            st.error("🔴 VENDER")

        # ALERTA DY
        if dy > 20:
            st.warning("⚠️ DY muito alto (cuidado!)")

    except:
        st.error("Erro ao carregar dados.")

# =========================
# ABA 2 - CARTEIRA
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
        if roe > 15:
            score += 1
        if dy > 5:
            score += 1
        if divida < 1:
            score += 1

        dados.append({
            "Ticker": t,
            "Preço": preco,
            "DY (%)": dy,
            "ROE (%)": roe,
            "Score": score
        })

    df = pd.DataFrame(dados)
    st.dataframe(df.sort_values(by="Score", ascending=False))

    top = df.sort_values(by="Score", ascending=False).iloc[0]
    st.success(f"🏆 Melhor ação: {top['Ticker']}")

    # GRÁFICO DA CARTEIRA
    st.subheader("📈 Evolução da Carteira")

    df_total = pd.DataFrame()

    for t in carteira:
        dados = yf.Ticker(f"{t}.SA").history(period="1y")['Close']
        if not dados.empty:
            df_total[t] = dados

    df_total['Total'] = df_total.sum(axis=1)

    fig2 = px.line(df_total, x=df_total.index, y='Total')
    st.plotly_chart(fig2, use_container_width=True)

# =========================
# ABA 3 - DIVIDENDOS
# =========================
with aba3:
    st.subheader("💰 Previsão de Dividendos")

    carteira = ["BBAS3", "GOAU4", "CMIG3", "CPLE4", "PETR4"]

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

        investimento = 1000
        dividendos = investimento * dy

        total += dividendos

        st.write(f"{t}: R$ {dividendos:.2f}/ano")

    st.success(f"💵 Total anual: R$ {total:.2f}")
