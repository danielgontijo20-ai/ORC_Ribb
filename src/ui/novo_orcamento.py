"""Tela Novo Orçamento — layout 2 colunas do PPTX."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.services.cadastros import (
    listar_caixas,
    listar_facas,
    listar_materias_primas,
    listar_suprimentos,
    listar_tubetes,
    obter_caixa_por_nome,
    obter_faca_por_tipo,
    obter_materia_por_nome,
    obter_tubete_por_nome,
)
from src.services.calculos_orcamento import (
    calcular_orcamento_etiqueta,
    calcular_orcamento_suprimentos,
)
from src.db.database import connect
from src.services.clientes import buscar_clientes, contar_clientes, obter_cliente
from src.services.configuracoes import (
    carregar_config,
    get_float,
    proximo_numero_orcamento,
)
from src.services.descricao_item import (
    montar_descricao_etiqueta,
    montar_descricao_suprimento,
)
from src.services.orcamentos import salvar_orcamento
from src.services.pdf_proposta import gerar_pdf_proposta
from src.ui.formatters import brl, texto_ou_traco
from src.ui.grid_select import dataframe_selecionavel
from src.ui.memoria_ui import render_memoria_completa
from src.ui.scroll import aplicar_scroll_se_pedido, marcar_scroll_form
from src.ui.state import (
    bump_form_seq,
    consumir_flash,
    flash_sucesso,
    marcar_proposta_salva,
    marcar_proposta_suja,
    media_lucro_pct_proposta,
    proposta_esta_salva,
    reiniciar_proposta,
    totais_proposta,
    voltar,
)

PLACE_SEL = "(selecione)"
PLACE_INS = "(inserir)"


def _fk(name: str) -> str:
    """Chave de widget ligada ao form_seq (limpa campos ao reiniciar)."""
    return f"{name}_{st.session_state.get('form_seq', 0)}"


def _parse_num(texto: str | None) -> float | None:
    if texto is None:
        return None
    t = str(texto).strip()
    if not t or t == PLACE_INS:
        return None
    t = t.replace("R$", "").replace("%", "").strip()
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except ValueError:
        return None


def render_novo_orcamento(conn) -> None:
    cfg = carregar_config(conn)
    proposta = st.session_state.proposta
    readonly = bool(st.session_state.get("proposta_readonly"))
    st.markdown('<div class="orc-top-spacer"></div>', unsafe_allow_html=True)

    top1, top2, top3 = st.columns([3.2, 1, 1.2])
    with top1:
        titulo = "Consulta de Orçamento" if readonly else "Novo Orçamento"
        st.markdown(f'<p class="orc-title">{titulo}</p>', unsafe_allow_html=True)
        if readonly:
            st.caption(
                f"Somente leitura — {proposta.get('numero') or 'sem número'}. "
                "Use Histórico de Orçamentos → Clonar para editar uma cópia."
            )
        else:
            st.caption("Menu → Novo Orçamento")
    with top2:
        if st.button("← Voltar", use_container_width=True, key="orc_voltar"):
            if readonly:
                st.session_state.proposta_readonly = False
            voltar()
    with top3:
        if not readonly and st.button(
            "Limpar orçamento",
            use_container_width=True,
            type="secondary",
            key="orc_limpar",
        ):
            reiniciar_proposta(conn)
            flash_sucesso("Orçamento e formulários limpos. Valores nativos mantidos.")
            st.rerun()

    consumir_flash()
    if readonly:
        st.info("Modo consulta: alterações desabilitadas.")

    # Dialogs também no modo consulta (memória de cálculo)
    _render_dialogs(cfg)

    # Duas colunas no mesmo nível: cliente/formação | prévia (sempre no topo)
    try:
        col_form, col_preview = st.columns(
            [1.05, 1], gap="medium", vertical_alignment="top"
        )
    except TypeError:
        col_form, col_preview = st.columns([1.05, 1], gap="medium")

    with col_form:
        _painel_esquerda(conn, cfg, proposta, readonly=readonly)
    with col_preview:
        _painel_proposta(conn, cfg, proposta, readonly=readonly)


def _painel_esquerda(conn, cfg, proposta, *, readonly: bool = False) -> None:
    modo = st.session_state.get("modo_form")

    with st.container(border=True):
        st.markdown("#### Selecionar cliente")
        if not readonly:
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button(
                    "Selecionar cliente",
                    use_container_width=True,
                    type="primary" if st.session_state.get("show_dialog") == "cliente" else "secondary",
                    key="btn_sel_cli",
                ):
                    st.session_state.show_dialog = "cliente"
                    st.rerun()
            with b2:
                if st.button(
                    "Cliente avulso",
                    use_container_width=True,
                    type="primary" if st.session_state.get("show_dialog") == "cliente_avulso" else "secondary",
                    key="btn_cli_avulso",
                ):
                    st.session_state.show_dialog = "cliente_avulso"
                    st.rerun()
            with b3:
                if st.button("Limpar cliente", use_container_width=True, key="btn_limpar_cli"):
                    proposta["cliente"] = None
                    flash_sucesso("Cliente removido do orçamento.")
                    st.rerun()

        cliente = proposta.get("cliente")
        if cliente:
            st.success(
                f"{cliente.get('nome')} | {texto_ou_traco(cliente.get('cnpj_cpf'))}"
            )
        else:
            st.warning("Nenhum cliente selecionado.")

    with st.container(border=True):
        st.markdown("#### Formação de orçamento")
        if not readonly:
            a1, a2, a3 = st.columns(3)
            with a1:
                if st.button(
                    "Inserir nova etiqueta",
                    use_container_width=True,
                    type="primary" if modo == "etiqueta" else "secondary",
                    key="btn_nova_etq",
                ):
                    bump_form_seq()
                    st.session_state.modo_form = "etiqueta"
                    st.session_state.memoria_calculo = None
                    marcar_scroll_form()
                    st.rerun()
            with a2:
                if st.button(
                    "Inserir novo suprimento",
                    use_container_width=True,
                    type="primary" if modo == "suprimentos" else "secondary",
                    key="btn_novo_sup",
                ):
                    bump_form_seq()
                    st.session_state.modo_form = "suprimentos"
                    st.session_state.memoria_calculo = None
                    marcar_scroll_form()
                    st.rerun()
            with a3:
                if st.button(
                    "Condições gerais",
                    use_container_width=True,
                    type="primary" if st.session_state.get("show_dialog") == "condicoes" else "secondary",
                    key="btn_condicoes",
                ):
                    st.session_state.show_dialog = "condicoes"
                    st.rerun()

        valor_total, lucro_total, frete_total = totais_proposta()
        media_lucro = media_lucro_pct_proposta()
        st.markdown(
            f'<div class="orc-total-bar">Valor total dos itens: {brl(valor_total)}</div>',
            unsafe_allow_html=True,
        )
        k1, k2, k3 = st.columns(3)
        k1.metric("Lucro total", brl(lucro_total))
        k2.metric("Média lucro %", f"{media_lucro:.2f}%".replace(".", ","))
        k3.metric("Frete total incluso", brl(frete_total))

        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button(
                "Memória de cálculo",
                use_container_width=True,
                key="btn_memoria_proposta",
            ):
                st.session_state.memoria_calculo = None  # só itens da proposta
                st.session_state.show_dialog = "memoria"
                st.rerun()
        with b2:
            if not readonly and st.button(
                "Salvar orçamento",
                use_container_width=True,
                type="primary",
                key="btn_salvar_orcamento",
            ):
                _salvar_formacao_orcamento(conn, proposta)
        with b3:
            pdf_ok = proposta_esta_salva() and bool(proposta.get("itens")) and bool(
                proposta.get("cliente")
            )
            if not readonly:
                if st.button(
                    "Gerar PDF da proposta",
                    use_container_width=True,
                    type="primary",
                    key="btn_gerar_pdf",
                    disabled=not pdf_ok,
                ):
                    _gerar_e_oferecer_pdf(conn, cfg, proposta)
                if not proposta_esta_salva():
                    st.caption("Salve o orçamento para habilitar o PDF.")

    if not readonly and modo in ("etiqueta", "suprimentos"):
        aplicar_scroll_se_pedido()
        if st.button(
            "↑ Recuar formulário de inserção",
            key="fechar_form_item",
            use_container_width=True,
        ):
            st.session_state.modo_form = None
            st.rerun()
        if modo == "etiqueta":
            _form_etiqueta(conn, cfg, proposta)
        else:
            _form_suprimentos(conn, cfg, proposta)


def _form_etiqueta(conn, cfg, proposta) -> None:
    with st.container(border=True):
        st.markdown("#### Inserir etiqueta")
        st.caption(
            "Campos nativos já vêm preenchidos. Demais campos começam em (selecione)/(inserir)."
        )

        facas = listar_facas(conn)
        materias = listar_materias_primas(conn)
        tubetes = listar_tubetes(conn)
        caixas = listar_caixas(conn)
        if not all([facas, materias, tubetes, caixas]):
            st.error("Cadastros incompletos. Importe a planilha / cadastre os itens.")
            return

        _form_etiqueta_body(conn, cfg, proposta, facas, materias, tubetes, caixas)


def _form_etiqueta_body(conn, cfg, proposta, facas, materias, tubetes, caixas) -> None:

    caixa_nativa = next(
        (c["nome"] for c in caixas if "tipo 1" in c["nome"].lower()),
        caixas[0]["nome"],
    )
    op_facas = [PLACE_SEL] + [f["tipo_faca"] for f in facas]
    op_mps = [PLACE_SEL] + [m["nome"] for m in materias]
    op_tubs = [PLACE_SEL] + [t["nome"] for t in tubetes]
    op_cxs = [c["nome"] for c in caixas]
    idx_caixa = op_cxs.index(caixa_nativa) if caixa_nativa in op_cxs else 0

    c1, c2 = st.columns(2)
    with c1:
        tipo_faca = st.selectbox(
            "Dimensão da etiqueta", op_facas, key=_fk("etq_faca")
        )
        qtd_etq_num = st.number_input(
            "Qtd de etiquetas por rolo",
            min_value=0.0,
            value=None,
            step=1.0,
            placeholder=PLACE_INS,
            key=_fk("etq_qtd_etq"),
        )
        unidade = st.text_input(
            "Unidade de medida",
            value=cfg.get("unidade_etiqueta", "Rol"),
            key=_fk("etq_und"),
        )
        qtd_total_num = st.number_input(
            "Qtd total (rolos)",
            min_value=0.0,
            value=None,
            step=1.0,
            placeholder=PLACE_INS,
            key=_fk("etq_qtd_total"),
        )
        qtd_caixas_num = st.number_input(
            "Qtd de caixas",
            min_value=0.0,
            value=None,
            step=1.0,
            placeholder=PLACE_INS,
            key=_fk("etq_qtd_cx"),
        )
        frete = st.number_input(
            "Valor do frete (nativo)",
            min_value=0.0,
            value=get_float(cfg, "frete_padrao", 0.0),
            step=10.0,
            key=_fk("etq_frete"),
        )
    with c2:
        materia_nome = st.selectbox(
            "Tipo de matéria-prima", op_mps, key=_fk("etq_mp")
        )
        tubete_nome = st.selectbox(
            "Tipo de tubete", op_tubs, key=_fk("etq_tub")
        )
        caixa_nome = st.selectbox(
            "Tipo de caixa (nativo)",
            op_cxs,
            index=idx_caixa,
            key=_fk("etq_cx"),
        )
        perda = st.number_input(
            "Perda (nativo)",
            min_value=0.0,
            max_value=1.0,
            value=get_float(cfg, "perda_padrao", 0.0),
            step=0.01,
            format="%.2f",
            key=_fk("etq_perda"),
        )
        lucro = st.number_input(
            "Lucro (nativo)",
            min_value=0.0,
            max_value=5.0,
            value=get_float(cfg, "lucro_etiqueta_padrao", 0.30),
            step=0.05,
            format="%.2f",
            key=_fk("etq_lucro"),
        )

    qtd_etq = float(qtd_etq_num) if qtd_etq_num is not None else None
    qtd_total = float(qtd_total_num) if qtd_total_num is not None else None
    qtd_caixas = float(qtd_caixas_num) if qtd_caixas_num is not None else None

    faltando = []
    if tipo_faca == PLACE_SEL:
        faltando.append("dimensão")
    if materia_nome == PLACE_SEL:
        faltando.append("matéria-prima")
    if tubete_nome == PLACE_SEL:
        faltando.append("tubete")
    if qtd_etq is None or qtd_etq <= 0:
        faltando.append("qtd etiquetas/rolo")
    if qtd_total is None or qtd_total <= 0:
        faltando.append("qtd total")
    if qtd_caixas is None or qtd_caixas < 0:
        faltando.append("qtd caixas")

    resultado = None
    descricao = ""
    if not faltando:
        faca = obter_faca_por_tipo(conn, tipo_faca)
        materia = obter_materia_por_nome(conn, materia_nome)
        tubete = obter_tubete_por_nome(conn, tubete_nome)
        caixa = obter_caixa_por_nome(conn, caixa_nome)
        if faca and materia and tubete and caixa:
            resultado = calcular_orcamento_etiqueta(
                area_faca=float(faca["area"]),
                qtd_etiquetas_por_rolo=float(qtd_etq),
                numero_rolos=float(qtd_total),
                custo_m2_materia=float(materia["custo"]),
                custo_tubete=float(tubete["custo"]),
                custo_caixa=float(caixa["custo"]),
                qtd_caixas=float(qtd_caixas),
                perda_processo=float(perda),
                frete_total=float(frete),
                lucro_percentual=float(lucro),
            )
            descricao = montar_descricao_etiqueta(
                nome_mp_orc=materia["nome_exibicao_orc"] or materia["nome"],
                nome_faca_orc=faca["nome_exibicao_orc"] or faca["tipo_faca"],
                qtd_etiquetas_por_rolo=qtd_etq,
                nome_tubete_orc=tubete["nome_exibicao_orc"] or tubete["nome"],
            )

    if faltando:
        st.info("Preencha/selecione: " + ", ".join(faltando) + " — valores abaixo atualizam ao completar.")
    if descricao:
        st.caption(f"Descrição gerada: **{descricao}**")

    # Sempre visíveis (não exige Enter no final para aparecer)
    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Venda unitária",
        brl(resultado.preco_com_imposto) if resultado else "R$ 0,00",
    )
    m2.metric(
        "Venda total do item",
        brl(resultado.valor_venda_total) if resultado else "R$ 0,00",
    )
    m3.metric(
        "Lucro total do item",
        brl(resultado.lucro_total) if resultado else "R$ 0,00",
    )

    d1, d2 = st.columns(2)
    with d1:
        if st.button("Exibir memória de cálculo", use_container_width=True, key=_fk("etq_mem")):
            if not resultado:
                st.error("Complete os campos obrigatórios para ver a memória de cálculo.")
            else:
                st.session_state.memoria_calculo = {
                    "tipo": "etiqueta",
                    "resultado": resultado,
                    "params": {
                        "Dimensão": tipo_faca,
                        "Qtd etiquetas/rolo": qtd_etq,
                        "Nº rolos": qtd_total,
                        "Matéria-prima": materia_nome,
                        "Tubete": tubete_nome,
                        "Caixa": caixa_nome,
                        "Qtd caixas": qtd_caixas,
                        "Perda": perda,
                        "Frete": frete,
                        "Lucro": lucro,
                    },
                }
                st.session_state.show_dialog = "memoria"
                st.rerun()
    with d2:
        if st.button(
            "Inserir item na proposta",
            type="primary",
            use_container_width=True,
            key=_fk("etq_ins"),
        ):
            if not resultado:
                st.error("Complete os campos obrigatórios antes de inserir.")
            elif not proposta.get("cliente"):
                st.error("Selecione um cliente antes de inserir o item.")
            else:
                with st.spinner("Inserindo item e salvando orçamento..."):
                    _garantir_numero(conn, proposta)
                    proposta["itens"].append(
                        {
                            "tipo_item": "etiqueta",
                            "descricao": descricao,
                            "unidade": unidade,
                            "quantidade": float(qtd_total),
                            "preco_unitario": resultado.preco_com_imposto,
                            "valor_venda_total": resultado.valor_venda_total,
                            "lucro_total": resultado.lucro_total,
                            "frete_item": float(frete),
                            "calculo": resultado.to_dict(),
                            "parametros": {
                                "faca": tipo_faca,
                                "materia": materia_nome,
                                "tubete": tubete_nome,
                                "caixa": caixa_nome,
                                "qtd_etq": qtd_etq,
                                "perda": perda,
                                "lucro": lucro,
                            },
                        }
                    )
                    salvar_orcamento(conn, proposta, status="rascunho")
                    marcar_proposta_suja()
                bump_form_seq()
                st.session_state.modo_form = None
                flash_sucesso("Item inserido com sucesso. Formulário limpo para o próximo item.")
                st.rerun()


def _salvar_formacao_orcamento(conn, proposta) -> None:
    if not proposta.get("cliente"):
        st.error("Selecione um cliente antes de salvar.")
        return
    if not proposta.get("itens"):
        st.error("Insira ao menos um item antes de salvar.")
        return
    with st.spinner("Salvando orçamento..."):
        _garantir_numero(conn, proposta)
        salvar_orcamento(conn, proposta, status="rascunho")
        marcar_proposta_salva()
    flash_sucesso(
        f"Orçamento {proposta.get('numero')} salvo. Agora você pode gerar o PDF."
    )
    st.rerun()


def _form_suprimentos(conn, cfg, proposta) -> None:
    with st.container(border=True):
        st.markdown("#### Inserir suprimento")
        st.caption(
            "Campos nativos já vêm preenchidos. Demais campos começam em (inserir)/(selecione)."
        )
        _form_suprimentos_body(conn, cfg, proposta)


def _form_suprimentos_body(conn, cfg, proposta) -> None:
    catalogo = listar_suprimentos(conn)
    cat_map = {
        f"{r['codigo']} — {r['nome_exibicao'] or r['descricao']}": r for r in catalogo
    }
    cat_opts = ["(inserir manualmente)"] + list(cat_map.keys())
    cat_sel = st.selectbox(
        "Suprimento do cadastro",
        cat_opts,
        key=_fk("sup_cat"),
        help="Selecione um pré-cadastro ou preencha manualmente.",
    )
    cat_row = cat_map.get(cat_sel) if cat_sel != "(inserir manualmente)" else None

    c1, c2 = st.columns(2)
    with c1:
        if cat_row is not None:
            descricao_in = cat_row["nome_exibicao"] or cat_row["descricao"] or ""
            st.text_input(
                "Descrição do item",
                value=descricao_in,
                disabled=True,
                key=_fk("sup_desc_locked"),
            )
            custo_default = float(cat_row["custo"] or 0)
            custo_num = st.number_input(
                "Custo",
                min_value=0.0,
                value=custo_default,
                step=0.01,
                format="%.4f",
                key=_fk("sup_custo"),
            )
        else:
            descricao_in = st.text_input(
                "Descrição do item",
                value="",
                placeholder=PLACE_INS,
                key=_fk("sup_desc"),
            )
            custo_num = st.number_input(
                "Custo",
                min_value=0.0,
                value=None,
                step=0.01,
                format="%.4f",
                placeholder=PLACE_INS,
                key=_fk("sup_custo"),
            )
        unidade = st.text_input(
            "Unidade de medida (nativo)",
            value=cfg.get("unidade_suprimentos", "UN"),
            key=_fk("sup_und"),
        )
        qtd_num = st.number_input(
            "Quantidade",
            min_value=0.0,
            value=None,
            step=1.0,
            placeholder=PLACE_INS,
            key=_fk("sup_qtd"),
        )
    with c2:
        difal_opts = [PLACE_SEL, "SIM", "NÃO"]
        difal_nativo = cfg.get("difal_padrao", "SIM").upper()
        difal_idx = difal_opts.index(difal_nativo) if difal_nativo in difal_opts else 1
        difal_sel = st.selectbox(
            "Difal (nativo)",
            difal_opts,
            index=difal_idx,
            key=_fk("sup_difal"),
        )
        frete = st.number_input(
            "Valor do frete (nativo)",
            min_value=0.0,
            value=get_float(cfg, "frete_padrao", 0.0),
            step=10.0,
            key=_fk("sup_frete"),
        )
        lucro = st.number_input(
            "Lucro (nativo)",
            min_value=0.0,
            max_value=5.0,
            value=get_float(cfg, "lucro_suprimentos_padrao", 0.20),
            step=0.05,
            format="%.2f",
            key=_fk("sup_lucro"),
        )

    custo = float(custo_num) if custo_num is not None else None
    quantidade = float(qtd_num) if qtd_num is not None else None
    faltando = []
    if not (descricao_in or "").strip():
        faltando.append("descrição")
    if custo is None or custo < 0:
        faltando.append("custo")
    if quantidade is None or quantidade <= 0:
        faltando.append("quantidade")
    if difal_sel == PLACE_SEL:
        faltando.append("difal")

    resultado = None
    descricao = montar_descricao_suprimento(descricao_in) if (descricao_in or "").strip() else ""
    if not faltando:
        difal = difal_sel == "SIM"
        resultado = calcular_orcamento_suprimentos(
            custo=float(custo),
            frete_total=float(frete),
            quantidade=float(quantidade),
            difal=difal,
            lucro_percentual=float(lucro),
        )

    if faltando:
        st.info("Preencha/selecione: " + ", ".join(faltando) + " — valores abaixo atualizam ao completar.")

    m1, m2, m3 = st.columns(3)
    m1.metric(
        "Venda unitária",
        brl(resultado.preco_com_imposto) if resultado else "R$ 0,00",
    )
    m2.metric(
        "Venda total do item",
        brl(resultado.valor_venda_total) if resultado else "R$ 0,00",
    )
    m3.metric(
        "Lucro total do item",
        brl(resultado.lucro_total) if resultado else "R$ 0,00",
    )

    d1, d2 = st.columns(2)
    with d1:
        if st.button("Exibir memória de cálculo", key=_fk("sup_mem"), use_container_width=True):
            if not resultado:
                st.error("Complete os campos obrigatórios para ver a memória de cálculo.")
            else:
                st.session_state.memoria_calculo = {
                    "tipo": "suprimentos",
                    "resultado": resultado,
                    "params": {
                        "Descrição": descricao,
                        "Custo": custo,
                        "Quantidade": quantidade,
                        "Difal": difal_sel,
                        "Frete": frete,
                        "Lucro": lucro,
                    },
                }
                st.session_state.show_dialog = "memoria"
                st.rerun()
    with d2:
        if st.button(
            "Inserir item na proposta",
            type="primary",
            key=_fk("sup_ins"),
            use_container_width=True,
        ):
            if not resultado:
                st.error("Complete os campos obrigatórios antes de inserir.")
            elif not proposta.get("cliente"):
                st.error("Selecione um cliente antes de inserir o item.")
            else:
                with st.spinner("Inserindo item e salvando orçamento..."):
                    _garantir_numero(conn, proposta)
                    proposta["itens"].append(
                        {
                            "tipo_item": "suprimentos",
                            "descricao": descricao,
                            "unidade": unidade,
                            "quantidade": float(quantidade),
                            "preco_unitario": resultado.preco_com_imposto,
                            "valor_venda_total": resultado.valor_venda_total,
                            "lucro_total": resultado.lucro_total,
                            "frete_item": float(frete),
                            "calculo": resultado.to_dict(),
                            "parametros": {
                                "custo": custo,
                                "difal": difal_sel == "SIM",
                                "lucro": lucro,
                            },
                        }
                    )
                    salvar_orcamento(conn, proposta, status="rascunho")
                    marcar_proposta_suja()
                bump_form_seq()
                st.session_state.modo_form = None
                flash_sucesso("Item inserido com sucesso. Formulário limpo para o próximo item.")
                st.rerun()


def _garantir_numero(conn, proposta) -> None:
    if not proposta.get("numero"):
        proposta["numero"] = proximo_numero_orcamento(conn)


def _painel_proposta(conn, cfg, proposta, *, readonly: bool = False) -> None:
    """Prévia na coluna direita — um único container com todo o conteúdo."""
    preview = st.container(border=True)
    with preview:
        st.markdown("#### Prévia da proposta")

        # Logo à esquerda; abaixo: empresa (esq.) | orçamento/cliente (dir.)
        logo = cfg.get("logo_cabecalho") or ""
        if logo and Path(logo).exists():
            st.image(logo, width=240)

        cliente = proposta.get("cliente") or {}
        col_emp, col_cli = st.columns(2)
        with col_emp:
            st.markdown(
                f"**Nome da empresa:** {cfg.get('empresa_nome') or '-'}  \n"
                f"**CNPJ da empresa:** {cfg.get('empresa_cnpj') or '-'}  \n"
                f"**Telefone da empresa:** {cfg.get('empresa_telefone') or '-'}  \n"
                f"**E-mail da empresa:** {cfg.get('empresa_email') or '-'}"
            )
        with col_cli:
            st.markdown(
                f"<div style='text-align:right'>"
                f"<b>Número do Orçamento:</b> {proposta.get('numero') or '(será gerado ao inserir o 1º item)'}<br/>"
                f"<b>Nome do Cliente:</b> {cliente.get('nome') or '-'}<br/>"
                f"<b>CNPJ do Cliente:</b> {cliente.get('cnpj_cpf') or '-'}<br/>"
                f"<b>Aos cuidados do(a) Sr.(a):</b> {proposta.get('solicitante') or '-'}"
                f"</div>",
                unsafe_allow_html=True,
            )
        st.divider()

        itens = proposta.get("itens") or []
        valor_total, lucro_total, frete_total = totais_proposta()

        if itens:
            df = pd.DataFrame(
                [
                    {
                        "N° Item": f"{i+1:02d}",
                        "Descrição": it["descricao"],
                        "Und": it.get("unidade"),
                        "Qtd": it.get("quantidade"),
                        "Preço Unit.": it.get("preco_unitario"),
                        "Valor total": it.get("valor_venda_total"),
                    }
                    for i, it in enumerate(itens)
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            if not readonly:
                rem = st.number_input(
                    "Remover item (nº da linha)",
                    min_value=0,
                    max_value=len(itens),
                    value=0,
                    step=1,
                    key="rem_item_preview",
                )
                if st.button("Remover item", key="btn_rem_item_preview") and rem > 0:
                    proposta["itens"].pop(rem - 1)
                    with st.spinner("Atualizando orçamento..."):
                        if proposta.get("numero"):
                            salvar_orcamento(conn, proposta, status="rascunho")
                    marcar_proposta_suja()
                    flash_sucesso(f"Item {rem:02d} removido com sucesso.")
                    st.rerun()
        else:
            st.info("Nenhum item na proposta ainda.")

        st.markdown(
            f'<div class="orc-total-bar">'
            f"Valor total dos itens: {brl(valor_total)}<br/>"
            f"<span style='font-weight:500;font-size:0.92rem'>"
            f"Lucro: {brl(lucro_total)} • Frete incluso: {brl(frete_total)}"
            f"</span></div>",
            unsafe_allow_html=True,
        )

        frete_exibicao = proposta.get("frete_tipo", "CIF")
        if frete_exibicao == "Taxa" and proposta.get("frete_taxa"):
            frete_exibicao = f"Taxa: {proposta.get('frete_taxa')}"

        st.markdown(
            f"**Condições Gerais de Fornecimento**  \n"
            f"Validade da Proposta: {proposta.get('validade_proposta')}  \n"
            f"Prazo de pagamento: {proposta.get('prazo_pagamento')}  \n"
            f"Prazo de entrega: {proposta.get('prazo_entrega')}  \n"
            f"Frete: {frete_exibicao}  \n"
            f"Impostos: {proposta.get('impostos')}"
        )
        st.markdown(
            f"**Observações Adicionais:**  \n{proposta.get('informacoes_adicionais')}"
        )

        # Rodapé: orçamentista à esquerda, logo alinhada à margem direita
        logo_r = cfg.get("logo_rodape") or ""
        f_info, f_sp, f_logo = st.columns([1.4, 0.4, 1])
        with f_info:
            st.markdown(
                f"{proposta.get('orcamentista_nome') or '-'}  \n"
                f"{proposta.get('orcamentista_cargo') or '-'}  \n"
                f"{proposta.get('orcamentista_telefone') or '-'}  \n"
                f"{proposta.get('orcamentista_email') or '-'}"
            )
        with f_logo:
            if logo_r and Path(logo_r).exists():
                st.image(logo_r, width=200)

        if not readonly and st.button(
            "Limpar orçamento (começar do zero)", key="limpar_preview"
        ):
            reiniciar_proposta(conn)
            flash_sucesso("Orçamento limpo com sucesso.")
            st.rerun()


def _gerar_e_oferecer_pdf(conn, cfg, proposta) -> None:
    if not proposta.get("cliente"):
        st.error("Selecione um cliente.")
        return
    if not proposta.get("itens"):
        st.error("Insira ao menos um item na proposta.")
        return

    progress = st.progress(0, text="Preparando orçamento...")
    try:
        progress.progress(20, text="Gerando número e gravando no histórico...")
        if not proposta.get("numero"):
            _garantir_numero(conn, proposta)
        valor_total, _, _ = totais_proposta()
        salvar_orcamento(conn, proposta, status="finalizado")

        progress.progress(55, text="Montando PDF da proposta...")
        cliente = proposta["cliente"]
        pdf_bytes = gerar_pdf_proposta(
            empresa=cfg,
            orcamento={
                "numero": proposta.get("numero"),
                "cliente_nome": cliente.get("nome"),
                "cliente_doc": cliente.get("cnpj_cpf"),
                "solicitante": proposta.get("solicitante"),
                "validade_proposta": proposta.get("validade_proposta"),
                "prazo_pagamento": proposta.get("prazo_pagamento"),
                "prazo_entrega": proposta.get("prazo_entrega"),
                "frete_tipo": proposta.get("frete_tipo"),
                "impostos": proposta.get("impostos"),
                "informacoes_adicionais": proposta.get("informacoes_adicionais"),
                "orcamentista_nome": proposta.get("orcamentista_nome"),
                "orcamentista_cargo": proposta.get("orcamentista_cargo"),
                "orcamentista_telefone": proposta.get("orcamentista_telefone"),
                "orcamentista_email": proposta.get("orcamentista_email"),
                "valor_total": valor_total,
            },
            itens=proposta["itens"],
            logo_cabecalho=cfg.get("logo_cabecalho") or None,
            logo_rodape=cfg.get("logo_rodape") or None,
        )
        progress.progress(100, text="PDF pronto.")
        st.session_state["_pdf_bytes"] = pdf_bytes
        st.session_state["_pdf_name"] = f"{proposta.get('numero') or 'proposta'}.pdf"
        flash_sucesso(
            f"Orçamento {proposta.get('numero')} finalizado e salvo no histórico."
        )
    finally:
        progress.empty()

    if st.session_state.get("_pdf_bytes"):
        st.download_button(
            "Baixar PDF",
            data=st.session_state["_pdf_bytes"],
            file_name=st.session_state.get("_pdf_name") or "proposta.pdf",
            mime="application/pdf",
            use_container_width=True,
            key="btn_download_pdf",
        )


def _render_dialogs(cfg) -> None:
    which = st.session_state.get("show_dialog")
    if which == "cliente":
        _dialog_cliente()
    elif which == "cliente_avulso":
        _dialog_cliente_avulso()
    elif which == "condicoes":
        _dialog_condicoes(cfg)
    elif which == "memoria":
        _dialog_memoria()


@st.dialog("Selecionar cliente")
def _dialog_cliente() -> None:
    termo = st.text_input("Pesquisar por CNPJ ou Nome", key="dlg_cli_termo")
    # Nova conexão nesta thread do popup (corrige ProgrammingError)
    with connect() as conn:
        total = contar_clientes(conn, termo=termo or None)
        clientes = buscar_clientes(conn, termo=termo or None, limite=None)
        st.caption(
            f"{total} cliente(s) encontrado(s) no banco — clique na linha para selecionar"
        )
        if not clientes:
            st.warning("Nenhum cliente encontrado.")
        else:
            df = pd.DataFrame([dict(c) for c in clientes])[
                ["cnpj_cpf", "nome", "uf"]
            ].rename(columns={"cnpj_cpf": "CNPJ", "nome": "Nome", "uf": "UF"})
            idx = dataframe_selecionavel(df, key="dlg_cli_grid", height=320)
            if idx is not None:
                st.success(
                    f"Selecionado: **{clientes[idx]['nome']}** | {clientes[idx]['cnpj_cpf']}"
                )
            else:
                st.info("Clique em uma linha da grade para selecionar o cliente.")

            if st.button("Confirmar", type="primary", key="dlg_cli_ok"):
                if idx is None:
                    st.error("Clique em um cliente na grade antes de confirmar.")
                else:
                    with connect() as conn2:
                        cli = obter_cliente(conn2, int(clientes[idx]["id"]))
                    st.session_state.proposta["cliente"] = dict(cli)
                    st.session_state.show_dialog = None
                    flash_sucesso(f"Cliente selecionado: {cli['nome']}")
                    st.rerun()
    if st.button("Fechar", key="dlg_cli_fechar"):
        st.session_state.show_dialog = None
        st.rerun()


@st.dialog("Cliente avulso")
def _dialog_cliente_avulso() -> None:
    cnpj = st.text_input("CNPJ")
    nome = st.text_input("Nome do cliente")
    if st.button("Confirmar", type="primary"):
        if not nome.strip():
            st.error("Informe o nome.")
        else:
            st.session_state.proposta["cliente"] = {
                "id": None,
                "nome": nome.strip(),
                "cnpj_cpf": cnpj.strip() or None,
                "uf": None,
            }
            st.session_state.show_dialog = None
            flash_sucesso(f"Cliente avulso definido: {nome.strip()}")
            st.rerun()
    if st.button("Fechar"):
        st.session_state.show_dialog = None
        st.rerun()


@st.dialog("Condições gerais de fornecimento")
def _dialog_condicoes(cfg) -> None:
    p = st.session_state.proposta
    p["solicitante"] = st.text_input("Nome do solicitante", value=p.get("solicitante") or "")
    p["validade_proposta"] = st.text_input(
        "Validade da proposta",
        value=p.get("validade_proposta") or cfg.get("validade_proposta"),
    )
    p["prazo_pagamento"] = st.text_input(
        "Prazo de pagamento",
        value=p.get("prazo_pagamento") or cfg.get("prazo_pagamento"),
    )
    p["prazo_entrega"] = st.text_input(
        "Prazo de entrega",
        value=p.get("prazo_entrega") or cfg.get("prazo_entrega", "5 dias"),
    )
    frete_opts = ["CIF", "FOB", "Taxa"]
    atual = p.get("frete_tipo") or "CIF"
    idx = frete_opts.index(atual) if atual in frete_opts else 0
    p["frete_tipo"] = st.selectbox("Frete", frete_opts, index=idx)
    if p["frete_tipo"] == "Taxa":
        p["frete_taxa"] = st.text_input("Valor/taxa do frete", value=p.get("frete_taxa") or "")
    p["impostos"] = st.text_input("Impostos", value=p.get("impostos") or cfg.get("impostos"))
    p["informacoes_adicionais"] = st.text_area(
        "Informações adicionais",
        value=p.get("informacoes_adicionais") or cfg.get("informacoes_adicionais"),
    )
    p["orcamentista_nome"] = st.text_input(
        "Nome do orçamentista",
        value=p.get("orcamentista_nome") or cfg.get("orcamentista_nome"),
    )
    p["orcamentista_cargo"] = st.text_input(
        "Cargo",
        value=p.get("orcamentista_cargo") or cfg.get("orcamentista_cargo"),
    )
    p["orcamentista_telefone"] = st.text_input(
        "Telefone",
        value=p.get("orcamentista_telefone") or cfg.get("orcamentista_telefone"),
    )
    p["orcamentista_email"] = st.text_input(
        "E-mail",
        value=p.get("orcamentista_email") or cfg.get("orcamentista_email"),
    )
    if st.button("Salvar condições", type="primary"):
        marcar_proposta_suja()
        st.session_state.show_dialog = None
        flash_sucesso("Condições gerais salvas com sucesso.")
        st.rerun()


@st.dialog("Memória de cálculo", width="large")
def _dialog_memoria() -> None:
    itens = (st.session_state.get("proposta") or {}).get("itens") or []
    rascunho = st.session_state.get("memoria_calculo")
    render_memoria_completa(itens=itens, rascunho=rascunho)
    if st.button("Fechar", key="mem_fechar"):
        st.session_state.show_dialog = None
        st.rerun()
