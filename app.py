import streamlit as st
import yfinance as yf
import pandas as pd

# 1. CONFIGURAÇÃO VISUAL PROFISSIONAL
st.set_page_config(page_title="Investidor PRO", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 20px; border-radius: 10px; }
    .main-title { text-align: center; color: #1E3A8A; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>🚀 Investidor PRO Universal</h1>", unsafe_allow_html=True)

# 2. FUNÇÃO DE BUSCA CORRIGIDA
@st.cache_data(ttl=600)
def buscar_dados_completos(ticker_input):
    ticker = ticker_input.upper().strip()
    # Tenta B3 primeiro, depois Global
    for t in [f"{ticker}.SA", ticker]:
        try:
            obj = yf.Ticker(t)
            hist = obj.history(period="1y")
            if not hist.empty:
                return obj.info, hist, t
        except:
            continue
    return None, None, None

# 3. INTERFACE DE BUSCA
busca = st.text_input("Digite o Ticker (Ex: MXRF11, PETR4, AAPL):", "MXRF11")

if busca:
    info, hist, ticker_final = buscar_dados_completos(busca)

    if ticker_final:
        # Extração de dados com tratamento de erro (Resolvendo o N/A)
        preco = hist["Close"].iloc[-1]
        # Para FIIs, o DY costuma estar em 'yield', para Ações em 'dividendYield'
        dy = (info.get('dividendYield') or info.get('yield') or 0) * 100
        pvp = preco / info.get('bookValue', 1) if info.get('bookValue') else 0
        pl = info.get('trailingPE') or 0
        roe = (info.get('returnOnEquity') or 0) * 100
        nome = info.get('longName', ticker_final)

        # 4. LAYOUT EM COLUNAS PROFISSIONAIS
        st.subheader(f"📊 Análise: {nome}")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Preço Atual", f"R$ {preco:.2f}")
        col2.metric("Dividend Yield", f"{dy:.2f}%")
        col3.metric("P/VP", f"{pvp:.2f}")
        col4.metric("P/L", f"{pl:.2f}" if pl > 0 else "N/A")

        # 5. LÓGICA DE SCORE DIFERENCIADA (Ações vs FIIs)
        score = 0
        is_fii = ".SA" in ticker_final and (len(ticker_final) >= 8 or ticker_final[-5:-3] == "11")
        
        if dy > 8: score += 4
        if 0.8 < pvp < 1.1: score += 3
        if not is_fii and roe > 15: score += 3
        if is_fii: score += 3 # Bônus de estabilidade para FIIs

        # 6. EXIBIÇÃO DO SCORE E GRÁFICO
        st.markdown("---")
        if score >= 7:
            st.success(f"**Pontuação: {score}/10** - Recomendação: 🟢 FORTE COMPRA")
        elif score >= 5:
            st.warning(f"**Pontuação: {score}/10** - Recomendação: 🟡 NEUTRO / OBSERVAÇÃO")
        else:
            st.error(f"**Pontuação: {score}/10** - Recomendação: 🔴 EVITAR NO MOMENTO")

        st.line_chart(hist["Close"])
        
        with st.expander("📂 Ver Detalhes Técnicos"):
            st.write(f"**Setor:** {info.get('sector', 'N/A')}")
            st.write(f"**Ticker Oficial:** {ticker_final}")
            st.write(f"**Resumo:** {info.get('longBusinessSummary', 'Sem resumo disponível.')}")
    else:
        st.error("❌ Ativo não encontrado. Tente digitar o código exato (Ex: PETR4).")
