# ORC_Ribb

Sistema para geração de orçamentos (etiquetas e suprimentos).

## Stack

- **Versão 01 (local):** Python + Streamlit + SQLite  
- **Web (fase 3):** FastAPI + Jinja2 + login/permissões + orçamento + cadastros CRUD + usuários + SQLite  
- pandas / openpyxl / reportlab

## Backup Versão 01

```bash
git fetch --tags
git checkout versao01
# ou: git checkout cursor/versao01-3237
```

## Como rodar — Web (recomendado)

```powershell
cd C:\Users\dani_\ORC_Ribb
git fetch origin
git checkout cursor/web-fase3-cadastros-usuarios-3237
git pull origin cursor/web-fase3-cadastros-usuarios-3237

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.db.migrate
python -m uvicorn web.main:app --reload --host 0.0.0.0 --port 8000
```

Abre `http://localhost:8000/login`  
Usuário inicial: `admin@ribbontech.com` / `admin123`

## Como rodar — Streamlit (Versão 01)

```powershell
python -m streamlit run app.py
```

Abre em `http://localhost:8501`.

## Telas (layout PPTX)

1. **Menu** — Novo ORC | Cadastros | Histórico de Vendas  
2. **Novo Orçamento** — formação à esquerda + prévia da proposta à direita  
3. **Cadastros** — clientes, MP, tubetes, facas, caixas, valores nativos  
4. **Histórico** — vendas por cliente agrupadas por NF  

## Primeiro uso recomendado

1. Vá em **Cadastros → Valores Nativos**
2. Preencha os dados da empresa (aparecem no cabeçalho da proposta)
3. Confirme prazo de entrega nativo (**5 dias**) e demais padrões
4. Ajuste os **nomes de exibição ORC** de matéria-prima, tubete e faca
5. Elabore um orçamento em **Novo ORC**

## Documentação

- `docs/etapa3-banco-de-dados.md`
- `docs/etapa4-interface-streamlit.md`
- `docs/etapa5-layout-pptx.md`
- `docs/web-fase1.md` / `docs/web-fase2.md` / `docs/web-fase3.md`
- `docs/deploy-hostinger-vps.md`
- `docs/layout/LAYOUT_ORC_RBT.pptx`
