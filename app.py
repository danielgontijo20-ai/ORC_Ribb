"""
ORC_Ribb — Interface alinhada ao LAYOUT_ORC_RBT.pptx

Como rodar:
    python -m streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from src.db.database import DB_PATH, connect
from src.db.migrate import migrate
from src.ui.cadastros_ui import render_cadastros
from src.ui.historico_ui import render_historico
from src.ui.menu import render_menu
from src.ui.novo_orcamento import render_novo_orcamento
from src.ui.state import init_state
from src.ui.styles import APP_CSS


def main() -> None:
    st.set_page_config(
        page_title="ORC_Ribb",
        page_icon="🏷️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(APP_CSS, unsafe_allow_html=True)

    if not DB_PATH.exists():
        st.error(
            "Banco não encontrado. Rode no terminal:\n\n"
            "`python -m src.db.import_banco_rbt`"
        )
        return

    # Migração leve (só uma vez por sessão) — evita lock desnecessário
    if not st.session_state.get("_migrated"):
        migrate(DB_PATH)
        st.session_state._migrated = True

    with connect() as conn:
        init_state(conn)
        total_cli = conn.execute("SELECT COUNT(*) c FROM clientes").fetchone()["c"]
        if total_cli == 0:
            st.error(
                "Banco vazio. Importe a planilha:\n\n"
                "`python -m src.db.import_banco_rbt`"
            )
            return

        tela = st.session_state.get("tela", "menu")
        if tela == "menu":
            render_menu(conn)
        elif tela == "novo_orcamento":
            render_novo_orcamento(conn)
        elif tela == "cadastros":
            render_cadastros(conn)
        elif tela == "historico":
            render_historico(conn)
        else:
            st.session_state.tela = "menu"
            st.rerun()


if __name__ == "__main__":
    main()
