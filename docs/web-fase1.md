# Adaptação Web — Fase 1

## Backup
- Tag: `versao01`
- Branch: `cursor/versao01-3237`

## Stack web
- FastAPI + Jinja2 + sessões
- Mesmo banco SQLite atual (`data/database/orc_ribb.db`)
- Reutiliza `src/services/*` (cálculos, PDF, orçamentos, cadastros)

## Rodar local (web)
```bash
python -m pip install -r requirements.txt
python -m src.db.migrate
python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
```
Abra `http://localhost:8000/login`

## Usuário padrão
- admin@ribbontech.com / admin123

## Papéis
- admin
- orcamentista
- aprovador
- consulta

## O que já funciona na web
- Login / logout
- Menu com permissões
- Histórico de orçamentos + filtros
- Detalhe, aprovar, gerar PDF
- Cadastros (consulta)
- Histórico de vendas (lista)

## Próxima fase
- Formulário completo de novo orçamento (etiqueta/suprimento) na web
- Edição de cadastros na web
- Gestão de usuários na interface
- PostgreSQL/MySQL em produção (opcional/recomendado)
