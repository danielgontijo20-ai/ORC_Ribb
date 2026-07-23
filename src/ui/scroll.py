"""Utilitário para acompanhar expansão da tela (scroll suave)."""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components


def marcar_scroll_form() -> None:
    """Pede scroll na próxima renderização (ao abrir formulário expandido)."""
    st.session_state["_scroll_form"] = True


def aplicar_scroll_se_pedido(*, ancora: str = "orc-expand-anchor") -> None:
    """Se houver pedido de scroll, centraliza a âncora / último card."""
    if not st.session_state.get("_scroll_form"):
        return
    st.session_state["_scroll_form"] = False
    st.markdown(f'<div id="{ancora}"></div>', unsafe_allow_html=True)
    components.html(
        f"""
        <script>
        (function() {{
          const doc = window.parent.document;
          const el = doc.getElementById("{ancora}");
          if (el) {{
            el.scrollIntoView({{ behavior: "smooth", block: "center" }});
            return;
          }}
          const blocks = doc.querySelectorAll('[data-testid="stVerticalBlockBorderWrapper"]');
          if (blocks.length) {{
            blocks[blocks.length - 1].scrollIntoView({{ behavior: "smooth", block: "center" }});
          }}
        }})();
        </script>
        """,
        height=0,
    )
