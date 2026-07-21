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
    label_status,
    obter_orcamento,
    orcamento_para_proposta,
    salvar_orcamento,
)
from src.services.pdf_memoria import gerar_pdf_memoria
from src.services.pdf_proposta import gerar_pdf_proposta
from src.services.usuarios import usuario_tem_permissao
from src.ui.formatters import brl, pct
from web.deps import get_current_user
from web import proposta_session as ps
from web.templating import render

router = APIRouter(prefix="/orcamentos")


def _require_user(request: Request, perm: str):
    user = get_current_user(request)
    if not user:
        return None, RedirectResponse("/login", status_code=303)
    if not usuario_tem_permissao(user, perm):
        return None, HTMLResponse("Sem permissão.", status_code=403)
    return user, None


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
    if dialog == "memoria":
        memoria_linhas = _montar_linhas_memoria(proposta, memoria)

    frete_exibicao = proposta.get("frete_tipo", "CIF")
    if frete_exibicao == "Taxa" and proposta.get("frete_taxa"):
        frete_exibicao = f"Taxa: {proposta.get('frete_taxa')}"

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
        "frete_exibicao": frete_exibicao,
        "form_vals": form_vals or {},
        "preview_item": None,
        **cats,
        "defaults": {
            "unidade_etiqueta": cfg.get("unidade_etiqueta", "Rol"),
            "unidade_suprimentos": cfg.get("unidade_suprimentos", "UN"),
            "perda": get_float(cfg, "perda_padrao", 0.0),
            "lucro_etiqueta": get_float(cfg, "lucro_etiqueta_padrao", 0.30),
            "lucro_suprimentos": get_float(cfg, "lucro_suprimentos_padrao", 0.20),
            "frete": get_float(cfg, "frete_padrao", 0.0),
            "difal": (cfg.get("difal_padrao") or "SIM").upper(),
        },
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
    }


def _montar_linhas_memoria(proposta: dict, rascunho: dict | None) -> list[dict]:
    linhas = []
    for i, it in enumerate(proposta.get("itens") or [], start=1):
        calc = it.get("calculo") or {}
        params = it.get("parametros") or {}
        linhas.append(
            {
                "titulo": f"Item {i:02d} — {it.get('descricao') or ''}",
                "params": params,
                "calc": calc,
            }
        )
    if rascunho and rascunho.get("calc"):
        linhas.append(
            {
                "titulo": "Rascunho (formulário atual)",
                "params": rascunho.get("params") or {},
                "calc": rascunho.get("calc") or {},
            }
        )
    return linhas


def _redirect_novo(query: str = "") -> RedirectResponse:
    url = "/orcamentos/novo"
    if query:
        url = f"{url}?{query}"
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
            "pode_aprovar": usuario_tem_permissao(user, "orcamento.aprovar"),
            "pode_pdf": usuario_tem_permissao(user, "orcamento.pdf"),
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
    if modo in ("etiqueta", "suprimentos"):
        ps.set_modo(request, modo)
        # formulário de inserção sempre limpo ao abrir (só nativos)
        request.session.pop("web_form_vals", None)
    elif modo == "fechar":
        ps.set_modo(request, None)
    return _redirect_novo()


@router.post("/novo/dialog")
def set_dialog(request: Request, dialog: str = Form(...)):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    if dialog in ("cliente", "cliente_avulso", "condicoes", "memoria", "fechar"):
        if dialog == "fechar":
            ps.set_dialog(request, None)
            ps.set_memoria(request, None)
        elif dialog == "memoria":
            ps.set_memoria(request, None)
            ps.set_dialog(request, "memoria")
        else:
            ps.set_dialog(request, dialog)
    return _redirect_novo()


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
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        proposta["cliente"] = None
        ps.set_proposta(request, proposta)
        ps.marcar_suja(request)
        ps.flash_ok(request, "Cliente removido do orçamento.")
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
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        proposta.update(
            {
                "solicitante": solicitante.strip(),
                "validade_proposta": validade_proposta.strip(),
                "prazo_pagamento": prazo_pagamento.strip(),
                "prazo_entrega": prazo_entrega.strip(),
                "frete_tipo": frete_tipo.strip() or "CIF",
                "frete_taxa": frete_taxa.strip(),
                "impostos": impostos.strip(),
                "informacoes_adicionais": informacoes_adicionais.strip(),
                "orcamentista_nome": orcamentista_nome.strip(),
                "orcamentista_cargo": orcamentista_cargo.strip(),
                "orcamentista_telefone": orcamentista_telefone.strip(),
                "orcamentista_email": orcamentista_email.strip(),
            }
        )
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
    tipo_faca = str(form.get("tipo_faca") or "")
    materia_nome = str(form.get("materia_nome") or "")
    tubete_nome = str(form.get("tubete_nome") or "")
    caixa_nome = str(form.get("caixa_nome") or "")
    unidade = str(form.get("unidade") or "Rol")
    qtd_etq = ps.parse_float(form.get("qtd_etq"))
    qtd_total = ps.parse_float(form.get("qtd_total"))
    qtd_caixas = ps.parse_float(form.get("qtd_caixas"))
    perda = ps.parse_float(form.get("perda"))
    lucro = ps.parse_float(form.get("lucro"))
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
            rascunho_mem = {
                "tipo": "etiqueta",
                "params": params,
                "calc": resultado.to_dict(),
            }
            ps.set_memoria(request, rascunho_mem)
            proposta = ps.get_proposta(request, conn)
            ctx = _ctx_novo(request, conn, user, form_vals=form_vals)
            ctx["memoria_linhas"] = _montar_linhas_memoria(proposta, rascunho_mem)
            ctx["preview_item"] = {
                "descricao": descricao,
                "unitario": resultado.preco_com_imposto,
                "total": resultado.valor_venda_total,
                "lucro": resultado.lucro_total,
            }
            return render(request, "orcamento_novo.html", ctx)

        proposta = ps.get_proposta(request, conn)
        if not proposta.get("cliente"):
            ps.flash_err(request, "Selecione um cliente antes de inserir o item.")
            ps.set_modo(request, "etiqueta")
            ctx = _ctx_novo(request, conn, user, form_vals=form_vals)
            ctx["preview_item"] = {
                "descricao": descricao,
                "unitario": resultado.preco_com_imposto,
                "total": resultado.valor_venda_total,
                "lucro": resultado.lucro_total,
            }
            return render(request, "orcamento_novo.html", ctx)

        _garantir_numero(conn, proposta)
        proposta["itens"].append(
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
                    "perda": perda,
                    "lucro": lucro,
                },
            }
        )
        ps.persistir(request, conn, proposta, status=STATUS_RASCUNHO)
        ps.marcar_suja(request)
        ps.set_modo(request, None)
        ps.set_dialog(request, None)
        ps.set_memoria(request, None)
        ps.flash_ok(
            request,
            "Item inserido com sucesso. Formulário limpo para o próximo item.",
        )
    return _redirect_novo()


