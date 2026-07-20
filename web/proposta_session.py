"""Estado da proposta na sessão web (equivalente ao session_state do Streamlit).

Após o primeiro save (cliente/itens), só o id fica na sessão — o restante
vem do SQLite, evitando estourar o cookie assinado do Starlette.
"""

from __future__ import annotations

from typing import Any

from fastapi import Request

from src.services.configuracoes import carregar_config
from src.services.orcamentos import (
    STATUS_GERADO,
    STATUS_RASCUNHO,
    orcamento_para_proposta,
    obter_orcamento,
    salvar_orcamento,
)


SESSION_PROPOSTA_ID = "web_proposta_id"
SESSION_DRAFT = "web_proposta_draft"
SESSION_MODO = "web_modo_form"
SESSION_SALVA = "web_proposta_salva"
SESSION_FLASH_OK = "web_flash_ok"
SESSION_FLASH_ERR = "web_flash_err"
SESSION_DIALOG = "web_dialog"
SESSION_MEMORIA = "web_memoria"
SESSION_READONLY = "web_proposta_readonly"
SESSION_FORM_VALS = "web_form_vals"
SESSION_EDIT_INDEX = "web_edit_index"


def nova_proposta(cfg: dict[str, str]) -> dict:
    return {
        "id": None,
        "numero": None,
        "cliente": None,
        "solicitante": "",
        "itens": [],
        "validade_proposta": cfg.get("validade_proposta", "15 dias"),
        "prazo_pagamento": cfg.get("prazo_pagamento", "21 dias"),
        "prazo_entrega": cfg.get("prazo_entrega", "5 dias"),
        "frete_tipo": cfg.get("frete_tipo", "CIF"),
        "frete_taxa": "",
        "impostos": cfg.get("impostos", "Inclusos"),
        "informacoes_adicionais": cfg.get(
            "informacoes_adicionais",
            "As quantidades podem sofrer alterações de 10% para mais ou para menos",
        ),
        "orcamentista_nome": cfg.get("orcamentista_nome", ""),
        "orcamentista_cargo": cfg.get("orcamentista_cargo", ""),
        "orcamentista_telefone": cfg.get("orcamentista_telefone", ""),
        "orcamentista_email": cfg.get("orcamentista_email", ""),
        "empresa_cnpj": cfg.get("empresa_cnpj") or "51.832.369/0001-00",
        "status": None,
    }


def _draft_leve(proposta: dict) -> dict:
    """Cópia sem itens/cálculos — cabe no cookie enquanto não há id no banco."""
    return {
        "id": None,
        "numero": None,
        "cliente": proposta.get("cliente"),
        "solicitante": proposta.get("solicitante") or "",
        "itens": [],
        "validade_proposta": proposta.get("validade_proposta"),
        "prazo_pagamento": proposta.get("prazo_pagamento"),
        "prazo_entrega": proposta.get("prazo_entrega"),
        "frete_tipo": proposta.get("frete_tipo"),
        "frete_taxa": proposta.get("frete_taxa") or "",
        "impostos": proposta.get("impostos"),
        "informacoes_adicionais": proposta.get("informacoes_adicionais"),
        "orcamentista_nome": proposta.get("orcamentista_nome") or "",
        "orcamentista_cargo": proposta.get("orcamentista_cargo") or "",
        "orcamentista_telefone": proposta.get("orcamentista_telefone") or "",
        "orcamentista_email": proposta.get("orcamentista_email") or "",
        "empresa_cnpj": proposta.get("empresa_cnpj") or "",
        "status": None,
    }


def get_proposta(request: Request, conn) -> dict:
    pid = request.session.get(SESSION_PROPOSTA_ID)
    if pid:
        orc = obter_orcamento(conn, int(pid))
        if orc:
            proposta = orcamento_para_proposta(orc)
            if not (proposta.get("empresa_cnpj") or "").strip():
                cfg = carregar_config(conn)
                proposta["empresa_cnpj"] = cfg.get("empresa_cnpj") or "51.832.369/0001-00"
            return proposta
        request.session.pop(SESSION_PROPOSTA_ID, None)

    draft = request.session.get(SESSION_DRAFT)
    if isinstance(draft, dict):
        if not (draft.get("empresa_cnpj") or "").strip():
            cfg = carregar_config(conn)
            draft["empresa_cnpj"] = cfg.get("empresa_cnpj") or "51.832.369/0001-00"
            request.session[SESSION_DRAFT] = draft
        return draft

    cfg = carregar_config(conn)
    proposta = nova_proposta(cfg)
    request.session[SESSION_DRAFT] = _draft_leve(proposta)
    return proposta


def persistir(request: Request, conn, proposta: dict, *, status: str | None = None) -> dict:
    """Grava no banco e passa a referenciar só pelo id na sessão."""
    if is_readonly(request):
        raise PermissionError("Orçamento em modo consulta — edição bloqueada.")
    st = status
    if st is None:
        st = proposta.get("status") or STATUS_RASCUNHO
        if st == STATUS_GERADO and not request.session.get(SESSION_SALVA):
            if proposta.get("id"):
                atual = obter_orcamento(conn, int(proposta["id"]))
                if atual and (atual.get("status") or "").lower() in (
                    STATUS_GERADO,
                    "finalizado",
                ):
                    st = STATUS_RASCUNHO
    salvar_orcamento(conn, proposta, status=st)
    proposta["status"] = st
    request.session[SESSION_PROPOSTA_ID] = proposta["id"]
    request.session.pop(SESSION_DRAFT, None)
    return proposta


