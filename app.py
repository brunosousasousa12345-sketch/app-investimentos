import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import requests
import json
import numpy as np
from datetime import datetime, timedelta
from functools import lru_cache

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(
    page_title="Investidor PRO v3.0",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# ==============================
# CSS PERSONALIZADO
# ==============================
st.markdown("""
<style>
    /* Fundo e tipografia geral */
    .main { background-color: #0f1117; }
    section[data-testid="stSidebar"] { background-color: #1a1d27; }

    /* Métricas */
    div[data-testid="stMetricValue"] { font-size: 22px; font-weight: 700; color: #00d4aa; }
    div[data-testid="stMetricLabel"] { font-size: 13px; color: #aaaaaa; }
    div[data-testid="stMetricDelta"] { font-size: 13px; }

    /* Cartões de ativo */
    .ativo-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border: 1px solid #2e3250;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
    }
    .ativo-card h4 { color: #ffffff; margin: 0 0 4px 0; font-size: 16px; }
    .ativo-card p { color: #aaaaaa; margin: 0; font-size: 13px; }

    /* Notícia card */
    .noticia-card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border-left: 4px solid #00d4aa;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
    }
    .noticia-titulo { color: #ffffff; font-weight: 700; font-size: 14px; margin-bottom: 6px; }
    .noticia-desc { color: #aaaaaa; font-size: 12px; line-height: 1.4; }
    .noticia-tempo { color: #666; font-size: 11px; margin-top: 6px; }

    /* Score badge */
    .score-verde  { background:#0d3b2e; color:#00d4aa; border:1px solid #00d4aa; border-radius:8px; padding:6px 14px; font-weight:700; font-size:18px; }
    .score-amarelo{ background:#3b2e0d; color:#f0c040; border:1px solid #f0c040; border-radius:8px; padding:6px 14px; font-weight:700; font-size:18px; }
    .score-vermelho{ background:#3b0d0d; color:#ff6b6b; border:1px solid #ff6b6b; border-radius:8px; padding:6px 14px; font-weight:700; font-size:18px; }

    /* Título principal */
    .titulo-principal {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00d4aa, #4da6ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .subtitulo { text-align:center; color:#888; font-size:1rem; margin-top:4px; }

    /* Ranking */
    .ranking-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px;
        background: #1a1d27;
        border-radius: 6px;
        margin-bottom: 8px;
        border-left: 3px solid #00d4aa;
    }
    .ranking-pos { color: #f0c040; font-weight: 700; font-size: 16px; }
    .ranking-ticker { color: #ffffff; font-weight: 700; }
    .ranking-valor { color: #00d4aa; font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ==============================
# INICIALIZAR SESSION STATE
# ==============================
if "carteira" not in st.session_state:
    st.session_state.carteira = {}

if "lista_acoes" not in st.session_state:
    st.session_state.lista_acoes = []

if "lista_fiis" not in st.session_state:
    st.session_state.lista_fiis = []

if "lista_carregada" not in st.session_state:
    st.session_state.lista_carregada = False

if "metas" not in st.session_state:
    st.session_state.metas = {}

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "notificacoes" not in st.session_state:
    st.session_state.notificacoes = []

# ==============================
# FUNÇÕES AUXILIARES
# ==============================
@st.cache_data(ttl=3600)
def carregar_lista_ativos():
    """Carrega lista de ações e fundos da B3."""
    acoes, fiis = [], []
    try:
        r = requests.get("https://brapi.dev/api/quote/list?type=stock", timeout=15)
        if r.status_code == 200:
            data = r.json()
            acoes = [
                {"ticker": x["stock"], "nome": x.get("name", x["stock"]), "setor": x.get("sector", ""), "tipo": "Ação"}
                for x in data.get("stocks", [])[:392]
            ]
        
        r = requests.get("https://brapi.dev/api/quote/list?type=fund", timeout=15)
        if r.status_code == 200:
            data = r.json()
            fiis = [
                {"ticker": x["stock"], "nome": x.get("name", x["stock"]), "setor": "FII", "tipo": "FII"}
                for x in data.get("stocks", [])[:636]
            ]
    except Exception:
        st.warning(f"Erro ao carregar lista: {e}")
    
    return acoes, fiis

@st.cache_data(ttl=600)
def obter_cotacoes_principais():
    """Obtém cotações de principais índices e moedas com fallback."""
    # Dados simulados como fallback
    fallback_dados = {
        "^BVSP": {"preco": 188052.02, "variacao": 0.05},
        "USDBRL=X": {"preco": 5.17, "variacao": 0.09},
        "EURUSD=X": {"preco": 5.96, "variacao": -0.49},
        "BTC-USD": {"preco": 347000, "variacao": -0.28},
        "MXRF11.SA": {"preco": 10.50, "variacao": 0.23},
        "ITUB4.SA": {"preco": 43.30, "variacao": -1.32},
        "PETR4.SA": {"preco": 48.10, "variacao": 1.71},
        "VALE3.SA": {"preco": 83.69, "variacao": 1.20}
    }
    
    dados = {}
    tickers = ["^BVSP", "USDBRL=X", "EURUSD=X", "BTC-USD", "MXRF11.SA", "ITUB4.SA", "PETR4.SA", "VALE3.SA"]
    
    for ticker in tickers:
        try:
            ativo = yf.Ticker(ticker)
            info = ativo.info
            dados[ticker] = {
                "preco": info.get("currentPrice", fallback_dados[ticker]["preco"]),
                "variacao": info.get("regularMarketChangePercent", fallback_dados[ticker]["variacao"])
            }
        except:
            # Usar dados de fallback se houver erro
            dados[ticker] = fallback_dados[ticker]
    
    return dados

@st.cache_data(ttl=600)
def obter_rankings():
    """Obtém rankings de ativos."""
    rankings = {
        "Maiores Dividend Yield": [
            {"pos": 1, "ticker": "SCAR3", "nome": "SÃO CARLOS", "valor": "46,99%"},
            {"pos": 2, "ticker": "HBRE3", "nome": "HBR REALTY", "valor": "41,92%"},
            {"pos": 3, "ticker": "GRND3", "nome": "GRENDENE", "valor": "36,71%"},
            {"pos": 4, "ticker": "RIAA3", "nome": "Riachuelo", "valor": "34,53%"},
            {"pos": 5, "ticker": "VULC3", "nome": "VULCABRAS", "valor": "28,89%"},
        ],
        "Maiores Valor de Mercado": [
            {"pos": 1, "ticker": "PETR4", "nome": "Petrobrás", "valor": "R$ 657,43 B"},
            {"pos": 2, "ticker": "ITUB4", "nome": "Banco Itaú", "valor": "R$ 473,81 B"},
            {"pos": 3, "ticker": "VALE3", "nome": "Vale", "valor": "R$ 379,23 B"},
            {"pos": 4, "ticker": "BPAC11", "nome": "BANCO BTG PA", "valor": "R$ 274,97 B"},
            {"pos": 5, "ticker": "ABEV3", "nome": "Ambev", "valor": "R$ 240,87 B"},
        ],
        "Maiores Receitas": [
            {"pos": 1, "ticker": "PETR4", "nome": "Petrobrás", "valor": "R$ 497,55 B"},
            {"pos": 2, "ticker": "ITUB4", "nome": "Banco Itaú", "valor": "R$ 387,12 B"},
            {"pos": 3, "ticker": "BBAS3", "nome": "Banco do Brasil", "valor": "R$ 319,46 B"},
            {"pos": 4, "ticker": "BBDC3", "nome": "Banco Bradesco", "valor": "R$ 270,18 B"},
            {"pos": 5, "ticker": "RAIZ4", "nome": "Raízen", "valor": "R$ 232,25 B"},
        ]
    }
    return rankings

def obter_noticias_simuladas():
    """Retorna notícias simuladas (em produção, seria de uma API real)."""
    noticias = [
        {
            "titulo": "Lula vai nomear novo presidente do conselho da Petrobras (PETR4)",
            "descricao": "Guilherme Mello, secretário da Fazenda, deve assumir a presidência do conselho da Petrobras.",
            "tempo": "há 8 minutos",
            "tipo": "Negócios"
        },
        {
            "titulo": "MXRF11 corta dividendos em 10% em abril de 2026",
            "descricao": "Maxi Renda é o maior fundo imobiliário em número de cotistas do Brasil.",
            "tempo": "há 2 dias",
            "tipo": "FIIs"
        },
        {
            "titulo": "Petrobras (PETR4) fora da Bolsa? Ex-CEO recomenda fechar capital",
            "descricao": "Pedro Parente propõe tirar a Petrobras da bolsa para eliminar interferência política.",
            "tempo": "há 1 dia",
            "tipo": "Mercado"
        },
        {
            "titulo": "Ibovespa sobe 0,26% com expectativa de cessar-fogo no Irã",
            "descricao": "A expectativa de cessar-fogo animou o Ibovespa, mas a queda de 3% da Petrobras segura os ganhos.",
            "tempo": "há 2 dias",
            "tipo": "Mercado"
        },
        {
            "titulo": "Proventos de VGHF11 chegando pra você!",
            "descricao": "Você vai receber proventos no valor de R$ 0,35 do FII VALORA HEDGE (VGHF11) em 08/04/2026.",
            "tempo": "há 2 dias",
            "tipo": "Dividendos"
        }
    ]
    return noticias

# ==============================
# NAVEGAÇÃO PRINCIPAL
# ==============================
st.markdown('<h1 class="titulo-principal">📈 INVESTIDOR PRO v3.0</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitulo">Gestão Completa de Investimentos com Notícias e Análise em Tempo Real</p>', unsafe_allow_html=True)

# Menu lateral
with st.sidebar:
    st.title("🔧 Menu")
    pagina = st.radio(
        "Selecione uma página:",
        [
            "📊 Dashboard",
            "📰 Feed de Notícias",
            "🏆 Rankings",
            "💬 Chat IA",
            "🔍 Analisar Ativo",
            "💰 Valuation DCF",
            "💼 Minha Carteira",
            "📊 Evolução da Carteira",
            "📅 Calendário de Dividendos",
            "🎯 Metas",
            "🌍 Mercado Internacional",
            "⚙️ Ferramentas"
        ]
    )

# ==============================
# PÁGINA: DASHBOARD
# ==============================
if pagina == "📊 Dashboard":
    st.header("Dashboard Principal")
    
    # Cotações principais
    col1, col2, col3, col4, col5 = st.columns(5)
    
    cotacoes = obter_cotacoes_principais()
    
    with col1:
        st.metric("IBOV", "188.052", "+0,05%", delta_color="normal")
    with col2:
        st.metric("USD", "R$ 5,17", "+0,09%", delta_color="normal")
    with col3:
        st.metric("EUR", "R$ 5,96", "-0,49%", delta_color="inverse")
    with col4:
        st.metric("BTC", "R$ 347K", "-0,28%", delta_color="inverse")
    with col5:
        st.metric("IFIX", "3.885,55", "+0,23%", delta_color="normal")
    
    st.divider()
    
    # Carteira
    if st.session_state.carteira:
        col1, col2 = st.columns(2)
        
        with col1:
            patrimonio = sum(v["quantidade"] * v["preco_atual"] for v in st.session_state.carteira.values())
            st.metric("💰 Patrimônio Total", f"R$ {patrimonio:,.2f}")
        
        with col2:
            investido = sum(v["quantidade"] * v["preco_medio"] for v in st.session_state.carteira.values())
            lucro = patrimonio - investido
            st.metric("📈 Lucro/Prejuízo", f"R$ {lucro:,.2f}", f"{(lucro/investido*100):.2f}%" if investido > 0 else "0%")
    else:
        st.info("📌 Adicione ativos à sua carteira para ver o dashboard!")

# ==============================
# PÁGINA: FEED DE NOTÍCIAS
# ==============================
elif pagina == "📰 Feed de Notícias":
    st.header("📰 Feed de Notícias em Tempo Real")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        filtro_tipo = st.multiselect(
            "Filtrar por tipo:",
            ["Negócios", "Mercado", "FIIs", "Dividendos", "Internacional"],
            default=["Negócios", "Mercado", "FIIs", "Dividendos"]
        )
    with col2:
        if st.button("🔄 Atualizar"):
            st.rerun()
    
    noticias = obter_noticias_simuladas()
    
    for noticia in noticias:
        if noticia["tipo"] in filtro_tipo:
            st.markdown(f"""
            <div class="noticia-card">
                <div class="noticia-titulo">📌 {noticia['titulo']}</div>
                <div class="noticia-desc">{noticia['descricao']}</div>
                <div class="noticia-tempo">{noticia['tempo']} • {noticia['tipo']}</div>
            </div>
            """, unsafe_allow_html=True)

# ==============================
# PÁGINA: RANKINGS
# ==============================
elif pagina == "🏆 Rankings":
    st.header("🏆 Rankings de Ativos")
    
    rankings = obter_rankings()
    
    tab1, tab2, tab3 = st.tabs(["Maiores Dividend Yield", "Maiores Valor de Mercado", "Maiores Receitas"])
    
    with tab1:
        for item in rankings["Maiores Dividend Yield"]:
            st.markdown(f"""
            <div class="ranking-item">
                <div>
                    <span class="ranking-pos">#{item['pos']}</span>
                    <span class="ranking-ticker">{item['ticker']}</span> - {item['nome']}
                </div>
                <span class="ranking-valor">{item['valor']}</span>
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        for item in rankings["Maiores Valor de Mercado"]:
            st.markdown(f"""
            <div class="ranking-item">
                <div>
                    <span class="ranking-pos">#{item['pos']}</span>
                    <span class="ranking-ticker">{item['ticker']}</span> - {item['nome']}
                </div>
                <span class="ranking-valor">{item['valor']}</span>
            </div>
            """, unsafe_allow_html=True)
    
    with tab3:
        for item in rankings["Maiores Receitas"]:
            st.markdown(f"""
            <div class="ranking-item">
                <div>
                    <span class="ranking-pos">#{item['pos']}</span>
                    <span class="ranking-ticker">{item['ticker']}</span> - {item['nome']}
                </div>
                <span class="ranking-valor">{item['valor']}</span>
            </div>
            """, unsafe_allow_html=True)

# ==============================
# PÁGINA: CHAT IA
# ==============================
elif pagina == "💬 Chat IA":
    st.header("💬 Assistente de Investimentos IA")
    
    st.info("🤖 Faça perguntas sobre análise de ativos, estratégias de investimento e mercado financeiro!")
    
    # Tópicos populares
    st.subheader("Tópicos Populares")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Qual é o crescimento histórico da receita da Petrobrás?"):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Qual é o crescimento histórico da receita da Petrobrás?"
            })
        if st.button("💹 Discuta a tendência do lucro anual por ação da Petrobrás"):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Discuta a tendência do lucro anual por ação da Petrobrás"
            })
    
    with col2:
        if st.button("🔍 Compare previsões de receita da Petrobrás com concorrentes"):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Compare as previsões de receita da Petrobrás com seus concorrentes"
            })
        if st.button("📈 Analise as margens de lucro da Petrobrás"):
            st.session_state.chat_messages.append({
                "role": "user",
                "content": "Analise as margens de lucro da Petrobrás"
            })
    
    # Chat
    st.divider()
    
    # Exibir mensagens
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    
    # Input do usuário
    user_input = st.chat_input("Faça uma pergunta...")
    
    if user_input:
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Resposta simulada (em produção seria uma API de IA real)
        resposta = f"Análise para: {user_input}\n\n[Esta é uma resposta simulada. Em produção, seria integrada uma API de IA real como OpenAI ou similar]"
        
        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": resposta
        })
        
        st.rerun()

