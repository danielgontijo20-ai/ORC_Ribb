"""Grade clicável (seleção de linha) para telas de pesquisa."""

from __future__ import annotations

import pandas as pd
import streamlit as st


def dataframe_selecionavel(
    df: pd.DataFrame,
    *,
    key: str,
    height: int = 320,
) -> int | None:
    """
    Exibe um dataframe com seleção de linha única.
    Retorna o índice da linha selecionada (ou None).
    """
    if df is None or df.empty:
        return None

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=height,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )
    try:
        rows = event.selection.rows  # type: ignore[attr-defined]
    except Exception:
        rows = []
    if rows:
        return int(rows[0])
    return None
