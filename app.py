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
OPER = ["Frete e Transporte de Mercadorias", "Manutenção de Máquinas e Peças"]
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
def normaliza_cc(v):
    """Extrai o centro de custo (CDK, CODI, VAREN, ALV) da coluna CONTA."""
    if v is None:
        return "CODI"
    c = str(v).strip().upper()
    if c in ("", "NAN"):
        return "CODI"
    if "CODI.COM" in c or "LOJA BASIC" in c or "CONTA-CAIXA" in c:
        return "CODI"
    for cc in ["CDK", "CODI", "VAREN", "ALV"]:
        if cc in c:
            return cc
    return c


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
    if "Centro de Custo" in df.columns:
        df["CentroCusto"] = df["Centro de Custo"].apply(normaliza_cc)
    else:
        df["CentroCusto"] = "CODI"
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
meses = meses_ordenados(df_dre)

# Sidebar - filtros
st.sidebar.header("Filtros")
sel = st.sidebar.multiselect("Meses", meses, default=meses)

# filtro de centro de custo (afeta DRE e Fluxo)
ccs = sorted(set(df_dre["CentroCusto"]) | set(df_flux["CentroCusto"]))
cc_sel = st.sidebar.multiselect("Centro de custo", ccs, default=ccs,
                                help="CDK, CODI, VAREN, ALV. O histórico está marcado como CODI.")

# aplica centro de custo primeiro
df_dre_cc = df_dre[df_dre["CentroCusto"].isin(cc_sel)] if cc_sel else df_dre
df_flux_cc = df_flux[df_flux["CentroCusto"].isin(cc_sel)] if cc_sel else df_flux

receita = df_dre_cc[df_dre_cc["Tipo"] == "Entrada"]
despesa = df_dre_cc[df_dre_cc["Tipo"] == "Saída"]
receita_fx = df_flux_cc[df_flux_cc["Tipo"] == "Entrada"]
despesa_fx = df_flux_cc[df_flux_cc["Tipo"] == "Saída"]

if sel:
    df_f = df_dre_cc[df_dre_cc["MesK"].isin(sel)]
    rec_f = receita[receita["MesK"].isin(sel)]
    desp_f = despesa[despesa["MesK"].isin(sel)]
    meses_f = [m for m in meses if m in sel]
else:
    df_f, rec_f, desp_f, meses_f = df_dre_cc, receita, despesa, meses

aba = st.sidebar.radio("Seção", ["Resumo", "Fluxo de Caixa", "DRE Gerencial",
                                  "Painel Comercial", "OS de Produção",
                                  "Simulador de Compra", "Régua de Crédito"])


# ----------------- helpers dos painéis -----------------
def dias_uteis(ini, fim, ano, mes):
    import datetime as _dt
    return sum(1 for d in range(ini, fim + 1) if _dt.date(ano, mes, d).weekday() < 5)

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

    if mostrar_ah and len(meses_f) >= 2:
        st.caption(f"AH% = variação percentual de {meses_f[-1]} em relação a {meses_f[-2]}. "
                   f"Verde/+ subiu, vermelho/- caiu.")
    elif mostrar_ah:
        st.caption("AH% precisa de pelo menos 2 meses selecionados no filtro.")
    if mostrar_av:
        st.caption("AV% = peso de cada linha sobre a Receita Bruta total do período "
                   "(análise vertical).")

