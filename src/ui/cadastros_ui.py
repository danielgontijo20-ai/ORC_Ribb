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
    excluir_tubete,
    listar_caixas,
    listar_facas,
    listar_materias_primas,
    listar_tubetes,
    salvar_caixa,
    salvar_faca,
    salvar_materia,
    salvar_tubete,
    upsert_cliente,
)
from src.services.clientes import buscar_clientes, contar_clientes
from src.services.configuracoes import carregar_config, salvar_config
from src.ui.state import voltar


LOGO_DIR = ROOT_DIR / "data" / "logos"


def _cad_seq() -> int:
    return int(st.session_state.get("cad_form_seq") or 0)


def _bump_cad_seq() -> None:
    st.session_state.cad_form_seq = _cad_seq() + 1


def _form_key(prefix: str, atual) -> str:
    """Chave dinâmica: recarrega campos ao trocar registro ou após salvar."""
    rid = atual["id"] if atual is not None else "novo"
    return f"{prefix}_{rid}_{_cad_seq()}"


def _preparar_nova_insercao(select_key: str) -> None:
    """Após salvar: limpa formulário e deixa pronto para nova inserção."""
    _bump_cad_seq()
    st.session_state[select_key] = "(novo)"


def render_cadastros(conn) -> None:
    top1, top2 = st.columns([4, 1])
    with top1:
        st.markdown('<p class="orc-title">Cadastros</p>', unsafe_allow_html=True)
    with top2:
        if st.button("← Voltar", key="cad_voltar"):
            # Se estiver num subcadastro, volta ao hub; senão ao menu
            if st.session_state.get("cadastro_tela", "hub") != "hub":
                st.session_state.cadastro_tela = "hub"
                st.rerun()
            voltar()

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
        ("Valores Nativos", "nativos"),
    ]
    cols = st.columns(3)
    for i, (label, key) in enumerate(opts):
        with cols[i % 3]:
            if st.button(label, use_container_width=True, key=f"hub_{key}"):
                st.session_state.cadastro_tela = key
                st.rerun()


def _voltar_hub_btn(key: str) -> None:
    if st.button("← Voltar", key=key):
        st.session_state.cadastro_tela = "hub"
        st.rerun()


