from __future__ import annotations

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from src.db.database import connect
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
from src.services.orcamentos import (
    STATUS_APROVADO,
    STATUS_GERADO,
    STATUS_RASCUNHO,
    atualizar_status_orcamento,
    buscar_orcamentos,
    clonar_para_novo,
    label_status,
    obter_orcamento,
    orcamento_para_proposta,
    salvar_orcamento,
)
from src.services.pdf_memoria import gerar_pdf_memoria
from src.services.pdf_proposta import gerar_pdf_proposta
from src.services.usuarios import usuario_tem_permissao
from src.services.memoria_format import coletar_secoes_memoria, resumo_memoria
from src.ui.formatters import brl, fator_para_pct_input, pct, pct_input_para_fator
from web.deps import get_current_user
from web import proposta_session as ps
from web.logos import logo_url
from web.templating import render

router = APIRouter(prefix="/orcamentos")


def _require_user(request: Request, perm: str):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, perm):
        return None, HTMLResponse("Sem permissão.", status_code=403)
    return user, None


def _block_readonly(request: Request):
    if ps.is_readonly(request):
        ps.flash_err(
            request,
            "Orçamento em modo consulta. Use Clonar para editar uma cópia.",
        )
        return _redirect_novo()
    return None


def _garantir_numero(conn, proposta: dict) -> None:
    if not proposta.get("numero"):
        proposta["numero"] = proximo_numero_orcamento(conn)


def _catalogos(conn) -> dict:
    facas = [dict(r) for r in listar_facas(conn)]
    materias = [dict(r) for r in listar_materias_primas(conn)]
    tubetes = [dict(r) for r in listar_tubetes(conn)]
    caixas = [dict(r) for r in listar_caixas(conn)]
    suprimentos = [dict(r) for r in listar_suprimentos(conn)]
    caixa_nativa = next(
        (c["nome"] for c in caixas if "tipo 1" in (c.get("nome") or "").lower()),
        caixas[0]["nome"] if caixas else "",
    )
    return {
        "facas": facas,
        "materias": materias,
        "tubetes": tubetes,
        "caixas": caixas,
        "suprimentos": suprimentos,
        "caixa_nativa": caixa_nativa,
        "cadastros_ok": bool(facas and materias and tubetes and caixas),
    }


def _ctx_novo(request: Request, conn, user, *, form_vals: dict | None = None) -> dict:
    proposta = ps.get_proposta(request, conn)
    cfg = carregar_config(conn)
    flash_ok, flash_err = ps.consumir_flash(request)
    valor_total, lucro_total, frete_total = ps.totais(proposta)
    media_lucro = ps.media_lucro_pct(proposta.get("itens") or [])
    dialog = ps.get_dialog(request)
    clientes = []
    termo_cli = ""
    if dialog == "cliente":
        termo_cli = (request.query_params.get("termo_cli") or "").strip()
        clientes = [dict(r) for r in buscar_clientes(conn, termo=termo_cli or None)]

    memoria = ps.get_memoria(request)
    memoria_linhas = []
    memoria_lucro_total = 0.0
    memoria_media_margem = 0.0
    if dialog == "memoria":
        memoria_linhas, memoria_lucro_total, memoria_media_margem = _montar_linhas_memoria(
            proposta, memoria
        )

    frete_exibicao = proposta.get("frete_tipo", "CIF")
    if frete_exibicao == "Taxa" and proposta.get("frete_taxa") not in (None, ""):
        frete_exibicao = f"Taxa: {proposta.get('frete_taxa')}"

    vals = form_vals if form_vals is not None else ps.get_form_vals(request)
    edit_index = ps.get_edit_index(request)

    cats = _catalogos(conn)
    return {
        "user": user,
        "cfg": cfg,
        "proposta": proposta,
        "modo": ps.get_modo(request),
        "dialog": dialog,
        "flash_ok": flash_ok,
        "flash_err": flash_err,
        "valor_total": valor_total,
        "lucro_total": lucro_total,
        "frete_total": frete_total,
        "media_lucro": media_lucro,
        "brl": brl,
        "pct": pct,
        "proposta_salva": ps.proposta_esta_salva(request),
        "status_label": label_status(proposta.get("status")),
        "clientes": clientes,
        "termo_cli": termo_cli,
        "total_clientes": contar_clientes(conn, termo=termo_cli or None)
        if dialog == "cliente"
        else 0,
        "memoria_linhas": memoria_linhas,
        "memoria_lucro_total": memoria_lucro_total,
        "memoria_media_margem": memoria_media_margem,
        "frete_exibicao": frete_exibicao,
        "form_vals": vals,
        "edit_index": edit_index,
        "preview_item": None,
        **cats,
        "defaults": {
            "unidade_etiqueta": cfg.get("unidade_etiqueta", "Rol"),
            "unidade_suprimentos": cfg.get("unidade_suprimentos", "UN"),
            "perda": get_float(cfg, "perda_padrao", 0.0),
            "lucro_etiqueta": fator_para_pct_input(
                get_float(cfg, "lucro_etiqueta_padrao", 0.30)
            ),
            "lucro_suprimentos": fator_para_pct_input(
                get_float(cfg, "lucro_suprimentos_padrao", 0.20)
            ),
            "frete": get_float(cfg, "frete_padrao", 0.0),
            "difal": (cfg.get("difal_padrao") or "SIM").upper(),
        },
        "empresa_cnpjs": [
            cfg.get("empresa_cnpj") or "51.832.369/0001-00",
            cfg.get("empresa_cnpj_2") or "31.382.218/0001-81",
        ],
        "empresa_cnpj_atual": (
            proposta.get("empresa_cnpj")
            or cfg.get("empresa_cnpj")
            or "51.832.369/0001-00"
        ),
        "cat_json": {
            "facas": {
                f["tipo_faca"]: {
                    "area": float(f["area"] or 0),
                    "nome_orc": f.get("nome_exibicao_orc") or f["tipo_faca"],
                }
                for f in cats["facas"]
            },
            "materias": {
                m["nome"]: {
                    "custo": float(m["custo"] or 0),
                    "nome_orc": m.get("nome_exibicao_orc") or m["nome"],
                }
                for m in cats["materias"]
            },
            "tubetes": {
                t["nome"]: {
                    "custo": float(t["custo"] or 0),
                    "nome_orc": t.get("nome_exibicao_orc") or t["nome"],
                }
                for t in cats["tubetes"]
            },
            "caixas": {
                c["nome"]: {"custo": float(c["custo"] or 0)}
                for c in cats["caixas"]
            },
            "imposto_etiqueta": 0.92,
            "imposto_suprimentos": 0.91,
            "aliquota_difal": 0.073,
        },
        "readonly": ps.is_readonly(request),
        "logo_cabecalho_url": logo_url(cfg.get("logo_cabecalho")),
        "logo_rodape_url": logo_url(cfg.get("logo_rodape")),
    }


