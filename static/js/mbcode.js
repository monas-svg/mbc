/*
 * Interactions legeres de l'interface MBCODE.
 * Aucune dependance externe : uniquement du JavaScript natif.
 */
document.addEventListener("DOMContentLoaded", function () {
  // Ferme automatiquement les messages flash apres quelques secondes.
  document.querySelectorAll(".mb-message").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity 0.4s ease";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 400);
    }, 6000);
  });

  // Confirmation avant toute action destructrice (boutons avec data-confirm).
  document.querySelectorAll("[data-confirm]").forEach(function (el) {
    el.addEventListener("click", function (event) {
      if (!window.confirm(el.getAttribute("data-confirm"))) {
        event.preventDefault();
      }
    });
  });

  // Impression directe de la page facture.
  document.querySelectorAll("[data-print]").forEach(function (el) {
    el.addEventListener("click", function () { window.print(); });
  });
});
