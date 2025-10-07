// Diese Datei erweitert die Listenlogik aus newsFeedCore.js um die Filterfunktionalität

// Funktion zum Ein- und Ausklappen von Filtersektionen
window.toggleFilter = function (name) {
  var section = document.getElementById("filter-" + name);
  var chevron = document.getElementById("chevron-" + name);
  if (!section || !chevron) {
    return;
  }
  var isHidden = section.classList.contains("hidden");
  if (isHidden) {
    section.classList.remove("hidden");
    chevron.style.transform = "rotate(90deg)";
  } else {
    section.classList.add("hidden");
    chevron.style.transform = "rotate(0deg)";
  }
};

document.addEventListener("DOMContentLoaded", function () {
  console.log("news.js: DOMContentLoaded handler started");
  // Prüft, ob newsFeedCore.js geladen wurde und bricht andernfalls mit einer Fehlermeldung ab
  if (!window.NewsFeedCore || typeof window.NewsFeedCore.initNewsFeed !== "function") {
    console.error("news.js: NewsFeedCore fehlt oder initNewsFeed nicht verfügbar");
    return;
  }
  console.log("news.js: NewsFeedCore vorhanden");

  // Referenzen auf alle relevanten Filterelemente erstellen
  var filterForm = document.getElementById("news-filter-form");
  var filterApplyButton = document.getElementById("apply-filter-btn");
  var filterResetButton = document.getElementById("reset-filter-btn");
  var filterSelectAllButton = document.getElementById("select-all-btn");

  // Ermittelt ein Locale-Präfix aus der URL, etwa /de
  function getLocalePrefix() {
    var match = window.location.pathname.match(/^\/([a-z]{2})(?=\/)/i);
    return match ? "/" + match[1] : "";
  }

  // Basis-URL für die News-Seite inklusive Sprachpräfix, etwa /de/news/
  function newsBasePath() {
    return (getLocalePrefix() + "/news/").replace(/\/{2,}/g, "/");
  }

  // Liest Werte aus dem Filterformular und erzeugt einen Query-String
  function buildQueryFromFilters() {
    if (!filterForm) {
      return "";
    }
    var formData = new FormData(filterForm);
    var params = new URLSearchParams();
    for (var pair of formData.entries()) {
      params.append(pair[0], pair[1]);
    }
    return params.toString();
  }

  // Setzt Checkboxen anhand der aktuellen URL-Parameter, etwa bei popstate
  function applyFiltersFromURL(urlParams) {
    if (!filterForm) {
      return;
    }
    var checkboxes = filterForm.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(function (cb) {
      cb.checked = false;
    });

    urlParams.forEach(function (value, key) {
      var selector = 'input[name="' + key + '"][value="' + value + '"]';
      var checkbox = filterForm.querySelector(selector);
      if (checkbox) {
        checkbox.checked = true;
      }
    });
  }

  // Initialisierung der Core-Logik mit Filterfunktionalität
  console.log("news.js: Initialisiere NewsFeedCore");
  window.NewsFeedCore.initNewsFeed({
    containerSelector: "#news-container",
    loadMoreSelector: "#load-more",
    limit: 20,
    initialOffset: 20,
    filterForm: filterForm,
    filterApplyButton: filterApplyButton,
    filterResetButton: filterResetButton,
    filterSelectAllButton: filterSelectAllButton,
    buildQueryFromFilters: buildQueryFromFilters,
    applyFiltersFromURL: applyFiltersFromURL,
    getBasePath: newsBasePath,
    // URL für Detailansicht
    getDetailPageUrl: function (id) {
      return newsBasePath() + id + "/";
    },
    // URL für AJAX-Nachladen der Detailansicht
    getDetailFetchUrl: function (id) {
      return newsBasePath() + id + "/?partial=true";
    },
    // Erzeugt die URLs für die Listenseite und das Nachladen basierend auf dem Query-String
    buildListUrls: function (query) {
      var base = newsBasePath();
      if (query) {
        return {
          pageUrl: base + "?" + query,
          fetchUrl: base + "partial/?" + query,
        };
      }
      return {
        pageUrl: base,
        fetchUrl: base + "partial/",
      };
    },
  });

  console.log("news.js: NewsFeedCore.initNewsFeed abgeschlossen");

  // Entfernt ein "Keine News gefunden"-Banner, wenn der "Mehr laden"-Button geklickt wird
  document.addEventListener("click", function (event) {
    var loadMoreBtn = event.target.closest ? event.target.closest("#load-more") : null;
    if (!loadMoreBtn) {
      return;
    }
    console.log("news.js: load-more Button erkannt");
  });


  // Logik für das Ein- und Ausklappen des Filter-Dropdowns auf Mobile
  const toggle = document.getElementById("filter-button");
  const dropdown = document.getElementById("filter-dropdown");
  const news = document.getElementById("news");

  if (!toggle || !dropdown) {
    console.warn("news.js: Toggle oder Dropdown fehlt", { toggleFound: !!toggle, dropdownFound: !!dropdown });
  }

  if (toggle && dropdown) {
    console.log("news.js: Registriere mobile Filter-Listener");
    toggle.addEventListener("click", (event) => {
      event.stopPropagation();
      const filter_is_Hidden = dropdown.classList.contains("max-md:hidden");
      if (filter_is_Hidden) {
        dropdown.classList.remove("max-md:hidden");
        news.classList.add("hidden")
        console.log("news.js: Mobile Filter geöffnet");
      } else {
        dropdown.classList.add("max-md:hidden");
        news.classList.remove("hidden");
        console.log("news.js: Mobile Filter geschlossen");
      }
    });

    // Schließt das Dropdown, wenn man außerhalb davon klickt
    document.addEventListener("click", (event) => {
      if (!dropdown.contains(event.target) && !toggle.contains(event.target)) {
        dropdown.classList.add("max-md:hidden");
        news.classList.remove("hidden")
        console.log("news.js: Mobile Filter über Outside-Click geschlossen");
      }
    });
  } else {
    console.error("Filter-Button oder Filter-Dropdown nicht gefunden.");
  }
});