def _rascunho_memoria(rascunho: dict | None) -> dict | None:
    """Normaliza rascunho da sessão web para o formato de memoria_ui/PDF."""
    if not rascunho:
        return None
    resultado = rascunho.get("resultado")
    if resultado is None:
        resultado = rascunho.get("calc")
    if resultado is None:
        return None
    return {
        "tipo": rascunho.get("tipo"),
        "params": rascunho.get("params") or {},
        "resultado": resultado,
    }


def _montar_linhas_memoria(
    proposta: dict, rascunho: dict | None
) -> tuple[list[dict], float, float]:
    """Seções formatadas (com R$) + lucro total e média de margem."""
    rasc = _rascunho_memoria(rascunho)
    itens = proposta.get("itens") or []
    secoes = coletar_secoes_memoria(itens, rasc)
    lucro, media = resumo_memoria(itens, rasc)
    return secoes, lucro, media


def _item_para_form_vals(item: dict) -> tuple[str, dict]:
    """Converte item da proposta em (modo, form_vals) para edição."""
    tipo = (item.get("tipo_item") or "").lower()
    params = item.get("parametros") or {}
    if tipo == "etiqueta":
        return "etiqueta", {
            "tipo_faca": params.get("faca") or params.get("Dimensão") or "(selecione)",
            "materia_nome": params.get("materia")
            or params.get("Matéria-prima")
            or "(selecione)",
            "tubete_nome": params.get("tubete") or params.get("Tubete") or "(selecione)",
            "caixa_nome": params.get("caixa") or params.get("Caixa") or "",
            "unidade": params.get("unidade") or item.get("unidade") or "Rol",
            "qtd_etq": params.get("qtd_etq") or params.get("Qtd etiquetas/rolo") or "",
            "qtd_total": params.get("qtd_total")
            or params.get("Nº rolos")
            or item.get("quantidade")
            or "",
            "qtd_caixas": params.get("qtd_caixas") or params.get("Qtd caixas") or "",
            "perda": params.get("perda") if params.get("perda") is not None else params.get("Perda", ""),
            "lucro": fator_para_pct_input(
                params.get("lucro") if params.get("lucro") is not None else params.get("Lucro", "")
            ),
            "frete": params.get("frete")
            if params.get("frete") is not None
            else (params.get("Frete") if params.get("Frete") is not None else item.get("frete_item", "")),
        }
    # suprimentos (padrão)
    difal = params.get("difal")
    if isinstance(difal, bool):
        difal = "SIM" if difal else "NÃO"
    difal = (difal or params.get("Difal") or "SIM")
    if str(difal).upper() in ("NAO", "NÃO", "N"):
        difal = "NÃO"
    elif str(difal).upper() == "SIM":
        difal = "SIM"
    return "suprimentos", {
        "catalogo": params.get("catalogo") or "",
        "descricao": params.get("descricao")
        or params.get("Descrição")
        or item.get("descricao")
        or "",
        "unidade": params.get("unidade") or item.get("unidade") or "UN",
        "difal": difal,
        "custo": params.get("custo") if params.get("custo") is not None else params.get("Custo", ""),
        "quantidade": params.get("quantidade")
        if params.get("quantidade") is not None
        else (params.get("Quantidade") if params.get("Quantidade") is not None else item.get("quantidade", "")),
        "lucro": fator_para_pct_input(
            params.get("lucro") if params.get("lucro") is not None else params.get("Lucro", "")
        ),
        "frete": params.get("frete")
        if params.get("frete") is not None
        else (params.get("Frete") if params.get("Frete") is not None else item.get("frete_item", "")),
    }


