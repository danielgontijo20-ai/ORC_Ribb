"""Grade clicável — seleção por clique em qualquer região da linha."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


def dataframe_selecionavel(
    df: pd.DataFrame,
    *,
    key: str,
    height: int = 320,
) -> int | None:
    """
    Exibe grade com seleção de linha única.
    Com AgGrid: clique em qualquer célula da linha seleciona.
    Fallback: st.dataframe + clique na linha/checkbox.
    """
    if df is None or df.empty:
        return None

    idx = _via_aggrid(df, key=key, height=height)
    if st.session_state.get(f"{key}__backend") == "aggrid":
        return idx

    return _via_streamlit_df(df, key=key, height=height)


def _via_aggrid(df: pd.DataFrame, *, key: str, height: int) -> int | None:
    try:
        from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
    except ImportError:
        return None

    st.session_state[f"{key}__backend"] = "aggrid"
    st.caption("Clique em qualquer célula da linha para selecionar.")

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection(
        selection_mode="single",
        use_checkbox=True,
    )
    gb.configure_grid_options(
        rowSelection="single",
        suppressRowClickSelection=False,
        animateRows=False,
    )
    gb.configure_default_column(resizable=True, filterable=True, sortable=True)

    grid = AgGrid(
        df.reset_index(drop=True),
        gridOptions=gb.build(),
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        height=height,
        theme="streamlit",
        fit_columns_on_grid_load=True,
        key=key,
        reload_data=False,
    )

    selected = grid.get("selected_rows")
    if selected is None:
        return None
    if isinstance(selected, pd.DataFrame):
        if selected.empty:
            return None
        row = selected.iloc[0].to_dict()
    elif isinstance(selected, list) and selected:
        row = selected[0]
        if not isinstance(row, dict):
            return None
    else:
        return None

    # AgGrid inclui às vezes '_selectedRowNodeInfo'
    row = {k: v for k, v in row.items() if not str(k).startswith("_")}
    return _match_row_index(df.reset_index(drop=True), row)


def _match_row_index(df: pd.DataFrame, row: dict[str, Any]) -> int | None:
    cols = [c for c in df.columns if c in row]
    if not cols:
        return None
    for i, (_, series) in enumerate(df.iterrows()):
        ok = True
        for col in cols:
            a, b = series[col], row[col]
            if pd.isna(a) and (b is None or b == "" or (isinstance(b, float) and pd.isna(b))):
                continue
            if str(a).strip() != str(b).strip():
                ok = False
                break
        if ok:
            return i
    return None


def _via_streamlit_df(df: pd.DataFrame, *, key: str, height: int) -> int | None:
    st.session_state[f"{key}__backend"] = "streamlit"
    st.caption("Clique na linha (ou no checkbox) para selecionar.")

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=False,
        height=height,
        on_select="rerun",
        selection_mode="single-row",
        key=key,
    )

    # Tenta fazer o clique na célula acionar o checkbox da linha
    components.html(
        """
        <script>
        (function() {
          const doc = window.parent.document;
          function wire() {
            doc.querySelectorAll('[data-testid="stDataFrame"] tbody tr').forEach(tr => {
              if (tr.dataset.orcRowWired) return;
              tr.dataset.orcRowWired = '1';
              tr.style.cursor = 'pointer';
              tr.addEventListener('click', function(e) {
                if (e.target.closest('input, button, a, label')) return;
                const cb = tr.querySelector('input[type="checkbox"]');
                if (cb) cb.click();
              });
            });
          }
          wire();
          setTimeout(wire, 400);
          setTimeout(wire, 1000);
        })();
        </script>
        """,
        height=0,
    )

    try:
        rows = event.selection.rows  # type: ignore[attr-defined]
    except Exception:
        rows = []
    if rows:
        return int(rows[0])
    return None
