import streamlit as st
import yfinance as yf
import pandas as pd
import sqlite3
import hashlib
from datetime import datetime

# =========================
# 🔒 BANCO DE DADOS
# =========================
conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    user TEXT,
    senha TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS carteira (
    user TEXT,
    ticker TEXT,
    valor REAL,
    data TEXT
)
""")

conn.commit()

# =========================
# 🔐 SEGURANÇA
# =========================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

def cadastrar(u, s):
    s_hash = hash_senha(s)
    cursor.execute("INSERT INTO usuarios VALUES (?, ?)", (u, s_hash))
    conn.commit()

def login(u, s):
    s_hash = hash_senha(s)
    cursor.execute("SELECT * FROM usuarios WHERE user=? AND senha=?", (u, s_hash))
    return cursor.fetchone()

# =========================
# 💼 CARTEIRA
# =========================
def add_ativo(u, t, v):
    data = datetime.now().strftime("%d/%m/%Y")
    cursor.execute("INSERT INTO carteira VALUES (?, ?, ?, ?)", (u, t, v, data))
    conn.commit()

def get_carteira(u):
    cursor.execute("SELECT ticker, valor FROM carteira WHERE user=?", (u,))
    return cursor.fetchall()

# =========================
# 📊 ANÁLISE PROFISSIONAL
# =========================
def analisar_ativo(ticker):
    try:
        if not ticker.endswith(".SA"):
            ticker += ".SA"

        ativo = yf.Ticker(ticker)
        info = ativo.info or {}

        nome = info.get("shortName", "N/A")
        setor = info.get("sector", "N/A")
        industria = info.get("industry", "N/A")

        preco = info.get("currentPrice", 0)

        dy_raw = info.get("dividendYield")
        dy = dy_raw * 100 if dy_raw and dy_raw < 1 else dy_raw or 0

        pvp = info.get("priceToBook", 0)
        pl = info.get("trailingPE", 0)
        roe = (info.get("returnOnEquity") or 0) * 100
        divida = info.get("debtToEquity", 0)

        receita = info.get("totalRevenue", 0)
        patrimonio = info.get("totalAssets", 0)

        try:
            hist = ativo.history(period="max")
            anos = len(hist) / 252
        except:
            anos = 0

        score = 0
        if dy > 6: score += 1
        if roe > 15: score += 2
        if pvp and pvp < 1.2: score += 2
        if divida and divida < 100: score += 1

        if score >= 5:
            status = "🟢 BOM"
        elif score >= 3:
            status = "🟡 MÉDIO"
        else:
            status = "🔴 RUIM"

        return {
            "Ticker": ticker.replace(".SA", ""),
            "Nome": nome,
            "Setor": setor,
            "Indústria": industria,
            "Preço": preco,
            "DY (%)": round(dy, 2),
            "P/VP": round(pvp, 2),
            "P/L": round(pl, 2),
            "ROE (%)": round(roe, 2),
            "Dívida": round(divida, 2),
            "Receita": receita,
            "Patrimônio": patrimonio,
            "Tempo": round(anos, 1),
            "Status": status
        }

    except Exception as e:
        return {"Erro": str(e)}

# =========================
# 🤖 RANKING + IA
# =========================
def gerar_ranking():
    ativos = ["BBAS3","PETR4","VALE3","ITUB4","BBDC4",
              "MXRF11","HGLG11","XPML11","VISC11","KNRI11"]

    lista = []

    for t in ativos:
        dados = analisar_ativo(t)

        if "Erro" not in dados:
            score = 0
            if dados["DY (%)"] > 6: score += 1
            if dados["ROE (%)"] > 15: score += 2
            if dados["P/VP"] < 1.2: score += 2

            lista.append({
                "Ativo": t,
                "DY": dados["DY (%)"],
                "Score": score
            })

    return pd.DataFrame(lista).sort_values(by="Score", ascending=False)

# =========================
# 🚀 INTERFACE
# =========================
st.title("📊 Investimentos PRO")

if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    aba = st.radio("Login / Cadastro", ["Login", "Cadastrar"])

    user = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if aba == "Cadastrar":
        if st.button("Criar conta"):
            cadastrar(user, senha)
            st.success("Conta criada!")

    else:
        if st.button("Entrar"):
            if login(user, senha):
                st.session_state.user = user
                st.success("Logado!")
            else:
                st.error("Erro no login")

else:
    st.sidebar.write(f"👤 {st.session_state.user}")

    aba1, aba2, aba3, aba4 = st.tabs(
        ["📊 Análise", "💼 Carteira", "💰 Dividendos", "🤖 IA"]
    )

    # =====================
    # 📊 ANÁLISE
    # =====================
    with aba1:
        ativo = st.text_input("Digite o ativo")

        if ativo:
            dados = analisar_ativo(ativo)

            if "Erro" in dados:
                st.error(dados["Erro"])
            else:
                st.subheader(f"{dados['Ticker']} - {dados['Status']}")
                st.write(dados)

    # =====================
    # 💼 CARTEIRA
    # =====================
    with aba2:
        ticker = st.text_input("Ativo")
        valor = st.number_input("Valor", 0.0)

        if st.button("Adicionar"):
            add_ativo(st.session_state.user, ticker, valor)
            st.success("Adicionado!")

        carteira = get_carteira(st.session_state.user)

        if carteira:
            df = pd.DataFrame(carteira, columns=["Ativo", "Valor"])
            st.dataframe(df)

            total = df["Valor"].sum()
            st.subheader(f"Total investido: R$ {total}")

    # =====================
    # 💰 DIVIDENDOS
    # =====================
    with aba3:
        carteira = get_carteira(st.session_state.user)

        total_dy = 0

        for t, v in carteira:
            dados = analisar_ativo(t)
            total_dy += v * (dados["DY (%)"] / 100)

        st.subheader(f"Renda estimada anual: R$ {round(total_dy,2)}")

    # =====================
    # 🤖 IA
    # =====================
    with aba4:
        ranking = gerar_ranking()
        st.dataframe(ranking)

        if not ranking.empty:
            top = ranking.iloc[0]
            st.success(f"Melhor ativo: {top['Ativo']}")