def _salvar_ou_atualizar_item(request: Request, proposta: dict, item: dict) -> str:
    """Insere ou substitui item conforme índice de edição. Retorna mensagem."""
    itens = list(proposta.get("itens") or [])
    edit_idx = ps.get_edit_index(request)
    if edit_idx is not None and 0 <= edit_idx < len(itens):
        itens[edit_idx] = item
        proposta["itens"] = itens
        ps.set_edit_index(request, None)
        return "Item atualizado com sucesso."
    itens.append(item)
    proposta["itens"] = itens
    return "Item inserido com sucesso. Formulário limpo para o próximo item."


def _redirect_novo(query: str = "", *, anchor: str = "") -> RedirectResponse:
    url = "/orcamentos/novo"
    if query:
        url = f"{url}?{query}"
    if anchor:
        url = f"{url}#{anchor}"
    return RedirectResponse(url, status_code=303)


# ---------------------------------------------------------------------------
# Lista / detalhe / aprovar / PDF (já existentes)
# ---------------------------------------------------------------------------


@router.get("", response_class=HTMLResponse)
def lista(
    request: Request,
    termo: str = Query(""),
    cliente: str = Query(""),
    status: str = Query(""),
):
    user, err = _require_user(request, "orcamento.ver")
    if err:
        return err

    with connect() as conn:
        rows = buscar_orcamentos(
            conn,
            termo=termo or None,
            cliente=cliente or None,
            status=status or None,
            limite=200,
        )
        lista_rows = [dict(r) for r in rows]
        for r in lista_rows:
            r["status_label"] = label_status(r.get("status"))

    return render(
        request,
        "orcamentos_lista.html",
        {
            "user": user,
            "lista": lista_rows,
            "termo": termo,
            "cliente": cliente,
            "status": status,
            "brl": brl,
            "pode_aprovar": usuario_tem_permissao(user, "orcamento.aprovar"),
            "pode_pdf": usuario_tem_permissao(user, "orcamento.pdf"),
            "pode_criar": usuario_tem_permissao(user, "orcamento.criar"),
        },
    )


@router.get("/novo", response_class=HTMLResponse)
def novo(request: Request):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    with connect() as conn:
        ctx = _ctx_novo(request, conn, user)
    return render(request, "orcamento_novo.html", ctx)


@router.post("/novo/iniciar")
def iniciar_limpo(request: Request):
    """Entrada pelo menu: orçamento zerado, como na versão 1."""
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    with connect() as conn:
        ps.reiniciar_proposta(request, conn)
    return _redirect_novo()


@router.post("/novo/limpar")
def limpar(request: Request):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    with connect() as conn:
        ps.reiniciar_proposta(request, conn)
    ps.flash_ok(request, "Orçamento e formulários limpos. Valores nativos mantidos.")
    return _redirect_novo()


@router.post("/novo/modo")
def set_modo_form(request: Request, modo: str = Form(...)):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked and modo != "fechar":
        return blocked
    if modo in ("etiqueta", "suprimentos"):
        ps.set_modo(request, modo)
        ps.clear_form_vals(request)
        ps.set_edit_index(request, None)
    elif modo == "fechar":
        ps.set_modo(request, None)
        ps.clear_form_vals(request)
        ps.set_edit_index(request, None)
    return _redirect_novo(anchor="form-item" if modo in ("etiqueta", "suprimentos") else "")


@router.post("/novo/dialog")
def set_dialog(request: Request, dialog: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)
    if dialog == "memoria" or dialog == "fechar":
        if not usuario_tem_permissao(user, "orcamento.ver"):
            return HTMLResponse("Sem permissão.", status_code=403)
    else:
        if not usuario_tem_permissao(user, "orcamento.criar"):
            return HTMLResponse("Sem permissão.", status_code=403)
        if ps.is_readonly(request):
            return _block_readonly(request)
    if dialog in ("cliente", "cliente_avulso", "condicoes", "memoria", "fechar"):
        if dialog == "fechar":
            ps.set_dialog(request, None)
            ps.set_memoria(request, None)
            # Mantém modo + form_vals para reabrir o formulário preenchido.
        elif dialog == "memoria":
            # Não limpa rascunho se já veio do formulário; só abre o dialog.
            ps.set_dialog(request, "memoria")
        else:
            ps.set_dialog(request, dialog)
    # Ao fechar memória com formulário ativo, volta ao popup do form.
    if dialog == "fechar" and ps.get_modo(request):
        return _redirect_novo(anchor="form-item")
    return _redirect_novo(anchor="modal" if dialog != "fechar" else "")


@router.get("/novo/clientes", response_class=HTMLResponse)
def buscar_cli(request: Request, termo_cli: str = Query("")):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    ps.set_dialog(request, "cliente")
    with connect() as conn:
        ctx = _ctx_novo(request, conn, user)
        ctx["termo_cli"] = termo_cli
        ctx["clientes"] = [
            dict(r) for r in buscar_clientes(conn, termo=termo_cli or None)
        ]
        ctx["total_clientes"] = contar_clientes(conn, termo=termo_cli or None)
    return render(request, "orcamento_novo.html", ctx)


@router.post("/novo/cliente/selecionar")
def selecionar_cliente(request: Request, cliente_id: int = Form(...)):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked:
        return blocked
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        cli = obter_cliente(conn, cliente_id)
        if not cli:
            ps.flash_err(request, "Cliente não encontrado.")
            return _redirect_novo()
        proposta["cliente"] = dict(cli)
        ps.set_proposta(request, proposta)
        ps.marcar_suja(request)
        ps.set_dialog(request, None)
        ps.flash_ok(request, f"Cliente selecionado: {cli['nome']}")
    return _redirect_novo()


