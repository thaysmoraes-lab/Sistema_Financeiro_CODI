import { useState, useEffect, useRef } from "react";

const STORAGE_KEY = "financeiro:dados";

const CATEGORIAS = [
  "Mercado", "Alimentação", "Combustível", "Transporte", "Moradia", "Saúde",
  "Farmácia", "Seguros", "Utilidades", "Pets", "Vestuário", "Lazer",
  "Assinaturas", "Educação", "Cartão de crédito", "Empréstimo/Financiamento",
  "Juros e encargos", "Outros",
];

const FORMAS = [
  "PIX", "Dinheiro", "Débito", "Cartão Bradesco", "Cartão Inter",
  "Cartão Nubank", "Mercado Pago", "Boleto", "Débito automático",
];

const SEED = {
  mesRef: "2026-09",
  receitas: [
    { id: "r1", fonte: "Salário Thays — TOTVS", titular: "Thays", natureza: "Fixa", previsto: 10880 },
    { id: "r2", fonte: "Salário Nayara — TOTVS", titular: "Nayara", natureza: "Fixa", previsto: 5600 },
    { id: "r3", fonte: "Salário Thays — CODI", titular: "Thays", natureza: "Fixa", previsto: 3500 },
    { id: "r4", fonte: "Horas extras / Tickets extras", titular: "Thays", natureza: "Variável", previsto: 0 },
  ],
  compromissos: [
    { id: "c1", nome: "Empréstimo Bradesco", categoria: "Empréstimo/Financiamento", previsto: 1888, venc: 10, nota: "12 parcelas restantes" },
    { id: "c2", nome: "Consórcio", categoria: "Empréstimo/Financiamento", previsto: 510, venc: 10, nota: "Encerra em dez/2026" },
    { id: "c3", nome: "Casa", categoria: "Moradia", previsto: 1100, venc: 5, nota: "" },
    { id: "c4", nome: "Carro", categoria: "Transporte", previsto: 1100, venc: 10, nota: "" },
    { id: "c5", nome: "Moto", categoria: "Transporte", previsto: 790, venc: 10, nota: "" },
    { id: "c6", nome: "Porto Seguro", categoria: "Seguros", previsto: 382, venc: 15, nota: "" },
    { id: "c7", nome: "Bradesco Seguros", categoria: "Seguros", previsto: 220, venc: 15, nota: "" },
    { id: "c8", nome: "Unimed Nayara", categoria: "Saúde", previsto: 395, venc: 20, nota: "" },
    { id: "c9", nome: "Unimed Thays", categoria: "Saúde", previsto: 495, venc: 20, nota: "" },
    { id: "c10", nome: "Cartão Inter", categoria: "Cartão de crédito", previsto: 3500, venc: 10, nota: "" },
    { id: "c11", nome: "Cartão Nubank", categoria: "Cartão de crédito", previsto: 1500, venc: 10, nota: "" },
    { id: "c12", nome: "Mercado Pago", categoria: "Cartão de crédito", previsto: 1350, venc: 10, nota: "" },
    { id: "c13", nome: "Cartão Bradesco", categoria: "Cartão de crédito", previsto: 8543.75, venc: 12, nota: "Calculado na planilha" },
    { id: "c14", nome: "Energia", categoria: "Utilidades", previsto: 38, venc: 15, nota: "" },
    { id: "c15", nome: "Água", categoria: "Utilidades", previsto: 100, venc: 15, nota: "" },
    { id: "c16", nome: "Internet", categoria: "Utilidades", previsto: 114, venc: 15, nota: "" },
  ],
  lancamentos: [],
};

const brl = (n) =>
  (Number(n) || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const hoje = () => new Date().toISOString().slice(0, 10);
const mesDe = (iso) => (iso || "").slice(0, 7);

const MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
  "agosto", "setembro", "outubro", "novembro", "dezembro"];
const rotuloMes = (m) => {
  const [a, mm] = (m || "").split("-");
  return mm ? `${MESES[Number(mm) - 1]} de ${a}` : m;
};

