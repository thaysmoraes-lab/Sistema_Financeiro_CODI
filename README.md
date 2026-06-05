# Sistema de Gestão Financeira — App Streamlit

App de visualização que lê o arquivo `sistema_financeiro.xlsx` e recalcula tudo ao vivo:
Fluxo de Caixa, DRE Gerencial, Simulador de Compra (com desconto de parcelas ativas)
e Régua de Crédito.

## Arquivos do repositório

```
seu-repositorio/
├── app.py                      # o aplicativo Streamlit
├── requirements.txt            # dependências
├── logo_codi.png               # logo CODI.COM exibida no app
└── sistema_financeiro.xlsx     # seus dados (aba "Lançamentos" é a fonte)
```

Os quatro arquivos precisam ficar na **raiz** do repositório.

## Como publicar no Streamlit Cloud (grátis)

1. Crie um repositório no GitHub e suba os três arquivos acima.
2. Acesse https://share.streamlit.io e faça login com o GitHub.
3. Clique em **New app**, escolha seu repositório, branch `main` e arquivo `app.py`.
4. Clique em **Deploy**. Em alguns minutos o app fica no ar com um link público.

## Como rodar no seu computador

```bash
pip install -r requirements.txt
streamlit run app.py
```

O navegador abre sozinho em `http://localhost:8501`.

## Como funciona

O app lê **apenas a aba "Lançamentos"** do Excel — ela é a fonte de verdade.
Fluxo de Caixa, DRE e os demais painéis são **calculados em Python** a partir dela,
então estão sempre corretos e atualizados (diferente do Excel, que pode ficar com
fórmulas "congeladas").

Para atualizar os dados: edite os Lançamentos no Excel, suba a nova versão do
`.xlsx` no GitHub, e o app recarrega automaticamente.

## Classificação da DRE

Os grupos da DRE (Operacional, Pessoal, Administrativas, Financeiras, etc.) estão
definidos no início do `app.py`, nas listas `CUSTO`, `OPER`, `PESSOAL`, `FINANC` e
`RETIRADAS`. Para mover uma categoria de grupo, basta editar essas listas.
Qualquer categoria não listada cai automaticamente em "Despesas Administrativas".
