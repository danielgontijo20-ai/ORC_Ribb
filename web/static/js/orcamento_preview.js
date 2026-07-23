(function () {
  function brl(v) {
    if (v == null || isNaN(v)) return "R$ 0,00";
    return (
      "R$ " +
      Number(v)
        .toFixed(2)
        .replace(".", ",")
        .replace(/\B(?=(\d{3})+(?!\d))/g, ".")
    );
  }

  function num(el) {
    if (!el) return null;
    var t = String(el.value || "").trim().replace(",", ".");
    if (!t) return null;
    var n = parseFloat(t);
    return isNaN(n) ? null : n;
  }

  function val(form, name) {
    var el = form.querySelector('[name="' + name + '"]');
    return el ? String(el.value || "").trim() : "";
  }

  function setText(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }

  var catEl = document.getElementById("orc-cat");
  var CAT = {};
  try {
    CAT = catEl ? JSON.parse(catEl.textContent || "{}") : {};
  } catch (e) {
    CAT = {};
  }

  function calcEtiqueta(form) {
    var tipo = val(form, "tipo_faca");
    var materia = val(form, "materia_nome");
    var tubete = val(form, "tubete_nome");
    var caixa = val(form, "caixa_nome");
    var qtdEtq = num(form.querySelector('[name="qtd_etq"]'));
    var qtdTotal = num(form.querySelector('[name="qtd_total"]'));
    var qtdCx = num(form.querySelector('[name="qtd_caixas"]'));
    var perda = num(form.querySelector('[name="perda"]'));
    var lucro = num(form.querySelector('[name="lucro"]'));
    var frete = num(form.querySelector('[name="frete"]'));
    if (perda == null) perda = 0;
    if (lucro == null) lucro = 0;
    else lucro = lucro / 100;
    if (frete == null) frete = 0;

    var faltando = [];
    if (!tipo || tipo === "(selecione)") faltando.push("dimensão");
    if (!materia || materia === "(selecione)") faltando.push("matéria-prima");
    if (!tubete || tubete === "(selecione)") faltando.push("tubete");
    if (qtdEtq == null || qtdEtq <= 0) faltando.push("qtd etiquetas/rolo");
    if (qtdTotal == null || qtdTotal <= 0) faltando.push("qtd total");
    if (qtdCx == null || qtdCx < 0) faltando.push("qtd caixas");

    if (faltando.length) {
      setText("etq-unit", "R$ 0,00");
      setText("etq-total", "R$ 0,00");
      setText("etq-lucro", "R$ 0,00");
      setText("etq-desc", "Descrição gerada: —");
      setText(
        "etq-hint",
        "Preencha/selecione: " + faltando.join(", ") + " — valores atualizam ao completar."
      );
      return;
    }

    var f = (CAT.facas || {})[tipo];
    var m = (CAT.materias || {})[materia];
    var t = (CAT.tubetes || {})[tubete];
    var c = (CAT.caixas || {})[caixa];
    if (!f || !m || !t || !c) {
      setText("etq-hint", "Cadastro incompleto para os itens selecionados.");
      return;
    }

    var area = f.area;
    var m2Rolo = qtdEtq * area;
    var custoMat = m2Rolo * m.custo;
    var custoCxTotal = qtdCx * c.custo;
    var custoCxRolo = custoCxTotal / qtdTotal;
    var custoPerda = (custoMat + t.custo + custoCxRolo) * perda;
    var custoSemFrete = custoMat + t.custo + custoCxRolo + custoPerda;
    var freteRolo = frete / qtdTotal;
    var custoComFrete = custoSemFrete + freteRolo;
    var lucroRolo = lucro * custoSemFrete;
    var lucroTotal = lucroRolo * qtdTotal;
    var precoSem = custoComFrete + lucroRolo;
    var imposto = CAT.imposto_etiqueta || 0.92;
    var precoCom = precoSem / imposto;
    var vendaTotal = precoCom * qtdTotal;

    var qtdFmt = String(Math.trunc(qtdEtq)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    var desc =
      "Etiqueta " +
      (m.nome_orc || materia) +
      " " +
      (f.nome_orc || tipo) +
      " - Rolo com " +
      qtdFmt +
      " - " +
      (t.nome_orc || tubete);

    setText("etq-unit", brl(precoCom));
    setText("etq-total", brl(vendaTotal));
    setText("etq-lucro", brl(lucroTotal));
    setText("etq-desc", "Descrição gerada: " + desc);
    setText("etq-hint", "Valores atualizados. Você pode inserir o item na proposta.");
  }

  function calcSuprimento(form) {
    var desc = val(form, "descricao");
    var difalSel = val(form, "difal").toUpperCase();
    var custo = num(form.querySelector('[name="custo"]'));
    var qtd = num(form.querySelector('[name="quantidade"]'));
    var lucro = num(form.querySelector('[name="lucro"]'));
    var frete = num(form.querySelector('[name="frete"]'));
    if (lucro == null) lucro = 0;
    else lucro = lucro / 100;
    if (frete == null) frete = 0;

    var faltando = [];
    if (!desc) faltando.push("descrição");
    if (custo == null || custo < 0) faltando.push("custo");
    if (qtd == null || qtd <= 0) faltando.push("quantidade");
    if (difalSel !== "SIM" && difalSel !== "NÃO" && difalSel !== "NAO") {
      faltando.push("difal");
    }

    if (faltando.length) {
      setText("sup-unit", "R$ 0,00");
      setText("sup-total", "R$ 0,00");
      setText("sup-lucro", "R$ 0,00");
      setText(
        "sup-hint",
        "Preencha/selecione: " + faltando.join(", ") + " — valores atualizam ao completar."
      );
      return;
    }

    var difal = difalSel === "SIM";
    var freteUnit = frete / qtd;
    var difalUnit = difal ? custo * (CAT.aliquota_difal || 0.073) : 0;
    var custoUnit = custo + freteUnit + difalUnit;
    var lucroUnit = lucro * custo;
    var lucroTotal = lucroUnit * qtd;
    var precoSem = custoUnit + lucroUnit;
    var imposto = CAT.imposto_suprimentos || 0.91;
    var precoCom = precoSem / imposto;
    var vendaTotal = precoCom * qtd;

    setText("sup-unit", brl(precoCom));
    setText("sup-total", brl(vendaTotal));
    setText("sup-lucro", brl(lucroTotal));
    setText("sup-hint", "Valores atualizados. Você pode inserir o item na proposta.");
  }

  function bindForm(form, calcFn) {
    if (!form) return;
    var handler = function () {
      calcFn(form);
    };
    form.addEventListener("input", handler);
    form.addEventListener("change", handler);
    handler();
  }

  var sel = document.getElementById("sup-catalogo");
  if (sel) {
    sel.addEventListener("change", function () {
      var opt = sel.options[sel.selectedIndex];
      var desc = document.getElementById("sup-desc");
      var custo = document.getElementById("sup-custo");
      if (!opt || !opt.value) return;
      if (desc && opt.dataset.desc) desc.value = opt.dataset.desc;
      if (custo && opt.dataset.custo) custo.value = opt.dataset.custo;
      var form = document.getElementById("form-suprimento");
      if (form) calcSuprimento(form);
    });
  }

  bindForm(document.getElementById("form-etiqueta"), calcEtiqueta);
  bindForm(document.getElementById("form-suprimento"), calcSuprimento);
})();
