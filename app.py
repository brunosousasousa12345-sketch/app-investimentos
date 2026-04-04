import streamlit as st
import yfinance as yf
import pandas as pd

# ==============================
# 1. CONFIGURAÇÃO DE INTERFACE (UI)
# ==============================
st.set_page_config(page_title="Investidor PRO | Universal", layout="wide", page_icon="📈")

# Estilização CSS para cartões e métricas
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #1E3A8A; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; }
    .status-box { padding: 20px; border-radius: 10px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='text-align:center;'>🚀 Investidor PRO</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;'>Análise Universal de Ações e FIIs</p>", unsafe_allow_html=True)

# ==============================
# 2. MOTOR DE BUSCA E TRATAMENTO DE DADOS
# ==============================
@st.cache_data(ttl=600)
def buscar_ativo_universal(ticker_input):
    ticker = ticker_input.upper().strip()
    # Tenta B3 primeiro (.SA), depois Global
    tentativas = [f"{ticker}.SA", ticker]
    
    for t in tentativas:
        try:
            ativo = yf.Ticker(t)
            hist = ativo.history(period="1y")
            if not hist.empty:
                # Retorna info, histórico e o ticker que funcionou
                return ativo.info, hist, t
        except:
            continue
    return None, None, None

def extrair_metricas(info, preco, ticker_final):
    # O Yahoo Finance muda as chaves entre Ações e FIIs. Esta lógica padroniza:
    dados = {
        "nome": info.get('longName', ticker_final),
        "setor": info.get('sector') or info.get('industry') or "Fundo Imobiliário / Internacional",
        "moeda": info.get('currency', 'BRL'),
        # Busca Dividend Yield em múltiplas chaves possíveis
        "dy": (info.get('dividendYield') or info.get('yield') or info.get('trailingAnnualDividendYield') or 0) * 100,
        # Cálculo manual de P/VP para evitar N/A
        "pvp": preco / info.get('bookValue', 1) if info.get('bookValue') else 0,
        "pl": info.get('trailingPE') or 0,
        "roe": (info.get('returnOnEquity') or 0) * 100,
        "resumo": info.get('longBusinessSummary', 'Descrição não disponível.')
    }
    return dados

# ==============================
# 3. LÓGICA DE PONTUAÇÃO (SCORE)
# ==============================
def calcular_score_pro(m, ticker):
    score = 0
    # Verifica se é FII (Geralmente termina em 11 na B3)
    is_fii = ticker.endswith("11.SA")
    
    # Critérios de Dividendos
    if m['dy'] > 8: score += 4
    elif m['dy'] > 5: score += 2
    
    # Critérios de Preço (P/VP)
    if 0.8 <= m['pvp'] <= 1.1: score += 3
    elif m['pvp'] < 1.3: score += 1
    
    # Critérios de Eficiência (Apenas para Ações)
    if not is_fii:
        if m['roe'] > 15: score += 3
        if 0 < m['pl'] < 15: score += 1
    else:
        # Bônus para FIIs (Compensa a falta de ROE/PL nos dados)
        score += 3
        
    return min(score, 10)

# ==============================
# 4. INTERFACE PRINCIPAL
# ==============================
with st.container():
    busca = st.text_input("Busca Universal: Digite o código do ativo (Ex: MXRF11, PETR4, AAPL, BTC-USD):", "MXRF11")
    btn_analisar = st.button("🔍 Analisar Agora")

if busca or btn_analisar:
    with st.spinner(f"Consultando dados de {busca}..."):
        info, hist, ticker_confirmado = buscar_ativo_universal(busca)

    if ticker_confirmado:
        # Processamento
        preco_atual = hist["Close"].iloc[-1]
        m = extrair_metricas(info, preco_atual, ticker_confirmado)
        score = calcular_score_pro(m, ticker_confirmado)
        
        # Exibição de Resultados
        st.markdown(f"## {m['nome']} (`{ticker_confirmado}`)")
        
        col1, col2, col3, col4 = st.columns(4)
        prefixo = "$" if m['moeda'] != 'BRL' else "R$"
        
        col1.metric("Preço Atual", f"{prefixo} {preco_atual:.2f}")
        col2.metric("Dividend Yield", f"{m['dy']:.2f}%")
        col3.metric("P/VP", f"{m['pvp']:.2f}")
        col4.metric("P/L", f"{m['pl']:.2f}" if m['pl'] > 0 else "N/A")

        # Recomendação Visual baseada no Score
        st.markdown("---")
        if score >= 7:
            st.success(f"### Score Investidor PRO: {score}/10 — 🟢 FORTE COMPRA")
        elif score >= 5:
            st.warning(f"### Score Investidor PRO: {score}/10 — 🟡 NEUTRO / OBSERVAÇÃO")
        else:
            st.error(f"### Score Investidor PRO: {score}/10 — 🔴 EVITAR NO MOMENTO")

        # Gráfico e Detalhes
        tab_grafico, tab_info = st.tabs(["📈 Histórico de Preços", "📖 Sobre a Empresa/Fundo"])
        
        with tab_grafico:
            st.line_chart(hist["Close"])
            
        with tab_info:
            st.write(f"**Setor:** {m['setor']}")
            st.write(f"**Moeda de Negociação:** {m['moeda']}")
            st.info(m['resumo'])
    else:
        st.error(f"❌ Não foi possível encontrar o ativo '{busca}'. Verifique o ticker e tente novamente.")

# Rodapé
st.markdown("---")
st.caption("Investidor PRO © 2026 - Dados fornecidos via Yahoo Finance API.")