def set_proposta(request: Request, proposta: dict) -> None:
    """Atualiza sessão: id no banco ou draft leve (sem itens)."""
    if proposta.get("id"):
        request.session[SESSION_PROPOSTA_ID] = proposta["id"]
        request.session.pop(SESSION_DRAFT, None)
    else:
        request.session.pop(SESSION_PROPOSTA_ID, None)
        request.session[SESSION_DRAFT] = _draft_leve(proposta)


def reiniciar_proposta(request: Request, conn) -> dict:
    cfg = carregar_config(conn)
    proposta = nova_proposta(cfg)
    request.session.pop(SESSION_PROPOSTA_ID, None)
    request.session[SESSION_DRAFT] = _draft_leve(proposta)
    request.session[SESSION_MODO] = None
    request.session[SESSION_SALVA] = False
    request.session[SESSION_DIALOG] = None
    request.session[SESSION_MEMORIA] = None
    request.session[SESSION_READONLY] = False
    request.session.pop(SESSION_FORM_VALS, None)
    request.session.pop(SESSION_EDIT_INDEX, None)
    return proposta


def set_readonly(request: Request, readonly: bool) -> None:
    request.session[SESSION_READONLY] = bool(readonly)


def is_readonly(request: Request) -> bool:
    return bool(request.session.get(SESSION_READONLY))


def carregar_proposta_do_banco(
    request: Request,
    conn,
    orcamento_id: int,
    *,
    readonly: bool = False,
) -> dict | None:
    orc = obter_orcamento(conn, orcamento_id)
    if not orc:
        return None
    proposta = orcamento_para_proposta(orc)
    request.session[SESSION_PROPOSTA_ID] = proposta["id"]
    request.session.pop(SESSION_DRAFT, None)
    status = (proposta.get("status") or "").lower()
    request.session[SESSION_SALVA] = status in (STATUS_GERADO, "finalizado", "aprovado")
    request.session[SESSION_MODO] = None
    request.session[SESSION_READONLY] = bool(readonly)
    return proposta


def marcar_suja(request: Request) -> None:
    request.session[SESSION_SALVA] = False


def marcar_salva(request: Request) -> None:
    request.session[SESSION_SALVA] = True


def proposta_esta_salva(request: Request) -> bool:
    return bool(request.session.get(SESSION_SALVA))


def get_modo(request: Request) -> str | None:
    modo = request.session.get(SESSION_MODO)
    return modo if modo in ("etiqueta", "suprimentos") else None


def set_modo(request: Request, modo: str | None) -> None:
    request.session[SESSION_MODO] = modo


def flash_ok(request: Request, msg: str) -> None:
    request.session[SESSION_FLASH_OK] = msg


def flash_err(request: Request, msg: str) -> None:
    request.session[SESSION_FLASH_ERR] = msg


def consumir_flash(request: Request) -> tuple[str | None, str | None]:
    ok = request.session.pop(SESSION_FLASH_OK, None)
    err = request.session.pop(SESSION_FLASH_ERR, None)
    return ok, err


def get_dialog(request: Request) -> str | None:
    return request.session.get(SESSION_DIALOG)


def set_dialog(request: Request, name: str | None) -> None:
    request.session[SESSION_DIALOG] = name


def get_memoria(request: Request) -> dict | None:
    return request.session.get(SESSION_MEMORIA)


def set_memoria(request: Request, data: dict | None) -> None:
    request.session[SESSION_MEMORIA] = data


def get_form_vals(request: Request) -> dict:
    vals = request.session.get(SESSION_FORM_VALS)
    return dict(vals) if isinstance(vals, dict) else {}


def set_form_vals(request: Request, vals: dict | None) -> None:
    if vals:
        request.session[SESSION_FORM_VALS] = dict(vals)
    else:
        request.session.pop(SESSION_FORM_VALS, None)


def clear_form_vals(request: Request) -> None:
    request.session.pop(SESSION_FORM_VALS, None)


def get_edit_index(request: Request) -> int | None:
    raw = request.session.get(SESSION_EDIT_INDEX)
    try:
        idx = int(raw)
    except (TypeError, ValueError):
        return None
    return idx if idx >= 0 else None


def set_edit_index(request: Request, index: int | None) -> None:
    if index is None:
        request.session.pop(SESSION_EDIT_INDEX, None)
    else:
        request.session[SESSION_EDIT_INDEX] = int(index)


def totais(proposta: dict) -> tuple[float, float, float]:
    itens = proposta.get("itens") or []
    valor = sum(float(i.get("valor_venda_total") or 0) for i in itens)
    lucro = sum(float(i.get("lucro_total") or 0) for i in itens)
    frete = sum(float(i.get("frete_item") or 0) for i in itens)
    return valor, lucro, frete


def media_lucro_pct(itens: list[dict]) -> float:
    soma_peso = 0.0
    soma_pond = 0.0
    for it in itens or []:
        valor = float(it.get("valor_venda_total") or 0)
        if valor <= 0:
            continue
        params = it.get("parametros") or {}
        if params.get("lucro") is not None:
            try:
                pct = float(params["lucro"]) * 100.0
            except (TypeError, ValueError):
                lucro = float(it.get("lucro_total") or 0)
                pct = (lucro / valor) * 100.0
        else:
            lucro = float(it.get("lucro_total") or 0)
            pct = (lucro / valor) * 100.0
        soma_pond += pct * valor
        soma_peso += valor
    if soma_peso <= 0:
        return 0.0
    return soma_pond / soma_peso


def parse_float(texto: Any) -> float | None:
    if texto is None:
        return None
    t = str(texto).strip()
    if not t:
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
