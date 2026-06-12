"""
Sistema de Gestão Financeira - App Streamlit
Lê o arquivo sistema_financeiro.xlsx (na raiz do repositório) e recalcula
tudo ao vivo: Fluxo de Caixa, DRE Gerencial, Simulador de Compra e Régua de Crédito.

Como rodar localmente:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="CODI.COM - Gestão Financeira", page_icon="📊", layout="wide")

# ----------------- Tema CODI.COM (preto + dourado) -----------------
DOURADO = "#D4B035"
PRETO = "#1A1A1A"
st.markdown(f"""
<style>
    .stApp {{ background-color: #FAFAF7; }}
    h1, h2, h3 {{ color: {PRETO}; }}
    h1 {{ border-bottom: 3px solid {DOURADO}; padding-bottom: 8px; }}
    [data-testid="stSidebar"] {{ background-color: {PRETO}; }}
    [data-testid="stSidebar"] * {{ color: #F5ECCB !important; }}
    [data-testid="stMetricValue"] {{ color: {PRETO}; }}
    .stRadio label, .stMultiSelect label, .stNumberInput label {{ color: {PRETO}; }}
    div[data-testid="stMetric"] {{
        background: #FFFFFF; border-left: 4px solid {DOURADO};
        padding: 10px 14px; border-radius: 6px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }}
    .stButton>button {{ background-color: {DOURADO}; color: {PRETO}; border: none; font-weight: 600; }}
</style>
""", unsafe_allow_html=True)


ARQUIVO = "sistema_financeiro.xlsx"

# ----------------- Classificação da DRE gerencial -----------------
CUSTO = ["Custo de Mercadoria Vendida"]
OPER = ["Facção", "Tecidos", "Lavanderia", "Acabamento Externo", "Aviamento", "Travete",
        "Criação de Modelos", "Etiquetas", "Frete e Transporte de Mercadorias", "Produção Externa",
        "Bordado Industrial", "Bordado Manual", "Outros Insumos", "Embalagens",
        "Manutenção de Máquinas e Peças"]
PESSOAL = ["Salário e Ordenados", "13º Salário", "Acertos e Recisões", "Férias", "Fgts, Gps e Pis", "Vale Transporte",
           "Vales e Adiantamentos", "Premiações e Abonos", "Exame Adminissional/Demissional",
           "Uniforme e EPIs", "Despesa com Sindicatos"]
FINANC = ["Empréstimos", "Empréstimos a Terceiros", "ICMS", "Juros de Empréstimos", "Tarifas e Custos de Op. Bancárias", "Consórcio",
          "Darf", "Outros Tributos", "Multas", "Multas e Juros por Atraso", "Ipva"]
RETIRADAS = ["Retiradas de Sócios"]
ACLASSIFICAR = ["Despesa não Identificada", "Suspenso (a classificar)"]

TAXAS = [("Simples Nacional (10,47% s/ Vendas)", 0.1047),
         ("Comissão de Vendedores (1,50% s/ Vendas)", 0.0150),
         ("Comissão de Assessores (0,10% s/ Vendas)", 0.0010)]


# ----------------- Leitura e preparo dos dados -----------------
@st.cache_data
def carregar_aba(caminho, aba):
    """Lê uma aba de lançamentos e normaliza."""
    df = pd.read_excel(caminho, sheet_name=aba, skiprows=4)
    df = df.rename(columns={"Valor (R$)": "Valor"})
    df = df.dropna(subset=["Data", "Tipo", "Categoria", "Valor"])
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    df = df.dropna(subset=["Data"])
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
    df["MesK"] = df["Data"].dt.strftime("%m/%Y")
    df["MesOrd"] = df["Data"].dt.year * 100 + df["Data"].dt.month
    df["Categoria"] = df["Categoria"].astype(str).str.strip()
    return df


def brl(v):
    """Formata número como moeda BR."""
    try:
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return v


def meses_ordenados(df):
    m = df[["MesK", "MesOrd"]].drop_duplicates().sort_values("MesOrd")
    return m["MesK"].tolist()


# ----------------- App -----------------
# Logo + título
_lc1, _lc2 = st.columns([1, 4])
with _lc1:
    try:
        st.image("logo_codi.png", width=200)
    except Exception:
        pass
with _lc2:
    st.title("Sistema de Gestão Financeira")
    st.caption("CODI.COM · Jeans Wear")

caminho = Path(ARQUIVO)
if not caminho.exists():
    st.error(f"Arquivo '{ARQUIVO}' não encontrado na raiz do repositório. "
             f"Coloque o Excel junto do app.py.")
    st.stop()

df_dre = carregar_aba(ARQUIVO, "Lançamentos DRE")      # competência (vencimento)
df_flux = carregar_aba(ARQUIVO, "Lançamentos Fluxo")    # caixa (baixa)

# CMV reaproveitado entra na base DRE se não houver categoria CMV
# (já vem nas duas abas conforme gerado no Excel)

receita = df_dre[df_dre["Tipo"] == "Entrada"]      # para DRE
despesa = df_dre[df_dre["Tipo"] == "Saída"]
receita_fx = df_flux[df_flux["Tipo"] == "Entrada"]  # para Fluxo
despesa_fx = df_flux[df_flux["Tipo"] == "Saída"]
meses = meses_ordenados(df_dre)

# Sidebar - filtro de período
st.sidebar.header("Filtros")
sel = st.sidebar.multiselect("Meses", meses, default=meses)
if sel:
    df_f = df_dre[df_dre["MesK"].isin(sel)]
    rec_f = receita[receita["MesK"].isin(sel)]
    desp_f = despesa[despesa["MesK"].isin(sel)]
    meses_f = [m for m in meses if m in sel]
else:
    df_f, rec_f, desp_f, meses_f = df_dre, receita, despesa, meses

aba = st.sidebar.radio("Seção", ["Resumo", "Fluxo de Caixa", "DRE Gerencial",
                                  "Simulador de Compra", "Régua de Crédito"])

# ============ RESUMO ============
if aba == "Resumo":
    tot_ent = rec_f["Valor"].sum()
    tot_sai = desp_f["Valor"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total de Entradas", brl(tot_ent))
    c2.metric("Total de Saídas", brl(tot_sai))
    c3.metric("Resultado", brl(tot_ent - tot_sai))

    st.subheader("Entradas x Saídas por mês")
    piv = pd.DataFrame({
        "Entradas": rec_f.groupby("MesK")["Valor"].sum(),
        "Saídas": desp_f.groupby("MesK")["Valor"].sum(),
    }).reindex(meses_f).fillna(0)
    st.bar_chart(piv)

    st.subheader("Maiores categorias de despesa")
    top = desp_f.groupby("Categoria")["Valor"].sum().sort_values(ascending=False).head(15)
    st.bar_chart(top)

# ============ FLUXO DE CAIXA ============
elif aba == "Fluxo de Caixa":
    st.header("Fluxo de Caixa Mensal")
    st.caption("Regime de caixa (data de baixa)")
    saldo_ini = st.number_input("Saldo inicial (R$)", value=0.0, step=1000.0)

    # Fluxo usa a base CAIXA (data de baixa)
    meses_fx = meses_ordenados(df_flux)
    if sel:
        rec_fx_f = receita_fx[receita_fx["MesK"].isin(sel)]
        desp_fx_f = despesa_fx[despesa_fx["MesK"].isin(sel)]
        meses_fx = [m for m in meses_fx if m in sel]
    else:
        rec_fx_f, desp_fx_f = receita_fx, despesa_fx
    linhas = []
    acum = saldo_ini
    for m in meses_fx:
        ent = rec_fx_f[rec_fx_f["MesK"] == m]["Valor"].sum()
        sai = desp_fx_f[desp_fx_f["MesK"] == m]["Valor"].sum()
        res = ent - sai
        acum += res
        linhas.append({"Mês": m, "Entradas": ent, "Saídas": sai,
                       "Resultado": res, "Saldo Acumulado": acum})
    fc = pd.DataFrame(linhas)
    total = {"Mês": "TOTAL", "Entradas": fc["Entradas"].sum(),
             "Saídas": fc["Saídas"].sum(), "Resultado": fc["Resultado"].sum(),
             "Saldo Acumulado": acum}
    fc_show = pd.concat([fc, pd.DataFrame([total])], ignore_index=True)
    for col in ["Entradas", "Saídas", "Resultado", "Saldo Acumulado"]:
        fc_show[col] = fc_show[col].apply(brl)
    st.dataframe(fc_show, use_container_width=True, hide_index=True)

    st.subheader("Saldo acumulado")
    st.line_chart(fc.set_index("Mês")["Saldo Acumulado"])

# ============ DRE GERENCIAL ============
elif aba == "DRE Gerencial":
    st.header("DRE Gerencial — Competência")
    st.caption("Regime de competência (data de vencimento)")

    def soma_cat(cats, m):
        return desp_f[(desp_f["Categoria"].isin(cats)) & (desp_f["MesK"] == m)]["Valor"].sum()

    def soma_grupo(cats):
        return desp_f[desp_f["Categoria"].isin(cats)]["Valor"].sum()

    def rec_total():
        return rec_f["Valor"].sum()

    rec = rec_total()
    impostos = sum(rec * a for _, a in TAXAS)
    rec_liq = rec - impostos
    cmv = soma_grupo(CUSTO)
    margem = rec_liq - cmv
    t_oper = soma_grupo(OPER)
    t_pess = soma_grupo(PESSOAL)
    classific = set(CUSTO + OPER + PESSOAL + FINANC + RETIRADAS + ACLASSIFICAR)
    admin_cats = sorted(set(desp_f["Categoria"]) - classific)
    t_admin = desp_f[desp_f["Categoria"].isin(admin_cats)]["Valor"].sum()
    ebitda = margem - t_oper - t_pess - t_admin
    t_fin = soma_grupo(FINANC)
    t_ret = soma_grupo(RETIRADAS)
    t_aclass = soma_grupo(ACLASSIFICAR)
    ebitda_final = ebitda - t_fin - t_ret - t_aclass

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita Líquida", brl(rec_liq))
    c2.metric("Margem", brl(margem))
    c3.metric("EBITDA", brl(ebitda))
    c4.metric("EBITDA Final", brl(ebitda_final))

    st.subheader("Demonstração (totais do período)")
    linhas = [
        ("(+) RECEITA BRUTA", rec, "sub"),
        ("(-) Impostos e Comissões", -impostos, "item"),
        ("(=) RECEITA LÍQUIDA", rec_liq, "res"),
        ("(-) CMV", -cmv, "item"),
        ("(=) MARGEM", margem, "res"),
        ("(-) Despesas Operacionais", -t_oper, "item"),
        ("(-) Despesas com Pessoal", -t_pess, "item"),
        ("(-) Despesas Administrativas", -t_admin, "item"),
        ("(=) EBITDA", ebitda, "res"),
        ("(-) Despesas Financeiras", -t_fin, "item"),
        ("(-) Retiradas de Sócios", -t_ret, "item"),
        ("(-) A Classificar", -t_aclass, "item"),
        ("(=) EBITDA FINAL", ebitda_final, "res"),
    ]
    dre_df = pd.DataFrame([{"Descrição": d, "Valor": brl(v)} for d, v, _ in linhas])
    st.dataframe(dre_df, use_container_width=True, hide_index=True)

    # ===== DRE mês a mês com Margem, EBITDA e Análise Horizontal =====
    st.subheader("DRE mês a mês")

    def rec_mes(m):
        return rec_f[rec_f["MesK"] == m]["Valor"].sum()

    # opção de expandir o plano de contas
    expandir = st.checkbox("Expandir plano de contas (mostrar todas as categorias)", value=False)
    mostrar_ah = st.checkbox("Mostrar análise horizontal (variação % entre meses)", value=True)

    grupos = [("CUSTO (CMV)", CUSTO), ("Despesas Operacionais", OPER),
              ("Despesas com Pessoal", PESSOAL), ("Despesas Administrativas", admin_cats),
              ("Despesas Financeiras", FINANC), ("Retiradas de Sócios", RETIRADAS),
              ("A Classificar", ACLASSIFICAR)]

    linhas_det = []

    # Receita
    linhas_det.append(("(+) RECEITA BRUTA", [rec_mes(m) for m in meses_f], "res"))
    # Impostos
    linhas_det.append(("(-) Impostos e Comissões",
                       [-sum(rec_mes(m) * a for _, a in TAXAS) for m in meses_f], "item"))
    # Receita Líquida
    rec_liq_m = [rec_mes(m) - sum(rec_mes(m) * a for _, a in TAXAS) for m in meses_f]
    linhas_det.append(("(=) RECEITA LÍQUIDA", rec_liq_m, "res"))
    # CMV
    cmv_m = [soma_cat(CUSTO, m) for m in meses_f]
    if expandir:
        for cat in CUSTO:
            linhas_det.append(("    " + cat, [soma_cat([cat], m) for m in meses_f], "cat"))
    linhas_det.append(("(-) CMV", [-v for v in cmv_m], "item"))
    # MARGEM
    margem_m = [rec_liq_m[i] - cmv_m[i] for i in range(len(meses_f))]
    linhas_det.append(("(=) MARGEM", margem_m, "res"))

    # Grupos de despesa (operacional, pessoal, admin)
    def grupo_total_m(cats, m):
        return soma_cat(cats, m)

    for nome, cats in [("Despesas Operacionais", OPER),
                       ("Despesas com Pessoal", PESSOAL),
                       ("Despesas Administrativas", admin_cats)]:
        if expandir:
            for cat in sorted(cats, key=lambda c: -soma_grupo([c])):
                vals = [soma_cat([cat], m) for m in meses_f]
                if any(vals):
                    linhas_det.append(("    " + cat, [-v for v in vals], "cat"))
        linhas_det.append((f"(-) {nome}",
                           [-grupo_total_m(cats, m) for m in meses_f], "item"))

    # EBITDA
    ebitda_m = [margem_m[i]
                - grupo_total_m(OPER, meses_f[i])
                - grupo_total_m(PESSOAL, meses_f[i])
                - grupo_total_m(admin_cats, meses_f[i])
                for i in range(len(meses_f))]
    linhas_det.append(("(=) EBITDA", ebitda_m, "res"))

    # Financeiras, Retiradas, A Classificar
    for nome, cats in [("Despesas Financeiras", FINANC),
                       ("Retiradas de Sócios", RETIRADAS),
                       ("A Classificar", ACLASSIFICAR)]:
        if expandir:
            for cat in sorted(cats, key=lambda c: -soma_grupo([c])):
                vals = [soma_cat([cat], m) for m in meses_f]
                if any(vals):
                    linhas_det.append(("    " + cat, [-v for v in vals], "cat"))
        linhas_det.append((f"(-) {nome}",
                           [-grupo_total_m(cats, m) for m in meses_f], "item"))

    # EBITDA FINAL
    ef_m = [ebitda_m[i]
            - grupo_total_m(FINANC, meses_f[i])
            - grupo_total_m(RETIRADAS, meses_f[i])
            - grupo_total_m(ACLASSIFICAR, meses_f[i])
            for i in range(len(meses_f))]
    linhas_det.append(("(=) EBITDA FINAL", ef_m, "res"))

    # montar DataFrame
    col_nome = "Descrição"
    dados = {}
    dados[col_nome] = [l[0] for l in linhas_det]
    for i, m in enumerate(meses_f):
        dados[m] = [l[1][i] for l in linhas_det]
    dados["TOTAL"] = [sum(l[1]) for l in linhas_det]
    # análise horizontal: variação % do último mês vs penúltimo
    if mostrar_ah and len(meses_f) >= 2:
        ah = []
        for l in linhas_det:
            ant, ult = l[1][-2], l[1][-1]
            if ant != 0:
                ah.append((ult - ant) / abs(ant))
            else:
                ah.append(None)
        dados[f"AH% ({meses_f[-1]} vs {meses_f[-2]})"] = ah

    det = pd.DataFrame(dados)

    # formatação: moeda nas colunas de mês e total; % na AH
    ah_col = f"AH% ({meses_f[-1]} vs {meses_f[-2]})" if (mostrar_ah and len(meses_f) >= 2) else None
    fmt = det.copy()
    for c in fmt.columns:
        if c == col_nome:
            continue
        if c == ah_col:
            fmt[c] = fmt[c].apply(lambda v: "" if v is None else f"{v*100:+.1f}%")
        else:
            fmt[c] = fmt[c].apply(brl)

    # destacar linhas de resultado
    def realcar(row):
        desc = row[col_nome]
        if desc.startswith("(="):
            return ["background-color: #1A1A1A; color: white; font-weight: bold"] * len(row)
        if desc.strip().startswith("(-)") or desc.strip().startswith("(+)"):
            return ["background-color: #F5ECCB; font-weight: bold"] * len(row)
        return [""] * len(row)

    st.dataframe(fmt.style.apply(realcar, axis=1), use_container_width=True,
                 hide_index=True, height=min(640, 40 + 35 * len(fmt)))

    if mostrar_ah:
        st.caption(f"AH% = variação percentual de {meses_f[-1]} em relação a {meses_f[-2]}. "
                   f"Verde/+ subiu, vermelho/- caiu.")

# ============ SIMULADOR DE COMPRA ============
elif aba == "Simulador de Compra":
    st.header("Simulador de Compra Parcelada")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Dados da compra")
        valor = st.number_input("Valor do produto (R$)", value=50000.0, step=1000.0)
        entrada = st.number_input("Entrada / sinal (R$)", value=5000.0, step=500.0)
        nparc = st.number_input("Número de parcelas", value=12, min_value=1, step=1)
        juros = st.number_input("Taxa de juros ao mês (%)", value=1.8, step=0.1) / 100
    with col2:
        st.subheader("Sua capacidade de pagamento")
        rec_m = st.number_input("Receita mensal média (R$)", value=60000.0, step=1000.0)
        desp_m = st.number_input("Despesas fixas mensais (R$)", value=40000.0, step=1000.0)
        pct = st.number_input("% da sobra que pode comprometer", value=30, step=5) / 100
        # média mensal por categoria (parcelas já ativas)
        media_cat = (despesa.groupby("Categoria")
                     .apply(lambda g: g["Valor"].sum() / g["MesK"].nunique())
                     .sort_index())
        cat_sel = st.selectbox("Parcelas já ativas - categoria",
                               ["(nenhuma)"] + list(media_cat.index))
        comprometido = media_cat.get(cat_sel, 0.0) if cat_sel != "(nenhuma)" else 0.0
        st.caption(f"Parcelas já comprometidas/mês: **{brl(comprometido)}**")

    financiado = valor - entrada
    if juros == 0:
        parcela = financiado / nparc
    else:
        parcela = financiado * (juros * (1 + juros) ** nparc) / ((1 + juros) ** nparc - 1)
    total_pago = entrada + parcela * nparc
    custo_juros = total_pago - valor
    limite = (rec_m - desp_m) * pct - comprometido

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Parcela mensal", brl(parcela))
    c2.metric("Total pago", brl(total_pago))
    c3.metric("Custo dos juros", brl(custo_juros))
    c4, c5 = st.columns(2)
    c4.metric("Limite disponível", brl(limite))
    c5.metric("Comprometido/mês", brl(comprometido))

    if parcela <= limite:
        st.success(f"✅ APROVADO — a parcela cabe no seu limite. "
                   f"Folga de {brl(limite - parcela)} por mês.")
    else:
        st.error(f"❌ NÃO RECOMENDADO — a parcela ultrapassa seu limite em "
                 f"{brl(parcela - limite)} por mês.")

# ============ RÉGUA DE CRÉDITO ============
elif aba == "Régua de Crédito":
    st.header("Régua de Crédito")
    st.write("Responda às perguntas. O sistema soma os pontos e decide a liberação.")
    perguntas = [
        ("O cliente já comprou com a gente antes?", 15),
        ("Os pagamentos anteriores foram em dia?", 25),
        ("Possui CNPJ ativo / cadastro regular?", 15),
        ("Está com o nome limpo (sem SPC/Serasa)?", 25),
        ("Apresentou comprovante de renda/faturamento?", 10),
        ("O valor pedido está dentro do histórico dele?", 10),
    ]
    total = 0
    for q, peso in perguntas:
        resp = st.radio(q, ["Não", "Sim"], horizontal=True, key=q)
        if resp == "Sim":
            total += peso
    st.divider()
    st.metric("Pontuação total", f"{total}/100")
    if total >= 80:
        st.success(f"✅ CRÉDITO LIBERADO ({total}/100) — perfil de baixo risco.")
    elif total >= 50:
        st.warning(f"⚠️ LIBERAR COM CAUTELA ({total}/100) — exigir entrada ou reduzir prazo.")
    else:
        st.error(f"❌ CRÉDITO NEGADO ({total}/100) — risco alto.")

st.sidebar.divider()
st.sidebar.caption("Dados lidos da aba 'Lançamentos'. Tudo recalculado ao vivo.")
