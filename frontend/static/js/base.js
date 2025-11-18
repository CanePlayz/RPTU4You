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

    // Custom Darkmode Toggle mit Sonne/Mond-Icon und LocalStorage
    const darkmodeToggle = document.getElementById('darkmode-toggle');
    const dot = document.getElementById('toggle-dot');
    const sunIcon = document.getElementById('sun-icon');
    const moonIcon = document.getElementById('moon-icon');
    let storedTheme = localStorage.getItem('theme');
    if (!storedTheme) {
        storedTheme = 'dark';
        localStorage.setItem('theme', storedTheme);
    }
    const isDark = storedTheme === 'dark';
    if (isDark) {
        document.documentElement.classList.add('dark');
        darkmodeToggle.checked = true;
        if (dot) dot.style.transform = 'translateX(24px)';
        if (sunIcon) sunIcon.classList.add('hidden');
        if (moonIcon) moonIcon.classList.remove('hidden');
    } else {
        document.documentElement.classList.remove('dark');
        darkmodeToggle.checked = false;
        if (dot) dot.style.transform = 'translateX(0)';
        if (sunIcon) sunIcon.classList.remove('hidden');
        if (moonIcon) moonIcon.classList.add('hidden');
    }
    if (dot) {
        // Disable transition for initial position to avoid visible jump
        dot.style.transition = 'none';
        void dot.offsetWidth; // force reflow
        dot.style.transition = '';
    }
    // Toggle event
    if (darkmodeToggle) {
        darkmodeToggle.addEventListener('change', function () {
            if (this.checked) {
                document.documentElement.classList.add('dark');
                localStorage.setItem('theme', 'dark');
                document.cookie = 'theme=dark;path=/;max-age=' + (60*60*24*365);
                if (dot) dot.style.transform = 'translateX(24px)';
                if (sunIcon) sunIcon.classList.add('hidden');
                if (moonIcon) moonIcon.classList.remove('hidden');
            } else {
                document.documentElement.classList.remove('dark');
                localStorage.setItem('theme', 'light');
                document.cookie = 'theme=light;path=/;max-age=' + (60*60*24*365);
                if (dot) dot.style.transform = 'translateX(0)';
                if (sunIcon) sunIcon.classList.remove('hidden');
                if (moonIcon) moonIcon.classList.add('hidden');
            }
        });
    }
});