@router.post("/novo/cliente/avulso")
def cliente_avulso(
    request: Request,
    nome: str = Form(...),
    cnpj: str = Form(""),
):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked:
        return blocked
    nome = (nome or "").strip()
    if not nome:
        ps.flash_err(request, "Informe o nome do cliente avulso.")
        ps.set_dialog(request, "cliente_avulso")
        return _redirect_novo()
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        proposta["cliente"] = {
            "id": None,
            "nome": nome,
            "cnpj_cpf": (cnpj or "").strip() or None,
            "uf": None,
        }
        ps.set_proposta(request, proposta)
        ps.marcar_suja(request)
        ps.set_dialog(request, None)
        ps.flash_ok(request, f"Cliente avulso definido: {nome}")
    return _redirect_novo()


@router.post("/novo/cliente/limpar")
def limpar_cliente(request: Request):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked:
        return blocked
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        proposta["cliente"] = None
        ps.set_proposta(request, proposta)
        ps.marcar_suja(request)
        ps.flash_ok(request, "Cliente removido do orçamento.")
    return _redirect_novo()


@router.post("/novo/empresa-cnpj")
def selecionar_empresa_cnpj(request: Request, empresa_cnpj: str = Form(...)):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked:
        return blocked
    cnpj = (empresa_cnpj or "").strip()
    with connect() as conn:
        cfg = carregar_config(conn)
        opcoes = {
            (cfg.get("empresa_cnpj") or "51.832.369/0001-00").strip(),
            (cfg.get("empresa_cnpj_2") or "31.382.218/0001-81").strip(),
        }
        if cnpj not in opcoes:
            ps.flash_err(request, "CNPJ da empresa inválido.")
            return _redirect_novo()
        proposta = ps.get_proposta(request, conn)
        proposta["empresa_cnpj"] = cnpj
        if proposta.get("id"):
            ps.persistir(
                request,
                conn,
                proposta,
                status=proposta.get("status") or STATUS_RASCUNHO,
            )
        else:
            ps.set_proposta(request, proposta)
        ps.marcar_suja(request)
        ps.flash_ok(request, f"CNPJ da empresa selecionado: {cnpj}")
    return _redirect_novo()


@router.post("/novo/condicoes")
def salvar_condicoes(
    request: Request,
    solicitante: str = Form(""),
    validade_proposta: str = Form(""),
    prazo_pagamento: str = Form(""),
    prazo_entrega: str = Form(""),
    frete_tipo: str = Form("CIF"),
    frete_taxa: str = Form(""),
    impostos: str = Form(""),
    informacoes_adicionais: str = Form(""),
    orcamentista_nome: str = Form(""),
    orcamentista_cargo: str = Form(""),
    orcamentista_telefone: str = Form(""),
    orcamentista_email: str = Form(""),
):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked:
        return blocked
    frete = (frete_tipo or "CIF").strip() or "CIF"
    taxa = frete_taxa.strip() if frete == "Taxa" else ""
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        proposta.update(
            {
                "solicitante": solicitante.strip(),
                "validade_proposta": validade_proposta.strip(),
                "prazo_pagamento": prazo_pagamento.strip(),
                "prazo_entrega": prazo_entrega.strip(),
                "frete_tipo": frete,
                "frete_taxa": taxa,
                "impostos": impostos.strip(),
                "informacoes_adicionais": informacoes_adicionais.strip(),
                "orcamentista_nome": orcamentista_nome.strip(),
                "orcamentista_cargo": orcamentista_cargo.strip(),
                "orcamentista_telefone": orcamentista_telefone.strip(),
                "orcamentista_email": orcamentista_email.strip(),
            }
        )
        # Com id no banco, set_proposta só guarda o id — precisa persistir.
        if proposta.get("id"):
            ps.persistir(
                request,
                conn,
                proposta,
                status=proposta.get("status") or STATUS_RASCUNHO,
            )
        else:
            ps.set_proposta(request, proposta)
        ps.marcar_suja(request)
        ps.set_dialog(request, None)
        ps.flash_ok(request, "Condições gerais salvas com sucesso.")
    return _redirect_novo()