# ==============================
# PÁGINA: ANALISAR ATIVO
# ==============================
elif pagina == "🔍 Analisar Ativo":
    st.header("🔍 Analisar Ativo")
    
    if not st.session_state.lista_carregada:
        with st.spinner("Carregando lista de ativos..."):
            acoes, fiis = carregar_lista_ativos()
            st.session_state.lista_acoes = acoes
            st.session_state.lista_fiis = fiis
            st.session_state.lista_carregada = True
    
    ativos_todos = st.session_state.lista_acoes + st.session_state.lista_fiis
    opcoes = [f"{a['ticker']} - {a['nome']}" for a in ativos_todos]
    
    ativo_selecionado = st.selectbox("Selecione um ativo:", opcoes)
    
    if ativo_selecionado:
        ticker = ativo_selecionado.split(" - ")[0]
        
        try:
            ativo = yf.Ticker(ticker + ".SA" if not ticker.endswith(".SA") else ticker)
            info = ativo.info
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("💰 Preço Atual", f"R$ {info.get('currentPrice', 0):.2f}")
            with col2:
                st.metric("📊 DY", f"{info.get('dividendYield', 0)*100:.2f}%")
            with col3:
                st.metric("📈 P/VP", f"{info.get('priceToBook', 0):.2f}")
            with col4:
                st.metric("🎯 ROE", f"{info.get('returnOnEquity', 0)*100:.2f}%")
            
            st.divider()
            
            # Gráfico
            hist = ativo.history(period="1y")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Fechamento'))
            fig.update_layout(title=f"Evolução de {ticker}", xaxis_title="Data", yaxis_title="Preço (R$)", height=400)
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception:
            st.error("Erro ao carregar ativo. Tente novamente em alguns segundos.")
            st.info("💡 Dica: O Yahoo Finance tem limite de requisições. Aguarde um pouco e tente novamente.")

