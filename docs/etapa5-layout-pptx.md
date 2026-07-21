# Etapa 5 — Layout alinhado ao PPTX

Esta etapa reformula a interface com base no arquivo `docs/layout/LAYOUT_ORC_RBT.pptx`.

## O que mudou na usabilidade

1. **Menu principal** com 3 entradas: Novo ORC, Cadastros, Histórico de Vendas
2. **Novo Orçamento em 2 colunas**
   - Esquerda: cliente, formulários, totais, PDF
   - Direita: prévia da proposta (atualiza sozinha)
3. **Popups** para cliente, cliente avulso, condições gerais e memória de cálculo
4. **Cadastros** com CRUD + campo `nome de exibição ... ORC`
5. **Valores nativos** (empresa no cabeçalho, prazo entrega 5 dias, orçamentista, logos…)
6. **Histórico de vendas** agrupado por NF
7. **Geração de PDF** da proposta

## Regra de descrição

Etiqueta:

`Etiqueta {mp ORC} {faca ORC} - Rolo com {qtd/rolo} - {tubete ORC}`

Suprimentos: descrição digitada.

## Como atualizar e rodar

```powershell
cd C:\Users\dani_\ORC_Ribb
git fetch origin
git checkout cursor/etapa5-layout-pptx-3237
git pull origin cursor/etapa5-layout-pptx-3237

.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.db.migrate
python -m streamlit run app.py
```

## Importante

1. Em **Cadastros → Valores Nativos**, preencha os dados da empresa (cabeçalho).
2. Ajuste os nomes de exibição ORC de matéria-prima, tubete e faca.
3. Faça upload das logos (master / cabeçalho / rodapé).
