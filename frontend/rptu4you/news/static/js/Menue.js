document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".profile-icon");
  const menu = document.querySelector(".dropdown-menu");

  // Dropdown-Menu anzeigen/verbergen, wenn auf das Bild geklickt wird
  toggle.addEventListener("click", () => {
      menu.style.display = menu.style.display === "block" ? "none" : "block";
  });

  // Schließt das Menü, wenn man außerhalb des Dropdowns klickt
  document.addEventListener("click", (event) => {
      if (!event.target.closest(".dropdown-container")) {
          menu.style.display = "none";
      }
  });
});