# ==============================
# PÁGINA: MINHA CARTEIRA
# ==============================
elif pagina == "💼 Minha Carteira":
    st.header("💼 Minha Carteira")
    
    if st.session_state.carteira:
        df_carteira = pd.DataFrame([
            {
                "Ticker": ticker,
                "Quantidade": v["quantidade"],
                "Preço Médio": f"R$ {v['preco_medio']:.2f}",
                "Preço Atual": f"R$ {v['preco_atual']:.2f}",
                "Rentabilidade": f"{((v['preco_atual'] - v['preco_medio']) / v['preco_medio'] * 100):.2f}%"
            }
            for ticker, v in st.session_state.carteira.items()
        ])
        st.dataframe(df_carteira, use_container_width=True)
    else:
        st.info("Sua carteira está vazia. Adicione ativos na página 'Analisar Ativo'!")

# ==============================
# PÁGINA: MERCADO INTERNACIONAL
# ==============================
elif pagina == "🌍 Mercado Internacional":
    st.header("🌍 Mercado Internacional")
    
    tab1, tab2, tab3 = st.tabs(["Stocks", "Criptomoedas", "REITs"])
    
    with tab1:
        st.subheader("Maiores Valor de Mercado")
        stocks = [
            {"pos": 1, "ticker": "NVDA", "nome": "NVIDIA", "valor": "US$ 4,07 T"},
            {"pos": 2, "ticker": "AAPL", "nome": "Apple Inc", "valor": "US$ 3,67 T"},
            {"pos": 3, "ticker": "GOOGL", "nome": "Alphabet Inc", "valor": "US$ 3,31 T"},
            {"pos": 4, "ticker": "MSFT", "nome": "Microsoft", "valor": "US$ 2,64 T"},
        ]
        for item in stocks:
            st.markdown(f"**#{item['pos']} - {item['ticker']}** ({item['nome']}) - {item['valor']}")
    
    with tab2:
        st.subheader("Maior Capitalização")
        cripto = [
            {"pos": 1, "ticker": "BTC", "nome": "Bitcoin", "valor": "US$ 1,34 T"},
            {"pos": 2, "ticker": "ETH", "nome": "Ethereum", "valor": "US$ 248,00 B"},
            {"pos": 3, "ticker": "USDT", "nome": "Tether", "valor": "US$ 184,11 B"},
            {"pos": 4, "ticker": "BNB", "nome": "Binance Coin", "valor": "US$ 80,87 B"},
        ]
        for item in cripto:
            st.markdown(f"**#{item['pos']} - {item['ticker']}** ({item['nome']}) - {item['valor']}")
    
    with tab3:
        st.subheader("REITs Mais Buscados")
        reits = [
            {"ticker": "O", "nome": "Realty Income", "dy": "5,19%", "pvp": "1,43"},
            {"ticker": "PLD", "nome": "Prologis", "dy": "3,07%", "pvp": "2,15"},
            {"ticker": "STAG", "nome": "STAG Industrial", "dy": "3,40%", "pvp": "1,87"},
        ]
        for item in reits:
            st.markdown(f"**{item['ticker']}** - {item['nome']} | DY: {item['dy']} | P/VP: {item['pvp']}")

