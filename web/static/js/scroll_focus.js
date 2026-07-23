(function () {
  function scrollToEl(el) {
    if (!el) return;
    try {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      el.scrollIntoView(true);
    }
  }

  function onReady() {
    var hash = (location.hash || "").replace("#", "");
    if (hash) {
      scrollToEl(document.getElementById(hash));
    } else {
      // Só foca modais já abertos (ignora js-modal fechado, ex.: Reprovar)
      var modal =
        document.querySelector(".modal-backdrop.is-open") ||
        Array.prototype.find.call(
          document.querySelectorAll(".modal-backdrop"),
          function (el) {
            return (
              !el.classList.contains("js-modal") && !el.hasAttribute("hidden")
            );
          }
        );
      var formItem = document.getElementById("form-item");
      if (modal) scrollToEl(modal);
      else if (formItem) scrollToEl(formItem);
    }

    document.querySelectorAll("details.nf-card").forEach(function (d) {
      d.addEventListener("toggle", function () {
        if (d.open) scrollToEl(d);
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }
})();
