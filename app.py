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
OPER = ["Criação de Modelos", "Etiquetas", "Frete e Transporte de Mercadorias",
        "Embalagens", "Manutenção de Máquinas e Peças"]
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
    mostrar_av = st.checkbox("Mostrar análise vertical (% sobre a Receita Bruta)", value=True)

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
    # análise vertical: cada linha como % da Receita Bruta total
    if mostrar_av:
        rec_bruta_total = sum(linhas_det[0][1])  # primeira linha = RECEITA BRUTA
        av = []
        for l in linhas_det:
            if rec_bruta_total != 0:
                av.append(sum(l[1]) / rec_bruta_total)
            else:
                av.append(None)
        dados["AV% s/ Receita"] = av

    det = pd.DataFrame(dados)

    # formatação: moeda nas colunas de mês e total; % na AH e AV
    ah_col = f"AH% ({meses_f[-1]} vs {meses_f[-2]})" if (mostrar_ah and len(meses_f) >= 2) else None
    av_col = "AV% s/ Receita" if mostrar_av else None
    fmt = det.copy()
    for c in fmt.columns:
        if c == col_nome:
            continue
        if c == ah_col:
            fmt[c] = fmt[c].apply(lambda v: "" if v is None else f"{v*100:+.1f}%")
        elif c == av_col:
            fmt[c] = fmt[c].apply(lambda v: "" if v is None else f"{v*100:.1f}%")
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
    if mostrar_av:
        st.caption("AV% = peso de cada linha sobre a Receita Bruta total do período "
                   "(análise vertical).")

# ============ SIMULADOR DE COMPRA ============
elif aba == "Simulador de Compra":
    st.header("Compras Parceladas — Contas a Pagar")
    st.caption("Lance uma compra parcelada: o sistema gera as parcelas mês a mês "
               "e soma no dashboard de contas a pagar.")

    # ---- base de contas a pagar (aba do Excel) ----
    @st.cache_data
    def carregar_contas(caminho):
        df = pd.read_excel(caminho, sheet_name="Contas a Pagar", skiprows=4)
        df = df.rename(columns={"Valor (R$)": "Valor"})
        df = df.dropna(subset=["Fornecedor", "Vencimento", "Valor"])
        df["Vencimento"] = pd.to_datetime(df["Vencimento"], errors="coerce")
        df = df.dropna(subset=["Vencimento"])
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        return df

    try:
        base = carregar_contas(ARQUIVO)
    except Exception:
        base = pd.DataFrame(columns=["Fornecedor", "Vencimento", "Parcelas",
                                     "Forma de Pagamento", "Valor", "Descrição", "Status"])

    # ---- estado: novas parcelas lançadas nesta sessão ----
    if "novas_parcelas" not in st.session_state:
        st.session_state["novas_parcelas"] = []

    # ---- formulário de lançamento ----
    st.subheader("Lançar nova compra parcelada")
    c1, c2, c3 = st.columns(3)
    with c1:
        fornecedor = st.text_input("Fornecedor")
        valor_total = st.number_input("Valor total (R$)", min_value=0.0,
                                      value=10000.0, step=500.0)
    with c2:
        data1 = st.date_input("Data da 1ª parcela")
        nparc = st.number_input("Nº de parcelas", min_value=1, max_value=60,
                                value=3, step=1)
    with c3:
        forma = st.selectbox("Forma de pagamento",
                             ["CHEQUE - EMPRESA", "CHEQUE - CLIENTE/TERCEIROS",
                              "BOLETO", "PIX", "CARTÃO", "DINHEIRO"])
        descricao = st.text_input("Descrição", value="")

    cga, cgb = st.columns([1, 1])
    gerar = cga.button("➕ Gerar parcelas", type="primary",
                       use_container_width=True)
    limpar = cgb.button("🗑️ Limpar lançamentos da sessão",
                        use_container_width=True)
    if limpar:
        st.session_state["novas_parcelas"] = []
        st.rerun()

    if gerar:
        if not fornecedor.strip():
            st.warning("Informe o fornecedor antes de gerar.")
        elif valor_total <= 0:
            st.warning("Informe um valor total maior que zero.")
        else:
            vparc = round(valor_total / nparc, 2)
            base_dt = pd.Timestamp(data1)
            for i in range(int(nparc)):
                venc = base_dt + pd.DateOffset(months=i)
                st.session_state["novas_parcelas"].append({
                    "Parcela": f"{i+1}/{int(nparc)}",
                    "Fornecedor": fornecedor.strip(),
                    "Vencimento": venc,
                    "Parcelas": int(nparc),
                    "Forma de Pagamento": forma,
                    "Valor": vparc,
                    "Descrição": descricao.strip(),
                    "Status": "A PAGAR",
                })
            st.success(f"{int(nparc)} parcela(s) de {brl(vparc)} geradas "
                       f"para {fornecedor.strip()}.")

    novas = pd.DataFrame(st.session_state["novas_parcelas"])

    # ---- parcelas geradas nesta sessão ----
    if not novas.empty:
        st.subheader("Parcelas geradas nesta sessão")
        show_novas = novas.copy()
        show_novas["Vencimento"] = pd.to_datetime(show_novas["Vencimento"]).dt.strftime("%d/%m/%Y")
        show_novas["Valor"] = show_novas["Valor"].apply(brl)
        st.dataframe(show_novas, use_container_width=True, hide_index=True)
        csv = novas.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Baixar parcelas geradas (CSV)", csv,
                           file_name="parcelas_geradas.csv", mime="text/csv")

    st.divider()

    # ---- dashboard: totais por mês (base + novas) ----
    st.subheader("Dashboard — Resumo de contas a pagar")
    df_dash = base[["Fornecedor", "Vencimento", "Valor"]].copy()
    if not novas.empty:
        df_dash = pd.concat([df_dash,
                             novas[["Fornecedor", "Vencimento", "Valor"]]],
                            ignore_index=True)
    if df_dash.empty:
        st.info("Nenhuma conta a pagar na base. Lance uma compra acima.")
    else:
        df_dash["Vencimento"] = pd.to_datetime(df_dash["Vencimento"])
        df_dash["Mes"] = df_dash["Vencimento"].dt.strftime("%m/%Y")
        df_dash["MesOrd"] = (df_dash["Vencimento"].dt.year * 100
                             + df_dash["Vencimento"].dt.month)
        tot_geral = df_dash["Valor"].sum()
        st.metric("TOTAL GERAL A PAGAR", brl(tot_geral))
        piv = (df_dash.groupby(["MesOrd", "Mes"])["Valor"].sum()
               .reset_index().sort_values("MesOrd"))
        cols = st.columns(min(6, max(1, len(piv))))
        for i, (_, row) in enumerate(piv.iterrows()):
            cols[i % len(cols)].metric(f"Total {row['Mes']}", brl(row["Valor"]))
        st.bar_chart(piv.set_index("Mes")["Valor"])

        # tabela completa de contas a pagar
        with st.expander("Ver todas as contas a pagar (base + novas)"):
            full = base.copy()
            if not novas.empty:
                add = novas.rename(columns={"Parcela": "Parc."})
                full = pd.concat([full, add[["Fornecedor", "Vencimento", "Parcelas",
                                             "Forma de Pagamento", "Valor",
                                             "Descrição", "Status"]]],
                                 ignore_index=True)
            full = full.sort_values("Vencimento")
            full["Vencimento"] = pd.to_datetime(full["Vencimento"]).dt.strftime("%d/%m/%Y")
            full["Valor"] = full["Valor"].apply(brl)
            st.dataframe(full, use_container_width=True, hide_index=True)

    st.caption("As novas parcelas valem só nesta sessão (o app não grava no Excel). "
               "Use o botão de download para salvar e colar na aba 'Contas a Pagar'.")