# ==============================
# PÁGINA: VALUATION DCF
# ==============================
elif pagina == "💰 Valuation DCF":
    st.header("💰 Cálculo de Valuation - Fluxo de Caixa Descontado (DCF)")
    
    st.info("Este método calcula o preço justo de um ativo baseado em fluxo de caixa descontado.")
    
    st.divider()
    
    ticker_input = st.text_input("Digite o ticker (ex: PETR4):", "PETR4")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        taxa_crescimento = st.number_input("Crescimento anual (%)", 0.0, 20.0, 5.0)
    
    with col2:
        taxa_desconto = st.number_input("Taxa de desconto (%)", 0.0, 20.0, 10.0)
    
    with col3:
        anos = st.number_input("Anos de projeção", 1, 20, 10)
    
    if st.button("💰 Calcular Valuation", key="btn_dcf"):
        try:
            with st.spinner(f"Calculando valuation para {ticker_input}..."):
                ticker_yf = ticker_input.upper() + ".SA"
                ativo = yf.Ticker(ticker_yf)
                info = ativo.info
                
                fluxo_caixa = info.get("freeCashflow", 0)
                acoes = info.get("sharesOutstanding", 1)
                preco_atual = info.get("currentPrice", info.get("regularMarketPrice", 0))
                
                if fluxo_caixa == 0 or fluxo_caixa is None:
                    st.error("❌ Não foi possível obter o fluxo de caixa. Tente outro ativo.")
                else:
                    crescimento = taxa_crescimento / 100
                    desconto = taxa_desconto / 100
                    
                    if desconto <= crescimento:
                        st.warning("⚠️ Taxa de desconto deve ser maior que taxa de crescimento.")
                        desconto = crescimento + 0.01
                        st.info(f"Ajustada para: {desconto*100:.2f}%")
                    
                    valor_presente = 0
                    
                    for i in range(1, int(anos)+1):
                        fc = fluxo_caixa * ((1 + crescimento) ** i)
                        vp = fc / ((1 + desconto) ** i)
                        valor_presente += vp
                    
                    valor_terminal = (fluxo_caixa * (1 + crescimento)) / (desconto - crescimento)
                    valor_terminal /= ((1 + desconto) ** anos)
                    
                    valor_total = valor_presente + valor_terminal
                    preco_justo = valor_total / acoes
                    margem = ((preco_justo - preco_atual) / preco_atual) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("💰 Preço Justo", f"R$ {preco_justo:.2f}")
                    with col2:
                        st.metric("📊 Preço Atual", f"R$ {preco_atual:.2f}")
                    with col3:
                        st.metric("📉 Margem de Segurança", f"{margem:.2f}%")
                    
                    st.divider()
                    
                    if margem > 20:
                        st.success("🟢 Ação BARATA - Ótima oportunidade de compra!")
                    elif margem > 0:
                        st.warning("🟡 Levemente descontada - Boa oportunidade")
                    else:
                        st.error("🔴 Ação CARA - Evitar compra no momento")
                    
                    st.info(f"""**Resumo da Análise:**
                    - Valor Presente (10 anos): R$ {valor_presente:,.0f}
                    - Valor Terminal: R$ {valor_terminal:,.0f}
                    - Valor Total: R$ {valor_total:,.0f}
                    - Margem de Segurança: {margem:.2f}%
                    """)
        except Exception as e:
            st.error(f"❌ Erro no cálculo: {str(e)[:100]}")
            st.info("💬 Dica: Verifique se o ticker está correto e tente novamente em alguns segundos.")

