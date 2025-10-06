// Diese Datei erweitert die Listenlogik aus newsFeedCore.js um das AJAX-basierte Speichern der Nutzerpräferenzen

document.addEventListener("DOMContentLoaded", function () {
  // Prüft, ob newsFeedCore.js geladen wurde und bricht andernfalls mit einer Fehlermeldung ab
  if (!window.NewsFeedCore || typeof window.NewsFeedCore.initNewsFeed !== "function") {
    console.error("NewsFeedCore ist nicht verfügbar. Bitte stelle sicher, dass newsFeedCore.js geladen ist.");
    return;
  }

  // Ermittelt ein Locale-Präfix aus der URL, etwa /de
  function getLocalePrefix() {
    var match = window.location.pathname.match(/^\/([a-z]{2})(?=\/)/i);
    return match ? "/" + match[1] : "";
  }

  // Basis-URL der ForYouPage inklusive Sprachpräfix, etwa /de/foryoupage/
  function forYouBasePath() {
    return (getLocalePrefix() + "/foryoupage/").replace(/\/{2,}/g, "/");
  }

  // Basis-URL für die News-Detailseite inklusive Sprachpräfix, etwa /de/news/
  function newsDetailBasePath() {
    return (getLocalePrefix() + "/news/").replace(/\/{2,}/g, "/");
  }

  // Initialisierung der Core-Logik ohne sichtbare Filter
  var manager = window.NewsFeedCore.initNewsFeed({
    containerSelector: "#news-container",
    loadMoreSelector: "#load-more",
    limit: 20,
    initialOffset: 20,
    // Es gibt keine sichtbaren Filter, diese Funktionen bleiben also leer
    buildQueryFromFilters: function () {
      return "";
    },
    applyFiltersFromURL: function () {
    },
    getBasePath: forYouBasePath,
    // Detailansichten bleiben unter der klassischen News-Route
    getDetailPageUrl: function (id) {
      return newsDetailBasePath() + id + "/";
    },
    getDetailFetchUrl: function (id) {
      return newsDetailBasePath() + id + "/?partial=true";
    },
    // Erzeugt die URLs für die Listenseite und das Nachladen basierend auf dem Query-String
    buildListUrls: function (query) {
      var base = forYouBasePath();
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

  // Abbruch, wenn das Formular nicht existiert
  var preferencesForm = document.getElementById("preferences-form");
  if (!preferencesForm) {
    return;
  }

  // Referenzen auf alle relevanten Formular-Elemente erstellen
  var submitButton = document.getElementById("preferences-submit-btn");
  var feedbackBox = document.getElementById("preferences-feedback");

  // Funktion zur Anzeige von Feedback-Nachrichten
  function updateFeedback(message, isError) {
    if (!feedbackBox) {
      return;
    }
    if (!message) {
      feedbackBox.textContent = "";
      feedbackBox.classList.add("hidden");
      feedbackBox.classList.remove("text-green-600", "text-red-600");
      return;
    }
    feedbackBox.textContent = message;
    feedbackBox.classList.remove("hidden");
    feedbackBox.classList.toggle("text-red-600", Boolean(isError));
    feedbackBox.classList.toggle("text-green-600", !isError);
  }

  // Liest den CSRF-Token aus dem Cookie
  function getCsrfToken() {
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  // Sendet das Formular per fetch, reagiert auf Erfolg und Fehler und synchronisiert anschließend den News-Feed
  preferencesForm.addEventListener("submit", function (event) {
    event.preventDefault();

    // Deaktiviert den Submit-Button, um Mehrfachsendungen zu verhindern
    if (submitButton) {
      submitButton.disabled = true;
    }
    updateFeedback("Speichere Präferenzen...", false);

    var formData = new FormData(preferencesForm);

    // Sendet die Daten per fetch an den Server
    fetch(preferencesForm.action, {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": getCsrfToken(),
      },
    })
      .then(function (response) {
        var contentType = response.headers.get("Content-Type") || "";
        // Gibt ein Promise zurück, damit der nächste then-Block immer ein konsistentes Ergebnis erhält
        if (!response.ok) {
          // Fehlerhafte Antwort vom Server
          return response.json().catch(function () {
            throw new Error("REQUEST_FAILED");
          });
        }
        // Bei JSON-Antworten die Daten weiterreichen, ansonsten nur ein success-Flag
        if (contentType.includes("application/json")) {
          return response.json();
        }
        return { success: true };
      })

      //
      .then(function (data) {
        // Der vorherige then-Block gibt immer ein Objekt zurück, hier entscheiden wir anhand von success
        if (!data || data.success !== true) {
          var errorMessage = "Speichern fehlgeschlagen";
          // Versucht, eine genauere Fehlermeldung aus den Daten zu extrahieren
          if (data && data.errors) {
            var errors = Array.isArray(data.errors)
              ? data.errors
              : Object.values(data.errors).flat();
            if (errors.length) {
              errorMessage = errors.join("; ");
            }
          }
          updateFeedback(errorMessage, true);
          return;
        }
        // Erfolgreiche Antwort vom Server
        updateFeedback(data.message || "Präferenzen gespeichert", false);
        if (manager && typeof manager.reloadList === "function") {
          return manager.reloadList({ resetOffset: true, scrollY: 0 });
        }
        // Fallback: Seite neu laden, wenn kein Reload möglich ist
        window.location.reload();
        return null;
      })

      .catch(function (error) {
        console.error("Fehler beim Speichern der Präferenzen:", error);
        // Weitergabe eines Fehlerzustands via UI und Hard-Reload als letzter Ausweg
        updateFeedback("Speichern fehlgeschlagen, Seite wird neu geladen", true);
        window.location.reload();
      })

      // Unabhängig vom Ergebnis den Submit-Button wieder aktivieren
      .finally(function () {
        if (submitButton) {
          submitButton.disabled = false;
        }
      });
  });
});