# ============ PAINEL COMERCIAL (metas × realizado) ============
elif aba == "Painel Comercial":
    st.header("Painel Comercial — Metas × Realizado 2026")

    @st.cache_data
    def carregar_metas(caminho):
        try:
            dfm = pd.read_excel(caminho, sheet_name="Metas", skiprows=4)
            dfm.columns = [str(c).strip() for c in dfm.columns]
            col_mes = [c for c in dfm.columns if "Mês" in c or "Mes" in c][0]
            col_meta = [c for c in dfm.columns if "Meta" in c][0]
            dfm = dfm.dropna(subset=[col_mes, col_meta])
            dfm["Meta"] = pd.to_numeric(dfm[col_meta], errors="coerce").fillna(0)
            return dict(zip(dfm[col_mes].astype(str).str.strip(), dfm["Meta"]))
        except Exception:
            return {}

    metas = carregar_metas(ARQUIVO)
    if not metas:
        st.warning("Aba 'Metas' não encontrada no Excel. Adicione as metas mensais nela.")
    else:
        # realizado por mês = receita (Entrada) da DRE
        real = {m: receita[receita["MesK"] == m]["Valor"].sum() for m in metas}
        # mês atual (parcial): último mês com realizado < meta e data no mês corrente
        hoje = pd.Timestamp.today().normalize()
        mes_atual = hoje.strftime("%m/%Y")

        linhas = []
        for mk in sorted(metas, key=lambda x: (int(x.split("/")[1]), int(x.split("/")[0]))):
            meta = metas[mk]
            rz = real.get(mk, 0.0)
            parcial = (mk == mes_atual)
            linhas.append({"mes": mk, "meta": meta, "real": rz, "parcial": parcial})

        # projeção do mês atual por dias úteis
        proj_atual = None
        if mes_atual in metas:
            import calendar
            ano, mes = int(mes_atual.split("/")[1]), int(mes_atual.split("/")[0])
            dias_mes = calendar.monthrange(ano, mes)[1]
            corte = hoje.day
            u_dec = dias_uteis(1, corte, ano, mes)
            u_tot = dias_uteis(1, dias_mes, ano, mes)
            real_atual = real.get(mes_atual, 0.0)
            if u_dec > 0 and real_atual > 0:
                proj_atual = real_atual / u_dec * u_tot

        # KPIs acumulados (meses fechados = não parciais e com realizado > 0)
        fechados = [l for l in linhas if not l["parcial"] and l["real"] > 0]
        acc_meta = sum(l["meta"] for l in fechados)
        acc_real = sum(l["real"] for l in fechados)
        acc_pct = acc_real / acc_meta * 100 if acc_meta else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Meta acum. (fechados)", brl(acc_meta))
        c2.metric("Realizado acum.", brl(acc_real),
                  delta=brl(acc_real - acc_meta))
        c3.metric("Atingimento acum.", f"{acc_pct:.1f}%")
        if proj_atual is not None:
            c4.metric(f"Projeção {mes_atual}", brl(proj_atual),
                      delta=f"{proj_atual / metas[mes_atual] * 100:.1f}% da meta")

        # gráfico meta × realizado
        st.subheader("Meta × Realizado por mês")
        graf = pd.DataFrame({
            "Meta": {l["mes"]: l["meta"] for l in linhas},
            "Realizado": {l["mes"]: (proj_atual if (l["parcial"] and proj_atual) else l["real"]) for l in linhas},
        })
        st.bar_chart(graf)
        if proj_atual is not None:
            st.caption(f"Obs.: {mes_atual} mostra a PROJEÇÃO ({brl(proj_atual)}), "
                       f"pois o mês ainda está em andamento.")

        # tabela detalhada
        st.subheader("Detalhamento mensal")
        rows = []
        for l in linhas:
            real_mostrar = l["real"]
            p = real_mostrar / l["meta"] * 100 if l["meta"] else 0
            status = "🟢" if p >= 100 else "🟡" if p >= 85 else "🔴"
            rows.append({
                "Mês": l["mes"] + (" (parcial)" if l["parcial"] else ""),
                "Meta": brl(l["meta"]),
                "Realizado": brl(real_mostrar),
                "Diferença": brl(real_mostrar - l["meta"]),
                "Atingimento": f"{status} {p:.1f}%",
            })
        if proj_atual is not None:
            pp = proj_atual / metas[mes_atual] * 100
            rows.append({
                "Mês": f"{mes_atual} (projeção)", "Meta": brl(metas[mes_atual]),
                "Realizado": brl(proj_atual), "Diferença": brl(proj_atual - metas[mes_atual]),
                "Atingimento": f"{'🟢' if pp>=100 else '🟡' if pp>=85 else '🔴'} {pp:.1f}%",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption("Atingimento: 🟢 ≥100% · 🟡 85–99% · 🔴 <85%. "
                   "Projeção do mês atual pelo ritmo de dias úteis.")

# ============ OS DE PRODUÇÃO ============
elif aba == "OS de Produção":
    st.header("OS de Produção — Acompanhamento")

    @st.cache_data
    def carregar_os(caminho):
        try:
            dfo = pd.read_excel(caminho, sheet_name="OS Produção", skiprows=4)
            dfo.columns = [str(c).strip() for c in dfo.columns]
            return dfo
        except Exception:
            return pd.DataFrame()

    osdf = carregar_os(ARQUIVO)
    if osdf.empty:
        st.warning("Aba 'OS Produção' não encontrada no Excel.")
    else:
        for col in ["Qtd Total", "Qtd Retorno", "Qtd Falta", "Valor Total", "Pago", "A Pagar"]:
            if col in osdf.columns:
                osdf[col] = pd.to_numeric(osdf[col], errors="coerce").fillna(0)
        osdf["Emissão"] = pd.to_datetime(osdf["Emissão"], errors="coerce")

        # em aberto = falta retornar OU falta pagar
        aberto = osdf[(osdf["Qtd Falta"] > 0) | (osdf["A Pagar"] > 0.01)].copy()
        hoje = pd.Timestamp.today().normalize()
        aberto["Dias"] = (hoje - aberto["Emissão"]).dt.days

        def pend(r):
            f = r["Qtd Falta"] > 0; p = r["A Pagar"] > 0.01
            return "Produção + Pagto" if (f and p) else ("Falta retornar" if f else "Falta pagar")
        aberto["Pendência"] = aberto.apply(pend, axis=1)
        aberto = aberto.sort_values("Dias", ascending=False)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("OS em aberto", len(aberto))
        c2.metric("Peças a retornar", int(aberto["Qtd Falta"].sum()))
        c3.metric("Valor a pagar", brl(aberto["A Pagar"].sum()))
        c4.metric("OS mais antiga", f"{int(aberto['Dias'].max()) if len(aberto) else 0} dias")

        st.subheader("Tempo em aberto por OS (aging)")
        aging = aberto.set_index(aberto["O.S."].astype(str))["Dias"]
        st.bar_chart(aging)
        st.caption("Aging = dias desde a emissão. Quanto maior, mais atrasada.")

        st.subheader("Ordens de serviço em aberto")
        show = aberto[["O.S.", "Fornecedor", "Produto", "Emissão", "Qtd Total",
                       "Qtd Retorno", "Qtd Falta", "Valor Total", "A Pagar",
                       "Pendência", "Dias"]].copy()
        show["Emissão"] = show["Emissão"].dt.strftime("%d/%m/%Y")
        for col in ["Valor Total", "A Pagar"]:
            show[col] = show[col].apply(brl)
        show = show.rename(columns={"Dias": "Aging (dias)"})
        st.dataframe(show, use_container_width=True, hide_index=True)
        st.caption(f"Total de OS na base: {len(osdf)} · concluídas: {len(osdf) - len(aberto)} · "
                   f"em aberto: {len(aberto)}. OS em aberto = falta retornar peças ou falta pagar.")

# ============ SIMULADOR DE COMPRA ============
elif aba == "Simulador de Compra":
    st.header("Simulador de Compra Parcelada")
    st.caption("Base: contas a pagar dos próximos 3 meses. "
               "Limite: média mensal paga nos últimos 6 meses.")

    # ---- contas a pagar (títulos em aberto, base real) ----
    @st.cache_data
    def carregar_contas(caminho):
        df = pd.read_excel(caminho, sheet_name="Contas a Pagar", skiprows=4)
        df = df.rename(columns={"Valor (R$)": "Valor"})
        df = df.dropna(subset=["Vencimento", "Valor"])
        df["Vencimento"] = pd.to_datetime(df["Vencimento"], errors="coerce")
        df = df.dropna(subset=["Vencimento"])
        df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce").fillna(0)
        return df

    contas = carregar_contas(ARQUIVO)

    hoje = pd.Timestamp.today().normalize()
    fim_3m = hoje + pd.DateOffset(months=3)

    # ---- BASE: parcelas a pagar nos próximos 3 meses ----
    prox = contas[(contas["Vencimento"] >= hoje) & (contas["Vencimento"] < fim_3m)]
    comprometido_3m = prox["Valor"].sum()
    comprometido_mensal = comprometido_3m / 3

    # ---- LIMITE: média mensal paga nos últimos 6 meses (base caixa) ----
    pagos = despesa_fx.copy()
    meses_pagos = (pagos[["MesK", "MesOrd"]].drop_duplicates()
                   .sort_values("MesOrd").tail(6))
    ult6 = pagos[pagos["MesK"].isin(meses_pagos["MesK"])]
    media_6m = ult6.groupby("MesK")["Valor"].sum().mean() if not ult6.empty else 0.0

    limite_disponivel = media_6m - comprometido_mensal

    # ---- painel de situação ----
    c1, c2, c3 = st.columns(3)
    c1.metric("Limite mensal (média 6m de pagamentos)", brl(media_6m))
    c2.metric("Comprometido/mês (parcelas próx. 3 meses)", brl(comprometido_mensal),
              help=f"Total a pagar nos próximos 3 meses: {brl(comprometido_3m)}")
    c3.metric("Limite disponível/mês", brl(limite_disponivel))

    if limite_disponivel <= 0:
        st.error(f"⛔ LIMITE JÁ ATINGIDO — as parcelas dos próximos 3 meses "
                 f"({brl(comprometido_mensal)}/mês) já consomem toda a média de "
                 f"pagamentos dos últimos 6 meses ({brl(media_6m)}/mês). "
                 f"Excedente: {brl(-limite_disponivel)}/mês.")
    else:
        st.success(f"Há {brl(limite_disponivel)}/mês de folga para novas compras.")

    st.divider()

    # ---- simulação de nova compra parcelada ----
    st.subheader("Simular nova compra")
    s1, s2, s3 = st.columns(3)
    with s1:
        fornecedor = st.text_input("Fornecedor (opcional)")
        valor_total = st.number_input("Valor total da compra (R$)",
                                      min_value=0.0, value=10000.0, step=500.0)
    with s2:
        data1 = st.date_input("Data da 1ª parcela", value=hoje)
        nparc = st.number_input("Nº de parcelas", min_value=1, max_value=60,
                                value=3, step=1)
    with s3:
        forma = st.selectbox("Forma de pagamento",
                             ["CHEQUE - EMPRESA", "CHEQUE - CLIENTE/TERCEIROS",
                              "BOLETO", "PIX", "CARTÃO", "DINHEIRO"])
        descricao = st.text_input("Descrição (opcional)")

    vparc = round(valor_total / nparc, 2) if nparc else 0.0

    # gerar cronograma de parcelas (lógica EDATE: vencimento mês a mês)
    base_dt = pd.Timestamp(data1)
    parcelas = []
    for i in range(int(nparc)):
        venc = base_dt + pd.DateOffset(months=i)
        parcelas.append({"Parcela": f"{i+1}/{int(nparc)}",
                         "Fornecedor": fornecedor.strip() or "-",
                         "Vencimento": venc,
                         "Forma de Pagamento": forma,
                         "Valor": vparc,
                         "Descrição": descricao.strip() or "-",
                         "Status": "SIMULAÇÃO"})
    df_parc = pd.DataFrame(parcelas)

    # ---- veredito ----
    st.subheader("Resultado da simulação")
    r1, r2 = st.columns(2)
    r1.metric("Valor da parcela mensal", brl(vparc))
    r2.metric("Limite disponível/mês", brl(limite_disponivel))

    if limite_disponivel <= 0:
        st.error(f"❌ NÃO RECOMENDADO — o limite já está estourado em "
                 f"{brl(-limite_disponivel)}/mês antes mesmo desta compra.")
    elif vparc <= limite_disponivel:
        st.success(f"✅ APROVADO — a parcela de {brl(vparc)} cabe no limite "
                   f"disponível. Folga restante: {brl(limite_disponivel - vparc)}/mês.")
    else:
        st.error(f"❌ NÃO RECOMENDADO — a parcela de {brl(vparc)} ultrapassa o "
                 f"limite disponível em {brl(vparc - limite_disponivel)}/mês.")

    # cronograma gerado
    with st.expander("Ver cronograma das parcelas simuladas"):
        show = df_parc.copy()
        show["Vencimento"] = show["Vencimento"].dt.strftime("%d/%m/%Y")
        show["Valor"] = show["Valor"].apply(brl)
        st.dataframe(show, use_container_width=True, hide_index=True)
        csv = df_parc.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ Baixar cronograma (CSV)", csv,
                           file_name="parcelas_simuladas.csv", mime="text/csv")

    # ---- dashboard: compromissos por mês (existentes + simulação) ----
    st.divider()
    st.subheader("Contas a pagar por mês (próximos meses + simulação)")
    horizonte = hoje + pd.DateOffset(months=12)
    fut = contas[(contas["Vencimento"] >= hoje) &
                 (contas["Vencimento"] < horizonte)][["Vencimento", "Valor"]].copy()
    fut["Origem"] = "Já comprometido"
    sim = df_parc[["Vencimento", "Valor"]].copy()
    sim["Origem"] = "Nova compra (simulação)"
    tudo = pd.concat([fut, sim], ignore_index=True)
    tudo["Mes"] = tudo["Vencimento"].dt.strftime("%m/%Y")
    tudo["MesOrd"] = tudo["Vencimento"].dt.year * 100 + tudo["Vencimento"].dt.month
    piv = (tudo.pivot_table(index=["MesOrd", "Mes"], columns="Origem",
                            values="Valor", aggfunc="sum", fill_value=0)
           .reset_index().sort_values("MesOrd"))
    piv = piv.drop(columns=["MesOrd"]).set_index("Mes")
    st.bar_chart(piv)
    pivf = piv.copy()
    for c in pivf.columns:
        pivf[c] = pivf[c].apply(brl)
    st.dataframe(pivf, use_container_width=True)
    st.caption(f"Linha de referência: limite mensal = {brl(media_6m)} "
               f"(média paga nos últimos 6 meses).")

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