@router.post("/novo/etiqueta")
async def inserir_etiqueta(request: Request):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    form = await request.form()
    acao = str(form.get("acao") or "inserir")
    if acao == "inserir":
        blocked = _block_readonly(request)
        if blocked:
            return blocked
    tipo_faca = str(form.get("tipo_faca") or "")
    materia_nome = str(form.get("materia_nome") or "")
    tubete_nome = str(form.get("tubete_nome") or "")
    caixa_nome = str(form.get("caixa_nome") or "")
    unidade = str(form.get("unidade") or "Rol")
    qtd_etq = ps.parse_float(form.get("qtd_etq"))
    qtd_total = ps.parse_float(form.get("qtd_total"))
    qtd_caixas = ps.parse_float(form.get("qtd_caixas"))
    perda = ps.parse_float(form.get("perda"))
    lucro = pct_input_para_fator(form.get("lucro"))
    frete = ps.parse_float(form.get("frete"))

    form_vals = {
        "tipo_faca": tipo_faca,
        "materia_nome": materia_nome,
        "tubete_nome": tubete_nome,
        "caixa_nome": caixa_nome,
        "unidade": unidade,
        "qtd_etq": form.get("qtd_etq") or "",
        "qtd_total": form.get("qtd_total") or "",
        "qtd_caixas": form.get("qtd_caixas") or "",
        "perda": form.get("perda") or "",
        "lucro": form.get("lucro") or "",
        "frete": form.get("frete") or "",
    }

    with connect() as conn:
        cfg = carregar_config(conn)
        if perda is None:
            perda = get_float(cfg, "perda_padrao", 0.0)
        if lucro is None:
            lucro = get_float(cfg, "lucro_etiqueta_padrao", 0.30)
        if frete is None:
            frete = get_float(cfg, "frete_padrao", 0.0)

        faltando = []
        if not tipo_faca or tipo_faca == "(selecione)":
            faltando.append("dimensão")
        if not materia_nome or materia_nome == "(selecione)":
            faltando.append("matéria-prima")
        if not tubete_nome or tubete_nome == "(selecione)":
            faltando.append("tubete")
        if qtd_etq is None or qtd_etq <= 0:
            faltando.append("qtd etiquetas/rolo")
        if qtd_total is None or qtd_total <= 0:
            faltando.append("qtd total")
        if qtd_caixas is None or qtd_caixas < 0:
            faltando.append("qtd caixas")

        if faltando:
            ps.flash_err(
                request,
                "Preencha/selecione: " + ", ".join(faltando),
            )
            ps.set_modo(request, "etiqueta")
            ps.set_form_vals(request, form_vals)
            ctx = _ctx_novo(request, conn, user, form_vals=form_vals)
            return render(request, "orcamento_novo.html", ctx)

        faca = obter_faca_por_tipo(conn, tipo_faca)
        materia = obter_materia_por_nome(conn, materia_nome)
        tubete = obter_tubete_por_nome(conn, tubete_nome)
        caixa = obter_caixa_por_nome(conn, caixa_nome)
        if not all([faca, materia, tubete, caixa]):
            ps.flash_err(request, "Cadastro incompleto para os itens selecionados.")
            return _redirect_novo()

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
        params = {
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
        }

        if acao == "memoria":
            ps.set_dialog(request, "memoria")
            ps.set_modo(request, "etiqueta")
            ps.set_form_vals(request, form_vals)
            rascunho_mem = {
                "tipo": "etiqueta",
                "params": params,
                "calc": resultado.to_dict(),
            }
            ps.set_memoria(request, rascunho_mem)
            return _redirect_novo(anchor="modal")

        proposta = ps.get_proposta(request, conn)
        if not proposta.get("cliente"):
            ps.flash_err(request, "Selecione um cliente antes de inserir o item.")
            ps.set_modo(request, "etiqueta")
            ps.set_form_vals(request, form_vals)
            ctx = _ctx_novo(request, conn, user, form_vals=form_vals)
            ctx["preview_item"] = {
                "descricao": descricao,
                "unitario": resultado.preco_com_imposto,
                "total": resultado.valor_venda_total,
                "lucro": resultado.lucro_total,
            }
            return render(request, "orcamento_novo.html", ctx)

        _garantir_numero(conn, proposta)
        msg = _salvar_ou_atualizar_item(
            request,
            proposta,
            {
                "tipo_item": "etiqueta",
                "descricao": descricao,
                "unidade": unidade or cfg.get("unidade_etiqueta", "Rol"),
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
                    "qtd_total": qtd_total,
                    "qtd_caixas": qtd_caixas,
                    "perda": perda,
                    "lucro": lucro,
                    "frete": frete,
                    "unidade": unidade,
                },
            },
        )
        ps.persistir(request, conn, proposta, status=STATUS_RASCUNHO)
        ps.marcar_suja(request)
        ps.set_modo(request, None)
        ps.set_dialog(request, None)
        ps.set_memoria(request, None)
        ps.clear_form_vals(request)
        ps.set_edit_index(request, None)
        ps.flash_ok(request, msg)
    return _redirect_novo()


