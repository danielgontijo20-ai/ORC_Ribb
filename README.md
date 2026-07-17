# ORC_Ribb

Sistema para geração de orçamentos da empresa (etiquetas e suprimentos).

## Stack escolhida

- **Python** — linguagem principal
- **Streamlit** — interface web (próximas etapas)
- **SQLite** — banco de dados local
- **pandas + openpyxl** — leitura da planilha Excel

## Estrutura atual

```
ORC_Ribb/
├── data/
│   ├── planilhas/Banco_RBT.xlsx
│   └── database/orc_ribb.db
├── docs/
│   └── etapa3-banco-de-dados.md
├── src/
│   ├── db/                 # schema, conexão e importação
│   └── services/           # regras de negócio
├── requirements.txt
└── README.md
```

## Como preparar o ambiente (passo a passo)

### 1) Entrar na pasta do projeto

```bash
cd ORC_Ribb
```

### 2) Criar um ambiente virtual (recomendado)

```bash
python -m venv .venv
```

Ativar:

- Windows (PowerShell): `.venv\Scripts\Activate.ps1`
- Windows (CMD): `.venv\Scripts\activate.bat`
- Mac/Linux: `source .venv/bin/activate`

### 3) Instalar dependências

```bash
python -m pip install -r requirements.txt
```

### 4) Importar a planilha para o banco

```bash
python -m src.db.import_banco_rbt
```

Ao terminar, o arquivo `data/database/orc_ribb.db` será criado/atualizado.

## O que já está pronto (Etapa 3)

- Planilha organizada em `data/planilhas/Banco_RBT.xlsx`
- Banco SQLite com cadastros e histórico de faturamento
- Consulta de **última venda do produto para o cliente**
- Base para o grid de itens já vendidos ao cliente

## Próximos passos

1. Tela Streamlit para escolher cliente
2. Grid de busca de produtos vendidos ao cliente
3. Cálculo de orçamento de etiquetas e suprimentos
4. Pré-orçamento final com lucro total

Leia também: [docs/etapa3-banco-de-dados.md](docs/etapa3-banco-de-dados.md)
