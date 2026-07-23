# Adaptação Web — Fase 3 (cadastros + usuários + contraste)

## O que entrou
- CRUD web completo: clientes, matérias-primas, tubetes, facas, caixas, suprimentos
- Valores Nativos (já na fase 2)
- Gestão de usuários (criar/editar, papel, ativo, senha)
- Ajuste de contraste em botões, campos, tabelas e alertas

## Papéis
- admin — tudo, inclusive usuários
- orcamentista — orçamentos + cadastros
- aprovador — aprovar / PDF / histórico
- consulta — leitura

## Como testar
```bash
git checkout cursor/web-fase3-cadastros-usuarios-3237
python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
```
Menu → Cadastros → editar um item  
Menu → Usuários → criar usuário (admin)
