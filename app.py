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
# MENU
# ==============================
st.sidebar.title("📊 Menu")

menu = st.sidebar.selectbox("Escolha:", [
    "📈 Analisar Ativo",
    "💼 Minha Carteira",
    "🏆 Ranking",
    "🤖 IA Carteira",
])

st.sidebar.markdown("---")

# ==============================
# PLANO PRO
# ==============================
st.sidebar.title("💰 Plano PRO")

st.sidebar.markdown("""
🔥 Acesso completo:

✔️ IA avançada  
✔️ Ranking completo  
✔️ Carteira automática  

💰 R$ 9,90/mês
""")

st.sidebar.markdown("[👉 Assinar agora](SEU_LINK_AQUI)")

# ==============================
# CACHE (ULTRA IMPORTANTE)
# ==============================

@st.cache_data(ttl=1800, show_spinner=False)
def get_data(ticker):
    if not ticker.endswith(".SA") and len(ticker) <= 6:
        ticker += ".SA"

    acao = yf.Ticker(ticker)

    try:
        info = acao.fast_info  # mais rápido
    except:
        info = acao.info

    hist = acao.history(period="3mo")

    return info, hist

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
    if score >= 8:
        return "🟢 FORTE COMPRA"
    elif score >= 6:
        return "🟡 BOA"
    elif score >= 4:
        return "⚠️ NEUTRO"
    else:
        return "🔴 EVITAR"

# ==============================
# 1. ANALISAR
# ==============================
if menu == "📈 Analisar Ativo":

    ticker = st.text_input("Digite o ativo:", "PETR4")

    if st.button("Analisar"):
        with st.spinner("🔄 Buscando dados..."):

            try:
                info, hist = get_data(ticker)
                preco = hist["Close"].iloc[-1]

                ind = calcular_indicadores(info, preco, ticker)
                score = score_ativo(ind)
                rec = recomendacao(score)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Preço", f"R$ {preco:.2f}")
                col2.metric("DY", f"{ind['DY']:.2f}%")
                col3.metric("ROE", f"{ind['ROE']:.2f}%")
                col4.metric("P/L", f"{ind['P/L']:.2f}")

                st.markdown("---")

                st.subheader(ind["Nome"])
                st.write(f"📊 Setor: {ind['Setor']}")
                st.write(f"📌 P/VP: {ind['P/VP']:.2f}")
                st.write(f"📌 Dívida/PL: {ind['Dívida']:.2f}")

                st.markdown("---")

                st.subheader("🤖 IA Recomenda:")
                st.success(rec)

                st.line_chart(hist["Close"])

            except:
                st.error("Erro ao buscar dados")

# ==============================
# 2. CARTEIRA
# ==============================
if menu == "💼 Minha Carteira":

    arquivo = "carteira.csv"

    if os.path.exists(arquivo):
        df = pd.read_csv(arquivo)
    else:
        df = pd.DataFrame(columns=["Ticker"])

    novo = st.text_input("Adicionar ativo")

    if st.button("Adicionar"):
        df.loc[len(df)] = [novo.upper()]
        df.to_csv(arquivo, index=False)

    st.dataframe(df)

    if st.button("Atualizar carteira"):
        total = 0

        for t in df["Ticker"]:
            try:
                info, hist = get_data(t)
                preco = hist["Close"].iloc[-1]
                ind = calcular_indicadores(info, preco, t)
                score = score_ativo(ind)

                st.write(f"{t} → Score {score}")
                total += score
            except:
                st.write(f"{t} erro")

        if len(df) > 0:
            st.success(f"Score médio: {total/len(df):.2f}")

# ==============================
# 3. RANKING
# ==============================
if menu == "🏆 Ranking":

    if st.button("Gerar Ranking"):

        ativos = ["PETR4","VALE3","ITUB4"]

        resultados = []

        with st.spinner("Gerando ranking..."):
            for t in ativos:
                try:
                    info, hist = get_data(t)
                    preco = hist["Close"].iloc[-1]
                    ind = calcular_indicadores(info, preco, t)
                    score = score_ativo(ind)

                    resultados.append([t, score])
                except:
                    pass

        df = pd.DataFrame(resultados, columns=["Ativo","Score"])
        df = df.sort_values(by="Score", ascending=False)

        st.dataframe(df)

# ==============================
# 4. IA CARTEIRA
# ==============================
if menu == "🤖 IA Carteira":

    perfil = st.selectbox("Perfil:", ["Conservador","Moderado","Agressivo"])

    if st.button("Gerar carteira"):

        if perfil == "Conservador":
            carteira = ["MXRF11","HGLG11","BBAS3"]
        elif perfil == "Moderado":
            carteira = ["ITUB4","VALE3","HGLG11"]
        else:
            carteira = ["PETR4","VALE3","GOAU4"]

        st.success("Carteira sugerida:")

        for a in carteira:
            st.write(a)
