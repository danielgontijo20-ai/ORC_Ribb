"""Telas de cadastros (slides 9–15)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.db.database import ROOT_DIR
from src.services.cadastros import (
    excluir_caixa,
    excluir_cliente,
    excluir_faca,
    excluir_materia,
    excluir_suprimento,
    excluir_tubete,
    listar_caixas,
    listar_facas,
    listar_materias_primas,
    listar_suprimentos,
    listar_tubetes,
    salvar_caixa,
    salvar_faca,
    salvar_materia,
    salvar_suprimento,
    salvar_tubete,
    upsert_cliente,
)
from src.services.clientes import buscar_clientes, contar_clientes
from src.services.configuracoes import carregar_config, salvar_config
from src.ui.grid_select import dataframe_selecionavel
from src.ui.state import consumir_flash, flash_sucesso, voltar


LOGO_DIR = ROOT_DIR / "data" / "logos"


def _cad_seq() -> int:
    return int(st.session_state.get("cad_form_seq") or 0)


def _bump_cad_seq() -> None:
    """Invalida select + campos (novas keys = formulário vazio em (novo))."""
    st.session_state.cad_form_seq = _cad_seq() + 1
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and (
            k.endswith("_grid_last")
            or k.endswith("_grid")
            or k.startswith("cad_editing_")
            or k.startswith("_last_modo_")
        ):
            del st.session_state[k]


def _entrar_tela(tela: str) -> None:
    """Abre subtela limpa: (novo), sem seleção na grade, sem modo edição."""
    st.session_state.cadastro_tela = tela
    _bump_cad_seq()
    st.session_state[f"cad_editing_{tela}"] = False
    st.rerun()


def _sel_key(base: str) -> str:
    return f"{base}_{_cad_seq()}"


def _form_key(prefix: str, atual) -> str:
    rid = atual["id"] if atual is not None else "novo"
    return f"{prefix}_{rid}_{_cad_seq()}"


def _init_widget(key: str, default) -> None:
    if key not in st.session_state:
        st.session_state[key] = default


def _text_input(label: str, key: str, default: str = "", *, disabled: bool = False, **kwargs):
    _init_widget(key, default)
    return st.text_input(label, key=key, disabled=disabled, **kwargs)


def _number_input(
    label: str, key: str, default: float = 0.0, *, disabled: bool = False, **kwargs
):
    _init_widget(key, float(default) if default is not None else 0.0)
    return st.number_input(label, key=key, disabled=disabled, **kwargs)


def _text_area(label: str, key: str, default: str = "", *, disabled: bool = False, **kwargs):
    _init_widget(key, default)
    return st.text_area(label, key=key, disabled=disabled, **kwargs)


def _edit_key(tela: str) -> str:
    return f"cad_editing_{tela}"


def _is_editing(tela: str) -> bool:
    return bool(st.session_state.get(_edit_key(tela), False))


def _set_editing(tela: str, on: bool) -> None:
    st.session_state[_edit_key(tela)] = on


def _campos_bloqueados(tela: str, atual) -> bool:
    """Registro existente fica bloqueado até clicar em Editar cadastro."""
    if atual is None:
        return False
    return not _is_editing(tela)


def _ao_mudar_registro(tela: str, modo: str) -> None:
    """Troca de registro: existente = visualização; (novo) = edição liberada."""
    last_key = f"_last_modo_{tela}"
    if st.session_state.get(last_key) != modo:
        st.session_state[last_key] = modo
        _set_editing(tela, modo == "(novo)")


def _botoes_crud(
    tela: str,
    *,
    atual,
    on_salvar,
    on_excluir=None,
    label_salvar: str = "Salvar",
) -> None:
    bloqueado = _campos_bloqueados(tela, atual)
    if atual is None:
        if st.button(label_salvar, type="primary", key=f"btn_salvar_{tela}"):
            on_salvar()
        return

    if bloqueado:
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("Editar cadastro", type="primary", key=f"btn_editar_{tela}"):
                _set_editing(tela, True)
                st.rerun()
        with b2:
            if on_excluir and st.button("Excluir", key=f"btn_excluir_{tela}"):
                on_excluir()
        with b3:
            st.caption("Campos bloqueados — clique em Editar para alterar.")
    else:
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button(label_salvar, type="primary", key=f"btn_salvar_{tela}"):
                on_salvar()
        with b2:
            if st.button("Cancelar edição", key=f"btn_cancel_{tela}"):
                _set_editing(tela, False)
                _bump_cad_seq()
                # Mantém o mesmo registro selecionado após cancelar
                if atual is not None:
                    # caller deve repor o select — usamos id no session
                    st.session_state["_restore_sel"] = {
                        "tela": tela,
                        "id": atual["id"],
                    }
                st.rerun()
        with b3:
            if on_excluir and st.button("Excluir", key=f"btn_excluir_{tela}"):
                on_excluir()


def render_cadastros(conn) -> None:
    top1, top2 = st.columns([4, 1])
    with top1:
        st.markdown('<p class="orc-title">Cadastros</p>', unsafe_allow_html=True)
    with top2:
        if st.button("← Voltar", key="cad_voltar"):
            if st.session_state.get("cadastro_tela", "hub") != "hub":
                st.session_state.cadastro_tela = "hub"
                _bump_cad_seq()
                st.rerun()
            voltar()

    consumir_flash()

    tela = st.session_state.get("cadastro_tela", "hub")
    if tela == "hub":
        _hub()
    elif tela == "clientes":
        _clientes(conn)
    elif tela == "materias":
        _materias(conn)
    elif tela == "tubetes":
        _tubetes(conn)
    elif tela == "facas":
        _facas(conn)
    elif tela == "caixas":
        _caixas(conn)
    elif tela == "suprimentos":
        _suprimentos(conn)
    elif tela == "nativos":
        _valores_nativos(conn)


def _hub() -> None:
    st.caption("Menu → Cadastros")
    opts = [
        ("Clientes", "clientes"),
        ("Matéria Prima", "materias"),
        ("Tubetes", "tubetes"),
        ("Facas", "facas"),
        ("Caixas", "caixas"),
        ("Suprimentos", "suprimentos"),
        ("Valores Nativos", "nativos"),
    ]
    cols = st.columns(3)
    for i, (label, key) in enumerate(opts):
        with cols[i % 3]:
            if st.button(label, use_container_width=True, key=f"hub_{key}"):
                _entrar_tela(key)


def _sync_select_from_grid(sel_base: str, label: str, tela: str) -> None:
    """Ao clicar na grade, carrega o registro em modo visualização."""
    if st.session_state.get(f"_{sel_base}_grid_last") == label:
        return
    st.session_state[f"_{sel_base}_grid_last"] = label
    _bump_cad_seq()
    st.session_state[_sel_key(sel_base)] = label
    _set_editing(tela, False)
    st.session_state[f"_last_modo_{tela}"] = label
    st.rerun()


def _restaurar_select_apos_cancel(sel_base: str, rows, label_fn) -> None:
    """Após cancelar edição, mantém o registro na combo."""
    restore = st.session_state.pop("_restore_sel", None)
    if not restore:
        return
    rid = restore.get("id")
    for r in rows:
        if r["id"] == rid:
            st.session_state[_sel_key(sel_base)] = label_fn(r)
            st.session_state[f"_last_modo_{restore.get('tela')}"] = label_fn(r)
            break


def _clientes(conn) -> None:
    tela = "clientes"
    st.subheader("Clientes")
    termo = st.text_input("Pesquisar cliente")
    total = contar_clientes(conn, termo=termo or None)
    rows = buscar_clientes(conn, termo=termo or None, limite=None)
    st.caption(f"{total} cliente(s) — clique na linha para selecionar")
    ids = {f"{r['id']} - {r['nome']}": r["id"] for r in rows}
    _restaurar_select_apos_cancel("cli_sel", rows, lambda r: f"{r['id']} - {r['nome']}")
    if rows:
        df = pd.DataFrame([dict(r) for r in rows])
        idx = dataframe_selecionavel(df, key=f"cli_grid_{_cad_seq()}", height=320)
        if idx is not None:
            _sync_select_from_grid(
                "cli_sel", f"{rows[idx]['id']} - {rows[idx]['nome']}", tela
            )

    st.markdown("#### Registro")
    modo = st.selectbox(
        "Registro",
        ["(novo)"] + list(ids.keys()),
        key=_sel_key("cli_sel"),
    )
    _ao_mudar_registro(tela, modo)
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    bloqueado = _campos_bloqueados(tela, atual)

    nome = _text_input(
        "Nome", _form_key("cli_nome", atual), atual["nome"] if atual else "", disabled=bloqueado
    )
    cnpj = _text_input(
        "CNPJ/CPF",
        _form_key("cli_cnpj", atual),
        atual["cnpj_cpf"] if atual else "",
        disabled=bloqueado,
    )
    uf = _text_input(
        "UF",
        _form_key("cli_uf", atual),
        (atual["uf"] if atual and atual["uf"] else ""),
        disabled=bloqueado,
    )

    def _salvar():
        if not nome.strip() or not cnpj.strip():
            st.error("Nome e CNPJ/CPF são obrigatórios.")
            return
        upsert_cliente(
            conn,
            cnpj_cpf=cnpj.strip(),
            nome=nome.strip(),
            uf=uf.strip() or None,
            cliente_id=atual["id"] if atual else None,
        )
        _bump_cad_seq()
        flash_sucesso("Cliente salvo com sucesso.")
        st.rerun()

    def _excluir():
        excluir_cliente(conn, atual["id"])
        _bump_cad_seq()
        flash_sucesso("Cliente excluído com sucesso.")
        st.rerun()

    _botoes_crud(tela, atual=atual, on_salvar=_salvar, on_excluir=_excluir if atual else None)


def _materias(conn) -> None:
    tela = "materias"
    st.subheader("Matéria-prima")
    st.info(
        "Campo **nome de exibição mp ORC** é usado na descrição automática do item na proposta."
    )
    rows = listar_materias_primas(conn)
    st.caption("Clique na linha da grade para selecionar o registro.")
    ids = {f"{r['id']} - {r['nome']}": r["id"] for r in rows}
    _restaurar_select_apos_cancel("mp_sel", rows, lambda r: f"{r['id']} - {r['nome']}")
    if rows:
        idx = dataframe_selecionavel(
            pd.DataFrame([dict(r) for r in rows]),
            key=f"mp_grid_{_cad_seq()}",
            height=280,
        )
        if idx is not None:
            _sync_select_from_grid(
                "mp_sel", f"{rows[idx]['id']} - {rows[idx]['nome']}", tela
            )

    modo = st.selectbox(
        "Registro",
        ["(novo)"] + list(ids.keys()),
        key=_sel_key("mp_sel"),
    )
    _ao_mudar_registro(tela, modo)
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    bloqueado = _campos_bloqueados(tela, atual)

    codigo = _text_input(
        "Código",
        _form_key("mp_cod", atual),
        atual["codigo"] if atual else "",
        disabled=bloqueado,
    )
    nome = _text_input(
        "Matéria-prima",
        _form_key("mp_nome", atual),
        atual["nome"] if atual else "",
        disabled=bloqueado,
    )
    nome_orc_default = ""
    if atual:
        nome_orc_default = atual["nome_exibicao_orc"] or atual["nome"] or ""
    nome_orc = _text_input(
        "Nome de exibição mp ORC",
        _form_key("mp_orc", atual),
        nome_orc_default,
        disabled=bloqueado,
    )
    preco = _number_input(
        "Preço de compra",
        _form_key("mp_preco", atual),
        float(atual["preco_compra"] or 0) if atual else 0.0,
        step=0.01,
        disabled=bloqueado,
    )
    custo = _number_input(
        "Custo",
        _form_key("mp_custo", atual),
        float(atual["custo"]) if atual else 0.0,
        step=0.01,
        disabled=bloqueado,
    )
    obs = _text_area(
        "Observações",
        _form_key("mp_obs", atual),
        (atual["observacoes"] if atual and atual["observacoes"] else ""),
        disabled=bloqueado,
    )

    def _salvar():
        salvar_materia(
            conn,
            codigo=codigo.strip(),
            nome=nome.strip(),
            nome_exibicao_orc=nome_orc.strip() or nome.strip(),
            preco_compra=preco,
            custo=custo,
            observacoes=obs or None,
            materia_id=atual["id"] if atual else None,
        )
        _bump_cad_seq()
        flash_sucesso("Matéria-prima salva com sucesso.")
        st.rerun()

    def _excluir():
        excluir_materia(conn, atual["id"])
        _bump_cad_seq()
        flash_sucesso("Matéria-prima excluída com sucesso.")
        st.rerun()

    _botoes_crud(
        tela,
        atual=atual,
        on_salvar=_salvar,
        on_excluir=_excluir if atual else None,
        label_salvar="Salvar matéria-prima",
    )


def _tubetes(conn) -> None:
    tela = "tubetes"
    st.subheader("Tubetes")
    st.info("Campo **nome de exibição tubete ORC** entra na descrição automática.")
    rows = listar_tubetes(conn)
    st.caption("Clique na linha da grade para selecionar o registro.")
    ids = {f"{r['id']} - {r['nome']}": r["id"] for r in rows}
    _restaurar_select_apos_cancel("tub_sel", rows, lambda r: f"{r['id']} - {r['nome']}")
    if rows:
        idx = dataframe_selecionavel(
            pd.DataFrame([dict(r) for r in rows]),
            key=f"tub_grid_{_cad_seq()}",
            height=280,
        )
        if idx is not None:
            _sync_select_from_grid(
                "tub_sel", f"{rows[idx]['id']} - {rows[idx]['nome']}", tela
            )
    modo = st.selectbox(
        "Registro",
        ["(novo)"] + list(ids.keys()),
        key=_sel_key("tub_sel"),
    )
    _ao_mudar_registro(tela, modo)
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    bloqueado = _campos_bloqueados(tela, atual)

    codigo = _text_input(
        "Código",
        _form_key("tub_cod", atual),
        atual["codigo"] if atual else "",
        disabled=bloqueado,
    )
    nome = _text_input(
        "Tubete",
        _form_key("tub_nome", atual),
        atual["nome"] if atual else "",
        disabled=bloqueado,
    )
    nome_orc_default = ""
    if atual:
        nome_orc_default = atual["nome_exibicao_orc"] or atual["nome"] or ""
    nome_orc = _text_input(
        "Nome de exibição tubete ORC",
        _form_key("tub_orc", atual),
        nome_orc_default,
        disabled=bloqueado,
    )
    preco = _number_input(
        "Preço compra",
        _form_key("tub_preco", atual),
        float(atual["preco_compra"] or 0) if atual else 0.0,
        step=0.01,
        disabled=bloqueado,
    )
    custo = _number_input(
        "Custo",
        _form_key("tub_custo", atual),
        float(atual["custo"]) if atual else 0.0,
        step=0.01,
        disabled=bloqueado,
    )

    def _salvar():
        salvar_tubete(
            conn,
            codigo=codigo.strip(),
            nome=nome.strip(),
            nome_exibicao_orc=nome_orc.strip() or nome.strip(),
            preco_compra=preco,
            custo=custo,
            tubete_id=atual["id"] if atual else None,
        )
        _bump_cad_seq()
        flash_sucesso("Tubete salvo com sucesso.")
        st.rerun()

    def _excluir():
        excluir_tubete(conn, atual["id"])
        _bump_cad_seq()
        flash_sucesso("Tubete excluído com sucesso.")
        st.rerun()

    _botoes_crud(
        tela,
        atual=atual,
        on_salvar=_salvar,
        on_excluir=_excluir if atual else None,
        label_salvar="Salvar tubete",
    )


def _caixas(conn) -> None:
    tela = "caixas"
    st.subheader("Caixas")
    rows = listar_caixas(conn)
    st.caption("Clique na linha da grade para selecionar o registro.")
    ids = {f"{r['id']} - {r['nome']}": r["id"] for r in rows}
    _restaurar_select_apos_cancel("cx_sel", rows, lambda r: f"{r['id']} - {r['nome']}")
    if rows:
        idx = dataframe_selecionavel(
            pd.DataFrame([dict(r) for r in rows]),
            key=f"cx_grid_{_cad_seq()}",
            height=280,
        )
        if idx is not None:
            _sync_select_from_grid(
                "cx_sel", f"{rows[idx]['id']} - {rows[idx]['nome']}", tela
            )
    modo = st.selectbox(
        "Registro",
        ["(novo)"] + list(ids.keys()),
        key=_sel_key("cx_sel"),
    )
    _ao_mudar_registro(tela, modo)
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    bloqueado = _campos_bloqueados(tela, atual)

    codigo = _text_input(
        "Código",
        _form_key("cx_cod", atual),
        atual["codigo"] if atual else "",
        disabled=bloqueado,
    )
    nome = _text_input(
        "Caixa",
        _form_key("cx_nome", atual),
        atual["nome"] if atual else "",
        disabled=bloqueado,
    )
    custo = _number_input(
        "Custo",
        _form_key("cx_custo", atual),
        float(atual["custo"]) if atual else 5.0,
        step=0.01,
        disabled=bloqueado,
    )

    def _salvar():
        salvar_caixa(
            conn,
            codigo=codigo.strip(),
            nome=nome.strip(),
            custo=custo,
            caixa_id=atual["id"] if atual else None,
        )
        _bump_cad_seq()
        flash_sucesso("Caixa salva com sucesso.")
        st.rerun()

    def _excluir():
        excluir_caixa(conn, atual["id"])
        _bump_cad_seq()
        flash_sucesso("Caixa excluída com sucesso.")
        st.rerun()

    _botoes_crud(
        tela,
        atual=atual,
        on_salvar=_salvar,
        on_excluir=_excluir if atual else None,
        label_salvar="Salvar caixa",
    )


def _facas(conn) -> None:
    tela = "facas"
    st.subheader("Facas")
    st.info(
        "Campo **nome de exibição faca ORC** entra na descrição automática. "
        "A área é recalculada automaticamente."
    )
    rows = listar_facas(conn)
    st.caption("Clique na linha da grade para selecionar o registro.")
    ids = {f"{r['id']} - {r['tipo_faca']}": r["id"] for r in rows}
    _restaurar_select_apos_cancel(
        "faca_sel", rows, lambda r: f"{r['id']} - {r['tipo_faca']}"
    )
    if rows:
        idx = dataframe_selecionavel(
            pd.DataFrame([dict(r) for r in rows]),
            key=f"faca_grid_{_cad_seq()}",
            height=280,
        )
        if idx is not None:
            _sync_select_from_grid(
                "faca_sel", f"{rows[idx]['id']} - {rows[idx]['tipo_faca']}", tela
            )
    modo = st.selectbox(
        "Registro",
        ["(novo)"] + list(ids.keys()),
        key=_sel_key("faca_sel"),
    )
    _ao_mudar_registro(tela, modo)
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    bloqueado = _campos_bloqueados(tela, atual)

    codigo = _text_input(
        "Código",
        _form_key("faca_cod", atual),
        str(atual["codigo"]) if atual else "",
        disabled=bloqueado,
    )
    tipo = _text_input(
        "Tipo faca",
        _form_key("faca_tipo", atual),
        atual["tipo_faca"] if atual else "",
        disabled=bloqueado,
    )
    nome_orc_default = ""
    if atual:
        nome_orc_default = atual["nome_exibicao_orc"] or atual["tipo_faca"] or ""
    nome_orc = _text_input(
        "Nome de exibição faca ORC",
        _form_key("faca_orc", atual),
        nome_orc_default,
        disabled=bloqueado,
    )
    c1, c2 = st.columns(2)
    with c1:
        largura = _number_input(
            "Largura",
            _form_key("faca_larg", atual),
            float(atual["largura"]) if atual else 0.1,
            format="%.6f",
            disabled=bloqueado,
        )
        altura = _number_input(
            "Altura",
            _form_key("faca_alt", atual),
            float(atual["altura"]) if atual else 0.1,
            format="%.6f",
            disabled=bloqueado,
        )
    with c2:
        gap_l = _number_input(
            "Gap lateral",
            _form_key("faca_gapl", atual),
            float(atual["gap_lateral"]) if atual else 0.006,
            format="%.6f",
            disabled=bloqueado,
        )
        gap_v = _number_input(
            "Gap vertical",
            _form_key("faca_gapv", atual),
            float(atual["gap_vertical"] or 0) if atual else 0.003,
            format="%.6f",
            disabled=bloqueado,
        )

    def _salvar():
        salvar_faca(
            conn,
            codigo=codigo.strip(),
            tipo_faca=tipo.strip(),
            nome_exibicao_orc=nome_orc.strip() or tipo.strip(),
            largura=largura,
            altura=altura,
            gap_lateral=gap_l,
            gap_vertical=gap_v,
            faca_id=atual["id"] if atual else None,
        )
        _bump_cad_seq()
        flash_sucesso("Faca salva com sucesso.")
        st.rerun()

    def _excluir():
        excluir_faca(conn, atual["id"])
        _bump_cad_seq()
        flash_sucesso("Faca excluída com sucesso.")
        st.rerun()

    _botoes_crud(
        tela,
        atual=atual,
        on_salvar=_salvar,
        on_excluir=_excluir if atual else None,
        label_salvar="Salvar faca",
    )


def _suprimentos(conn) -> None:
    tela = "suprimentos"
    st.subheader("Suprimentos")
    st.info(
        "Pré-cadastro importado de **Tabela_Suprimentos.xlsx**. "
        "O **nome de exibição** é usado na descrição do item na proposta."
    )
    rows = listar_suprimentos(conn, ativos_only=False)
    st.caption("Clique na linha da grade para selecionar o registro.")
    ids = {
        f"{r['id']} - {r['nome_exibicao'] or r['descricao']}": r["id"] for r in rows
    }
    _restaurar_select_apos_cancel(
        "sup_sel",
        rows,
        lambda r: f"{r['id']} - {r['nome_exibicao'] or r['descricao']}",
    )
    if rows:
        df = pd.DataFrame(
            [
                {
                    "id": r["id"],
                    "codigo": r["codigo"],
                    "marca": r["marca"],
                    "descricao": r["descricao"],
                    "nome_exibicao": r["nome_exibicao"],
                    "preco_compra": r["preco_compra"],
                    "custo": r["custo"],
                    "ativo": "SIM" if r["ativo"] else "NÃO",
                }
                for r in rows
            ]
        )
        idx = dataframe_selecionavel(df, key=f"sup_grid_{_cad_seq()}", height=280)
        if idx is not None:
            label = f"{rows[idx]['id']} - {rows[idx]['nome_exibicao'] or rows[idx]['descricao']}"
            _sync_select_from_grid("sup_sel", label, tela)

    modo = st.selectbox(
        "Registro",
        ["(novo)"] + list(ids.keys()),
        key=_sel_key("sup_sel"),
    )
    _ao_mudar_registro(tela, modo)
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    bloqueado = _campos_bloqueados(tela, atual)

    codigo = _text_input(
        "Código",
        _form_key("sup_cod", atual),
        atual["codigo"] if atual else "",
        disabled=bloqueado,
    )
    marca = _text_input(
        "Marca",
        _form_key("sup_marca", atual),
        (atual["marca"] if atual and atual["marca"] else ""),
        disabled=bloqueado,
    )
    descricao = _text_input(
        "Descrição",
        _form_key("sup_desc", atual),
        atual["descricao"] if atual else "",
        disabled=bloqueado,
    )
    nome_exib_default = ""
    if atual:
        nome_exib_default = atual["nome_exibicao"] or atual["descricao"] or ""
    nome_exib = _text_input(
        "Nome de exibição",
        _form_key("sup_exib", atual),
        nome_exib_default,
        disabled=bloqueado,
    )
    preco = _number_input(
        "Preço de compra",
        _form_key("sup_preco", atual),
        float(atual["preco_compra"] or 0) if atual else 0.0,
        step=0.01,
        disabled=bloqueado,
    )
    custo = _number_input(
        "Custo",
        _form_key("sup_custo", atual),
        float(atual["custo"]) if atual else 0.0,
        step=0.01,
        disabled=bloqueado,
    )
    ativo_default = True if atual is None else bool(atual["ativo"])
    _init_widget(_form_key("sup_ativo", atual), ativo_default)
    ativo = st.checkbox(
        "Ativo",
        key=_form_key("sup_ativo", atual),
        disabled=bloqueado,
    )

    def _salvar():
        if not codigo.strip() or not descricao.strip():
            st.error("Código e descrição são obrigatórios.")
            return
        salvar_suprimento(
            conn,
            codigo=codigo.strip(),
            marca=marca.strip() or None,
            descricao=descricao.strip(),
            nome_exibicao=nome_exib.strip() or descricao.strip(),
            preco_compra=preco,
            custo=custo,
            ativo=bool(ativo),
            suprimento_id=atual["id"] if atual else None,
        )
        _bump_cad_seq()
        flash_sucesso("Suprimento salvo com sucesso.")
        st.rerun()

    def _excluir():
        excluir_suprimento(conn, atual["id"])
        _bump_cad_seq()
        flash_sucesso("Suprimento excluído com sucesso.")
        st.rerun()

    _botoes_crud(
        tela,
        atual=atual,
        on_salvar=_salvar,
        on_excluir=_excluir if atual else None,
        label_salvar="Salvar suprimento",
    )


def _valores_nativos(conn) -> None:
    st.subheader("Valores nativos")
    cfg = carregar_config(conn)
    LOGO_DIR.mkdir(parents=True, exist_ok=True)

    st.markdown("#### Dados da empresa (cabeçalho da proposta)")
    empresa_nome = st.text_input("Nome da empresa", value=cfg.get("empresa_nome", ""))
    empresa_cnpj = st.text_input("CNPJ da empresa", value=cfg.get("empresa_cnpj", ""))
    empresa_telefone = st.text_input("Telefone da empresa", value=cfg.get("empresa_telefone", ""))
    empresa_email = st.text_input("E-mail da empresa", value=cfg.get("empresa_email", ""))

    st.markdown("#### Padrões de cálculo e proposta")
    c1, c2 = st.columns(2)
    with c1:
        frete_padrao = st.text_input("Frete padrão (R$)", value=cfg.get("frete_padrao", "0"))
        perda_padrao = st.text_input("Perda padrão", value=cfg.get("perda_padrao", "0"))
        validade = st.text_input("Validade da proposta", value=cfg.get("validade_proposta", "15 dias"))
        prazo_pag = st.text_input("Prazo de pagamento", value=cfg.get("prazo_pagamento", "21 dias"))
        prazo_ent = st.text_input("Prazo de entrega", value=cfg.get("prazo_entrega", "5 dias"))
        und_etq = st.text_input("Unidade ORC Etiqueta", value=cfg.get("unidade_etiqueta", "Rol"))
        und_sup = st.text_input("Unidade ORC Suprimentos", value=cfg.get("unidade_suprimentos", "UN"))
    with c2:
        impostos = st.text_input("Impostos", value=cfg.get("impostos", "Inclusos"))
        frete_tipo = st.selectbox(
            "Frete tipo padrão",
            ["CIF", "FOB", "Taxa"],
            index=["CIF", "FOB", "Taxa"].index(cfg.get("frete_tipo", "CIF"))
            if cfg.get("frete_tipo", "CIF") in ["CIF", "FOB", "Taxa"]
            else 0,
        )
        difal = st.selectbox(
            "Difal padrão",
            ["SIM", "NÃO"],
            index=0 if cfg.get("difal_padrao", "SIM") == "SIM" else 1,
        )
        orc_nome = st.text_input("Nome orçamentista", value=cfg.get("orcamentista_nome", ""))
        orc_cargo = st.text_input("Cargo orçamentista", value=cfg.get("orcamentista_cargo", ""))
        orc_tel = st.text_input("Telefone orçamentista", value=cfg.get("orcamentista_telefone", ""))
        orc_email = st.text_input("E-mail orçamentista", value=cfg.get("orcamentista_email", ""))

    info = st.text_area(
        "Informações adicionais",
        value=cfg.get("informacoes_adicionais", ""),
    )

    st.markdown("#### Logos (upload)")
    st.caption(
        "Sugestão: Master 1200×330 px | Cabeçalho/Rodapé 240×124 px (ou 480×250 px)"
    )
    up_master = st.file_uploader("Logo master", type=["png", "jpg", "jpeg", "webp"])
    up_cab = st.file_uploader("Logo cabeçalho", type=["png", "jpg", "jpeg", "webp"])
    up_rod = st.file_uploader("Logo rodapé", type=["png", "jpg", "jpeg", "webp"])

    logo_master = cfg.get("logo_master", "")
    logo_cab = cfg.get("logo_cabecalho", "")
    logo_rod = cfg.get("logo_rodape", "")

    if up_master:
        path = LOGO_DIR / f"logo_master.{up_master.name.split('.')[-1].lower()}"
        path.write_bytes(up_master.getvalue())
        logo_master = str(path)
        st.success(f"Logo master salva: {path.name}")
    if up_cab:
        path = LOGO_DIR / f"logo_cabecalho.{up_cab.name.split('.')[-1].lower()}"
        path.write_bytes(up_cab.getvalue())
        logo_cab = str(path)
        st.success(f"Logo cabeçalho salva: {path.name}")
    if up_rod:
        path = LOGO_DIR / f"logo_rodape.{up_rod.name.split('.')[-1].lower()}"
        path.write_bytes(up_rod.getvalue())
        logo_rod = str(path)
        st.success(f"Logo rodapé salva: {path.name}")

    if st.button("Salvar valores nativos", type="primary"):
        salvar_config(
            conn,
            {
                "empresa_nome": empresa_nome,
                "empresa_cnpj": empresa_cnpj,
                "empresa_telefone": empresa_telefone,
                "empresa_email": empresa_email,
                "frete_padrao": frete_padrao,
                "perda_padrao": perda_padrao,
                "validade_proposta": validade,
                "prazo_pagamento": prazo_pag,
                "prazo_entrega": prazo_ent,
                "frete_tipo": frete_tipo,
                "impostos": impostos,
                "informacoes_adicionais": info,
                "orcamentista_nome": orc_nome,
                "orcamentista_cargo": orc_cargo,
                "orcamentista_telefone": orc_tel,
                "orcamentista_email": orc_email,
                "unidade_etiqueta": und_etq,
                "unidade_suprimentos": und_sup,
                "difal_padrao": difal,
                "logo_master": logo_master,
                "logo_cabecalho": logo_cab,
                "logo_rodape": logo_rod,
            },
        )
        flash_sucesso("Valores nativos salvos com sucesso.")
        st.rerun()
