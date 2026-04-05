import streamlit as st
import yfinance as yf
import pandas as pd
import sqlite3
import hashlib
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import numpy as np

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(
    page_title="Investidor PRO v4.0",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="expanded"
)

# ==============================
# CSS PERSONALIZADO
# ==============================
st.markdown("""
<style>
    .main { background-color: #0f1117; }
    section[data-testid="stSidebar"] { background-color: #1a1d27; }
    
    div[data-testid="stMetricValue"] { font-size: 22px; font-weight: 700; color: #00d4aa; }
    div[data-testid="stMetricLabel"] { font-size: 13px; color: #aaaaaa; }
    
    .card {
        background: linear-gradient(135deg, #1e2130, #252840);
        border: 1px solid #2e3250;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 10px;
    }
    
    .titulo-principal {
        text-align: center;
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00d4aa, #4da6ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    
    .score-verde { background:#0d3b2e; color:#00d4aa; border:1px solid #00d4aa; border-radius:8px; padding:6px 14px; font-weight:700; }
    .score-amarelo { background:#3b2e0d; color:#f0c040; border:1px solid #f0c040; border-radius:8px; padding:6px 14px; font-weight:700; }
    .score-vermelho { background:#3b0d0d; color:#ff6b6b; border:1px solid #ff6b6b; border-radius:8px; padding:6px 14px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

# ==============================
# BANCO DE DADOS
# ==============================
conn = sqlite3.connect("investidor_pro.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS usuarios (
    user TEXT PRIMARY KEY,
    senha TEXT,
    data_criacao TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS carteira (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    ticker TEXT,
    quantidade REAL,
    preco_medio REAL,
    data_adicao TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS metas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    nome TEXT,
    valor_alvo REAL,
    valor_atual REAL,
    data_criacao TEXT
)""")

conn.commit()

# ==============================
# FUNÇÕES DE SEGURANÇA
# ==============================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def cadastrar_usuario(usuario, senha):
    try:
        cursor.execute("INSERT INTO usuarios VALUES (?,?,?)", 
                      (usuario, hash_senha(senha), datetime.now().strftime("%d/%m/%Y %H:%M")))
        conn.commit()
        return True
    except:
        return False

def login_usuario(usuario, senha):
    cursor.execute("SELECT * FROM usuarios WHERE user=? AND senha=?", 
                  (usuario, hash_senha(senha)))
    return cursor.fetchone()

# ==============================
# FUNÇÕES DE CARTEIRA
# ==============================
def adicionar_ativo(usuario, ticker, quantidade, preco_medio):
    cursor.execute("INSERT INTO carteira VALUES (NULL,?,?,?,?,?)",
                  (usuario, ticker.upper(), quantidade, preco_medio, 
                   datetime.now().strftime("%d/%m/%Y")))
    conn.commit()

def obter_carteira(usuario):
    cursor.execute("SELECT ticker, quantidade, preco_medio FROM carteira WHERE user=?", (usuario,))
    return cursor.fetchall()

def remover_ativo(usuario, ticker):
    cursor.execute("DELETE FROM carteira WHERE user=? AND ticker=?", (usuario, ticker.upper()))
    conn.commit()

# ==============================
# FUNÇÕES DE CLASSIFICAÇÃO DE FIIs
# ==============================
def tipo_fii(nome):
    """Classifica o tipo de FII baseado no nome."""
    nome = nome.lower()
    
    if "log" in nome:
        return "Logística"
    elif "shop" in nome:
        return "Shopping"
    elif "receb" in nome or "cri" in nome:
        return "Papel"
    elif "office" in nome or "corp" in nome:
        return "Escritório"
    else:
        return "Outros"

def renda_mensal_estimada(carteira_fiis):
    """Calcula renda mensal estimada de uma carteira de FIIs."""
    total_renda = 0
    for ticker in carteira_fiis:
        dados = analisar_ativo(ticker)
        if "Erro" not in dados:
            # Simulação: DY anual / 12 meses * 1000 reais investidos
            renda_mensal = (dados["DY"] / 100 / 12) * 1000
            total_renda += renda_mensal
    
    return round(total_renda, 2)