elif aba == "Régua de Crédito":
    st.header("Régua de Crédito")
    st.write("Responda às perguntas. Os critérios marcados com 🔴 são "
             "**determinantes**: se a resposta for Não, o crédito é negado "
             "na hora, independente da pontuação.")

    # (pergunta, peso, eliminatória?)
    perguntas = [
        ("O cliente já comprou com a gente antes?", 15, False),
        ("🔴 Os pagamentos anteriores foram em dia?", 25, True),
        ("🔴 Possui CNPJ ativo / cadastro regular?", 15, True),
        ("🔴 Está com o nome limpo (sem SPC/Serasa)?", 25, True),
        ("Apresentou comprovante de renda/faturamento?", 10, False),
        ("O valor pedido está dentro do histórico dele?", 10, False),
    ]

    total = 0
    eliminado_por = []
    for q, peso, elim in perguntas:
        if "pagamentos anteriores" in q:
            # cliente novo não tem histórico: opção neutra
            resp = st.radio(q, ["Não", "Sim", "Não se aplica (cliente novo)"],
                            horizontal=True, key=q)
            if resp == "Sim":
                total += peso
            elif resp == "Não":
                eliminado_por.append("Pagamentos anteriores em atraso")
        else:
            resp = st.radio(q, ["Não", "Sim"], horizontal=True, key=q)
            if resp == "Sim":
                total += peso
            elif elim:
                if "CNPJ" in q:
                    eliminado_por.append("CNPJ inativo / cadastro irregular")
                elif "nome limpo" in q:
                    eliminado_por.append("Restrição no SPC/Serasa")

    st.divider()
    st.metric("Pontuação total", f"{total}/100")

    if eliminado_por:
        motivos = "; ".join(eliminado_por)
        st.error(f"⛔ CRÉDITO NEGADO — critério determinante: {motivos}. "
                 f"A negativa é imediata, independente da pontuação.")
    elif total >= 80:
        st.success(f"✅ CRÉDITO LIBERADO ({total}/100) — perfil de baixo risco.")
    elif total >= 50:
        st.warning(f"⚠️ LIBERAR COM CAUTELA ({total}/100) — exigir entrada ou reduzir prazo.")
    else:
        st.error(f"❌ CRÉDITO NEGADO ({total}/100) — risco alto.")

st.sidebar.divider()
st.sidebar.caption("Dados: DRE (competência) e Fluxo (caixa). Recalculado ao vivo.")
