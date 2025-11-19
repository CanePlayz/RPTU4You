// Diese Datei erweitert die Listenlogik aus newsFeedCore.js um das AJAX-basierte Speichern der Nutzerpräferenzen

// Funktion zum Ein- und Ausklappen von Filtersektionen (analog zur News-Seite)
window.toggleFilter = function (name) {
  var section = document.getElementById("filter-" + name);
  var chevron = document.getElementById("chevron-" + name);
  var trigger = document.querySelector('[data-filter-target="' + name + '"]');
  if (!section) {
    return;
  }
  var isHidden = section.classList.contains("hidden");
  section.classList.toggle("hidden", !isHidden);
  section.setAttribute("aria-hidden", isHidden ? "false" : "true");
  if (chevron) {
    chevron.classList.toggle("rotate-90", isHidden);
  }
  if (trigger) {
    trigger.setAttribute("aria-expanded", isHidden ? "true" : "false");
  }
};

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

  // Basis-URL der ForYouPage inklusive Sprachpräfix, etwa /de/for-you/
  function forYouBasePath() {
    return (getLocalePrefix() + "/for-you/").replace(/\/{2,}/g, "/");
  }

  // Basis-URL für die News-Detailseite inklusive Sprachpräfix, etwa /de/news/
  function newsDetailBasePath() {
    return (getLocalePrefix() + "/news/").replace(/\/{2,}/g, "/");
  }

  // Initialisierung der Core-Logik ohne sichtbare Filter
  var manager = window.NewsFeedCore.initNewsFeed({
    containerSelector: "#news-container",
    scrollContainerSelector: "#news",
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

  // Logik für das Ein- und Ausklappen des Filter-Dropdowns auf Mobile
  const toggle = document.getElementById("4youfilter-button");
  const dropdown = document.getElementById("4youfilter");
  const overlay = document.getElementById("foryou-filter-overlay");

  if (dropdown) {
    dropdown.setAttribute("aria-hidden", dropdown.classList.contains("max-md:hidden") ? "true" : "false");
  }

  if (!toggle || !dropdown) {
    console.warn("foryoupage.js: Toggle oder Dropdown fehlt", { toggleFound: !!toggle, dropdownFound: !!dropdown });
  }

  function openFilter() {
    dropdown.classList.remove("max-md:hidden");
    dropdown.setAttribute("aria-hidden", "false");
    if (overlay) {
      overlay.classList.remove("hidden");
    }
    document.body.classList.add("overflow-hidden");
    toggle.setAttribute("aria-expanded", "true");
  }

  function closeFilter() {
    dropdown.classList.add("max-md:hidden");
    dropdown.setAttribute("aria-hidden", "true");
    if (overlay) {
      overlay.classList.add("hidden");
    }
    document.body.classList.remove("overflow-hidden");
    toggle.setAttribute("aria-expanded", "false");
  }

  if (toggle && dropdown) {
    toggle.addEventListener("click", function (event) {
      event.stopPropagation();
      var filterIsHidden = dropdown.classList.contains("max-md:hidden");
      if (filterIsHidden) {
        openFilter();
      } else {
        closeFilter();
      }
    });

    document.addEventListener("click", function (event) {
      if (!dropdown.contains(event.target) && !toggle.contains(event.target)) {
        closeFilter();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeFilter();
      }
    });

    if (overlay) {
      overlay.addEventListener("click", function () {
        closeFilter();
      });
    }
  } else {
    console.error("Filter-Button oder Filter-Dropdown nicht gefunden.");
  }

  // Abbruch, wenn das Formular nicht existiert (z. B. anonyme Nutzer)
  var preferencesForm = document.getElementById("preferences-form");
  if (!preferencesForm) {
    return;
  }

  // Referenzen auf alle relevanten Formular-Elemente erstellen
  var submitButton = document.getElementById("preferences-submit-btn");
  var resetButton = document.getElementById("preferences-reset-btn");
  var feedbackBox = document.getElementById("preferences-feedback");
  var feedbackMessageEl = feedbackBox ? feedbackBox.querySelector(".alert-banner__message") : null;
  var feedbackDotEl = feedbackBox ? feedbackBox.querySelector(".alert-banner__dot") : null;
  var ALERT_VARIANTS = ["success", "error", "info", "warning"];
  var feedbackSpaceReserved = feedbackBox ? !feedbackBox.hasAttribute("hidden") : false;
  var lastFeedbackHeight = 0;

  var preferencesEndpoint = (function deriveEndpoint() {
    if (!preferencesForm) {
      return "";
    }
    var raw = preferencesForm.getAttribute("action") || "";
    if (!raw) {
      var fallback = (window.location.origin || "") + (getLocalePrefix() + "/preferences/").replace(/\/{2,}/g, "/");
      return fallback;
    }
    var anchor = document.createElement("a");
    anchor.href = raw;
    return anchor.href;
  })();

  function resolveVariant(status) {
    if (typeof status === "string" && ALERT_VARIANTS.includes(status)) {
      return status;
    }
    if (status === true) {
      return "error";
    }
    if (status === false) {
      return "success";
    }
    return "info";
  }

  function applyVariantClasses(variant) {
    if (!feedbackBox) {
      return;
    }
    ALERT_VARIANTS.forEach(function (state) {
      feedbackBox.classList.remove("alert-banner--" + state);
      if (feedbackDotEl) {
        feedbackDotEl.classList.remove("alert-dot--" + state);
      }
    });
    feedbackBox.classList.add("alert-banner--" + variant);
    if (feedbackDotEl) {
      feedbackDotEl.classList.add("alert-dot--" + variant);
    }
  }

  // Funktion zur Anzeige von Feedback-Nachrichten
  function updateFeedback(message, status) {
    if (!feedbackBox) {
      return;
    }
    if (!message) {
      if (feedbackMessageEl) {
        feedbackMessageEl.textContent = "";
      } else {
        feedbackBox.textContent = "";
      }
      if (!feedbackSpaceReserved) {
        feedbackBox.setAttribute("hidden", "hidden");
      } else {
        feedbackBox.setAttribute("aria-hidden", "true");
        feedbackBox.style.visibility = "hidden";
        if (lastFeedbackHeight) {
          feedbackBox.style.minHeight = lastFeedbackHeight + "px";
        }
      }
      return;
    }

    feedbackBox.removeAttribute("hidden");
    feedbackBox.removeAttribute("aria-hidden");
    feedbackBox.style.visibility = "visible";
    feedbackBox.style.minHeight = "";
    feedbackSpaceReserved = true;
    if (feedbackMessageEl) {
      feedbackMessageEl.textContent = message;
    } else {
      feedbackBox.textContent = message;
    }
    applyVariantClasses(resolveVariant(status));
    lastFeedbackHeight = feedbackBox.offsetHeight;
  }

  // Liest den CSRF-Token aus dem Cookie
  function getCsrfToken() {
    var match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : "";
  }

  // Setzt sämtliche Präferenz-Checkboxen zurück, damit der UI-Status nach einem Server-Reset passt
  function clearPreferenceSelections() {
    if (!preferencesForm) {
      return;
    }
    var checkboxes = preferencesForm.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(function (checkbox) {
      if (checkbox.name === "csrfmiddlewaretoken") {
        return;
      }
      checkbox.checked = false;
      checkbox.removeAttribute("checked");
    });
  }

  function readCheckedValues(section) {
    var nodes = section ? section.querySelectorAll('input[type="checkbox"]:checked') : [];
    return Array.prototype.map.call(nodes, function (checkbox) {
      return checkbox.value || checkbox.id || checkbox.name;
    });
  }

  // Synchronisiert den Ein-/Ausklappzustand einer Sektion anhand der aktuell gewählten Werte
  function syncFilterSection(name) {
    var section = document.getElementById("filter-" + name);
    if (!section) {
      return;
    }
    var chevron = document.getElementById("chevron-" + name);
    var trigger = document.querySelector('[data-filter-target="' + name + '"]');
    var checkedValues = readCheckedValues(section);
    var anyChecked = checkedValues.length > 0;
    section.classList.toggle("hidden", !anyChecked);
    section.setAttribute("aria-hidden", anyChecked ? "false" : "true");
    if (chevron) {
      chevron.classList.toggle("rotate-90", anyChecked);
    }
    if (trigger) {
      trigger.setAttribute("aria-expanded", anyChecked ? "true" : "false");
    }
  }

  // Synchronisiert alle relevanten Sektionen nach Änderungen
  function syncAllFilterSections() {
    ["standorte", "kategorien", "zielgruppen", "quellen"].forEach(syncFilterSection);
  }

  // Sendet das Formular per fetch, reagiert auf Erfolg und Fehler und synchronisiert anschließend den News-Feed
  preferencesForm.addEventListener("submit", function (event) {
    event.preventDefault();

    // Deaktiviert den Submit-Button, um Mehrfachsendungen zu verhindern
    if (submitButton) {
      submitButton.disabled = true;
    }
    updateFeedback("", null);

    var formData = new FormData(preferencesForm);

    // Sendet die Daten per fetch an den Server
    fetch(preferencesEndpoint, {
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
        // Aktualisiere den Ein-/Ausklappzustand basierend auf den aktuellen Auswahlwerten
        syncAllFilterSections();
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

  if (resetButton && preferencesForm) {
    resetButton.addEventListener("click", function (event) {
      // Eigene Behandlung, damit das Formular nicht zusätzlich den Submit-Handler auslöst
      event.preventDefault();
      event.stopPropagation();
      if (resetButton.disabled) {
        return;
      }
      resetButton.disabled = true;
      updateFeedback("", null);
      var formData = new FormData(preferencesForm);
      formData.set("action", "reset");

      fetch(preferencesEndpoint, {
        method: "POST",
        body: formData,
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": getCsrfToken(),
        },
      })
        .then(function (response) {
          if (!response.ok) return response.json().catch(function () { throw new Error("REQUEST_FAILED"); });
          return response.json();
        })
        .then(function (data) {
          if (!data || data.success !== true) {
            updateFeedback("Zurücksetzen fehlgeschlagen", true);
            return;
          }
          updateFeedback(data.message || "Präferenzen zurückgesetzt", false);
          // Formular zurücksetzen und News-Feed neu laden
          clearPreferenceSelections();
          syncAllFilterSections();
          if (manager && typeof manager.reloadList === "function") {
            return manager.reloadList({ resetOffset: true, scrollY: 0 });
          }
          window.location.reload();
        })
        .catch(function (err) {
          console.error("Fehler beim Zurücksetzen der Präferenzen:", err);
          updateFeedback("Zurücksetzen fehlgeschlagen", true);
          window.location.reload();
        })
        .finally(function () {
          resetButton.disabled = false;
        });
    });
  }
});
