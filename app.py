import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import sqlite3

st.set_page_config(page_title="Investidor PRO", layout="wide")

# =========================
# 🗄️ BANCO DE DADOS
# =========================
conn = sqlite3.connect("banco.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    username TEXT,
    password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS carteira (
    username TEXT,
    ticker TEXT,
    valor REAL
)
""")

conn.commit()

# =========================
# 🔐 FUNÇÕES
# =========================
def cadastrar(user, senha):
    cursor.execute("INSERT INTO usuarios VALUES (?, ?)", (user, senha))
    conn.commit()

def login(user, senha):
    cursor.execute("SELECT * FROM usuarios WHERE username=? AND password=?", (user, senha))
    return cursor.fetchone()

def salvar_ativo(user, ticker, valor):
    cursor.execute("INSERT INTO carteira VALUES (?, ?, ?)", (user, ticker, valor))
    conn.commit()

def carregar_carteira(user):
    cursor.execute("SELECT ticker, valor FROM carteira WHERE username=?", (user,))
    return cursor.fetchall()

def limpar_carteira(user):
    cursor.execute("DELETE FROM carteira WHERE username=?", (user,))
    conn.commit()

# =========================
# 🎨 VISUAL
# =========================
st.markdown("""
<style>
body { background-color: #0E1117; }
div[data-testid="stMetric"] {
    background-color: #1E222A;
    padding: 15px;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 🔐 LOGIN
# =========================
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login - Investidor PRO")

    aba_login, aba_cadastro = st.tabs(["Entrar", "Cadastrar"])

    with aba_login:
        user = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")

        if st.button("Entrar"):
            if login(user, senha):
                st.session_state.logado = True
                st.session_state.user = user
                st.success("Login realizado!")
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")

    with aba_cadastro:
        new_user = st.text_input("Novo usuário")
        new_pass = st.text_input("Nova senha", type="password")

        if st.button("Cadastrar"):
            cadastrar(new_user, new_pass)
            st.success("Cadastro realizado!")

    st.stop()

# =========================
# 🚪 LOGADO
# =========================
st.title(f"📈 Investidor PRO | {st.session_state.user}")

if st.button("Sair"):
    st.session_state.logado = False
    st.rerun()

ticker = st.sidebar.text_input("Ticker", "BBAS3").upper()
if not ticker.endswith(".SA"):
    ticker += ".SA"

aba1, aba2, aba3 = st.tabs(["📊 Análise", "💼 Carteira", "💰 Dividendos"])

# =========================
# 📊 ANÁLISE
# =========================
with aba1:
    try:
        acao = yf.Ticker(ticker)
        hist = acao.history(period="1y")
        info = acao.info or {}

        preco = hist['Close'].iloc[-1] if not hist.empty else 0
        roe = (info.get('returnOnEquity') or 0) * 100

        dy_raw = info.get('dividendYield')
        dy = dy_raw * 100 if dy_raw and dy_raw < 1 else dy_raw or 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Preço", f"R$ {preco:.2f}")
        c2.metric("DY", f"{dy:.2f}%")
        c3.metric("ROE", f"{roe:.2f}%")

        fig = px.line(hist, x=hist.index, y="Close")
        st.plotly_chart(fig, use_container_width=True)

    except:
        st.error("Erro ao carregar dados")

# =========================
# 💼 CARTEIRA
# =========================
with aba2:
    st.subheader("💼 Minha Carteira")

    col1, col2, col3 = st.columns(3)

    with col1:
        novo = st.text_input("Ticker").upper()

    with col2:
        valor = st.number_input("Valor investido", min_value=0.0)

    with col3:
        if st.button("Adicionar"):
            salvar_ativo(st.session_state.user, novo, valor)
            st.success("Adicionado!")

    carteira = carregar_carteira(st.session_state.user)

    total_investido = 0
    total_atual = 0
    dados = []

    for t, valor in carteira:
        if not t.endswith(".SA"):
            t += ".SA"

        acao = yf.Ticker(t)
        hist = acao.history(period="1d")

        preco = hist['Close'].iloc[-1] if not hist.empty else 0

        cotas = valor / preco if preco > 0 else 0
        atual = cotas * preco
        lucro = atual - valor

        total_investido += valor
        total_atual += atual

        dados.append({
            "Ticker": t,
            "Investido": valor,
            "Atual": atual,
            "Lucro": lucro
        })

    if dados:
        df = pd.DataFrame(dados)
        st.dataframe(df, use_container_width=True)

        lucro_total = total_atual - total_investido

        c1, c2, c3 = st.columns(3)
        c1.metric("Investido", f"R$ {total_investido:.2f}")
        c2.metric("Atual", f"R$ {total_atual:.2f}")
        c3.metric("Lucro", f"R$ {lucro_total:.2f}")

        # GRÁFICO
        df_total = pd.DataFrame()

        for t, _ in carteira:
            if not t.endswith(".SA"):
                t += ".SA"

            hist = yf.Ticker(t).history(period="1y")['Close']
            if not hist.empty:
                df_total[t] = hist

        if not df_total.empty:
            df_total["Total"] = df_total.sum(axis=1)
            fig = px.line(df_total, x=df_total.index, y="Total")
            st.plotly_chart(fig, use_container_width=True)

    if st.button("🗑️ Limpar Carteira"):
        limpar_carteira(st.session_state.user)
        st.warning("Carteira apagada!")

# =========================
# 💰 DIVIDENDOS
# =========================
with aba3:
    st.subheader("💰 Dividendos")

    carteira = carregar_carteira(st.session_state.user)
    total = 0

    for t, valor in carteira:
        if not t.endswith(".SA"):
            t += ".SA"

        info = yf.Ticker(t).info or {}
        dy_raw = info.get("dividendYield")

        dy = dy_raw if dy_raw and dy_raw < 1 else (dy_raw or 0) / 100
        dividendos = valor * dy

        total += dividendos
        st.write(f"{t}: R$ {dividendos:.2f}/ano")

    st.success(f"Total anual: R$ {total:.2f}")
