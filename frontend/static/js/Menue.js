document.addEventListener("DOMContentLoaded", () => {
  const toggle = document.querySelector(".profile-icon");
  const menu = document.querySelector(".dropdown-menu");

  // Dropdown-Menu anzeigen/verbergen, wenn auf das Bild geklickt wird
  toggle.addEventListener("click", (event) => {
      event.stopPropagation(); // Prevent click from propagating to document
      menu.style.display = menu.style.display === "block" ? "none" : "block";
  });

  // Schließt das Menü, wenn man außerhalb des Dropdowns klickt
  document.addEventListener("click", (event) => {
      if (!menu.contains(event.target) && !toggle.contains(event.target)) {
          menu.style.display = "none";
      }
  });

  const languageButton = document.querySelector('[data-dropdown-toggle="language-dropdown-menu"]');
  const languageDropdown = document.getElementById('language-dropdown-menu');

  if (languageButton && languageDropdown) {
      languageButton.addEventListener('click', (event) => {
          event.stopPropagation(); // Prevent click from propagating to document
          const isHidden = languageDropdown.classList.contains('hidden');
          if (isHidden) {
              languageDropdown.classList.remove('hidden');
          } else {
              languageDropdown.classList.add('hidden');
          }
      });

      // Schließt das Dropdown, wenn man außerhalb klickt
      document.addEventListener('click', (event) => {
          if (!languageDropdown.contains(event.target) && !languageButton.contains(event.target)) {
              languageDropdown.classList.add('hidden');
          }
      });
  } else {
      console.error("Language button or dropdown not found");
  }
});