@router.post("/novo/suprimento")
async def inserir_suprimento(request: Request):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    form = await request.form()
    acao = str(form.get("acao") or "inserir")
    if acao == "inserir":
        blocked = _block_readonly(request)
        if blocked:
            return blocked
    descricao_in = str(form.get("descricao") or "").strip()
    unidade = str(form.get("unidade") or "UN")
    difal_sel = str(form.get("difal") or "").upper()
    custo = ps.parse_float(form.get("custo"))
    quantidade = ps.parse_float(form.get("quantidade"))
    lucro = pct_input_para_fator(form.get("lucro"))
    frete = ps.parse_float(form.get("frete"))
    catalogo_sel = str(form.get("catalogo") or "")

    form_vals = {
        "catalogo": catalogo_sel,
        "descricao": descricao_in,
        "unidade": unidade,
        "difal": difal_sel,
        "custo": form.get("custo") or "",
        "quantidade": form.get("quantidade") or "",
        "lucro": form.get("lucro") or "",
        "frete": form.get("frete") or "",
    }

    with connect() as conn:
        cfg = carregar_config(conn)
        if lucro is None:
            lucro = get_float(cfg, "lucro_suprimentos_padrao", 0.20)
        if frete is None:
            frete = get_float(cfg, "frete_padrao", 0.0)

        faltando = []
        if not descricao_in:
            faltando.append("descrição")
        if custo is None or custo < 0:
            faltando.append("custo")
        if quantidade is None or quantidade <= 0:
            faltando.append("quantidade")
        if difal_sel not in ("SIM", "NÃO", "NAO"):
            faltando.append("difal")

        if faltando:
            ps.flash_err(
                request,
                "Preencha/selecione: " + ", ".join(faltando),
            )
            ps.set_modo(request, "suprimentos")
            ps.set_form_vals(request, form_vals)
            ctx = _ctx_novo(request, conn, user, form_vals=form_vals)
            return render(request, "orcamento_novo.html", ctx)

        difal = difal_sel == "SIM"
        resultado = calcular_orcamento_suprimentos(
            custo=float(custo),
            frete_total=float(frete),
            quantidade=float(quantidade),
            difal=difal,
            lucro_percentual=float(lucro),
        )
        descricao = montar_descricao_suprimento(descricao_in)
        params = {
            "Descrição": descricao,
            "Custo": custo,
            "Quantidade": quantidade,
            "Difal": "SIM" if difal else "NÃO",
            "Frete": frete,
            "Lucro": lucro,
        }

        if acao == "memoria":
            ps.set_memoria(
                request,
                {
                    "tipo": "suprimentos",
                    "params": params,
                    "calc": resultado.to_dict(),
                    "descricao": descricao,
                },
            )
            ps.set_dialog(request, "memoria")
            ps.set_modo(request, "suprimentos")
            ps.set_form_vals(request, form_vals)
            return _redirect_novo(anchor="modal")

        proposta = ps.get_proposta(request, conn)
        if not proposta.get("cliente"):
            ps.flash_err(request, "Selecione um cliente antes de inserir o item.")
            ps.set_modo(request, "suprimentos")
            ps.set_form_vals(request, form_vals)
            ctx = _ctx_novo(request, conn, user, form_vals=form_vals)
            return render(request, "orcamento_novo.html", ctx)

        _garantir_numero(conn, proposta)
        msg = _salvar_ou_atualizar_item(
            request,
            proposta,
            {
                "tipo_item": "suprimentos",
                "descricao": descricao,
                "unidade": unidade or cfg.get("unidade_suprimentos", "UN"),
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
                    "frete": frete,
                    "quantidade": quantidade,
                    "descricao": descricao_in,
                    "unidade": unidade,
                    "catalogo": catalogo_sel,
                },
            },
        )
        ps.persistir(request, conn, proposta, status=STATUS_RASCUNHO)
        ps.marcar_suja(request)
        ps.set_modo(request, None)
        ps.set_dialog(request, None)
        ps.set_memoria(request, None)
        ps.clear_form_vals(request)
        ps.set_edit_index(request, None)
        ps.flash_ok(request, msg)
    return _redirect_novo()


@router.post("/novo/item/editar")
def editar_item(request: Request, indice: int = Form(...)):
    """Abre o formulário com os dados do item selecionado na prévia."""
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked:
        return blocked
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        itens = proposta.get("itens") or []
        if not (1 <= indice <= len(itens)):
            ps.flash_err(request, "Selecione um item válido para editar.")
            return _redirect_novo()
        item = itens[indice - 1]
        modo, form_vals = _item_para_form_vals(item)
        ps.set_modo(request, modo)
        ps.set_form_vals(request, form_vals)
        ps.set_edit_index(request, indice - 1)
        ps.set_dialog(request, None)
        ps.flash_ok(
            request,
            f"Editando item {indice:02d}. Altere os campos e salve para atualizar a prévia.",
        )
    return _redirect_novo(anchor="form-item")


@router.post("/novo/item/remover")
def remover_item(request: Request, indice: int = Form(...)):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked:
        return blocked
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        itens = proposta.get("itens") or []
        if 1 <= indice <= len(itens):
            itens.pop(indice - 1)
            proposta["itens"] = itens
            edit_idx = ps.get_edit_index(request)
            if edit_idx is not None:
                if edit_idx == indice - 1:
                    ps.set_edit_index(request, None)
                    ps.clear_form_vals(request)
                    ps.set_modo(request, None)
                elif edit_idx > indice - 1:
                    ps.set_edit_index(request, edit_idx - 1)
            if proposta.get("id") or proposta.get("numero"):
                ps.persistir(request, conn, proposta, status=STATUS_RASCUNHO)
            else:
                ps.set_proposta(request, proposta)
            ps.marcar_suja(request)
            ps.flash_ok(request, f"Item {indice:02d} removido com sucesso.")
        else:
            ps.flash_err(request, "Número de item inválido.")
    return _redirect_novo()


@router.post("/novo/salvar")
def salvar_formacao(request: Request):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    blocked = _block_readonly(request)
    if blocked:
        return blocked
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        if not proposta.get("cliente"):
            ps.flash_err(request, "Selecione um cliente antes de salvar.")
            return _redirect_novo()
        if not proposta.get("itens"):
            ps.flash_err(request, "Insira ao menos um item antes de salvar.")
            return _redirect_novo()
        _garantir_numero(conn, proposta)
        ps.persistir(request, conn, proposta, status=STATUS_GERADO)
        ps.marcar_salva(request)
        ps.flash_ok(
            request,
            f"Orçamento {proposta.get('numero')} salvo com status "
            f"{label_status(STATUS_GERADO)}. Agora você pode gerar o PDF.",
        )
    return _redirect_novo()


