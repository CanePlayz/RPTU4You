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

    //-----------------------
    // Darkmode-Einstellungen
    //-----------------------

    const darkmodeToggle = document.getElementById('darkmode-toggle');
    // Hilfsfunktion: Cookie setzen
    function setCookie(name, value, days) {
        let expires = "";
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days*24*60*60*1000));
            expires = "; expires=" + date.toUTCString();
        }
        document.cookie = name + "=" + value + expires + "; path=/";
    }
    // Hilfsfunktion: Cookie lesen
    function getCookie(name) {
        const value = "; " + document.cookie;
        const parts = value.split("; " + name + "=");
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }
    // Darkmode anwenden und Button anpassen
    function applyDarkmode(isDark) {
        if (isDark) {
            document.documentElement.classList.add('dark');
            darkmodeToggle.textContent = "Light";
        } else {
            document.documentElement.classList.remove('dark');
            darkmodeToggle.textContent = "Dark";
        }
    }
    // Beim Laden prüfen, ob Darkmode-Cookie gesetzt ist
    const darkmodeCookie = getCookie('darkmode');
    if (darkmodeCookie === 'true') {
        applyDarkmode(true);
    } else {
        applyDarkmode(false);
    }
    // Button-Event
    if (darkmodeToggle) {
        darkmodeToggle.addEventListener('click', () => {
            const isDark = !document.documentElement.classList.contains('dark');
            applyDarkmode(isDark);
            setCookie('darkmode', isDark ? 'true' : 'false', 365);
        });
    }
});