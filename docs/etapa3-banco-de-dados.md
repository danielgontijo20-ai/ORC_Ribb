# Etapa 3 — Banco de dados e importação da planilha

Esta etapa transforma a planilha `Banco_RBT.xlsx` em um banco SQLite.

## Por que SQLite?

- É um banco em **um único arquivo** (`data/database/orc_ribb.db`)
- Não precisa instalar MySQL/PostgreSQL para começar
- Perfeito para aprender e para um sistema interno

## O que foi criado

```
data/
  planilhas/Banco_RBT.xlsx   ← planilha oficial
  database/orc_ribb.db       ← banco gerado pela importação
src/db/
  schema.sql                 ← desenho das tabelas
  database.py                ← conexão com o banco
  import_banco_rbt.py        ← lê a planilha e grava no banco
src/services/
  historico_vendas.py        ← consulta última venda por cliente+produto
```

## Como as abas viraram tabelas

| Aba Excel | Tabela SQLite |
|---|---|
| Faturamento | `faturamento` + `clientes` |
| Materia_Prima | `materias_primas` |
| Tubetes | `tubetes` |
| Caixas | `caixas` |
| Facas | `facas` |
| Segmento | `segmentos` + `produtos` |
| ORC_Etiqueta / ORC_Suprimentos | regras de cálculo (próximas etapas) |

Também já existem as tabelas `orcamentos` e `orcamento_itens` (ainda vazias),
para as telas de orçamento.

## Como rodar a importação

Na pasta do projeto:

```bash
python -m pip install -r requirements.txt
python -m src.db.import_banco_rbt
```

Isso:
1. apaga o banco antigo (se existir)
2. cria as tabelas
3. importa todos os cadastros e o histórico
4. mostra um resumo das quantidades

## Regra importante já preparada

Quando formos orçar:

1. escolhemos o **cliente**
2. abrimos um **grid** com itens já vendidos a esse cliente
3. ao selecionar o produto, mostramos a **última venda desse produto para esse cliente**

Essa consulta está em `src/services/historico_vendas.py`.

## Próxima etapa

Etapa 4: criar a interface Streamlit (selecionar cliente, buscar produtos e montar o pré-orçamento).