@router.get("/novo/pdf")
def pdf_da_sessao(request: Request):
    user, err = _require_user(request, "orcamento.pdf")
    if err:
        return err
    if not ps.proposta_esta_salva(request) and not ps.is_readonly(request):
        ps.flash_err(request, "Salve o orçamento para habilitar o PDF.")
        return _redirect_novo()

    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        cfg = carregar_config(conn)
        if not proposta.get("cliente") or not proposta.get("itens"):
            ps.flash_err(request, "Cliente e itens são obrigatórios para o PDF.")
            return _redirect_novo()

        valor_total, _, _ = ps.totais(proposta)
        cliente = proposta["cliente"]
        frete_exibicao = proposta.get("frete_tipo", "CIF")
        if frete_exibicao == "Taxa" and proposta.get("frete_taxa"):
            frete_exibicao = f"Taxa: {proposta.get('frete_taxa')}"

        pdf_bytes = gerar_pdf_proposta(
            empresa={
                **cfg,
                "empresa_cnpj": proposta.get("empresa_cnpj")
                or cfg.get("empresa_cnpj")
                or "51.832.369/0001-00",
            },
            orcamento={
                "numero": proposta.get("numero"),
                "cliente_nome": cliente.get("nome"),
                "cliente_doc": cliente.get("cnpj_cpf"),
                "solicitante": proposta.get("solicitante"),
                "validade_proposta": proposta.get("validade_proposta"),
                "prazo_pagamento": proposta.get("prazo_pagamento"),
                "prazo_entrega": proposta.get("prazo_entrega"),
                "frete_tipo": frete_exibicao,
                "impostos": proposta.get("impostos"),
                "informacoes_adicionais": proposta.get("informacoes_adicionais"),
                "orcamentista_nome": proposta.get("orcamentista_nome"),
                "orcamentista_cargo": proposta.get("orcamentista_cargo"),
                "orcamentista_telefone": proposta.get("orcamentista_telefone"),
                "orcamentista_email": proposta.get("orcamentista_email"),
                "valor_total": valor_total,
            },
            itens=proposta.get("itens") or [],
            logo_cabecalho=cfg.get("logo_cabecalho") or None,
            logo_rodape=cfg.get("logo_rodape") or None,
        )
    nome = f"{proposta.get('numero') or 'proposta'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/novo/memoria/pdf")
def pdf_memoria_sessao(request: Request):
    user, err = _require_user(request, "orcamento.pdf")
    if err:
        return err
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        cfg = carregar_config(conn)
        memoria = ps.get_memoria(request)
        rascunho = None
        if memoria:
            rascunho = {
                "tipo": memoria.get("tipo"),
                "params": memoria.get("params"),
                "resultado": memoria.get("calc"),
            }
        cliente = proposta.get("cliente") or {}
        pdf_bytes = gerar_pdf_memoria(
            itens=proposta.get("itens") or [],
            rascunho=rascunho,
            orcamento={
                "numero": proposta.get("numero"),
                "cliente_nome": cliente.get("nome"),
            },
            empresa=cfg,
        )
    numero = proposta.get("numero") or "rascunho"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="memoria_{numero}.pdf"'
        },
    )


@router.post("/novo/continuar")
def continuar_rascunho(request: Request, orcamento_id: int = Form(...)):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
        if not orc:
            ps.flash_err(request, "Orçamento não encontrado.")
            return RedirectResponse("/orcamentos", status_code=303)
        status = (orc.get("status") or "").lower()
        if status not in ("rascunho", ""):
            # gerado/aprovado: só consulta
            ps.carregar_proposta_do_banco(
                request, conn, orcamento_id, readonly=True
            )
            ps.flash_ok(
                request,
                f"Orçamento {orc.get('numero') or orcamento_id} aberto em consulta "
                f"(status: {label_status(status)}). Use Clonar para editar.",
            )
            return _redirect_novo()
        ps.carregar_proposta_do_banco(request, conn, orcamento_id, readonly=False)
        ps.flash_ok(
            request,
            f"Rascunho {orc.get('numero') or orcamento_id} carregado para edição.",
        )
    return _redirect_novo()


@router.post("/{orcamento_id}/consultar")
def consultar(request: Request, orcamento_id: int):
    user, err = _require_user(request, "orcamento.ver")
    if err:
        return err
    with connect() as conn:
        proposta = ps.carregar_proposta_do_banco(
            request, conn, orcamento_id, readonly=True
        )
        if not proposta:
            return HTMLResponse("Orçamento não encontrado.", status_code=404)
        ps.flash_ok(
            request,
            f"Orçamento {proposta.get('numero') or orcamento_id} aberto em modo consulta "
            f"(status: {label_status(proposta.get('status'))}).",
        )
    return _redirect_novo()


@router.post("/{orcamento_id}/clonar")
def clonar(request: Request, orcamento_id: int):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
        if not orc:
            return HTMLResponse("Orçamento não encontrado.", status_code=404)
        proposta = clonar_para_novo(orc)
        # Persiste como rascunho novo para caber itens fora do cookie
        ps.set_readonly(request, False)
        salvar_orcamento(conn, proposta, status=STATUS_RASCUNHO)
        request.session[ps.SESSION_PROPOSTA_ID] = proposta["id"]
        request.session.pop(ps.SESSION_DRAFT, None)
        ps.marcar_suja(request)
        ps.set_modo(request, None)
        ps.flash_ok(
            request,
            f"Clone criado a partir de {orc.get('numero') or orcamento_id}. "
            "Edite e salve como novo orçamento.",
        )
    return _redirect_novo()


