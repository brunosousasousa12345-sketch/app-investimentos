import streamlit as st
import yfinance as yf
import pandas as pd
import os

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(page_title="Investidor PRO Universal", layout="wide", page_icon="📊")

st.markdown("<h1 style='text-align:center;'>🚀 Investidor PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Análise Universal: Ações, FIIs, Stocks e Cripto</p>", unsafe_allow_html=True)

# ==============================
# MOTOR DE BUSCA UNIVERSAL
# ==============================
@st.cache_data(ttl=1800)
def get_universal_data(ticker_input):
    ticker_input = ticker_input.upper().strip()
    
    # Lista de tentativas: 1. Como digitado | 2. Com .SA (Brasil)
    tentativas = [ticker_input, f"{ticker_input}.SA"]
    
    for t in tentativas:
        try:
            ativo = yf.Ticker(t)
            hist = ativo.history(period="6mo")
            
            if not hist.empty:
                # Se achou dados históricos, o ticker é válido
                try:
                    info = ativo.info
                except:
                    info = {}
                return info, hist, t
        except:
            continue
    return None, None, None

def calcular_indicadores(info, preco, ticker):
    # Dicionário com travas para evitar erros de dados ausentes
    res = {
        "DY": (info.get("dividendYield", 0) or 0) * 100,
        "ROE": (info.get("returnOnEquity", 0) or 0) * 100,
        "PL": info.get("trailingPE", 0) or 0,
        "PVP": preco / (info.get("bookValue", 1) or 1) if info.get("bookValue") else 0,
        "Divida": info.get("debtToEquity", 0) or 0,
        "Setor": info.get("sector", "Outros/Internacional"),
        "Nome": info.get("longName", ticker),
        "Moeda": info.get("currency", "N/A")
    }
    return res

def calcular_score(ind, ticker):
    score = 0
    # Diferencia FIIs de Ações pela terminação (regra geral B3)
    is_fii = ticker.endswith("11.SA")
    
    # Critérios Universais
    if ind["DY"] > 6: score += 3
    if 0.1 < ind["PVP"] < 1.2: score += 3
    
    if not is_fii:
        if ind["ROE"] > 12: score += 2
        if 0 < ind["PL"] < 20: score += 2
    else:
        # FIIs ganham pontos por outros critérios implícitos aqui
        score += 4
        
    return min(score, 10)

# ==============================
# INTERFACE PRINCIPAL
# ==============================
menu = st.sidebar.selectbox("Navegação", ["📈 Analisar", "💼 Carteira"])

if menu == "📈 Analisar":
    col1, col2 = st.columns([3, 1])
    with col1:
        busca = st.text_input("Busca Universal (Ex: PETR4, MXRF11, AAPL, BTC-USD, EURBRL=X)", "PETR4")
    with col2:
        st.write("##")
        btn = st.button("🔍 Analisar Agora")

    if btn or busca:
        with st.spinner(f"Consultando mercado global por {busca}..."):
            info, hist, ticker_final = get_universal_data(busca)

            if ticker_final:
                preco_atual = hist["Close"].iloc[-1]
                ind = calcular_indicadores(info, preco_atual, ticker_final)
                score = calcular_score(ind, ticker_final)
                
                # Cabeçalho
                st.subheader(f"{ind['Nome']} | Ticker: `{ticker_final}`")
                
                # Métricas
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Preço", f"{ind['Moeda']} {preco_atual:.2f}")
                m2.metric("Div. Yield", f"{ind['DY']:.2f}%")
                m3.metric("P/L", f"{ind['PL']:.2f}")
                m4.metric("P/VP", f"{ind['PVP']:.2f}")

                # Recomendação
                if score >= 8: st.success(f"Score: {score}/10 - 🟢 Recomendação: Forte Compra")
                elif score >= 5: st.warning(f"Score: {score}/10 - 🟡 Recomendação: Observação/Neutro")
                else: st.error(f"Score: {score}/10 - 🔴 Recomendação: Evitar no momento")

                # Gráfico
                st.line_chart(hist["Close"])
                
                with st.expander("Ver dados brutos do setor"):
                    st.write(f"**Setor:** {ind['Setor']}")
                    st.write(f"**Dívida/Equity:** {ind['Divida']}")
            else:
                st.error("Ativo não encontrado. Verifique se o ticker está correto.")

# ==============================
# CARTEIRA SIMPLES
# ==============================
if menu == "💼 Carteira":
    st.subheader("Sua Lista de Monitoramento")
    
    if 'minha_carteira' not in st.session_state:
        st.session_state.minha_carteira = []

    novo_ativo = st.text_input("Adicionar Ticker à lista:")
    if st.button("Adicionar"):
        if novo_ativo:
            _, _, t_validado = get_universal_data(novo_ativo)
            if t_validado:
                st.session_state.minha_carteira.append(t_validado)
                st.rerun()
            else:
                st.error("Ativo inválido.")

    if st.session_state.minha_carteira:
        for a in list(set(st.session_state.minha_carteira)):
            st.write(f"📌 {a}")