def montar_carteira_fii(perfil):
    """Monta carteira específica de FIIs por perfil."""
    ativos = ["HGLG11", "MXRF11", "XPML11", "VILG11", "KNRI11", "KNCR11", "KNIP11"]
    carteira = []
    
    for ticker in ativos:
        dados = analisar_ativo(ticker)
        if "Erro" not in dados:
            if perfil == "Conservador":
                if dados["DY"] > 7 and tipo_fii(dados["Nome"]) == "Papel":
                    carteira.append(ticker)
            
            elif perfil == "Moderado":
                if dados["DY"] > 6:
                    carteira.append(ticker)
            
            elif perfil == "Agressivo":
                if dados["Potencial"] > 15:
                    carteira.append(ticker)
    
    return carteira[:5]

# ==============================
# FUNÇÕES DE ANÁLISE
# ==============================
@st.cache_data(ttl=600)
def analisar_ativo(ticker):
    """Análise completa de um ativo."""
    try:
        if not ticker.endswith(".SA"):
            ticker += ".SA"
        
        ativo = yf.Ticker(ticker)
        info = ativo.info or {}
        
        # Extrair dados
        dy_raw = info.get("dividendYield", 0)
        dy = dy_raw * 100 if dy_raw and dy_raw < 1 else dy_raw or 0
        
        roe = (info.get("returnOnEquity", 0) or 0) * 100
        pvp = info.get("priceToBook", 0) or 0
        divida = info.get("debtToEquity", 0) or 0
        
        lpa = info.get("trailingEps", 0) or 0
        vpa = info.get("bookValue", 0) or 0
        preco = info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0
        
        # Preço justo (Método Graham)
        pj = (22.5 * lpa * vpa) ** 0.5 if lpa > 0 and vpa > 0 else 0
        potencial = ((pj / preco) - 1) * 100 if pj and preco else 0
        
        # Score
        score = 0
        if dy > 6: score += 1
        if roe > 15: score += 2
        if pvp and pvp < 1.2: score += 2
        if divida and divida < 100: score += 1
        if potencial > 20: score += 2
        
        status = "🟢 BOM" if score >= 6 else "🟡 MÉDIO" if score >= 3 else "🔴 RUIM"
        
        return {
            "Ticker": ticker.replace(".SA", ""),
            "Nome": info.get("shortName", ""),
            "Setor": info.get("sector", ""),
            "Preço": preco,
            "DY": round(dy, 2),
            "PVP": pvp,
            "ROE": roe,
            "Divida": divida,
            "Preço Justo": round(pj, 2),
            "Potencial": round(potencial, 2),
            "Status": status,
            "Score": score,
            "Tipo": tipo_fii(info.get("longName", ""))
        }
    except Exception as e:
        return {"Erro": str(e)}

# ==============================
# FUNÇÕES DE RECOMENDAÇÃO IA
# ==============================
def recomendacao_ia(dados):
    """Recomendação automática baseada em análise."""
    if "Erro" in dados:
        return "⚠️ Dados indisponíveis"
    
    if dados["Status"] == "🟢 BOM":
        return "🔥 FORTE COMPRA"
    elif dados["Status"] == "🟡 MÉDIO":
        return "⚠️ ANALISAR"
    else:
        return "❌ EVITAR"

# ==============================
# MONTAGEM AUTOMÁTICA DE CARTEIRA
# ==============================
def montar_carteira_ia(perfil):
    """Monta carteira automática baseada no perfil do investidor."""
    base = ["BBAS3", "PETR4", "VALE3", "ITUB4", "BBDC4", "MXRF11", "HGLG11", "XPML11", "KNCR11", "KNIP11"]
    
    selecionados = []
    
    for ticker in base:
        dados = analisar_ativo(ticker)
        if "Erro" not in dados:
            if perfil == "Conservador":
                if dados["DY"] > 7 and dados["Status"] != "🔴 RUIM":
                    selecionados.append(ticker)
            
            elif perfil == "Moderado":
                if dados["Status"] != "🔴 RUIM":
                    selecionados.append(ticker)
            
            elif perfil == "Agressivo":
                if dados["Potencial"] > 15:
                    selecionados.append(ticker)
    
    return selecionados[:5]

