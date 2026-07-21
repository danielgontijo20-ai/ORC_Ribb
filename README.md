# ORC_Ribb

Sistema para geração de orçamentos da empresa (etiquetas e suprimentos).

## Stack

- **Python**
- **Streamlit** (interface)
- **SQLite** (banco local)
- **pandas + openpyxl** (importação da planilha)

## Estrutura

```
ORC_Ribb/
├── app.py                      ← tela Streamlit
├── data/
│   ├── planilhas/Banco_RBT.xlsx
│   └── database/orc_ribb.db
├── docs/
│   ├── etapa3-banco-de-dados.md
│   └── etapa4-interface-streamlit.md
├── src/
│   ├── db/                     ← banco e importação
│   ├── services/               ← regras de negócio e cálculos
│   └── ui/                     ← helpers da interface
└── requirements.txt
```

## Preparar o ambiente (Windows)

```powershell
cd C:\Users\dani_\ORC_Ribb
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.db.import_banco_rbt
```

## Rodar o sistema

```powershell
streamlit run app.py
```

Abre no navegador: `http://localhost:8501`

## Fluxo atual

1. Selecionar cliente (ou avulso)
2. Buscar produto no histórico do cliente (grid + filtros)
3. Ver preço da última venda **daquele produto para aquele cliente**
4. Calcular orçamento de Etiqueta ou Suprimentos
5. Salvar itens no pré-orçamento
6. Ver valor total e lucro total

## Documentação didática

- [Etapa 3 — Banco e importação](docs/etapa3-banco-de-dados.md)
- [Etapa 4 — Interface Streamlit](docs/etapa4-interface-streamlit.md)
