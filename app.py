import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import sqlite3

st.set_page_config(page_title="Investidor PRO", layout="wide")

# =========================
# 🗄️ BANCO
# =========================
conn = sqlite3.connect("banco.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS usuarios (user TEXT, senha TEXT)""")
cursor.execute("""CREATE TABLE IF NOT EXISTS carteira (user TEXT, ticker TEXT, valor REAL)""")
conn.commit()

# =========================
# 🔐 FUNÇÕES
# =========================
def cadastrar(u, s):
    cursor.execute("INSERT INTO usuarios VALUES (?, ?)", (u, s))
    conn.commit()

def login(u, s):
    cursor.execute("SELECT * FROM usuarios WHERE user=? AND senha=?", (u, s))
    return cursor.fetchone()

def add_ativo(u, t, v):
    cursor.execute("INSERT INTO carteira VALUES (?, ?, ?)", (u, t, v))
    conn.commit()

def get_carteira(u):
    cursor.execute("SELECT ticker, valor FROM carteira WHERE user=?", (u,))
    return cursor.fetchall()

def limpar(u):
    cursor.execute("DELETE FROM carteira WHERE user=?", (u,))
    conn.commit()

# =========================
# 🔐 LOGIN
# =========================
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🔐 Login")

    aba1, aba2 = st.tabs(["Entrar", "Cadastrar"])

    with aba1:
        u = st.text_input("Usuário")
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if login(u, s):
                st.session_state.logado = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Erro no login")

    with aba2:
        nu = st.text_input("Novo usuário")
        ns = st.text_input("Nova senha", type="password")
        if st.button("Cadastrar"):
            cadastrar(nu, ns)
            st.success("Cadastrado!")

    st.stop()

# =========================
# 🚪 APP
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
# 📊 ANÁLISE (AÇÃO + FII)
# =========================
with aba1:
    try:
        acao = yf.Ticker(ticker)
        hist = acao.history(period="1y")
        info = acao.info or {}

        preco = hist['Close'].iloc[-1] if not hist.empty else 0
        tipo = info.get("quoteType", "")

        st.subheader("📊 Dados")

        dy_raw = info.get("dividendYield")
        dy = dy_raw * 100 if dy_raw and dy_raw < 1 else dy_raw or 0

        score = 0

        if tipo == "EQUITY":
            st.write("📈 Ação")

            roe = (info.get("returnOnEquity") or 0) * 100
            pl = info.get("trailingPE") or 0
            divida = info.get("debtToEquity") or 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço", f"R$ {preco:.2f}")
            c2.metric("DY", f"{dy:.2f}%")
            c3.metric("ROE", f"{roe:.2f}%")
            c4.metric("P/L", f"{pl:.2f}")

            if roe > 20: score += 2
            elif roe > 10: score += 1

            if dy > 8: score += 2
            elif dy > 4: score += 1

            if divida < 0.5: score += 2
            elif divida < 1: score += 1

        else:
            st.write("🏢 Fundo Imobiliário")

            pvp = info.get("priceToBook") or 0
            div_mensal = (preco * (dy / 100)) / 12 if dy > 0 else 0

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Preço", f"R$ {preco:.2f}")
            c2.metric("DY", f"{dy:.2f}%")
            c3.metric("P/VP", f"{pvp:.2f}")
            c4.metric("Div/Mês", f"R$ {div_mensal:.2f}")

            if dy > 10: score += 2
            elif dy > 7: score += 1

            if 0.8 < pvp < 1.2:
                score += 2
            elif pvp < 0.8:
                score += 1

        # GRÁFICO
        fig = px.line(hist, x=hist.index, y="Close")
        st.plotly_chart(fig, use_container_width=True)

        # RESULTADO FINAL
        st.subheader("🧠 Avaliação")

        if score >= 5:
            st.success("🟢 BOA | 💰 APORTAR")
        elif score >= 3:
            st.warning("🟡 MÉDIA | 🤔 ANALISAR")
        else:
            st.error("🔴 FRACA | ❌ NÃO APORTAR")

    except:
        st.error("Erro ao carregar")

# =========================
# 💼 CARTEIRA
# =========================
with aba2:
    st.subheader("💼 Carteira")

    col1, col2, col3 = st.columns(3)

    with col1:
        novo = st.text_input("Ticker").upper()

    with col2:
        valor = st.number_input("Valor", min_value=0.0)

    with col3:
        if st.button("Adicionar"):
            add_ativo(st.session_state.user, novo, valor)
            st.success("Adicionado")

    carteira = get_carteira(st.session_state.user)

    total_i = 0
    total_a = 0
    dados = []

    for t, v in carteira:
        if not t.endswith(".SA"):
            t += ".SA"

        hist = yf.Ticker(t).history(period="1d")
        preco = hist['Close'].iloc[-1] if not hist.empty else 0

        atual = v
        lucro = atual - v

        total_i += v
        total_a += atual

        dados.append({"Ticker": t, "Investido": v, "Atual": atual, "Lucro": lucro})

    if dados:
        df = pd.DataFrame(dados)
        st.dataframe(df)

        lucro_total = total_a - total_i

        c1, c2, c3 = st.columns(3)
        c1.metric("Investido", f"{total_i:.2f}")
        c2.metric("Atual", f"{total_a:.2f}")
        c3.metric("Lucro", f"{lucro_total:.2f}")

    if st.button("Limpar Carteira"):
        limpar(st.session_state.user)
        st.warning("Carteira limpa")

# =========================
# 💰 DIVIDENDOS
# =========================
with aba3:
    st.subheader("💰 Dividendos")

    carteira = get_carteira(st.session_state.user)
    total = 0

    for t, v in carteira:
        if not t.endswith(".SA"):
            t += ".SA"

        info = yf.Ticker(t).info or {}
        dy_raw = info.get("dividendYield")

        dy = dy_raw if dy_raw and dy_raw < 1 else (dy_raw or 0)/100
        div = v * dy

        total += div
        st.write(f"{t}: R$ {div:.2f}/ano")

    st.success(f"Total: R$ {total:.2f}")
