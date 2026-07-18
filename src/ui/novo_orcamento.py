"""Tela Novo Orçamento — layout 2 colunas do PPTX."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.services.cadastros import (
    listar_caixas,
    listar_facas,
    listar_materias_primas,
    listar_tubetes,
    obter_caixa_por_nome,
    obter_faca_por_tipo,
    obter_materia_por_nome,
    obter_tubete_por_nome,
)
from src.services.calculos_orcamento import (
    ResultadoEtiqueta,
    ResultadoSuprimentos,
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
from src.services.pdf_proposta import gerar_pdf_proposta
from src.ui.formatters import brl, texto_ou_traco
from src.ui.state import reiniciar_proposta, totais_proposta, voltar


def render_novo_orcamento(conn) -> None:
    cfg = carregar_config(conn)
    proposta = st.session_state.proposta

    top1, top2, top3 = st.columns([3.2, 1, 1.2])
    with top1:
        st.markdown(
            '<p class="orc-title">Novo Orçamento</p>',
            unsafe_allow_html=True,
        )
        st.caption("Menu → Novo Orçamento")
    with top2:
        if st.button("← Voltar", use_container_width=True, key="orc_voltar"):
            voltar()
    with top3:
        if st.button(
            "Limpar orçamento",
            use_container_width=True,
            type="secondary",
            key="orc_limpar",
        ):
            reiniciar_proposta(conn)
            st.success("Orçamento limpo. Você pode começar do zero.")
            st.rerun()

    # Dialogs (abrem conexão própria — evita erro de thread do SQLite)
    _render_dialogs(cfg)

    col_form, col_preview = st.columns([1.05, 1], gap="medium")

    with col_form:
        _painel_esquerda(conn, cfg, proposta)

    with col_preview:
        _painel_proposta(cfg, proposta)


def _painel_esquerda(conn, cfg, proposta) -> None:
    st.markdown('<div class="orc-card">', unsafe_allow_html=True)
    st.markdown("#### Selecionar cliente")
    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Selecionar cliente", use_container_width=True):
            st.session_state.show_dialog = "cliente"
            st.rerun()
    with b2:
        if st.button("Cliente avulso", use_container_width=True):
            st.session_state.show_dialog = "cliente_avulso"
            st.rerun()
    with b3:
        if st.button("Limpar cliente", use_container_width=True):
            proposta["cliente"] = None
            st.rerun()

    cliente = proposta.get("cliente")
    if cliente:
        st.success(
            f"{cliente.get('nome')} | {texto_ou_traco(cliente.get('cnpj_cpf'))}"
        )
    else:
        st.warning("Nenhum cliente selecionado.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="orc-card">', unsafe_allow_html=True)
    st.markdown("#### Formação de orçamento")
    a1, a2, a3 = st.columns(3)
    with a1:
        if st.button("Inserir nova etiqueta", use_container_width=True, type="primary"):
            st.session_state.modo_form = "etiqueta"
            st.session_state.memoria_calculo = None
            st.rerun()
    with a2:
        if st.button("Inserir novo suprimento", use_container_width=True):
            st.session_state.modo_form = "suprimentos"
            st.session_state.memoria_calculo = None
            st.rerun()
    with a3:
        if st.button("Condições gerais", use_container_width=True):
            st.session_state.show_dialog = "condicoes"
            st.rerun()

    _, lucro_total, frete_total = totais_proposta()
    k1, k2, k3 = st.columns(3)
    k1.metric("Lucro total da proposta", brl(lucro_total))
    k2.metric("Frete total incluso", brl(frete_total))
    with k3:
        st.write("")
        if st.button("Gerar PDF da proposta", use_container_width=True):
            _gerar_e_oferecer_pdf(cfg, proposta)
    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.modo_form in ("etiqueta", "suprimentos"):
        if st.button("← Fechar formulário de inserção", key="fechar_form_item"):
            st.session_state.modo_form = None
            st.rerun()
        if st.session_state.modo_form == "etiqueta":
            _form_etiqueta(conn, cfg, proposta)
        else:
            _form_suprimentos(cfg, proposta)


def _form_etiqueta(conn, cfg, proposta) -> None:
    st.markdown('<div class="orc-card">', unsafe_allow_html=True)
    st.markdown("#### Inserir etiqueta")

    facas = listar_facas(conn)
    materias = listar_materias_primas(conn)
    tubetes = listar_tubetes(conn)
    caixas = listar_caixas(conn)
    if not all([facas, materias, tubetes, caixas]):
        st.error("Cadastros incompletos. Importe a planilha / cadastre os itens.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    c1, c2 = st.columns(2)
    with c1:
        tipo_faca = st.selectbox("Dimensão da etiqueta", [f["tipo_faca"] for f in facas])
        qtd_etq = st.number_input(
            "Qtd de etiquetas por rolo", min_value=1, value=1000, step=1
        )
        unidade = st.text_input(
            "Unidade de medida", value=cfg.get("unidade_etiqueta", "Rol")
        )
        qtd_total = st.number_input("Qtd total (rolos)", min_value=1, value=50, step=1)
        qtd_caixas = st.number_input("Qtd de caixas", min_value=0, value=1, step=1)
        frete = st.number_input(
            "Valor do frete",
            min_value=0.0,
            value=get_float(cfg, "frete_padrao", 0.0),
            step=10.0,
        )
    with c2:
        materia_nome = st.selectbox("Tipo de matéria-prima", [m["nome"] for m in materias])
        tubete_nome = st.selectbox("Tipo de tubete", [t["nome"] for t in tubetes])
        caixa_default = next(
            (c["nome"] for c in caixas if "tipo 1" in c["nome"].lower()),
            caixas[0]["nome"],
        )
        caixa_nome = st.selectbox(
            "Tipo de caixa",
            [c["nome"] for c in caixas],
            index=[c["nome"] for c in caixas].index(caixa_default),
        )
        perda = st.number_input(
            "Perda (ex.: 0.02 = 2%)",
            min_value=0.0,
            max_value=1.0,
            value=get_float(cfg, "perda_padrao", 0.0),
            step=0.01,
            format="%.2f",
        )
        lucro = st.number_input(
            "Lucro (ex.: 0.30 = 30%)",
            min_value=0.0,
            max_value=5.0,
            value=get_float(cfg, "lucro_etiqueta_padrao", 0.30),
            step=0.05,
            format="%.2f",
        )

    faca = obter_faca_por_tipo(conn, tipo_faca)
    materia = obter_materia_por_nome(conn, materia_nome)
    tubete = obter_tubete_por_nome(conn, tubete_nome)
    caixa = obter_caixa_por_nome(conn, caixa_nome)

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
    st.caption(f"Descrição gerada: **{descricao}**")

    m1, m2, m3 = st.columns(3)
    m1.metric("Venda unitária", brl(resultado.preco_com_imposto))
    m2.metric("Venda total do item", brl(resultado.valor_venda_total))
    m3.metric("Lucro total do item", brl(resultado.lucro_total))

    d1, d2 = st.columns(2)
    with d1:
        if st.button("Exibir memória de cálculo", use_container_width=True):
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
        if st.button("Inserir item na proposta", type="primary", use_container_width=True):
            if not proposta.get("cliente"):
                st.error("Selecione um cliente antes de inserir o item.")
            else:
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
                st.success("Item inserido na proposta.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _form_suprimentos(cfg, proposta) -> None:
    st.markdown('<div class="orc-card">', unsafe_allow_html=True)
    st.markdown("#### Inserir suprimento")

    c1, c2 = st.columns(2)
    with c1:
        descricao_in = st.text_input("Descrição do item")
        custo = st.number_input("Custo", min_value=0.0, value=0.0, step=0.1)
        unidade = st.text_input(
            "Unidade de medida",
            value=cfg.get("unidade_suprimentos", "UN"),
            key="und_sup",
        )
        quantidade = st.number_input("Quantidade", min_value=1.0, value=1.0, step=1.0)
    with c2:
        difal_default = 0 if cfg.get("difal_padrao", "SIM").upper() == "SIM" else 1
        difal = st.selectbox("Difal", ["SIM", "NÃO"], index=difal_default) == "SIM"
        frete = st.number_input(
            "Valor do frete",
            min_value=0.0,
            value=get_float(cfg, "frete_padrao", 0.0),
            step=10.0,
            key="frete_sup",
        )
        lucro = st.number_input(
            "Lucro (ex.: 0.20 = 20%)",
            min_value=0.0,
            max_value=5.0,
            value=get_float(cfg, "lucro_suprimentos_padrao", 0.20),
            step=0.05,
            format="%.2f",
            key="lucro_sup",
        )

    resultado = calcular_orcamento_suprimentos(
        custo=float(custo),
        frete_total=float(frete),
        quantidade=float(quantidade),
        difal=difal,
        lucro_percentual=float(lucro),
    )
    descricao = montar_descricao_suprimento(descricao_in)

    m1, m2, m3 = st.columns(3)
    m1.metric("Venda unitária", brl(resultado.preco_com_imposto))
    m2.metric("Venda total do item", brl(resultado.valor_venda_total))
    m3.metric("Lucro total do item", brl(resultado.lucro_total))

    d1, d2 = st.columns(2)
    with d1:
        if st.button("Exibir memória de cálculo", key="mem_sup", use_container_width=True):
            st.session_state.memoria_calculo = {
                "tipo": "suprimentos",
                "resultado": resultado,
                "params": {
                    "Descrição": descricao,
                    "Custo": custo,
                    "Quantidade": quantidade,
                    "Difal": "SIM" if difal else "NÃO",
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
            key="ins_sup",
            use_container_width=True,
        ):
            if not proposta.get("cliente"):
                st.error("Selecione um cliente antes de inserir o item.")
            elif not descricao:
                st.error("Informe a descrição do item.")
            else:
                _garantir_numero_from_session(proposta)
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
                            "difal": difal,
                            "lucro": lucro,
                        },
                    }
                )
                st.success("Item inserido na proposta.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _garantir_numero(conn, proposta) -> None:
    if not proposta.get("numero"):
        proposta["numero"] = proximo_numero_orcamento(conn)


def _garantir_numero_from_session(proposta) -> None:
    if not proposta.get("numero"):
        with connect() as conn:
            proposta["numero"] = proximo_numero_orcamento(conn)


def _painel_proposta(cfg, proposta) -> None:
    st.markdown('<div class="proposta-box">', unsafe_allow_html=True)
    st.markdown("#### Prévia da proposta")
    st.caption("Atualiza automaticamente conforme as inserções")

    logo = cfg.get("logo_cabecalho") or ""
    if logo and Path(logo).exists():
        st.image(logo, width=120)

    st.markdown(
        f"**{cfg.get('empresa_nome') or '(Nome da empresa — preencher em Valores Nativos)'}**  \n"
        f"CNPJ: {cfg.get('empresa_cnpj') or '-'}  \n"
        f"Tel: {cfg.get('empresa_telefone') or '-'}  \n"
        f"E-mail: {cfg.get('empresa_email') or '-'}"
    )
    st.divider()

    cliente = proposta.get("cliente") or {}
    st.markdown(
        f"**Número do Orçamento:** {proposta.get('numero') or '(será gerado ao inserir o 1º item)'}  \n"
        f"**Nome do Cliente:** {cliente.get('nome') or '-'}  \n"
        f"**CNPJ do Cliente:** {cliente.get('cnpj_cpf') or '-'}  \n"
        f"**Aos cuidados do(a) Sr.(a):** {proposta.get('solicitante') or '-'}"
    )

    itens = proposta.get("itens") or []
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
        rem = st.number_input(
            "Remover item (nº da linha)",
            min_value=0,
            max_value=len(itens),
            value=0,
            step=1,
        )
        if st.button("Remover item") and rem > 0:
            proposta["itens"].pop(rem - 1)
            st.rerun()
    else:
        st.info("Nenhum item na proposta ainda.")

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
    st.markdown(
        f"{proposta.get('orcamentista_nome') or '-'}  \n"
        f"{proposta.get('orcamentista_cargo') or '-'}  \n"
        f"{proposta.get('orcamentista_telefone') or '-'}  \n"
        f"{proposta.get('orcamentista_email') or '-'}"
    )

    logo_r = cfg.get("logo_rodape") or ""
    if logo_r and Path(logo_r).exists():
        st.image(logo_r, width=100)

    if st.button("Limpar orçamento (começar do zero)", key="limpar_preview"):
        with connect() as conn:
            reiniciar_proposta(conn)
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _gerar_e_oferecer_pdf(cfg, proposta) -> None:
    if not proposta.get("cliente"):
        st.error("Selecione um cliente.")
        return
    if not proposta.get("itens"):
        st.error("Insira ao menos um item na proposta.")
        return
    if not proposta.get("numero"):
        _garantir_numero_from_session(proposta)

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
        },
        itens=proposta["itens"],
        logo_cabecalho=cfg.get("logo_cabecalho") or None,
        logo_rodape=cfg.get("logo_rodape") or None,
    )
    st.download_button(
        "Baixar PDF",
        data=pdf_bytes,
        file_name=f"{proposta.get('numero') or 'proposta'}.pdf",
        mime="application/pdf",
        use_container_width=True,
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
    termo = st.text_input("Pesquisar por CNPJ ou Nome")
    # Nova conexão nesta thread do popup (corrige ProgrammingError)
    with connect() as conn:
        total = contar_clientes(conn, termo=termo or None)
        clientes = buscar_clientes(conn, termo=termo or None, limite=None)
        st.caption(f"{total} cliente(s) encontrado(s) no banco")
        if not clientes:
            st.warning("Nenhum cliente encontrado.")
        else:
            df = pd.DataFrame([dict(c) for c in clientes])[
                ["cnpj_cpf", "nome", "uf"]
            ].rename(columns={"cnpj_cpf": "CNPJ", "nome": "Nome", "uf": "UF"})
            st.dataframe(df, use_container_width=True, hide_index=True, height=320)
            opcoes = {f"{c['nome']} | {c['cnpj_cpf']}": c["id"] for c in clientes}
            escolha = st.selectbox("Cliente", list(opcoes.keys()))
            if st.button("Confirmar", type="primary"):
                with connect() as conn2:
                    cli = obter_cliente(conn2, opcoes[escolha])
                st.session_state.proposta["cliente"] = dict(cli)
                st.session_state.show_dialog = None
                st.rerun()
    if st.button("Fechar"):
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
        st.session_state.show_dialog = None
        st.rerun()


@st.dialog("Memória de cálculo")
def _dialog_memoria() -> None:
    mem = st.session_state.get("memoria_calculo")
    if not mem:
        st.warning("Sem memória de cálculo.")
        return
    st.write(f"Tipo: **{mem['tipo']}**")
    st.json(mem.get("params") or {})
    resultado = mem.get("resultado")
    if isinstance(resultado, (ResultadoEtiqueta, ResultadoSuprimentos)):
        st.json(resultado.to_dict())
    elif isinstance(resultado, dict):
        st.json(resultado)
    if st.button("Fechar"):
        st.session_state.show_dialog = None
        st.rerun()