# ==============================
# RANKING DE ATIVOS
# ==============================
def gerar_ranking():
    """Gera ranking de ativos com scoring."""
    lista = ["BBAS3", "PETR4", "VALE3", "ITUB4", "MXRF11", "HGLG11", "KNCR11", "KNIP11"]
    dados = []
    
    for ticker in lista:
        d = analisar_ativo(ticker)
        if "Erro" not in d:
            dados.append({
                "Ativo": ticker,
                "Score": d["Score"],
                "DY": d["DY"],
                "P/VP": d["PVP"],
                "ROE": d["ROE"],
                "Status": d["Status"]
            })
    
    return pd.DataFrame(dados).sort_values("Score", ascending=False)

# ==============================
# INICIALIZAR SESSION STATE
# ==============================
if "usuario" not in st.session_state:
    st.session_state.usuario = None

if "pagina" not in st.session_state:
    st.session_state.pagina = "Dashboard"

# ==============================
# TELA DE LOGIN/CADASTRO
# ==============================
if not st.session_state.usuario:
    st.markdown('<h1 class="titulo-principal">📈 INVESTIDOR PRO v4.0</h1>', unsafe_allow_html=True)
    st.markdown('<p style="text-align:center; color:#888;">Sistema Inteligente de Gestão de Investimentos</p>', unsafe_allow_html=True)
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        modo = st.radio("Escolha uma opção:", ["Login", "Cadastrar"], horizontal=True)
        
        usuario = st.text_input("👤 Usuário")
        senha = st.text_input("🔐 Senha", type="password")
        
        if modo == "Cadastrar":
            if st.button("✅ Criar Conta", use_container_width=True):
                if usuario and senha:
                    if cadastrar_usuario(usuario, senha):
                        st.success("✅ Conta criada com sucesso! Faça login agora.")
                    else:
                        st.error("❌ Usuário já existe!")
                else:
                    st.warning("⚠️ Preencha todos os campos!")
        else:
            if st.button("🔓 Entrar", use_container_width=True):
                if login_usuario(usuario, senha):
                    st.session_state.usuario = usuario
                    st.success(f"✅ Bem-vindo, {usuario}!")
                    st.rerun()
                else:
                    st.error("❌ Usuário ou senha incorretos!")