export default function ControleFinanceiro() {
  const [dados, setDados] = useState(SEED);
  const [carregando, setCarregando] = useState(true);
  const [erroStorage, setErroStorage] = useState(false);
  const [aba, setAba] = useState("registrar");

  useEffect(() => {
    (async () => {
      try {
        const res = await window.storage.get(STORAGE_KEY);
        if (res && res.value) setDados({ ...SEED, ...JSON.parse(res.value) });
      } catch {
        // primeira abertura: ainda não existe registro salvo
      }
      setCarregando(false);
    })();
  }, []);

  const salvar = async (novo) => {
    setDados(novo);
    try {
      const r = await window.storage.set(STORAGE_KEY, JSON.stringify(novo));
      setErroStorage(!r);
    } catch {
      setErroStorage(true);
    }
  };

  const mes = dados.mesRef;
  const doMes = dados.lancamentos.filter((l) => mesDe(l.data) === mes);

  const totalReceitasPrevistas = dados.receitas.reduce((s, r) => s + Number(r.previsto || 0), 0);
  const receitasRecebidas = doMes.filter((l) => l.tipo === "Receita").reduce((s, l) => s + l.valor, 0);
  const fixosPrevistos = dados.compromissos.reduce((s, c) => s + Number(c.previsto || 0), 0);
  const pagoPorCompromisso = (nome) =>
    doMes.filter((l) => l.compromisso === nome).reduce((s, l) => s + l.valor, 0);
  const fixosPagos = dados.compromissos.reduce((s, c) => s + pagoPorCompromisso(c.nome), 0);
  const variaveis = doMes
    .filter((l) => l.tipo === "Variável" && !l.compromisso)
    .reduce((s, l) => s + l.valor, 0);
  const saidasPrevistas = fixosPrevistos + variaveis;
  const saldo = totalReceitasPrevistas - saidasPrevistas;
  const dividas = dados.compromissos
    .filter((c) => c.categoria === "Cartão de crédito" || c.categoria === "Empréstimo/Financiamento")
    .reduce((s, c) => s + Number(c.previsto || 0), 0);
  const pctDividas = totalReceitasPrevistas ? dividas / totalReceitasPrevistas : 0;

  const ctx = {
    dados, salvar, mes, doMes, brl,
    totais: { totalReceitasPrevistas, receitasRecebidas, fixosPrevistos, fixosPagos,
      variaveis, saidasPrevistas, saldo, dividas, pctDividas },
    pagoPorCompromisso,
  };

  if (carregando) {
    return (
      <div className="lg-root">
        <Estilos />
        <div className="lg-vazio">Abrindo o livro…</div>
      </div>
    );
  }

  return (
    <div className="lg-root">
      <Estilos />
      <header className="lg-head">
        <div className="lg-head-top">
          <span className="lg-eyebrow">Livro de contas</span>
          <select
            className="lg-mes"
            value={mes}
            onChange={(e) => salvar({ ...dados, mesRef: e.target.value })}
          >
            {["2026-07", "2026-08", "2026-09", "2026-10", "2026-11", "2026-12", "2027-01"].map((m) => (
              <option key={m} value={m}>{rotuloMes(m)}</option>
            ))}
          </select>
        </div>
        <div className="lg-saldo-bloco">
          <span className="lg-label">Sobra prevista do mês</span>
          <span className={`lg-saldo ${saldo < 0 ? "neg" : "pos"}`}>
            {saldo < 0 ? "−" : ""}R$ {brl(Math.abs(saldo))}
          </span>
          <span className="lg-sub">
            R$ {brl(totalReceitasPrevistas)} de receita · R$ {brl(saidasPrevistas)} de saída
          </span>
        </div>
      </header>

      {erroStorage && (
        <p className="lg-aviso">
          O último registro não foi gravado. Anote o valor e tente salvar de novo.
        </p>
      )}

      <nav className="lg-abas">
        {[["registrar", "Registrar"], ["painel", "Painel"], ["lancamentos", "Lançamentos"],
          ["compromissos", "Compromissos"], ["receitas", "Receitas"]].map(([k, r]) => (
          <button key={k} onClick={() => setAba(k)} className={aba === k ? "lg-aba on" : "lg-aba"}>
            {r}
          </button>
        ))}
      </nav>

      <main className="lg-main">
        {aba === "registrar" && <Registrar ctx={ctx} />}
        {aba === "painel" && <Painel ctx={ctx} />}
        {aba === "lancamentos" && <Lancamentos ctx={ctx} />}
        {aba === "compromissos" && <Compromissos ctx={ctx} />}
        {aba === "receitas" && <Receitas ctx={ctx} />}
      </main>
    </div>
  );
}

