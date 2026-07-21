"""Histórico de orçamentos — consultar (somente leitura) e clonar."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.services.configuracoes import carregar_config
from src.services.orcamentos import (
    STATUS_APROVADO,
    STATUS_GERADO,
    STATUS_RASCUNHO,
    STATUS_CANCELADO,
    anos_orcamentos,
    atualizar_status_orcamento,
    buscar_orcamentos,
    clonar_para_novo,
    label_status,
    obter_orcamento,
    orcamento_para_proposta,
)
from src.services.pdf_memoria import gerar_pdf_memoria
from src.ui.formatters import brl, pct
from src.ui.grid_select import dataframe_selecionavel
from src.ui.memoria_ui import (
    lucro_total_itens,
    media_lucro_pct_proporcional,
    render_memorias_itens,
)
from src.ui.state import (
    bump_form_seq,
    flash_sucesso,
    ir_para,
    marcar_proposta_suja,
    voltar,
)

_MESES = [
    "(todos)",
    "01 - Janeiro",
    "02 - Fevereiro",
    "03 - Março",
    "04 - Abril",
    "05 - Maio",
    "06 - Junho",
    "07 - Julho",
    "08 - Agosto",
    "09 - Setembro",
    "10 - Outubro",
    "11 - Novembro",
    "12 - Dezembro",
]

_STATUS_FILTRO = [
    ("(todos)", None),
    ("Orçamento gerado", STATUS_GERADO),
    ("Aprovado", STATUS_APROVADO),
    ("Rascunho", STATUS_RASCUNHO),
    ("Cancelado", STATUS_CANCELADO),
]


def render_historico_orcamentos(conn) -> None:
    top1, top2 = st.columns([4, 1])
    with top1:
        st.markdown(
            '<p class="orc-title">Histórico de Orçamentos</p>',
            unsafe_allow_html=True,
        )
        st.caption(
            "Consulte orçamentos realizados. Histórico é somente leitura — "
            "use Clonar para reaproveitar. Abra um orçamento para marcar como Aprovado."
        )
    with top2:
        if st.button("← Voltar", key="hist_orc_voltar"):
            voltar()

    with st.container(border=True):
        termo = st.text_input(
            "Buscar por número do orçamento",
            placeholder="Ex.: ORC-00005",
            key="hist_orc_termo",
        )

        f1, f2, f3, f4, f5 = st.columns(5)
        anos = anos_orcamentos(conn)
        ano_opts = ["(todos)"] + [str(a) for a in anos]
        with f1:
            dia_sel = st.selectbox(
                "Dia",
                ["(todos)"] + [f"{d:02d}" for d in range(1, 32)],
                key="hist_orc_dia",
            )
        with f2:
            mes_sel = st.selectbox("Mês", _MESES, key="hist_orc_mes")
        with f3:
            ano_sel = st.selectbox("Ano", ano_opts, key="hist_orc_ano")
        with f4:
            cliente_filtro = st.text_input(
                "Cliente",
                placeholder="Nome ou CNPJ",
                key="hist_orc_cliente",
            )
        with f5:
            status_labels = [x[0] for x in _STATUS_FILTRO]
            status_sel = st.selectbox("Status", status_labels, key="hist_orc_status")

        b1, b2, _ = st.columns([1, 1, 2])
        with b1:
            buscar = st.button(
                "Buscar", type="primary", use_container_width=True, key="hist_orc_buscar"
            )
        with b2:
            limpar = st.button("Limpar", use_container_width=True, key="hist_orc_limpar")

        if limpar:
            for k in (
                "hist_orc_termo",
                "hist_orc_dia",
                "hist_orc_mes",
                "hist_orc_ano",
                "hist_orc_cliente",
                "hist_orc_status",
            ):
                if k in st.session_state:
                    del st.session_state[k]
            st.session_state.hist_orc_lista = None
            st.session_state.hist_orc_detalhe_id = None
            st.rerun()

        if buscar or st.session_state.get("hist_orc_lista") is not None:
            dia = None if dia_sel == "(todos)" else int(dia_sel)
            mes = None if mes_sel == "(todos)" else int(mes_sel.split(" - ")[0])
            ano = None if ano_sel == "(todos)" else int(ano_sel)
            status_code = next(
                (c for lab, c in _STATUS_FILTRO if lab == status_sel), None
            )
            with st.spinner("Buscando orçamentos..."):
                rows = buscar_orcamentos(
                    conn,
                    termo=termo or None,
                    cliente=cliente_filtro or None,
                    status=status_code,
                    dia=dia,
                    mes=mes,
                    ano=ano,
                )
            st.session_state.hist_orc_lista = [dict(r) for r in rows]

        lista = st.session_state.get("hist_orc_lista")
        if lista is None:
            st.info("Ajuste os filtros (opcional) e clique em **Buscar**.")
            return

        if not lista:
            st.warning("Nenhum orçamento encontrado.")
            return

        df = pd.DataFrame(
            [
                {
                    "ID": r["id"],
                    "Número": r.get("numero") or "-",
                    "Cliente": r.get("cliente_nome") or "-",
                    "Status": label_status(r.get("status")),
                    "Valor total": brl(r.get("valor_total") or 0),
                    "Criado em": r.get("criado_em") or "-",
                    "Atualizado em": r.get("atualizado_em") or "-",
                }
                for r in lista
            ]
        )
        st.caption(f"{len(lista)} orçamento(s) — clique na linha para selecionar.")
        idx = dataframe_selecionavel(df, key="hist_orc_grid", height=360)
        orc_id = None
        if idx is not None:
            orc_id = int(lista[idx]["id"])
            st.success(
                f"Selecionado: **{lista[idx].get('numero') or '-'}** — "
                f"{lista[idx].get('cliente_nome') or '-'} — "
                f"Status: **{label_status(lista[idx].get('status'))}**"
            )
        else:
            st.info("Clique em uma linha para selecionar.")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Abrir (somente leitura)", type="primary", use_container_width=True):
                if orc_id is None:
                    st.error("Selecione um orçamento na grade.")
                else:
                    _abrir_readonly(conn, orc_id)
        with c2:
            if st.button("Aprovado", use_container_width=True, key="hist_btn_aprovar"):
                if orc_id is None:
                    st.error("Selecione um orçamento na grade.")
                else:
                    _aprovar(conn, orc_id)
        with c3:
            if st.button("Clonar como novo orçamento", use_container_width=True):
                if orc_id is None:
                    st.error("Selecione um orçamento na grade.")
                else:
                    _clonar(conn, orc_id)
        with c4:
            if st.button("Ver detalhes aqui", use_container_width=True):
                if orc_id is None:
                    st.error("Selecione um orçamento na grade.")
                else:
                    st.session_state.hist_orc_detalhe_id = orc_id
                    st.rerun()

    detalhe_id = st.session_state.get("hist_orc_detalhe_id")
    if detalhe_id:
        _painel_detalhe(conn, detalhe_id)


def _aprovar(conn, orcamento_id: int) -> None:
    orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        st.error("Orçamento não encontrado.")
        return
    if (orc.get("status") or "").lower() == STATUS_APROVADO:
        flash_sucesso("Este orçamento já está Aprovado.")
        st.rerun()
        return
    with st.spinner("Atualizando status..."):
        atualizar_status_orcamento(conn, orcamento_id, STATUS_APROVADO)
    # Atualiza lista em memória
    lista = st.session_state.get("hist_orc_lista") or []
    for r in lista:
        if r.get("id") == orcamento_id:
            r["status"] = STATUS_APROVADO
    flash_sucesso(
        f"Orçamento {orc.get('numero') or orcamento_id} marcado como Aprovado."
    )
    st.rerun()


def _abrir_readonly(conn, orcamento_id: int) -> None:
    with st.spinner("Carregando orçamento..."):
        orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        st.error("Orçamento não encontrado.")
        return
    st.session_state.proposta = orcamento_para_proposta(orc)
    st.session_state.proposta_readonly = True
    st.session_state.modo_form = None
    bump_form_seq()
    flash_sucesso(
        f"Orçamento {orc.get('numero') or orcamento_id} aberto em modo consulta "
        f"(status: {label_status(orc.get('status'))})."
    )
    ir_para("novo_orcamento")


def _clonar(conn, orcamento_id: int) -> None:
    with st.spinner("Clonando orçamento..."):
        orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        st.error("Orçamento não encontrado.")
        return
    st.session_state.proposta = clonar_para_novo(orc)
    st.session_state.proposta_readonly = False
    st.session_state.modo_form = None
    marcar_proposta_suja()
    bump_form_seq()
    flash_sucesso(
        f"Clone criado a partir de {orc.get('numero') or orcamento_id}. "
        "Edite e salve como novo orçamento."
    )
    ir_para("novo_orcamento")


def _painel_detalhe(conn, orcamento_id: int) -> None:
    orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        return
    with st.container(border=True):
        st.markdown(f"#### Detalhe — {orc.get('numero') or orcamento_id}")
        st.markdown(
            f"**Cliente:** {orc.get('cliente_nome') or '-'}  \n"
            f"**CNPJ:** {orc.get('cliente_doc') or '-'}  \n"
            f"**Status:** {label_status(orc.get('status'))}  \n"
            f"**Valor total:** {brl(orc.get('valor_total') or 0)}  \n"
            f"**Lucro:** {brl(orc.get('lucro_total') or 0)}  \n"
            f"**Criado em:** {orc.get('criado_em')}  \n"
            f"**Atualizado em:** {orc.get('atualizado_em')}"
        )
        itens_db = orc.get("itens") or []
        if itens_db:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "N°": f"{i+1:02d}",
                            "Descrição": it.get("descricao"),
                            "Und": it.get("unidade"),
                            "Qtd": it.get("quantidade"),
                            "Preço Unit.": it.get("preco_unitario"),
                            "Valor total": it.get("preco_total"),
                        }
                        for i, it in enumerate(itens_db)
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("Abrir este (somente leitura)", key="det_abrir"):
                _abrir_readonly(conn, orcamento_id)
        with c2:
            if st.button("Aprovado", key="det_aprovar"):
                _aprovar(conn, orcamento_id)
        with c3:
            if st.button("Clonar este", key="det_clonar"):
                _clonar(conn, orcamento_id)
        with c4:
            mostrar_mem = st.button("Ver memória de cálculo", key="det_memoria")

        if mostrar_mem or st.session_state.get("hist_orc_show_mem") == orcamento_id:
            st.session_state.hist_orc_show_mem = orcamento_id
            st.markdown("#### Memória de cálculo")
            prop = orcamento_para_proposta(orc)
            itens_mem = prop.get("itens") or []
            m1, m2 = st.columns(2)
            m1.metric("Lucro total", brl(lucro_total_itens(itens_mem)))
            m2.metric("Média de margens", pct(media_lucro_pct_proporcional(itens_mem)))
            render_memorias_itens(itens_mem, key_prefix=f"hist_mem_{orcamento_id}")
            cfg = carregar_config(conn)
            pdf_bytes = gerar_pdf_memoria(
                itens=itens_mem,
                orcamento={
                    "numero": orc.get("numero"),
                    "cliente_nome": orc.get("cliente_nome"),
                },
                empresa=cfg,
            )
            st.download_button(
                "Gerar PDF da memória",
                data=pdf_bytes,
                file_name=f"memoria_{orc.get('numero') or orcamento_id}.pdf",
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key=f"btn_pdf_mem_hist_{orcamento_id}",
            )
