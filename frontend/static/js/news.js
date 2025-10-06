// Diese Datei erweitert die Listenlogik aus newsFeedCore.js um die Filterfunktionalität

document.addEventListener("DOMContentLoaded", function () {
  // Prüft, ob newsFeedCore.js geladen wurde und bricht andernfalls mit einer Fehlermeldung ab
  if (!window.NewsFeedCore || typeof window.NewsFeedCore.initNewsFeed !== "function") {
    console.error("NewsFeedCore ist nicht verfügbar. Bitte stelle sicher, dass newsFeedCore.js geladen ist.");
    return;
  }

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
});