/* ================= REGISTRAR (foto → valor) ================= */

function Registrar({ ctx }) {
  const { dados, salvar, mes } = ctx;
  const [imagem, setImagem] = useState(null);
  const [nomeArquivo, setNomeArquivo] = useState("");
  const [lendo, setLendo] = useState(false);
  const [erro, setErro] = useState("");
  const [confirmado, setConfirmado] = useState("");
  const inputRef = useRef(null);

  const vazio = {
    data: `${mes}-01`, descricao: "", categoria: "Mercado", tipo: "Variável",
    forma: "PIX", compromisso: "", valor: "", obs: "",
  };
  const [form, setForm] = useState(vazio);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const escolherArquivo = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setErro(""); setConfirmado("");
    setNomeArquivo(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      setImagem({ dataUrl: reader.result, media: file.type });
      lerComprovante(reader.result.split(",")[1], file.type);
    };
    reader.onerror = () => setErro("Não deu para abrir esse arquivo. Tente outra foto.");
    reader.readAsDataURL(file);
  };

  const lerComprovante = async (b64, media) => {
    setLendo(true); setErro("");
    try {
      const resp = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-6",
          max_tokens: 1000,
          messages: [{
            role: "user",
            content: [
              { type: "image", source: { type: "base64", media_type: media || "image/jpeg", data: b64 } },
              {
                type: "text",
                text:
                  "Leia este comprovante, cupom fiscal, nota ou print de pagamento brasileiro e devolva SOMENTE " +
                  "um objeto JSON, sem markdown, sem crases, sem texto antes ou depois, no formato:\n" +
                  '{"valor": number, "data": "AAAA-MM-DD", "estabelecimento": string, "categoria": string, "forma": string, "confianca": "alta"|"media"|"baixa"}\n\n' +
                  "Regras:\n" +
                  "- valor: o TOTAL pago, em número com ponto decimal. Ignore subtotais, troco e descontos já aplicados.\n" +
                  "- data: a data da compra. Se não houver, use string vazia.\n" +
                  "- estabelecimento: nome do lugar, curto.\n" +
                  "- categoria: escolha exatamente uma desta lista: " + CATEGORIAS.join(", ") + ".\n" +
                  "- forma: escolha uma desta lista se identificar, senão string vazia: " + FORMAS.join(", ") + ".\n" +
                  "- confianca: quão legível estava a imagem.",
              },
            ],
          }],
        }),
      });
      const data = await resp.json();
      const texto = (data.content || [])
        .filter((b) => b.type === "text").map((b) => b.text).join("\n");
      const limpo = texto.replace(/```json|```/g, "").trim();
      const inicio = limpo.indexOf("{");
      const fim = limpo.lastIndexOf("}");
      const lido = JSON.parse(limpo.slice(inicio, fim + 1));

      setForm((f) => ({
        ...f,
        valor: lido.valor ? String(lido.valor) : "",
        data: lido.data || f.data,
        descricao: lido.estabelecimento || "",
        categoria: CATEGORIAS.includes(lido.categoria) ? lido.categoria : "Outros",
        forma: FORMAS.includes(lido.forma) ? lido.forma : f.forma,
        obs: lido.confianca === "baixa" ? "Imagem pouco legível — confira o valor" : "",
      }));
    } catch {
      setErro("Não consegui ler os números dessa imagem. Preencha os campos à mão abaixo.");
    }
    setLendo(false);
  };

  const gravar = () => {
    const valor = Number(String(form.valor).replace(/\./g, "").replace(",", "."));
    if (!valor || !form.descricao.trim()) {
      setErro("Descrição e valor são obrigatórios.");
      return;
    }
    const novo = {
      ...dados,
      lancamentos: [
        { ...form, valor, id: `l${Date.now()}`, temFoto: !!imagem },
        ...dados.lancamentos,
      ],
    };
    salvar(novo);
    setConfirmado(`${form.descricao} · R$ ${brl(valor)} registrado`);
    setForm({ ...vazio, data: form.data });
    setImagem(null); setNomeArquivo(""); setErro("");
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <section>
      <h2 className="lg-h2">Registrar uma despesa</h2>
      <p className="lg-p">
        Fotografe o cupom ou o comprovante. O valor, a data e o estabelecimento entram sozinhos —
        você confere antes de gravar.
      </p>

      <div className="lg-captura">
        <label className="lg-btn-foto">
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            capture="environment"
            onChange={escolherArquivo}
            className="lg-file"
          />
          {imagem ? "Trocar foto" : "Tirar foto ou anexar imagem"}
        </label>
        {nomeArquivo && <span className="lg-arquivo">{nomeArquivo}</span>}
      </div>

      {imagem && (
        <div className="lg-preview">
          <img src={imagem.dataUrl} alt="Comprovante anexado" />
          {lendo && <div className="lg-lendo">Lendo o comprovante…</div>}
        </div>
      )}

      {erro && <p className="lg-erro">{erro}</p>}
      {confirmado && <p className="lg-ok">{confirmado}</p>}

      <div className="lg-form">
        <Campo rotulo="Descrição">
          <input className="lg-in" value={form.descricao}
            onChange={(e) => set("descricao", e.target.value)} placeholder="Onde foi a compra" />
        </Campo>
        <div className="lg-dupla">
          <Campo rotulo="Valor (R$)">
            <input className="lg-in mono" inputMode="decimal" value={form.valor}
              onChange={(e) => set("valor", e.target.value)} placeholder="0,00" />
          </Campo>
          <Campo rotulo="Data">
            <input className="lg-in mono" type="date" value={form.data}
              onChange={(e) => set("data", e.target.value)} />
          </Campo>
        </div>
        <div className="lg-dupla">
          <Campo rotulo="Categoria">
            <select className="lg-in" value={form.categoria} onChange={(e) => set("categoria", e.target.value)}>
              {CATEGORIAS.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Campo>
          <Campo rotulo="Forma de pagamento">
            <select className="lg-in" value={form.forma} onChange={(e) => set("forma", e.target.value)}>
              {FORMAS.map((c) => <option key={c}>{c}</option>)}
            </select>
          </Campo>
        </div>
        <div className="lg-dupla">
          <Campo rotulo="Tipo">
            <select className="lg-in" value={form.tipo} onChange={(e) => set("tipo", e.target.value)}>
              {["Variável", "Fixo", "Receita"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </Campo>
          <Campo rotulo="Quita qual compromisso">
            <select className="lg-in" value={form.compromisso} onChange={(e) => set("compromisso", e.target.value)}>
              <option value="">Nenhum</option>
              {dados.compromissos.map((c) => <option key={c.id} value={c.nome}>{c.nome}</option>)}
            </select>
          </Campo>
        </div>
        <Campo rotulo="Observação">
          <input className="lg-in" value={form.obs} onChange={(e) => set("obs", e.target.value)} />
        </Campo>
        <button className="lg-btn" onClick={gravar}>Gravar lançamento</button>
      </div>
    </section>
  );
}

function Campo({ rotulo, children }) {
  return (
    <label className="lg-campo">
      <span className="lg-label">{rotulo}</span>
      {children}
    </label>
  );
}

/* ================= PAINEL ================= */

function Painel({ ctx }) {
  const { totais: t, mes } = ctx;
  const pct = Math.round(t.pctDividas * 100);
  return (
    <section>
      <h2 className="lg-h2">Painel de {rotuloMes(mes)}</h2>
      <table className="lg-tabela">
        <tbody>
          <Linha rotulo="Receitas previstas" valor={t.totalReceitasPrevistas} />
          <Linha rotulo="Receitas já recebidas" valor={t.receitasRecebidas} suave />
          <Linha rotulo="Compromissos fixos" valor={t.fixosPrevistos} />
          <Linha rotulo="Fixos já pagos" valor={t.fixosPagos} suave />
          <Linha rotulo="Gastos variáveis lançados" valor={t.variaveis} />
          <Linha rotulo="Total de saídas" valor={t.saidasPrevistas} regra />
          <tr className="lg-total">
            <td>Sobra do mês</td>
            <td className={`mono ${t.saldo < 0 ? "neg" : "pos"}`}>
              {t.saldo < 0 ? "−" : ""}{brl(Math.abs(t.saldo))}
            </td>
          </tr>
        </tbody>
      </table>

      <div className="lg-medidor">
        <div className="lg-medidor-topo">
          <span className="lg-label">Da receita, quanto vai para dívida</span>
          <span className="mono lg-pct">{pct}%</span>
        </div>
        <div className="lg-barra">
          <div className="lg-barra-in" style={{ width: `${Math.min(pct, 100)}%` }} />
        </div>
        <p className="lg-nota">
          R$ {brl(t.dividas)} em cartões, empréstimo e consórcio, sobre R$ {brl(t.totalReceitasPrevistas)} de receita.
        </p>
      </div>
    </section>
  );
}

function Linha({ rotulo, valor, suave, regra }) {
  return (
    <tr className={`${suave ? "lg-suave" : ""} ${regra ? "lg-regra" : ""}`}>
      <td>{rotulo}</td>
      <td className="mono">{brl(valor)}</td>
    </tr>
  );
}

/* ================= LANÇAMENTOS ================= */

function Lancamentos({ ctx }) {
  const { dados, salvar, doMes, mes } = ctx;
  const [filtro, setFiltro] = useState("");

  const lista = doMes.filter(
    (l) =>
      !filtro ||
      l.descricao.toLowerCase().includes(filtro.toLowerCase()) ||
      l.categoria.toLowerCase().includes(filtro.toLowerCase())
  );

  const apagar = (id) =>
    salvar({ ...dados, lancamentos: dados.lancamentos.filter((l) => l.id !== id) });

  const baixarCSV = () => {
    const cab = ["Data", "Descrição", "Categoria", "Tipo", "Forma", "Compromisso", "Valor", "Observação"];
    const linhas = dados.lancamentos.map((l) =>
      [l.data, l.descricao, l.categoria, l.tipo, l.forma, l.compromisso || "",
       String(l.valor).replace(".", ","), l.obs || ""]
        .map((c) => `"${String(c).replace(/"/g, '""')}"`).join(";")
    );
    const csv = "\uFEFF" + [cab.join(";"), ...linhas].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `lancamentos-${mes}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section>
      <h2 className="lg-h2">Lançamentos de {rotuloMes(mes)}</h2>
      <div className="lg-barra-acoes">
        <input className="lg-in" placeholder="Buscar por descrição ou categoria"
          value={filtro} onChange={(e) => setFiltro(e.target.value)} />
        <button className="lg-btn-sec" onClick={baixarCSV}>Baixar CSV</button>
      </div>

      {lista.length === 0 ? (
        <p className="lg-vazio-txt">
          Nenhum lançamento neste mês ainda. Vá em Registrar e fotografe o primeiro comprovante.
        </p>
      ) : (
        <ul className="lg-lista">
          {lista.map((l) => (
            <li key={l.id} className="lg-item">
              <div className="lg-item-l">
                <span className="lg-item-desc">{l.descricao}</span>
                <span className="lg-item-meta">
                  {l.data.split("-").reverse().join("/")} · {l.categoria} · {l.forma}
                  {l.compromisso ? ` · quita ${l.compromisso}` : ""}
                  {l.temFoto ? " · com foto" : ""}
                </span>
                {l.obs && <span className="lg-item-obs">{l.obs}</span>}
              </div>
              <div className="lg-item-r">
                <span className={`mono ${l.tipo === "Receita" ? "pos" : ""}`}>{brl(l.valor)}</span>
                <button className="lg-apagar" onClick={() => apagar(l.id)} aria-label="Apagar lançamento">
                  apagar
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/* ================= COMPROMISSOS ================= */

function Compromissos({ ctx }) {
  const { dados, salvar, pagoPorCompromisso, totais } = ctx;

  const editar = (id, campo, valor) =>
    salvar({
      ...dados,
      compromissos: dados.compromissos.map((c) =>
        c.id === id ? { ...c, [campo]: campo === "previsto" ? Number(valor) || 0 : valor } : c
      ),
    });

  return (
    <section>
      <h2 className="lg-h2">Compromissos fixos</h2>
      <table className="lg-tabela larga">
        <thead>
          <tr>
            <th>Compromisso</th><th>Previsto</th><th>Pago</th><th>Situação</th>
          </tr>
        </thead>
        <tbody>
          {dados.compromissos.map((c) => {
            const pago = pagoPorCompromisso(c.nome);
            const sit = pago === 0 ? "em aberto" : pago + 0.01 >= c.previsto ? "pago" : "parcial";
            return (
              <tr key={c.id}>
                <td>
                  {c.nome}
                  {c.nota && <span className="lg-item-obs">{c.nota}</span>}
                </td>
                <td>
                  <input className="lg-in-mini mono" value={c.previsto}
                    onChange={(e) => editar(c.id, "previsto", e.target.value)} />
                </td>
                <td className="mono">{brl(pago)}</td>
                <td><span className={`lg-tag ${sit.replace("ç", "c").replace(" ", "")}`}>{sit}</span></td>
              </tr>
            );
          })}
          <tr className="lg-total">
            <td>Total</td>
            <td className="mono">{brl(totais.fixosPrevistos)}</td>
            <td className="mono">{brl(totais.fixosPagos)}</td>
            <td />
          </tr>
        </tbody>
      </table>
    </section>
  );
}

/* ================= RECEITAS ================= */

function Receitas({ ctx }) {
  const { dados, salvar, totais } = ctx;
  const editar = (id, valor) =>
    salvar({
      ...dados,
      receitas: dados.receitas.map((r) =>
        r.id === id ? { ...r, previsto: Number(valor) || 0 } : r
      ),
    });

  return (
    <section>
      <h2 className="lg-h2">Receitas</h2>
      <table className="lg-tabela larga">
        <thead>
          <tr><th>Fonte</th><th>Titular</th><th>Previsto</th></tr>
        </thead>
        <tbody>
          {dados.receitas.map((r) => (
            <tr key={r.id}>
              <td>
                {r.fonte}
                {r.natureza === "Variável" && <span className="lg-item-obs">varia todo mês</span>}
              </td>
              <td>{r.titular}</td>
              <td>
                <input className="lg-in-mini mono" value={r.previsto}
                  onChange={(e) => editar(r.id, e.target.value)} />
              </td>
            </tr>
          ))}
          <tr className="lg-total">
            <td>Total</td><td />
            <td className="mono">{brl(totais.totalReceitasPrevistas)}</td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

/* ================= ESTILO ================= */

function Estilos() {
  return (
    <style>{`
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Sans+Condensed:wght@600;700&display=swap');

.lg-root {
  --papel: #F3F5EC;
  --pauta: #C6D4C0;
  --tinta: #1B2A24;
  --tinta-suave: #5C6B63;
  --vermelho: #A32E28;
  --azul: #23486B;
  --verde: #2F6B45;
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
  color: var(--tinta);
  background: var(--papel);
  min-height: 100%;
  padding: 0 0 48px;
  line-height: 1.5;
}
.lg-root .mono { font-family: 'IBM Plex Mono', monospace; font-variant-numeric: tabular-nums; }
.lg-root .neg { color: var(--vermelho); }
.lg-root .pos { color: var(--verde); }

.lg-head { padding: 22px 20px 18px; border-bottom: 1px solid var(--pauta); }
.lg-head-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.lg-eyebrow {
  font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 700;
  text-transform: uppercase; letter-spacing: .16em; font-size: 11px; color: var(--tinta-suave);
}
.lg-mes {
  font-family: 'IBM Plex Mono', monospace; font-size: 13px; background: transparent;
  border: 1px solid var(--pauta); border-radius: 2px; padding: 4px 8px; color: var(--tinta);
}
.lg-saldo-bloco { margin-top: 16px; display: flex; flex-direction: column; gap: 2px; }
.lg-label {
  font-family: 'IBM Plex Sans Condensed', sans-serif; text-transform: uppercase;
  letter-spacing: .12em; font-size: 10.5px; color: var(--tinta-suave); font-weight: 600;
}
.lg-saldo {
  font-family: 'IBM Plex Mono', monospace; font-size: clamp(30px, 9vw, 44px);
  font-weight: 500; letter-spacing: -.02em; font-variant-numeric: tabular-nums;
}
.lg-sub { font-size: 12.5px; color: var(--tinta-suave); font-family: 'IBM Plex Mono', monospace; }

.lg-aviso, .lg-erro {
  margin: 12px 20px 0; padding: 9px 12px; font-size: 13px;
  border-left: 3px solid var(--vermelho); background: #F7EAE9; color: #6E1F1B;
}
.lg-ok {
  margin: 12px 0 0; padding: 9px 12px; font-size: 13px;
  border-left: 3px solid var(--verde); background: #E8F0E9; color: #1F4A2F;
}

.lg-abas {
  display: flex; gap: 0; overflow-x: auto; border-bottom: 1px solid var(--pauta);
  padding: 0 12px; background: var(--papel); position: sticky; top: 0; z-index: 5;
}
.lg-aba {
  font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 600; font-size: 13px;
  text-transform: uppercase; letter-spacing: .08em; background: none; border: none;
  padding: 13px 12px; color: var(--tinta-suave); cursor: pointer; white-space: nowrap;
  border-bottom: 2px solid transparent;
}
.lg-aba.on { color: var(--tinta); border-bottom-color: var(--vermelho); }
.lg-aba:focus-visible { outline: 2px solid var(--azul); outline-offset: -2px; }

.lg-main { padding: 20px; max-width: 720px; margin: 0 auto; }
.lg-h2 {
  font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 700; font-size: 19px;
  margin: 0 0 6px; letter-spacing: -.01em;
}
.lg-p { font-size: 13.5px; color: var(--tinta-suave); margin: 0 0 18px; }

.lg-captura { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.lg-btn-foto {
  display: inline-block; border: 1.5px dashed var(--pauta); border-radius: 3px;
  padding: 18px 20px; width: 100%; text-align: center; cursor: pointer;
  font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 600; font-size: 14px;
  text-transform: uppercase; letter-spacing: .08em; color: var(--azul); background: #FBFCF7;
}
.lg-btn-foto:hover { border-color: var(--azul); }
.lg-file { position: absolute; width: 1px; height: 1px; opacity: 0; }
.lg-arquivo { font-size: 12px; color: var(--tinta-suave); font-family: 'IBM Plex Mono', monospace; }

.lg-preview { margin-top: 14px; position: relative; border: 1px solid var(--pauta); }
.lg-preview img { width: 100%; display: block; max-height: 260px; object-fit: contain; background: #fff; }
.lg-lendo {
  position: absolute; inset: 0; display: grid; place-items: center;
  background: rgba(243,245,236,.9); font-family: 'IBM Plex Mono', monospace; font-size: 13px;
}

.lg-form { margin-top: 22px; display: flex; flex-direction: column; gap: 14px; }
.lg-campo { display: flex; flex-direction: column; gap: 5px; }
.lg-dupla { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.lg-in {
  font-family: 'IBM Plex Sans', sans-serif; font-size: 15px; padding: 9px 10px;
  border: 1px solid var(--pauta); border-radius: 2px; background: #FBFCF7; color: var(--tinta);
  width: 100%; box-sizing: border-box;
}
.lg-in:focus-visible { outline: 2px solid var(--azul); outline-offset: -1px; }
.lg-in-mini {
  font-size: 14px; padding: 5px 7px; border: 1px solid var(--pauta);
  background: #FBFCF7; width: 100px; border-radius: 2px; text-align: right;
}
.lg-btn {
  font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 700; font-size: 14px;
  text-transform: uppercase; letter-spacing: .1em; background: var(--tinta); color: var(--papel);
  border: none; padding: 14px; border-radius: 2px; cursor: pointer;
}
.lg-btn:hover { background: #0F1A15; }
.lg-btn-sec {
  font-family: 'IBM Plex Sans Condensed', sans-serif; font-weight: 600; font-size: 12.5px;
  text-transform: uppercase; letter-spacing: .08em; background: none; color: var(--azul);
  border: 1px solid var(--pauta); padding: 9px 12px; border-radius: 2px; cursor: pointer;
  white-space: nowrap;
}

.lg-tabela { width: 100%; border-collapse: collapse; font-size: 14.5px; }
.lg-tabela td, .lg-tabela th { padding: 10px 4px; border-bottom: 1px solid var(--pauta); text-align: left; }
.lg-tabela td:last-child, .lg-tabela th:last-child { text-align: right; }
.lg-tabela th {
  font-family: 'IBM Plex Sans Condensed', sans-serif; text-transform: uppercase;
  font-size: 10.5px; letter-spacing: .12em; color: var(--tinta-suave); font-weight: 600;
}
.lg-tabela.larga td:nth-child(2), .lg-tabela.larga th:nth-child(2) { text-align: right; }
.lg-suave td { color: var(--tinta-suave); font-size: 13px; }
.lg-regra td { border-bottom: 1px solid var(--tinta); }
.lg-total td {
  font-weight: 600; border-bottom: 3px double var(--vermelho); border-top: none;
  padding-top: 12px; font-size: 15.5px;
}

.lg-medidor { margin-top: 30px; }
.lg-medidor-topo { display: flex; justify-content: space-between; align-items: baseline; }
.lg-pct { font-size: 24px; font-weight: 500; }
.lg-barra { height: 8px; background: #E2E8DC; margin-top: 8px; position: relative; overflow: hidden; }
.lg-barra-in { height: 100%; background: var(--vermelho); }
.lg-nota { font-size: 12.5px; color: var(--tinta-suave); margin: 8px 0 0; }

.lg-barra-acoes { display: flex; gap: 10px; margin-bottom: 16px; }
.lg-lista { list-style: none; margin: 0; padding: 0; }
.lg-item {
  display: flex; justify-content: space-between; gap: 14px; align-items: flex-start;
  padding: 12px 0; border-bottom: 1px solid var(--pauta);
}
.lg-item-l { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.lg-item-desc { font-weight: 500; font-size: 15px; }
.lg-item-meta { font-size: 12px; color: var(--tinta-suave); font-family: 'IBM Plex Mono', monospace; }
.lg-item-obs { display: block; font-size: 11.5px; color: var(--vermelho); margin-top: 2px; }
.lg-item-r { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.lg-item-r .mono { font-size: 15px; }
.lg-apagar {
  background: none; border: none; font-size: 11px; color: var(--tinta-suave);
  cursor: pointer; text-decoration: underline; padding: 0;
}

.lg-tag {
  font-family: 'IBM Plex Sans Condensed', sans-serif; font-size: 10.5px; text-transform: uppercase;
  letter-spacing: .08em; padding: 3px 7px; border: 1px solid var(--pauta); border-radius: 2px;
}
.lg-tag.pago { color: var(--verde); border-color: var(--verde); }
.lg-tag.emaberto { color: var(--vermelho); border-color: var(--vermelho); }

.lg-vazio, .lg-vazio-txt {
  padding: 40px 20px; text-align: center; color: var(--tinta-suave); font-size: 14px;
}

@media (max-width: 480px) {
  .lg-dupla { grid-template-columns: 1fr; }
  .lg-barra-acoes { flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
    `}</style>
  );
}