def _clientes(conn) -> None:
    _voltar_hub_btn("back_cli")
    st.subheader("Clientes")
    termo = st.text_input("Pesquisar cliente")
    total = contar_clientes(conn, termo=termo or None)
    rows = buscar_clientes(conn, termo=termo or None, limite=None)
    st.caption(f"{total} cliente(s) encontrado(s)")
    if rows:
        st.dataframe(
            pd.DataFrame([dict(r) for r in rows]),
            use_container_width=True,
            hide_index=True,
            height=320,
        )

    st.markdown("#### Inserir / editar")
    ids = {f"{r['id']} - {r['nome']}": r["id"] for r in rows}
    modo = st.selectbox(
        "Registro",
        ["(novo)"] + list(ids.keys()),
        key="cli_sel",
    )
    atual = None
    if modo != "(novo)":
        atual = next(r for r in rows if r["id"] == ids[modo])

    nome = st.text_input(
        "Nome",
        value=(atual["nome"] if atual else ""),
        key=_form_key("cli_nome", atual),
    )
    cnpj = st.text_input(
        "CNPJ/CPF",
        value=(atual["cnpj_cpf"] if atual else ""),
        key=_form_key("cli_cnpj", atual),
    )
    uf = st.text_input(
        "UF",
        value=(atual["uf"] if atual and atual["uf"] else ""),
        key=_form_key("cli_uf", atual),
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Salvar cliente", type="primary"):
            if not nome.strip() or not cnpj.strip():
                st.error("Nome e CNPJ/CPF são obrigatórios.")
            else:
                upsert_cliente(
                    conn,
                    cnpj_cpf=cnpj.strip(),
                    nome=nome.strip(),
                    uf=uf.strip() or None,
                    cliente_id=atual["id"] if atual else None,
                )
                _preparar_nova_insercao("cli_sel")
                st.success("Cliente salvo. Formulário pronto para nova inserção.")
                st.rerun()
    with c2:
        if atual and st.button("Excluir cliente"):
            excluir_cliente(conn, atual["id"])
            _preparar_nova_insercao("cli_sel")
            st.success("Cliente excluído.")
            st.rerun()


def _materias(conn) -> None:
    _voltar_hub_btn("back_mp")
    st.subheader("Matéria-prima")
    st.info(
        "Campo **nome de exibição mp ORC** é usado na descrição automática do item na proposta."
    )
    rows = listar_materias_primas(conn)
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True, hide_index=True)

    ids = {f"{r['id']} - {r['nome']}": r["id"] for r in rows}
    modo = st.selectbox("Registro", ["(novo)"] + list(ids.keys()), key="mp_sel")
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)

    codigo = st.text_input(
        "Código",
        value=(atual["codigo"] if atual else ""),
        key=_form_key("mp_cod", atual),
    )
    nome = st.text_input(
        "Matéria-prima",
        value=(atual["nome"] if atual else ""),
        key=_form_key("mp_nome", atual),
    )
    nome_orc = st.text_input(
        "Nome de exibição mp ORC",
        value=(
            atual["nome_exibicao_orc"]
            if atual and atual["nome_exibicao_orc"]
            else (atual["nome"] if atual else "")
        ),
        key=_form_key("mp_orc", atual),
    )
    preco = st.number_input(
        "Preço de compra",
        value=float(atual["preco_compra"] or 0) if atual else 0.0,
        step=0.01,
        key=_form_key("mp_preco", atual),
    )
    custo = st.number_input(
        "Custo",
        value=float(atual["custo"]) if atual else 0.0,
        step=0.01,
        key=_form_key("mp_custo", atual),
    )
    obs = st.text_area(
        "Observações",
        value=(atual["observacoes"] if atual and atual["observacoes"] else ""),
        key=_form_key("mp_obs", atual),
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Salvar matéria-prima", type="primary"):
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
            _preparar_nova_insercao("mp_sel")
            st.success("Salvo. Formulário pronto para nova inserção.")
            st.rerun()
    with c2:
        if atual and st.button("Excluir matéria-prima"):
            excluir_materia(conn, atual["id"])
            _preparar_nova_insercao("mp_sel")
            st.success("Excluído.")
            st.rerun()


def _tubetes(conn) -> None:
    _voltar_hub_btn("back_tub")
    st.subheader("Tubetes")
    st.info("Campo **nome de exibição tubete ORC** entra na descrição automática.")
    rows = listar_tubetes(conn)
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True, hide_index=True)
    ids = {f"{r['id']} - {r['nome']}": r["id"] for r in rows}
    modo = st.selectbox("Registro", ["(novo)"] + list(ids.keys()), key="tub_sel")
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    codigo = st.text_input(
        "Código",
        value=(atual["codigo"] if atual else ""),
        key=_form_key("tub_cod", atual),
    )
    nome = st.text_input(
        "Tubete",
        value=(atual["nome"] if atual else ""),
        key=_form_key("tub_nome", atual),
    )
    nome_orc = st.text_input(
        "Nome de exibição tubete ORC",
        value=(
            atual["nome_exibicao_orc"]
            if atual and atual["nome_exibicao_orc"]
            else (atual["nome"] if atual else "")
        ),
        key=_form_key("tub_orc", atual),
    )
    preco = st.number_input(
        "Preço compra",
        value=float(atual["preco_compra"] or 0) if atual else 0.0,
        step=0.01,
        key=_form_key("tub_preco", atual),
    )
    custo = st.number_input(
        "Custo",
        value=float(atual["custo"]) if atual else 0.0,
        step=0.01,
        key=_form_key("tub_custo", atual),
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Salvar tubete", type="primary"):
            salvar_tubete(
                conn,
                codigo=codigo.strip(),
                nome=nome.strip(),
                nome_exibicao_orc=nome_orc.strip() or nome.strip(),
                preco_compra=preco,
                custo=custo,
                tubete_id=atual["id"] if atual else None,
            )
            _preparar_nova_insercao("tub_sel")
            st.success("Salvo. Formulário pronto para nova inserção.")
            st.rerun()
    with c2:
        if atual and st.button("Excluir tubete"):
            excluir_tubete(conn, atual["id"])
            _preparar_nova_insercao("tub_sel")
            st.success("Excluído.")
            st.rerun()


def _caixas(conn) -> None:
    _voltar_hub_btn("back_cx")
    st.subheader("Caixas")
    rows = listar_caixas(conn)
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True, hide_index=True)
    ids = {f"{r['id']} - {r['nome']}": r["id"] for r in rows}
    modo = st.selectbox("Registro", ["(novo)"] + list(ids.keys()), key="cx_sel")
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    codigo = st.text_input(
        "Código",
        value=(atual["codigo"] if atual else ""),
        key=_form_key("cx_cod", atual),
    )
    nome = st.text_input(
        "Caixa",
        value=(atual["nome"] if atual else ""),
        key=_form_key("cx_nome", atual),
    )
    custo = st.number_input(
        "Custo",
        value=float(atual["custo"]) if atual else 5.0,
        step=0.01,
        key=_form_key("cx_custo", atual),
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Salvar caixa", type="primary"):
            salvar_caixa(
                conn,
                codigo=codigo.strip(),
                nome=nome.strip(),
                custo=custo,
                caixa_id=atual["id"] if atual else None,
            )
            _preparar_nova_insercao("cx_sel")
            st.success("Salvo. Formulário pronto para nova inserção.")
            st.rerun()
    with c2:
        if atual and st.button("Excluir caixa"):
            excluir_caixa(conn, atual["id"])
            _preparar_nova_insercao("cx_sel")
            st.success("Excluído.")
            st.rerun()


def _facas(conn) -> None:
    _voltar_hub_btn("back_faca")
    st.subheader("Facas")
    st.info(
        "Campo **nome de exibição faca ORC** entra na descrição automática. "
        "A área é recalculada automaticamente."
    )
    rows = listar_facas(conn)
    if rows:
        st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True, hide_index=True)
    ids = {f"{r['id']} - {r['tipo_faca']}": r["id"] for r in rows}
    modo = st.selectbox("Registro", ["(novo)"] + list(ids.keys()), key="faca_sel")
    atual = next((r for r in rows if modo != "(novo)" and r["id"] == ids[modo]), None)
    codigo = st.text_input(
        "Código",
        value=(str(atual["codigo"]) if atual else ""),
        key=_form_key("faca_cod", atual),
    )
    tipo = st.text_input(
        "Tipo faca",
        value=(atual["tipo_faca"] if atual else ""),
        key=_form_key("faca_tipo", atual),
    )
    nome_orc = st.text_input(
        "Nome de exibição faca ORC",
        value=(
            atual["nome_exibicao_orc"]
            if atual and atual["nome_exibicao_orc"]
            else (atual["tipo_faca"] if atual else "")
        ),
        key=_form_key("faca_orc", atual),
    )
    c1, c2 = st.columns(2)
    with c1:
        largura = st.number_input(
            "Largura",
            value=float(atual["largura"]) if atual else 0.1,
            format="%.6f",
            key=_form_key("faca_larg", atual),
        )
        altura = st.number_input(
            "Altura",
            value=float(atual["altura"]) if atual else 0.1,
            format="%.6f",
            key=_form_key("faca_alt", atual),
        )
    with c2:
        gap_l = st.number_input(
            "Gap lateral",
            value=float(atual["gap_lateral"]) if atual else 0.006,
            format="%.6f",
            key=_form_key("faca_gapl", atual),
        )
        gap_v = st.number_input(
            "Gap vertical",
            value=float(atual["gap_vertical"] or 0) if atual else 0.003,
            format="%.6f",
            key=_form_key("faca_gapv", atual),
        )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Salvar faca", type="primary"):
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
            _preparar_nova_insercao("faca_sel")
            st.success("Salvo. Formulário pronto para nova inserção.")
            st.rerun()
    with c2:
        if atual and st.button("Excluir faca"):
            excluir_faca(conn, atual["id"])
            _preparar_nova_insercao("faca_sel")
            st.success("Excluído.")
            st.rerun()


def _valores_nativos(conn) -> None:
    _voltar_hub_btn("back_nat")
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
        _bump_cad_seq()
        st.success("Valores nativos salvos.")
        st.rerun()