@router.post("/novo/suprimento")
async def inserir_suprimento(request: Request):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err

    form = await request.form()
    acao = str(form.get("acao") or "inserir")
    descricao_in = str(form.get("descricao") or "").strip()
    unidade = str(form.get("unidade") or "UN")
    difal_sel = str(form.get("difal") or "").upper()
    custo = ps.parse_float(form.get("custo"))
    quantidade = ps.parse_float(form.get("quantidade"))
    lucro = ps.parse_float(form.get("lucro"))
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
            ctx = _ctx_novo(request, conn, user, form_vals=form_vals)
            ctx["preview_item"] = {
                "descricao": descricao,
                "unitario": resultado.preco_com_imposto,
                "total": resultado.valor_venda_total,
                "lucro": resultado.lucro_total,
            }
            return render(request, "orcamento_novo.html", ctx)

        proposta = ps.get_proposta(request, conn)
        if not proposta.get("cliente"):
            ps.flash_err(request, "Selecione um cliente antes de inserir o item.")
            ps.set_modo(request, "suprimentos")
            ctx = _ctx_novo(request, conn, user, form_vals=form_vals)
            return render(request, "orcamento_novo.html", ctx)

        _garantir_numero(conn, proposta)
        proposta["itens"].append(
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
                },
            }
        )
        ps.persistir(request, conn, proposta, status=STATUS_RASCUNHO)
        ps.marcar_suja(request)
        ps.set_modo(request, None)
        ps.set_dialog(request, None)
        ps.set_memoria(request, None)
        ps.flash_ok(
            request,
            "Item inserido com sucesso. Formulário limpo para o próximo item.",
        )
    return _redirect_novo()


@router.post("/novo/item/remover")
def remover_item(request: Request, indice: int = Form(...)):
    user, err = _require_user(request, "orcamento.criar")
    if err:
        return err
    with connect() as conn:
        proposta = ps.get_proposta(request, conn)
        itens = proposta.get("itens") or []
        if 1 <= indice <= len(itens):
            itens.pop(indice - 1)
            proposta["itens"] = itens
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
    if not ps.proposta_esta_salva(request):
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
            empresa=cfg,
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
        proposta = ps.carregar_proposta_do_banco(request, conn, orcamento_id)
        if not proposta:
            ps.flash_err(request, "Orçamento não encontrado.")
            return RedirectResponse("/orcamentos", status_code=303)
        ps.flash_ok(
            request,
            f"Orçamento {proposta.get('numero') or orcamento_id} carregado para edição.",
        )
    return _redirect_novo()


@router.get("/{orcamento_id}", response_class=HTMLResponse)
def detalhe(request: Request, orcamento_id: int):
    user, err = _require_user(request, "orcamento.ver")
    if err:
        return err

    with connect() as conn:
        orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        return HTMLResponse("Orçamento não encontrado.", status_code=404)

    return render(
        request,
        "orcamento_detalhe.html",
        {
            "user": user,
            "orc": orc,
            "status_label": label_status(orc.get("status")),
            "pode_aprovar": usuario_tem_permissao(user, "orcamento.aprovar")
            and (orc.get("status") or "").lower() in ("gerado", "finalizado"),
            "pode_pdf": usuario_tem_permissao(user, "orcamento.pdf"),
            "pode_editar": usuario_tem_permissao(user, "orcamento.criar")
            and (orc.get("status") or "").lower()
            in ("rascunho", "gerado", "finalizado"),
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
        empresa=cfg,
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