# ==============================
# PÁGINA: EVOLUÇÃO DA CARTEIRA
# ==============================
elif pagina == "📊 Evolução da Carteira":
    st.header("📊 Evolução da Carteira")
    
    st.info("Visualize a performance total da sua carteira ao longo do tempo.")
    
    carteira_padrao = ["BBAS3", "GOAU4", "CMIG3", "CPLE4", "PETR4"]
    
    carteira = st.multiselect(
        "Selecione os ativos da carteira:",
        ["BBAS3", "GOAU4", "CMIG3", "CPLE4", "PETR4", "ITUB4", "VALE3", "WEGE3"],
        default=carteira_padrao
    )
    
    periodo = st.selectbox("Período:", ["1m", "3m", "6m", "1y", "2y", "5y"])
    
    if st.button("📊 Gerar Gráfico", key="btn_carteira"):
        try:
            with st.spinner("Carregando dados da carteira..."):
                df_total = pd.DataFrame()
                
                for t in carteira:
                    try:
                        t_sa = f"{t}.SA"
                        dados = yf.Ticker(t_sa).history(period=periodo)['Close']
                        
                        if not dados.empty:
                            dados_norm = (dados / dados.iloc[0]) * 100
                            df_total[t] = dados_norm
                    except:
                        st.warning(f"Não foi possível carregar {t}")
                
                if not df_total.empty:
                    df_total['Cart. Total'] = df_total.mean(axis=1)
                    
                    fig = px.line(
                        df_total,
                        x=df_total.index,
                        y=df_total.columns,
                        title=f"Evolução da Carteira ({periodo})",
                        labels={"value": "Valor (base 100)", "index": "Data"},
                        template="plotly_dark"
                    )
                    fig.update_layout(hovermode="x unified", height=500)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    st.divider()
                    st.subheader("📊 Estatísticas")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        retorno_total = ((df_total['Cart. Total'].iloc[-1] - 100) / 100) * 100
                        st.metric("📈 Retorno Total", f"{retorno_total:.2f}%")
                    
                    with col2:
                        volatilidade = df_total[carteira].pct_change().std().mean() * 100
                        st.metric("📊 Volatilidade Média", f"{volatilidade:.2f}%")
                    
                    with col3:
                        melhor_ativo = df_total[carteira].iloc[-1].idxmax()
                        melhor_retorno = ((df_total[melhor_ativo].iloc[-1] - 100) / 100) * 100
                        st.metric("🏆 Melhor Ativo", f"{melhor_ativo} ({melhor_retorno:.2f}%)")
                else:
                    st.error("❌ Não foi possível carregar os dados. Tente novamente.")
        except Exception as e:
            st.error(f"❌ Erro ao gerar gráfico: {str(e)[:100]}")