@router.get("/{orcamento_id}/memoria", response_class=HTMLResponse)
def memoria_orcamento(request: Request, orcamento_id: int):
    user, err = _require_user(request, "orcamento.ver")
    if err:
        return err
    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
        if not orc:
            return HTMLResponse("Orçamento não encontrado.", status_code=404)
        prop = orcamento_para_proposta(orc)
        linhas, mem_lucro, mem_media = _montar_linhas_memoria(prop, None)
    return render(
        request,
        "orcamento_memoria.html",
        {
            "user": user,
            "orc": orc,
            "status_label": label_status(orc.get("status")),
            "memoria_linhas": linhas,
            "memoria_lucro_total": mem_lucro,
            "memoria_media_margem": mem_media,
            "brl": brl,
            "pct": pct,
            "pode_pdf": usuario_tem_permissao(user, "orcamento.pdf"),
        },
    )


@router.get("/{orcamento_id}/memoria/pdf")
def memoria_pdf_orcamento(request: Request, orcamento_id: int):
    user, err = _require_user(request, "orcamento.pdf")
    if err:
        return err
    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
        cfg = carregar_config(conn)
        if not orc:
            return HTMLResponse("Orçamento não encontrado.", status_code=404)
        prop = orcamento_para_proposta(orc)
        pdf_bytes = gerar_pdf_memoria(
            itens=prop.get("itens") or [],
            rascunho=None,
            orcamento={
                "numero": prop.get("numero"),
                "cliente_nome": (prop.get("cliente") or {}).get("nome"),
            },
            empresa=cfg,
        )
    nome = f"memoria_{prop.get('numero') or orcamento_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )


@router.get("/{orcamento_id}", response_class=HTMLResponse)
def detalhe(request: Request, orcamento_id: int):
    user, err = _require_user(request, "orcamento.ver")
    if err:
        return err

    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        return HTMLResponse("Orçamento não encontrado.", status_code=404)

    status = (orc.get("status") or "").lower()
    return render(
        request,
        "orcamento_detalhe.html",
        {
            "user": user,
            "orc": orc,
            "status_label": label_status(orc.get("status")),
            "brl": brl,
            "pode_aprovar": usuario_tem_permissao(user, "orcamento.aprovar")
            and status in ("gerado", "finalizado"),
            "pode_pdf": usuario_tem_permissao(user, "orcamento.pdf"),
            "pode_consultar": True,
            "pode_clonar": usuario_tem_permissao(user, "orcamento.criar"),
            "pode_editar_rascunho": usuario_tem_permissao(user, "orcamento.criar")
            and status == "rascunho",
            "pode_memoria": True,
        },
    )


@router.post("/{orcamento_id}/aprovar")
def aprovar(request: Request, orcamento_id: int):
    user, err = _require_user(request, "orcamento.aprovar")
    if err:
        return err
    with connect() as conn:
        atualizar_status_orcamento(conn, orcamento_id, STATUS_APROVADO)
    return RedirectResponse(f"/orcamentos/{orcamento_id}", status_code=303)


@router.get("/{orcamento_id}/pdf")
def pdf(request: Request, orcamento_id: int):
    user, err = _require_user(request, "orcamento.pdf")
    if err:
        return err

    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
        cfg = carregar_config(conn)
    if not orc:
        return HTMLResponse("Orçamento não encontrado.", status_code=404)

    prop = orcamento_para_proposta(orc)
    cliente = prop.get("cliente") or {}
    frete_exibicao = prop.get("frete_tipo", "CIF")
    if frete_exibicao == "Taxa" and prop.get("frete_taxa"):
        frete_exibicao = f"Taxa: {prop.get('frete_taxa')}"

    pdf_bytes = gerar_pdf_proposta(
        empresa={
            **cfg,
            "empresa_cnpj": prop.get("empresa_cnpj")
            or cfg.get("empresa_cnpj")
            or "51.832.369/0001-00",
        },
        orcamento={
            "numero": prop.get("numero"),
            "cliente_nome": cliente.get("nome"),
            "cliente_doc": cliente.get("cnpj_cpf"),
            "solicitante": prop.get("solicitante"),
            "validade_proposta": prop.get("validade_proposta"),
            "prazo_pagamento": prop.get("prazo_pagamento"),
            "prazo_entrega": prop.get("prazo_entrega"),
            "frete_tipo": frete_exibicao,
            "impostos": prop.get("impostos"),
            "informacoes_adicionais": prop.get("informacoes_adicionais"),
            "orcamentista_nome": prop.get("orcamentista_nome"),
            "orcamentista_cargo": prop.get("orcamentista_cargo"),
            "orcamentista_telefone": prop.get("orcamentista_telefone"),
            "orcamentista_email": prop.get("orcamentista_email"),
            "valor_total": orc.get("valor_total") or 0,
        },
        itens=prop.get("itens") or [],
        logo_cabecalho=cfg.get("logo_cabecalho") or None,
        logo_rodape=cfg.get("logo_rodape") or None,
    )
    nome = f"{prop.get('numero') or orcamento_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome}"'},
    )