# ==============================
# APP PRINCIPAL
# ==============================
else:
    st.markdown('<h1 class="titulo-principal">📈 INVESTIDOR PRO v4.0</h1>', unsafe_allow_html=True)
    
    # Logout
    col1, col2 = st.columns([10, 1])
    with col2:
        if st.button("🚪 Sair"):
            st.session_state.usuario = None
            st.rerun()
    
    st.markdown(f"**Usuário:** {st.session_state.usuario}", unsafe_allow_html=True)
    
    st.divider()
    
    # Menu
    with st.sidebar:
        st.title("🔧 Menu")
        pagina = st.radio(
            "Selecione:",
            [
                "📊 Dashboard",
                "🔍 Analisar Ativo",
                "💼 Minha Carteira",
                "💰 Valuation DCF",
                "🤖 IA - Recomendações",
                "🎯 Montar Carteira IA",
                "🏆 Ranking",
                "📅 Metas",
                "⚙️ Configurações"
            ]
        )
    
    # ==============================
    # PÁGINA: DASHBOARD
    # ==============================
    if pagina == "📊 Dashboard":
        st.header("📊 Dashboard")
        
        carteira = obter_carteira(st.session_state.usuario)
        
        if carteira:
            patrimonio_total = 0
            investido_total = 0
            
            for ticker, qtd, preco_medio in carteira:
                try:
                    ativo = yf.Ticker(ticker + ".SA")
                    preco_atual = ativo.info.get("currentPrice", preco_medio)
                    patrimonio_total += qtd * preco_atual
                    investido_total += qtd * preco_medio
                except:
                    patrimonio_total += qtd * preco_medio
                    investido_total += qtd * preco_medio
            
            lucro = patrimonio_total - investido_total
            rentabilidade = (lucro / investido_total * 100) if investido_total > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💰 Patrimônio Total", f"R$ {patrimonio_total:,.2f}")
            with col2:
                st.metric("📈 Lucro/Prejuízo", f"R$ {lucro:,.2f}", f"{rentabilidade:.2f}%")
            with col3:
                st.metric("📊 Investido", f"R$ {investido_total:,.2f}")
            
            st.divider()
            
            st.subheader("📋 Seus Ativos")
            for ticker, qtd, preco_medio in carteira:
                try:
                    ativo = yf.Ticker(ticker + ".SA")
                    preco_atual = ativo.info.get("currentPrice", preco_medio)
                    valor_total = qtd * preco_atual
                    rentab = ((preco_atual - preco_medio) / preco_medio * 100)
                    
                    st.markdown(f"""
                    <div class="card">
                        <b>{ticker}</b> | Qtd: {qtd} | Preço: R$ {preco_atual:.2f} | Total: R$ {valor_total:,.2f} | Rentabilidade: {rentab:.2f}%
                    </div>
                    """, unsafe_allow_html=True)
                except:
                    pass
        else:
            st.info("📌 Sua carteira está vazia. Adicione ativos!")
    
    # ==============================
    # PÁGINA: ANALISAR ATIVO
    # ==============================
    elif pagina == "🔍 Analisar Ativo":
        st.header("🔍 Analisar Ativo")
        
        ticker = st.text_input("Digite o ticker (ex: PETR4):")
        
        if ticker:
            dados = analisar_ativo(ticker)
            
            if "Erro" in dados:
                st.error(f"❌ {dados['Erro']}")
            else:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("💰 Preço", f"R$ {dados['Preço']:.2f}")
                with col2:
                    st.metric("📊 DY", f"{dados['DY']:.2f}%")
                with col3:
                    st.metric("📈 P/VP", f"{dados['PVP']:.2f}")
                with col4:
                    st.metric("🎯 ROE", f"{dados['ROE']:.2f}%")
                
                st.divider()
                
                st.markdown(f"**Preço Justo (Graham):** R$ {dados['Preço Justo']:.2f}")
                st.markdown(f"**Potencial:** {dados['Potencial']:.2f}%")
                st.markdown(f"**Status:** {dados['Status']}")
                
                st.divider()
                
                st.markdown(f"### 🤖 Recomendação: {recomendacao_ia(dados)}")
                
                if st.button("➕ Adicionar à Carteira"):
                    qtd = st.number_input("Quantidade:", 1)
                    preco_medio = st.number_input("Preço Médio:", dados['Preço'])
                    
                    if st.button("✅ Confirmar"):
                        adicionar_ativo(st.session_state.usuario, ticker, qtd, preco_medio)
                        st.success("✅ Ativo adicionado à carteira!")
    
    # ==============================
    # PÁGINA: MINHA CARTEIRA
    # ==============================
    elif pagina == "💼 Minha Carteira":
        st.header("💼 Minha Carteira")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("➕ Adicionar Ativo")
            ticker = st.text_input("Ticker:")
            qtd = st.number_input("Quantidade:", 1)
            preco = st.number_input("Preço Médio:", 0.0)
            
            if st.button("Adicionar"):
                adicionar_ativo(st.session_state.usuario, ticker, qtd, preco)
                st.success("✅ Ativo adicionado!")
        
        with col2:
            st.subheader("📋 Seus Ativos")
            carteira = obter_carteira(st.session_state.usuario)
            
            if carteira:
                for ticker, qtd, preco_medio in carteira:
                    col_ticker, col_remove = st.columns([4, 1])
                    with col_ticker:
                        st.write(f"{ticker} - {qtd} cotas @ R$ {preco_medio:.2f}")
                    with col_remove:
                        if st.button("❌", key=ticker):
                            remover_ativo(st.session_state.usuario, ticker)
                            st.rerun()
            else:
                st.info("Carteira vazia")
    
    # ==============================
    # PÁGINA: VALUATION DCF
    # ==============================
    elif pagina == "💰 Valuation DCF":
        st.header("💰 Valuation - Fluxo de Caixa Descontado")
        
        ticker = st.text_input("Ticker:", "PETR4")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            crescimento = st.number_input("Crescimento (%)", 0.0, 20.0, 5.0)
        with col2:
            desconto = st.number_input("Taxa de Desconto (%)", 0.0, 20.0, 10.0)
        with col3:
            anos = st.number_input("Anos:", 1, 20, 10)
        
        if st.button("Calcular"):
            try:
                ativo = yf.Ticker(ticker + ".SA")
                info = ativo.info
                
                fc = info.get("freeCashflow", 0)
                acoes = info.get("sharesOutstanding", 1)
                preco = info.get("currentPrice", 0)
                
                if fc and fc > 0:
                    cresc = crescimento / 100
                    desc = desconto / 100
                    
                    if desc <= cresc:
                        desc = cresc + 0.01
                    
                    vp = 0
                    for i in range(1, int(anos) + 1):
                        fc_proj = fc * ((1 + cresc) ** i)
                        vp += fc_proj / ((1 + desc) ** i)
                    
                    vt = (fc * (1 + cresc)) / (desc - cresc)
                    vt /= ((1 + desc) ** anos)
                    
                    valor_total = vp + vt
                    pj = valor_total / acoes
                    margem = ((pj - preco) / preco) * 100
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Preço Justo", f"R$ {pj:.2f}")
                    with col2:
                        st.metric("Preço Atual", f"R$ {preco:.2f}")
                    with col3:
                        st.metric("Margem", f"{margem:.2f}%")
                    
                    if margem > 20:
                        st.success("🟢 BARATA!")
                    elif margem > 0:
                        st.warning("🟡 Levemente descontada")
                    else:
                        st.error("🔴 CARA")
                else:
                    st.error("Dados não disponíveis")
            except Exception as e:
                st.error(f"Erro: {e}")
    
    # ==============================
    # PÁGINA: IA - RECOMENDAÇÕES
    # ==============================
    elif pagina == "🤖 IA - Recomendações":
        st.header("🤖 Recomendações Inteligentes")
        
        ticker = st.text_input("Ticker para análise:")
        
        if ticker:
            dados = analisar_ativo(ticker)
            
            if "Erro" not in dados:
                st.markdown(f"### {dados['Ticker']} - {dados['Status']}")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("DY", f"{dados['DY']:.2f}%")
                with col2:
                    st.metric("P/VP", f"{dados['PVP']:.2f}")
                with col3:
                    st.metric("ROE", f"{dados['ROE']:.2f}%")
                with col4:
                    st.metric("Score", dados['Score'])
                
                st.divider()
                st.markdown(f"### 🔥 Recomendação: {recomendacao_ia(dados)}")
    
    # ==============================
    # PÁGINA: MONTAR CARTEIRA IA
    # ==============================
    elif pagina == "🎯 Montar Carteira IA":
        st.header("🎯 Montar Carteira Automática")
        
        perfil = st.selectbox("Seu Perfil de Investidor:", 
                             ["Conservador", "Moderado", "Agressivo"])
        
        if st.button("🤖 Gerar Carteira"):
            with st.spinner("Analisando ativos..."):
                carteira = montar_carteira_ia(perfil)
                
                st.subheader("📊 Carteira Sugerida")
                for ativo in carteira:
                    st.markdown(f"✅ **{ativo}**")
    
    # ==============================
    # PÁGINA: RANKING
    # ==============================
    elif pagina == "🏆 Ranking":
        st.header("🏆 Ranking de Ativos")
        
        if st.button("Atualizar Ranking"):
            with st.spinner("Gerando ranking..."):
                ranking = gerar_ranking()
                st.dataframe(ranking, use_container_width=True)
    
    # ==============================
    # PÁGINA: CONFIGURAÇÕES
    # ==============================
    elif pagina == "⚙️ Configurações":
        st.header("⚙️ Configurações")
        
        st.subheader("👤 Perfil")
        st.write(f"**Usuário:** {st.session_state.usuario}")
        st.write(f"**Data de Login:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        st.divider()
        
        if st.button("🚪 Fazer Logout"):
            st.session_state.usuario = None
            st.rerun()


    # ==============================
    # PÁGINA: FIIs
    # ==============================
    elif pagina == "🏢 FIIs":
        st.header("🏢 Análise de Fundos Imobiliários (FIIs)")
        
        ticker = st.text_input("Digite o ticker do FII (ex: MXRF11):")
        
        if ticker:
            dados = analisar_ativo(ticker)
            
            if "Erro" not in dados:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("💰 Preço", f"R$ {dados['Preço']:.2f}")
                with col2:
                    st.metric("📊 DY", f"{dados['DY']:.2f}%")
                with col3:
                    st.metric("🏢 Tipo", dados['Tipo'])
                
                st.divider()
                
                st.markdown(f"""
                <div class="card">
                    <b>Nome:</b> {dados['Nome']}<br>
                    <b>Tipo:</b> {dados['Tipo']}<br>
                    <b>Setor:</b> {dados['Setor']}<br>
                    <b>P/VP:</b> {dados['PVP']:.2f}<br>
                    <b>Potencial:</b> {dados['Potencial']:.2f}%
                </div>
                """, unsafe_allow_html=True)
                
                st.divider()
                
                if st.button("➕ Adicionar à Carteira"):
                    qtd = st.number_input("Quantidade:", 1)
                    preco_medio = st.number_input("Preço Médio:", dados['Preço'])
                    
                    if st.button("✅ Confirmar"):
                        adicionar_ativo(st.session_state.usuario, ticker, qtd, preco_medio)
                        st.success("✅ FII adicionado à carteira!")
    
    # ==============================
    # PÁGINA: MONTAR CARTEIRA FII
    # ==============================
    elif pagina == "🎯 Montar Carteira FII":
        st.header("🎯 Montar Carteira de FIIs")
        
        perfil = st.selectbox("Seu Perfil de Investidor:", 
                             ["Conservador", "Moderado", "Agressivo"])
        
        if st.button("🤖 Gerar Carteira FII"):
            with st.spinner("Analisando FIIs..."):
                carteira_fii = montar_carteira_fii(perfil)
                
                if carteira_fii:
                    st.subheader("📊 Carteira de FIIs Sugerida")
                    
                    for fii in carteira_fii:
                        dados = analisar_ativo(fii)
                        if "Erro" not in dados:
                            st.markdown(f"""
                            <div class="card">
                                ✅ <b>{fii}</b> - {dados['Nome']}<br>
                                🏢 Tipo: {dados['Tipo']} | DY: {dados['DY']}%
                            </div>
                            """, unsafe_allow_html=True)
                    
                    st.divider()
                    
                    renda = renda_mensal_estimada(carteira_fii)
                    st.metric("💰 Renda Mensal Estimada", f"R$ {renda:.2f}", 
                             "(Simulação com R$ 1.000 por FII)")
                else:
                    st.warning("⚠️ Nenhum FII encontrado para este perfil.")


    st.divider()
st.markdown("""
<div style="text-align: center; color: #888; font-size: 12px; margin-top: 20px;">
    <p>Investidor PRO v4.0 © 2026 · Com Autenticação e IA</p>
    <p>⚠️ Apenas para fins educacionais</p>
</div>
""", unsafe_allow_html=True)