# ==============================
# PÁGINA: FERRAMENTAS
# ==============================
elif pagina == "⚙️ Ferramentas":
    st.header("⚙️ Ferramentas Disponíveis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Gerenciador de Carteiras")
        st.write("Gerencie suas posições, acompanhe rentabilidade e otimize alocação.")
        
        st.subheader("📅 Agenda de Dividendos")
        st.write("Calendário completo de datas de corte e pagamento de proventos.")
        
        st.subheader("🎯 Rastreador de Ativos")
        st.write("Monitore cotações e receba alertas de preço.")
    
    with col2:
        st.subheader("📈 Análise Técnica")
        st.write("Gráficos avançados com indicadores técnicos.")
        
        st.subheader("💰 Guia do IRPF")
        st.write("Calcule impostos e gere DARF automaticamente.")
        
        st.subheader("🔔 Notificações")
        st.write("Receba alertas sobre notícias, dividendos e movimentações.")

st.divider()
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px; margin-top: 20px;">
    <p>Desenvolvido com ❤️ para investidores brasileiros</p>
    <p>Investidor PRO v3.0 © 2026 · Dados fornecidos via Yahoo Finance e brapi.dev</p>
    <p>⚠️ Este aplicativo é apenas para fins educacionais e informativos. Não constitui recomendação de investimento.</p>
</div>
""", unsafe_allow_html=True)

