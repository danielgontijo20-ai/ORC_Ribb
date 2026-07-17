# Etapa 4 — Interface Streamlit

Nesta etapa criamos a **tela do sistema** para elaborar orçamentos.

## O que você consegue fazer agora

1. Selecionar um **cliente cadastrado** (busca por nome/CNPJ) ou **cliente avulso**
2. Abrir o **grid** com itens já vendidos para aquele cliente
3. Pesquisar por texto e filtrar por **segmento**
4. Selecionar produto e ver o **preço da última venda para aquele cliente**
5. Calcular item do tipo **Etiqueta** ou **Suprimentos**
6. Salvar vários itens no **pré-orçamento**
7. Ver **valor total** e **lucro total**

## Como rodar no seu computador

Na pasta do projeto:

```bash
cd C:\Users\dani_\ORC_Ribb
git fetch origin
git checkout cursor/etapa4-interface-streamlit-3237
git pull origin cursor/etapa4-interface-streamlit-3237

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.db.import_banco_rbt
streamlit run app.py
```

O navegador deve abrir em `http://localhost:8501`.

## Como usar a tela (passo a passo)

### Aba Cliente
- Pesquise e confirme o cliente
- Ou marque cliente avulso

### Aba Produto
- Veja o grid do histórico daquele cliente
- Filtre por texto/segmento
- Confirme o produto
- Se não houver histórico, use **Item avulso**

### Aba Calcular
- Veja o comparativo da última venda
- Escolha Etiqueta ou Suprimentos
- Ajuste os parâmetros
- Clique em **Salvar item no pré-orçamento**

### Aba Pré-orçamento
- Veja todos os itens salvos
- Confira valor total e lucro total
- Remova itens se necessário

## Arquivos novos

- `app.py` — tela principal Streamlit
- `src/services/clientes.py` — busca de clientes
- `src/services/cadastros.py` — facas, matérias, tubetes, caixas
- `src/services/calculos_orcamento.py` — fórmulas da planilha
- `src/ui/formatters.py` — formatação de valores

## Próxima etapa (ideia)

- Salvar o orçamento no banco (`orcamentos` / `orcamento_itens`)
- Gerar PDF/Excel do orçamento
- Melhorias de usabilidade na tela
