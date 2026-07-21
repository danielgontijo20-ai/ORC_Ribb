"""
ORC_Ribb — Interface Streamlit (Etapa 4)

Como rodar:
    streamlit run app.py

Fluxo da tela:
1. Escolher cliente (cadastrado ou avulso)
2. Buscar produto no histórico do cliente (grid)
3. Calcular orçamento (Etiqueta ou Suprimentos)
4. Salvar item no pré-orçamento
5. Ver resumo com lucro total
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from src.db.database import DB_PATH, connect, init_db
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
    calcular_orcamento_etiqueta,
    calcular_orcamento_suprimentos,
)
from src.services.clientes import buscar_clientes, listar_segmentos, obter_cliente
from src.services.historico_vendas import listar_itens_vendidos_ao_cliente
from src.ui.formatters import brl, texto_ou_traco

ROOT = Path(__file__).resolve().parent


def garantir_banco() -> None:
    """Se o banco não existir, cria as tabelas (a importação deve ser feita antes)."""
    if not DB_PATH.exists():
        init_db(DB_PATH)


def init_session() -> None:
    defaults = {
        "cliente": None,  # dict ou None
        "cliente_avulso": False,
        "produto_selecionado": None,  # dict
        "tipo_orcamento": "etiqueta",
        "pre_orcamento": [],  # lista de itens salvos
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reiniciar_orcamento() -> None:
    st.session_state.cliente = None
    st.session_state.cliente_avulso = False
    st.session_state.produto_selecionado = None
    st.session_state.tipo_orcamento = "etiqueta"
    st.session_state.pre_orcamento = []


def resumo_pre_orcamento() -> tuple[float, float]:
    itens = st.session_state.pre_orcamento
    valor_total = sum(i.get("valor_venda_total", 0) or 0 for i in itens)
    lucro_total = sum(i.get("lucro_total", 0) or 0 for i in itens)
    return valor_total, lucro_total


def sidebar() -> None:
    st.sidebar.title("ORC_Ribb")
    st.sidebar.caption("Sistema de orçamentos")

    cliente = st.session_state.cliente
    if cliente:
        st.sidebar.success(
            f"Cliente: {cliente.get('nome', 'Avulso')}\n\n"
            f"Doc: {texto_ou_traco(cliente.get('cnpj_cpf'))}"
        )
    else:
        st.sidebar.info("Nenhum cliente selecionado")

    valor_total, lucro_total = resumo_pre_orcamento()
    st.sidebar.metric("Itens no pré-orçamento", len(st.session_state.pre_orcamento))
    st.sidebar.metric("Valor total", brl(valor_total))
    st.sidebar.metric("Lucro total", brl(lucro_total))

    if st.sidebar.button("Novo orçamento", use_container_width=True):
        reiniciar_orcamento()
        st.rerun()


def aba_cliente(conn) -> None:
    st.subheader("1) Selecionar cliente")
    st.write(
        "Pesquise um cliente cadastrado pelo **nome** ou **CNPJ/CPF**. "
        "Se for um cliente novo, use **orçamento avulso**."
    )

    modo = st.radio(
        "Tipo de cliente",
        ["Cliente cadastrado", "Cliente avulso"],
        horizontal=True,
        key="modo_cliente",
    )

    if modo == "Cliente avulso":
        nome = st.text_input("Nome do cliente avulso")
        doc = st.text_input("CNPJ/CPF (opcional)")
        if st.button("Usar cliente avulso", type="primary"):
            if not nome.strip():
                st.error("Informe o nome do cliente avulso.")
            else:
                st.session_state.cliente = {
                    "id": None,
                    "nome": nome.strip(),
                    "cnpj_cpf": doc.strip() or None,
                    "uf": None,
                }
                st.session_state.cliente_avulso = True
                st.session_state.produto_selecionado = None
                st.success(f"Cliente avulso definido: {nome.strip()}")
        return

    termo = st.text_input(
        "Pesquisar cliente",
        placeholder="Ex.: Verdemar, 65.124, Instituto...",
    )
    clientes = buscar_clientes(conn, termo=termo or None, limite=50)

    if not clientes:
        st.warning("Nenhum cliente encontrado.")
        return

    df = pd.DataFrame([dict(c) for c in clientes])
    df_exibe = df.rename(
        columns={
            "id": "ID",
            "nome": "Nome",
            "cnpj_cpf": "CNPJ/CPF",
            "uf": "UF",
        }
    )
    st.dataframe(df_exibe, use_container_width=True, hide_index=True)

    opcoes = {
        f"{c['nome']} | {c['cnpj_cpf']}": c["id"] for c in clientes
    }
    escolha = st.selectbox("Selecione o cliente na lista", list(opcoes.keys()))
    if st.button("Confirmar cliente", type="primary"):
        cliente = obter_cliente(conn, opcoes[escolha])
        st.session_state.cliente = dict(cliente)
        st.session_state.cliente_avulso = False
        st.session_state.produto_selecionado = None
        st.success(f"Cliente selecionado: {cliente['nome']}")


def aba_produto(conn) -> None:
    st.subheader("2) Selecionar produto")
    cliente = st.session_state.cliente
    if not cliente:
        st.info("Primeiro selecione um cliente na aba **Cliente**.")
        return

    st.write(
        f"Histórico de itens já vendidos para **{cliente['nome']}**. "
        "Use a busca por texto e o filtro de segmento."
    )

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        termo = st.text_input(
            "Buscar por código ou descrição",
            placeholder="Ex.: ribbon, etiqueta, 100x50...",
            key="busca_produto",
        )
    with col2:
        segmentos = ["(todos)"] + listar_segmentos(conn)
        segmento = st.selectbox("Segmento", segmentos)
    with col3:
        st.write("")
        st.write("")
        item_avulso = st.checkbox("Item avulso (sem histórico)")

    if item_avulso:
        st.markdown("#### Item avulso")
        codigo = st.text_input("Código (opcional)", key="avulso_codigo")
        descricao = st.text_input("Descrição do item", key="avulso_descricao")
        segmento_avulso = st.selectbox(
            "Segmento do item",
            listar_segmentos(conn) or ["Avulso"],
            key="avulso_segmento",
        )
        if st.button("Usar item avulso", type="primary"):
            if not descricao.strip():
                st.error("Informe a descrição do item avulso.")
            else:
                st.session_state.produto_selecionado = {
                    "codigo_item": codigo.strip() or None,
                    "descricao_item": descricao.strip(),
                    "segmento": segmento_avulso,
                    "preco_ultima_venda": None,
                    "data_ultima_venda": None,
                    "avulso": True,
                }
                st.success("Item avulso selecionado.")
        return

    if cliente.get("id") is None:
        st.warning(
            "Cliente avulso não tem histórico. Marque **Item avulso** "
            "ou selecione um cliente cadastrado."
        )
        return

    itens = listar_itens_vendidos_ao_cliente(
        conn,
        cliente_id=cliente["id"],
        termo=termo or None,
        segmento=None if segmento == "(todos)" else segmento,
    )

    if not itens:
        st.warning(
            "Nenhum item encontrado para este cliente com os filtros atuais. "
            "Você pode marcar **Item avulso**."
        )
        return

    df = pd.DataFrame([dict(i) for i in itens])
    df_exibe = df.rename(
        columns={
            "codigo_item": "Código",
            "descricao_item": "Descrição",
            "segmento": "Segmento",
            "data_ultima_venda": "Última venda",
            "qtd_ultima_venda": "Qtd última",
            "preco_ultima_venda": "Preço última venda",
            "valor_total_ultima_venda": "Valor total última",
            "vezes_vendido": "Vezes vendido",
        }
    )
    st.dataframe(df_exibe, use_container_width=True, hide_index=True)

    labels = []
    mapa = {}
    for i, item in enumerate(itens):
        codigo = item["codigo_item"] or "SEM CÓDIGO"
        preco = brl(item["preco_ultima_venda"])
        label = f"{codigo} | {item['descricao_item']} | última: {preco}"
        labels.append(label)
        mapa[label] = item

    escolha = st.selectbox("Escolha o produto do grid", labels)
    if st.button("Confirmar produto", type="primary"):
        item = dict(mapa[escolha])
        item["avulso"] = False
        st.session_state.produto_selecionado = item
        st.success(
            f"Produto selecionado. Última venda para este cliente: "
            f"{brl(item.get('preco_ultima_venda'))}"
        )


def painel_ultima_venda(produto: dict) -> None:
    st.markdown("#### Comparativo — última venda deste cliente")
    c1, c2, c3 = st.columns(3)
    c1.metric("Preço última venda", brl(produto.get("preco_ultima_venda")))
    c2.metric("Data", texto_ou_traco(produto.get("data_ultima_venda")))
    c3.metric(
        "Código",
        texto_ou_traco(produto.get("codigo_item")),
    )
    st.caption(f"Descrição: {produto.get('descricao_item')}")


def formulario_etiqueta(conn, produto: dict) -> None:
    facas = listar_facas(conn)
    materias = listar_materias_primas(conn)
    tubetes = listar_tubetes(conn)
    caixas = listar_caixas(conn)

    if not facas or not materias or not tubetes or not caixas:
        st.error("Cadastros incompletos. Rode a importação da planilha.")
        return

    st.markdown("#### Cálculo de etiqueta")
    c1, c2 = st.columns(2)
    with c1:
        tipo_faca = st.selectbox(
            "Dimensão / faca",
            [f["tipo_faca"] for f in facas],
        )
        qtd_etq = st.number_input(
            "Qtd etiquetas por rolo", min_value=1, value=1500, step=1
        )
        n_rolos = st.number_input("Número de rolos", min_value=1, value=50, step=1)
        materia_nome = st.selectbox(
            "Matéria-prima",
            [m["nome"] for m in materias],
        )
    with c2:
        tubete_nome = st.selectbox("Tubete", [t["nome"] for t in tubetes])
        caixa_nome = st.selectbox("Tipo de caixa", [c["nome"] for c in caixas])
        qtd_caixas = st.number_input("Qtd de caixas", min_value=0, value=5, step=1)
        perda = st.number_input(
            "Perda de processo (ex.: 0.02 = 2%)",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.01,
            format="%.2f",
        )
        frete = st.number_input("Frete total (R$)", min_value=0.0, value=120.0, step=10.0)
        lucro = st.number_input(
            "Lucro sobre custo sem frete (ex.: 0.30 = 30%)",
            min_value=0.0,
            max_value=5.0,
            value=0.30,
            step=0.05,
            format="%.2f",
        )

    faca = obter_faca_por_tipo(conn, tipo_faca)
    materia = obter_materia_por_nome(conn, materia_nome)
    tubete = obter_tubete_por_nome(conn, tubete_nome)
    caixa = obter_caixa_por_nome(conn, caixa_nome)

    try:
        resultado = calcular_orcamento_etiqueta(
            area_faca=float(faca["area"]),
            qtd_etiquetas_por_rolo=float(qtd_etq),
            numero_rolos=float(n_rolos),
            custo_m2_materia=float(materia["custo"]),
            custo_tubete=float(tubete["custo"]),
            custo_caixa=float(caixa["custo"]),
            qtd_caixas=float(qtd_caixas),
            perda_processo=float(perda),
            frete_total=float(frete),
            lucro_percentual=float(lucro),
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Erro no cálculo: {exc}")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Custo/rolo c/ frete", brl(resultado.custo_com_frete))
    m2.metric("Preço/rolo c/ imposto", brl(resultado.preco_com_imposto))
    m3.metric("Valor venda total", brl(resultado.valor_venda_total))
    m4.metric("Lucro total", brl(resultado.lucro_total))

    if produto.get("preco_ultima_venda") is not None:
        diff = resultado.preco_com_imposto - float(produto["preco_ultima_venda"])
        st.info(
            f"Comparativo: última venda = {brl(produto['preco_ultima_venda'])} | "
            f"novo preço/rolo = {brl(resultado.preco_com_imposto)} | "
            f"diferença = {brl(diff)}"
        )

    with st.expander("Detalhes do cálculo"):
        st.json(resultado.to_dict())

    if st.button("Salvar item no pré-orçamento", type="primary", key="salvar_etiqueta"):
        item = {
            "tipo_item": "etiqueta",
            "codigo_item": produto.get("codigo_item"),
            "descricao": produto.get("descricao_item"),
            "segmento": produto.get("segmento"),
            "quantidade": float(n_rolos),
            "unidade": "rolo",
            "preco_unitario": resultado.preco_com_imposto,
            "valor_venda_total": resultado.valor_venda_total,
            "lucro_total": resultado.lucro_total,
            "preco_ultima_venda": produto.get("preco_ultima_venda"),
            "parametros": {
                "faca": tipo_faca,
                "materia_prima": materia_nome,
                "tubete": tubete_nome,
                "caixa": caixa_nome,
                "qtd_etiquetas_por_rolo": qtd_etq,
                "qtd_caixas": qtd_caixas,
                "perda": perda,
                "frete": frete,
                "lucro": lucro,
            },
            "calculo": resultado.to_dict(),
        }
        st.session_state.pre_orcamento.append(item)
        st.success("Item salvo no pré-orçamento.")


def formulario_suprimentos(produto: dict) -> None:
    st.markdown("#### Cálculo de suprimentos")
    c1, c2 = st.columns(2)
    with c1:
        custo = st.number_input("Custo unitário (R$)", min_value=0.0, value=2.90, step=0.1)
        frete = st.number_input(
            "Frete total (R$)", min_value=0.0, value=120.0, step=10.0, key="frete_sup"
        )
        quantidade = st.number_input("Quantidade", min_value=1.0, value=300.0, step=1.0)
    with c2:
        difal = st.selectbox("Difal", ["NÃO", "SIM"]) == "SIM"
        lucro = st.number_input(
            "Lucro sobre custo (ex.: 0.20 = 20%)",
            min_value=0.0,
            max_value=5.0,
            value=0.20,
            step=0.05,
            format="%.2f",
            key="lucro_sup",
        )

    try:
        resultado = calcular_orcamento_suprimentos(
            custo=float(custo),
            frete_total=float(frete),
            quantidade=float(quantidade),
            difal=difal,
            lucro_percentual=float(lucro),
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"Erro no cálculo: {exc}")
        return

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Custo unitário", brl(resultado.custo_unitario))
    m2.metric("Preço c/ imposto", brl(resultado.preco_com_imposto))
    m3.metric("Valor venda total", brl(resultado.valor_venda_total))
    m4.metric("Lucro total", brl(resultado.lucro_total))

    if produto.get("preco_ultima_venda") is not None:
        diff = resultado.preco_com_imposto - float(produto["preco_ultima_venda"])
        st.info(
            f"Comparativo: última venda = {brl(produto['preco_ultima_venda'])} | "
            f"novo preço = {brl(resultado.preco_com_imposto)} | "
            f"diferença = {brl(diff)}"
        )

    with st.expander("Detalhes do cálculo"):
        st.json(resultado.to_dict())

    if st.button("Salvar item no pré-orçamento", type="primary", key="salvar_sup"):
        item = {
            "tipo_item": "suprimentos",
            "codigo_item": produto.get("codigo_item"),
            "descricao": produto.get("descricao_item"),
            "segmento": produto.get("segmento"),
            "quantidade": float(quantidade),
            "unidade": "UN",
            "preco_unitario": resultado.preco_com_imposto,
            "valor_venda_total": resultado.valor_venda_total,
            "lucro_total": resultado.lucro_total,
            "preco_ultima_venda": produto.get("preco_ultima_venda"),
            "parametros": {
                "custo": custo,
                "frete": frete,
                "difal": difal,
                "lucro": lucro,
            },
            "calculo": resultado.to_dict(),
        }
        st.session_state.pre_orcamento.append(item)
        st.success("Item salvo no pré-orçamento.")


def aba_calcular(conn) -> None:
    st.subheader("3) Calcular item do orçamento")
    cliente = st.session_state.cliente
    produto = st.session_state.produto_selecionado

    if not cliente:
        st.info("Selecione um cliente primeiro.")
        return
    if not produto:
        st.info("Selecione um produto na aba **Produto**.")
        return

    painel_ultima_venda(produto)

    tipo = st.radio(
        "Tipo deste item",
        ["etiqueta", "suprimentos"],
        horizontal=True,
        format_func=lambda x: "Etiqueta" if x == "etiqueta" else "Suprimentos",
        key="tipo_item_radio",
    )
    st.session_state.tipo_orcamento = tipo

    if tipo == "etiqueta":
        formulario_etiqueta(conn, produto)
    else:
        formulario_suprimentos(produto)


def aba_pre_orcamento() -> None:
    st.subheader("4) Pré-orçamento final")
    cliente = st.session_state.cliente
    itens = st.session_state.pre_orcamento

    if not cliente:
        st.info("Selecione um cliente para iniciar.")
        return

    st.write(f"Cliente: **{cliente['nome']}** | Doc: **{texto_ou_traco(cliente.get('cnpj_cpf'))}**")

    if not itens:
        st.warning("Nenhum item salvo ainda. Calcule e salve itens na aba **Calcular**.")
        return

    df = pd.DataFrame(
        [
            {
                "Tipo": i["tipo_item"],
                "Código": i.get("codigo_item"),
                "Descrição": i.get("descricao"),
                "Segmento": i.get("segmento"),
                "Qtd": i.get("quantidade"),
                "Preço unit.": i.get("preco_unitario"),
                "Última venda": i.get("preco_ultima_venda"),
                "Total": i.get("valor_venda_total"),
                "Lucro": i.get("lucro_total"),
            }
            for i in itens
        ]
    )
    st.dataframe(df, use_container_width=True, hide_index=True)

    valor_total, lucro_total = resumo_pre_orcamento()
    c1, c2, c3 = st.columns(3)
    c1.metric("Itens", len(itens))
    c2.metric("Valor total do orçamento", brl(valor_total))
    c3.metric("Lucro total do orçamento", brl(lucro_total))

    remover = st.number_input(
        "Remover item (número da linha começando em 1)",
        min_value=0,
        max_value=len(itens),
        value=0,
        step=1,
    )
    if st.button("Remover item selecionado") and remover > 0:
        st.session_state.pre_orcamento.pop(remover - 1)
        st.rerun()

    st.success(
        "Pré-orçamento montado. Nas próximas etapas vamos salvar no banco e gerar PDF/Excel."
    )


def main() -> None:
    st.set_page_config(
        page_title="ORC_Ribb — Orçamentos",
        page_icon="📦",
        layout="wide",
    )
    garantir_banco()
    init_session()
    sidebar()

    st.title("ORC_Ribb — Elaboração de orçamentos")
    st.caption(
        "Escolha o cliente → busque o produto no histórico → calcule → "
        "salve no pré-orçamento → veja o lucro total."
    )

    if not DB_PATH.exists():
        st.error(
            "Banco não encontrado. No terminal, rode:\n\n"
            "`python -m src.db.import_banco_rbt`"
        )
        return

    # Verifica se há dados
    with connect() as conn:
        total_cli = conn.execute("SELECT COUNT(*) c FROM clientes").fetchone()["c"]
        if total_cli == 0:
            st.error(
                "O banco está vazio. Importe a planilha com:\n\n"
                "`python -m src.db.import_banco_rbt`"
            )
            return

        aba1, aba2, aba3, aba4 = st.tabs(
            ["Cliente", "Produto", "Calcular", "Pré-orçamento"]
        )
        with aba1:
            aba_cliente(conn)
        with aba2:
            aba_produto(conn)
        with aba3:
            aba_calcular(conn)
        with aba4:
            aba_pre_orcamento()


if __name__ == "__main__":
    main()
