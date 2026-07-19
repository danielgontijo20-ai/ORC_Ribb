# Backup Versão 01

Snapshot do sistema **antes** da adaptação web.

## Como recuperar

### Opção A — tag Git
```bash
git fetch --tags
git checkout versao01
```

### Opção B — branch de snapshot
```bash
git fetch origin
git checkout cursor/versao01-3237
```

## O que era a Versão 01
- Python + Streamlit + SQLite local
- Telas: menu, novo orçamento, cadastros, históricos
- Sem login web / sem multi-usuário

## Rodar a Versão 01 (Streamlit)
```bash
python -m pip install -r requirements.txt
python -m src.db.migrate
python -m streamlit run app.py
```
