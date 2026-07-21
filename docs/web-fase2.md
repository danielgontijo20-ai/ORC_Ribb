# Adaptação Web — Fase 2 (formação de orçamento)

## O que entrou
- Tela **Novo Orçamento** completa na web (etiqueta + suprimento)
- Seleção de cliente / cliente avulso
- Condições gerais de fornecimento
- Inserção/remoção de itens com os **mesmos cálculos** da versão 1
- Salvar orçamento (status Orçamento gerado) e Gerar PDF
- Memória de cálculo (tela + PDF)
- Continuar/editar orçamento a partir do detalhe
- Cadastros → **Valores Nativos** (edição web)

## Como usar
1. Login → Menu → Novo Orçamento
2. Selecionar cliente
3. Inserir etiqueta ou suprimento
4. Salvar orçamento → Gerar PDF

## Persistência do rascunho
- Após o 1º item, o rascunho fica no SQLite
- A sessão guarda só o `id` do orçamento (evita limite de cookie)

## Ainda na sequência (fase 3)
- ~~Edição de cadastros na web~~ → ver `docs/web-fase3.md`
- ~~Gestão de usuários na interface~~ → ver `docs/web-fase3.md`
- PostgreSQL/MySQL (opcional em produção)
