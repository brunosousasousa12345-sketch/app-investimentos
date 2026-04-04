import streamlit as st
import yfinance as yf
import pandas as pd
import os

# ==============================
# CONFIG
# ==============================
st.set_page_config(page_title="Investidor PRO", layout="wide")

st.markdown("<h1 style='text-align:center;'>🚀 Investidor PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Sua IA de investimentos</p>", unsafe_allow_html=True)

# ==============================
# BASE INTELIGENTE
# ==============================
ativos_base = {
    "petrobras": "PETR4",
    "vale": "VALE3",
    "itau": "ITUB4",
    "itaú": "ITUB4",
    "banco do brasil": "BBAS3",
    "bradesco": "BBDC4",
    "weg": "WEGE3",
    "ambev": "ABEV3",

    "mxrf": "MXRF11",
    "hglg": "HGLG11",
    "xplg": "XPLG11",

    "apple": "AAPL",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "amazon": "AMZN",
    "tesla": "TSLA"
}

def buscar_ticker(nome):
    nome = nome.lower().strip()

    if len(nome) <= 6 and nome.isalnum():
        return nome.upper()

    for chave in ativos_base:
        if nome in chave:
            return ativos_base[chave]

    return None

# ==============================
# CACHE RÁPIDO
# ==============================
@st.cache_data(ttl=1800)
def get_data(ticker):
    ticker = ticker.upper()

    if "." not in ticker and len(ticker) <= 6:
        ticker += ".SA"

    acao = yf.Ticker(ticker)

    try:
        hist = acao.history(period="3mo")
        if hist.empty:
            return None, None

        try:
            info = acao.info
        except:
            info = {}

        return info, hist
    except:
        return None, None

@st.cache_data(ttl=1800)
def calcular_indicadores(info, preco, ticker):
    try:
        dy = (info.get("dividendYield") or 0) * 100
        roe = (info.get("returnOnEquity") or 0) * 100
        pl = info.get("trailingPE") or 0
        pvp = preco / (info.get("bookValue") or 1)
        divida = info.get("debtToEquity") or 0
        setor = info.get("sector") or "N/A"
        nome = info.get("longName") or ticker
    except:
        dy, roe, pl, pvp, divida, setor, nome = 0,0,0,0,0,"N/A",ticker

    return {
        "DY": dy,
        "ROE": roe,
        "P/L": pl,
        "P/VP": pvp,
        "Dívida": divida,
        "Setor": setor,
        "Nome": nome
    }

def score_ativo(ind):
    score = 0
    if ind["DY"] > 6: score += 2
    if ind["ROE"] > 15: score += 2
    if ind["P/L"] > 0 and ind["P/L"] < 15: score += 2
    if ind["P/VP"] < 1.5: score += 2
    if ind["Dívida"] < 100: score += 2
    return score

def recomendacao(score):
    if score >= 8: return "🟢 FORTE COMPRA"
    elif score >= 6: return "🟡 BOA"
    elif score >= 4: return "⚠️ NEUTRO"
    else: return "🔴 EVITAR"

# ==============================
# MENU
# ==============================
menu = st.sidebar.selectbox("Menu", [
    "📈 Analisar",
    "💼 Carteira",
    "🏆 Ranking",
    "🤖 IA Carteira"
])

# ==============================
# ANALISAR
# ==============================
if menu == "📈 Analisar":

    entrada = st.text_input("🔎 Nome ou código:", "petrobras")

    sugestoes = list(ativos_base.keys())
    escolha = st.selectbox("Sugestões:", [""] + sugestoes)

    if escolha:
        entrada = escolha

    if st.button("Analisar"):

        ticker = buscar_ticker(entrada)

        if not ticker:
            st.error("Ativo não encontrado")
        else:
            st.success(f"{ticker}")

            with st.spinner("Buscando dados..."):
                info, hist = get_data(ticker)

            if hist is None:
                st.error("Erro ao buscar dados")
            else:
                preco = hist["Close"].iloc[-1]

                ind = calcular_indicadores(info, preco, ticker)
                score = score_ativo(ind)
                rec = recomendacao(score)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Preço", f"R$ {preco:.2f}")
                col2.metric("DY", f"{ind['DY']:.2f}%")
                col3.metric("ROE", f"{ind['ROE']:.2f}%")
                col4.metric("P/L", f"{ind['P/L']:.2f}")

                st.write(f"Setor: {ind['Setor']}")
                st.write(f"P/VP: {ind['P/VP']:.2f}")
                st.write(f"Dívida: {ind['Dívida']:.2f}")

                st.subheader("Recomendação")
                st.success(rec)

                st.line_chart(hist["Close"])

# ==============================
# CARTEIRA
# ==============================
if menu == "💼 Carteira":

    arquivo = "carteira.csv"

    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo)
    else:
        df = pd.DataFrame(columns=["Ticker"])

    novo = st.text_input("Adicionar ativo")

    if st.button("Adicionar"):
        ticker = buscar_ticker(novo)
        if ticker:
            df.loc[len(df)] = [ticker]
            df.to_csv(arquivo, index=False)

    st.dataframe(df)

    if st.button("Atualizar"):
        total = 0

        for t in df["Ticker"]:
            info, hist = get_data(t)

            if hist is not None:
                preco = hist["Close"].iloc[-1]
                ind = calcular_indicadores(info, preco, t)
                score = score_ativo(ind)

                st.write(f"{t} → {score}")
                total += score

        if len(df) > 0:
            st.success(f"Média: {total/len(df):.2f}")

# ==============================
# RANKING
# ==============================
if menu == "🏆 Ranking":

    if st.button("Gerar Ranking"):

        ativos = ["PETR4","VALE3","ITUB4","BBAS3","MXRF11"]

        lista = []

        for t in ativos:
            info, hist = get_data(t)

            if hist is not None:
                preco = hist["Close"].iloc[-1]
                ind = calcular_indicadores(info, preco, t)
                score = score_ativo(ind)

                lista.append([t, score])

        df = pd.DataFrame(lista, columns=["Ativo","Score"])
        df = df.sort_values(by="Score", ascending=False)

        st.dataframe(df)

# ==============================
# IA CARTEIRA
# ==============================
if menu == "🤖 IA Carteira":

    perfil = st.selectbox("Perfil", ["Conservador","Moderado","Agressivo"])

    if st.button("Gerar"):

        if perfil == "Conservador":
            carteira = ["MXRF11","HGLG11","BBAS3"]
        elif perfil == "Moderado":
            carteira = ["ITUB4","VALE3","HGLG11"]
        else:
            carteira = ["PETR4","VALE3","GOAU4"]

        for a in carteira:
            st.write(a)
