// Diese Datei bietet gemeinsame Steuerlogik für News-Listen mit AJAX-Nachladen, History-Management und Caching
// Aufbau von History-Einträgen (Listenansicht): { type: "list", key: "..."} (key ist der Cache-Schlüssel)
// Aufbau von History-Einträgen (Detailansicht): { type: "detail", id: 123, keyPrevUrl: "..." } (keyPrevUrl ist die vorherige Listen-URL, dient zum Check auf Cache)
// Aufbau von Cache-Objekten: { htmlCache: "...", scrollY: 123, offset: 40 }

(function (global) {
  if (global.NewsFeedCore) {
    return;
  }

  // Normalisiert Pfad und Query in einen stabilen Schlüssel, der als Identifier für History und Cache dient
  function canonicalKey(pathname, search) {
    var normalizedPath = pathname.endsWith("/") ? pathname : pathname + "/";
    var query = new URLSearchParams(search).toString();
    return query ? normalizedPath + "?" + query : normalizedPath;
  }

  // Liefert eine sichere sessionStorage Referenz oder null bei verbotener Nutzung
  function safeSessionStorage() {
    try {
      var storage = global.sessionStorage;
      storage.setItem("__storage_test__", "1");
      storage.removeItem("__storage_test__");
      return storage;
    } catch (err) {
      return null;
    }
  }

  // Wandelt relative URLs in ein Ankerobjekt um, damit Pfad und Query getrennt verfügbar sind
  function parseUrl(relativeUrl) {
    var anchor = document.createElement("a");
    anchor.href = relativeUrl;
    return anchor;
  }

  // Zentraler Einstiegspunkt, der von den Seiten mit individuellen Einstellungen aufgerufen wird
  function initNewsFeed(config) {
    if (!config || typeof config.getBasePath !== "function") {
      console.error("getBasePath-Funktion in config fehlt oder ist ungültig");
      return null;
    }

    var containerSelector = config.containerSelector || "#news-container";
    var container = document.querySelector(containerSelector);
    if (!container) {
      console.warn("container-Element für gegebenen Selektor nicht gefunden");
      return null;
    }

    // Variablen mit sinnvollen Default-Werten initialisieren
    var limit = typeof config.limit === "number" ? config.limit : 20;
    var initialOffset = typeof config.initialOffset === "number" ? config.initialOffset : limit;
    var offset = initialOffset;
    var loadMoreSelector = config.loadMoreSelector || "#load-more";
    var loadMoreHandler = null;
    var pageState = {};
    var storage = safeSessionStorage();

    // Basis-URL wird über getBasePath gegeben und hier noch normalisiert
    function getBasePath() {
      var base = config.getBasePath();
      if (!base.endsWith("/")) {
        base += "/";
      }
      return base.replace(/\/{2,}/g, "/");
    }

    // Funktionen aus der Config extrahieren, damit sie leichter nutzbar sind
    var buildListUrls = config.buildListUrls;
    var buildQueryFromFilters = config.buildQueryFromFilters;
    var applyFiltersFromURL = config.applyFiltersFromURL;
    var getDetailPageUrl = config.getDetailPageUrl;
    var getDetailFetchUrl = config.getDetailFetchUrl;

    // Schreibt sämtliche Listeninformationen in den Memory Cache und optional in sessionStorage
    function saveListState(key, state) {
      if (!key) {
        return;
      }
      pageState[key] = state;
      if (storage) {
        try {
          storage.setItem(key, JSON.stringify(state));
        } catch (err) {
          // Ignorieren, wenn der Speicher voll ist oder blockiert wird
        }
      }
    }

    // Laden eines gespeicherten Zustands aus Memory Cache oder sessionStorage mit Fallback auf null
    function loadListState(key) {
      if (!key) {
        return null;
      }
      if (pageState[key]) {
        return pageState[key];
      }
      if (storage) {
        try {
          var raw = storage.getItem(key);
          if (raw) {
            var parsed = JSON.parse(raw);
            pageState[key] = parsed;
            return parsed;
          }
        } catch (err) {
          return null;
        }
      }
      return null;
    }

    // Liefert den Schlüssel für den aktuellen Seitenzustand
    function currentKey() {
      return canonicalKey(global.location.pathname, global.location.search);
    }

    // Blendet den Nachlade-Button aus, etwa in Detailansichten
    function hideLoadMoreButton() {
      var button = document.querySelector(loadMoreSelector);
      if (button) {
        button.classList.add("hidden");
      }
    }

    // Zeigt den Nachlade-Button an, etwa nach der Rückkehr in die Liste
    function showLoadMoreButton() {
      var button = document.querySelector(loadMoreSelector);
      if (button) {
        button.classList.remove("hidden");
      }
    }

    // Funktionalität des Nachladen-Buttons
    function bindLoadMoreButton() {
      var button = document.querySelector(loadMoreSelector);
      if (!button) {
        return;
      }
      // Bereits gebundene Handler entfernen, damit nicht mehrfach reagiert wird
      if (loadMoreHandler) {
        button.removeEventListener("click", loadMoreHandler);
      }
      loadMoreHandler = function () {
        // URLs für die Listenseite und das Nachladen ermitteln
        var urls = buildListUrls(buildQueryFromFilters());
        var fetchUrl = urls.fetchUrl;
        var separator = fetchUrl.indexOf("?") === -1 ? "?" : "&";
        button.disabled = true;

        // AJAX-Anfrage zum Nachladen weiterer News,alten Zustand sichern, neues HTML anhängen, Button reaktivieren
        fetch(fetchUrl + separator + "offset=" + offset + "&limit=" + limit)
          .then(function (response) {
            return response.text();
          })
          .then(function (html) {
            var tempDiv = document.createElement("div");
            tempDiv.innerHTML = html;
            button.remove();
            while (tempDiv.firstChild) {
              container.appendChild(tempDiv.firstChild);
            }
            offset += limit;
            // Aktuellen Zustand mit erweitertem HTML und neuem Offset sichern
            saveListState(currentKey(), {
              htmlCache: container.innerHTML,
              scrollY: global.scrollY,
              offset: offset,
            });
            bindLoadMoreButton();
            showLoadMoreButton();
          })
          .catch(function (error) {
            console.error("Fehler beim Laden weiterer News:", error);
            button.disabled = false;
          });
      };
      button.addEventListener("click", loadMoreHandler);
    }

    // Erstellt den sichtbaren Listenbereich neu und kümmert sich um Scroll-Position sowie Button-Zustand
    function renderListFromHTML(html, options) {
      var settings = options || {};
      container.innerHTML = html;
      if (settings.resetOffset !== false) {
        offset = initialOffset;
      }
      if (typeof settings.scrollY === "number") {
        global.scrollTo(0, settings.scrollY);
      } else {
        global.scrollTo(0, 0);
      }
      bindLoadMoreButton();
      showLoadMoreButton();
    }

    // Neuladen der Liste mit aktualisierten Nutzerpräferenzen
    function reloadList(options) {
      var settings = options || {};
      var query = typeof settings.queryOverride === "string" ? settings.queryOverride : new URLSearchParams(global.location.search).toString();
      var urls = buildListUrls(query);
      return fetch(urls.fetchUrl)
        .then(function (response) {
          return response.text();
        })
        .then(function (html) {
          renderListFromHTML(html, { scrollY: settings.scrollY || 0, resetOffset: settings.resetOffset !== false });
          var urlObj = parseUrl(urls.pageUrl);
          var key = canonicalKey(urlObj.pathname, urlObj.search);
          saveListState(key, {
            htmlCache: container.innerHTML,
            scrollY: settings.scrollY || 0,
            offset: offset,
          });
          showLoadMoreButton();
          if (settings.updateHistory !== false) {
            history.replaceState({ type: "list", key: key }, "", urls.pageUrl);
          }
        })
        .catch(function (error) {
          console.error("Fehler beim Aktualisieren der News-Liste:", error);
        });
    }

    // Sichert den aktuellen Zustand, bevor in eine Detailansicht gewechselt wird
    function saveCurrentState() {
      saveListState(currentKey(), {
        htmlCache: container.innerHTML,
        scrollY: global.scrollY,
        offset: offset,
      });
    }

    // Verarbeitet Klicks auf den Filter-Anwenden-Button
    function handleFilterApply() {
      if (!config.filterApplyButton) {
        return;
      }
      config.filterApplyButton.addEventListener("click", function () {
        // Neue Query aus den Filtern erstellen und URLs generieren
        var query = config.buildQueryFromFilters();
        var urls = buildListUrls(query);
        var urlObj = parseUrl(urls.pageUrl);
        var key = canonicalKey(urlObj.pathname, urlObj.search);

        // Neuen Zustand auf History-Stack legen
        history.pushState({ type: "list", key: key }, "", urls.pageUrl);

        // Neue Liste laden, rendern und Zustand sichern
        fetch(urls.fetchUrl)
          .then(function (response) {
            return response.text();
          })
          .then(function (html) {
            renderListFromHTML(html, { resetOffset: true, scrollY: 0 });
            saveListState(key, {
              htmlCache: container.innerHTML,
              scrollY: 0,
              offset: offset,
            });
          })
          .catch(function (error) {
            console.error("Fehler beim Anwenden der Filter:", error);
          });
      });
    }

    // Verarbeitet Klicks auf Filter-Zurücksetzen und Alle-Auswählen-Buttons
    function handleFilterUtilities() {
      if (!config.filterForm) {
        return;
      }
      if (config.filterResetButton) {
        config.filterResetButton.addEventListener("click", function () {
          var checkboxes = config.filterForm.querySelectorAll('input[type="checkbox"]');
          checkboxes.forEach(function (cb) {
            cb.checked = false;
          });
        });
      }
      if (config.filterSelectAllButton) {
        config.filterSelectAllButton.addEventListener("click", function () {
          var checkboxes = config.filterForm.querySelectorAll('input[type="checkbox"]');
          checkboxes.forEach(function (cb) {
            cb.checked = true;
          });
        });
      }
    }

    // Verarbeitet Klicks auf News-Karten und den Zurück-zur-Liste-Button in Detailansichten
    function handleCardClicks() {

      // Handler für jedwede Klicks im Body registrieren
      document.body.addEventListener("click", function (event) {

        // Klick auf eine News-Karte, daher Detailansicht nachladen
        var card = event.target.closest ? event.target.closest(".news-card") : null;
        if (card) {
          event.preventDefault();
          // ID der News aus dem data-Attribut extrahieren
          var newsId = card.dataset.id;
          if (!newsId) {
            return;
          }
          // Vorherigen Zustand sichern, damit ein Zurückspringen möglich ist
          saveCurrentState();
          var previousKey = currentKey();
          history.pushState({ type: "detail", id: newsId, keyPrevUrl: previousKey }, "", getDetailPageUrl(newsId));
          // Detailansicht per AJAX nachladen und anzeigen
          fetch(getDetailFetchUrl(newsId))
            .then(function (response) {
              return response.text();
            })
            .then(function (html) {
              container.innerHTML = html;
              hideLoadMoreButton();
              global.scrollTo(0, 0);
            })
            .catch(function (error) {
              console.error("Fehler beim Laden der Detailansicht:", error);
            });
          return;
        }

        // Klick auf den Zurück-zur-Liste-Button, daher zurück zur vorherigen Listenansicht
        if (event.target && event.target.id === "back-to-list") {
          event.preventDefault();
          // Aktuellen State laden und mit keyPrevUrl prüfen, ob ein passender Cache-Eintrag existiert
          var state = history.state;
          var keyPrevUrl = state && state.keyPrevUrl;
          var hasCachedState = keyPrevUrl && (pageState[keyPrevUrl] || (storage && storage.getItem && storage.getItem(keyPrevUrl)));
          // Falls ein gecachter Zustand existiert, history.back() nutzen, löst popstate aus
          if (hasCachedState) {
            history.back();
            // Ansonsten zur vorherigen Listen-URL navigieren, was einen Seitenreload auslöst
          } else if (keyPrevUrl) {
            global.location.href = keyPrevUrl;
          } else {
            global.location.href = getBasePath();
          }
        }
      });
    }

    // Verarbeitet popstate-Events, die durch history.back() oder Vor-/Zurück-Buttons im Browser ausgelöst werden
    function handlePopState() {
      global.addEventListener("popstate", function (event) {
        // State-Objekt des angesteuerten Eintrags extrahieren
        var state = event.state;
        var params = new URLSearchParams(global.location.search);
        applyFiltersFromURL(params);

        // Angesteuerte Ansicht ist eine Detailansicht, daher diese laden
        if (state && state.type === "detail") {
          // Mit state.id die Detailansicht per AJAX nachladen und anzeigen
          fetch(getDetailFetchUrl(state.id))
            .then(function (response) {
              return response.text();
            })
            .then(function (html) {
              container.innerHTML = html;
              hideLoadMoreButton();
              global.scrollTo(0, 0);
            })
            .catch(function (error) {
              console.error("Fehler beim Laden der Detailansicht:", error);
            });
          return;
        }

        // Angesteuerte Ansicht ist eine Listenansicht, daher Zustand aus Cache laden
        // In state.key ist der Schlüssel für den Cache gespeichert
        var key = state && state.key ? state.key : currentKey();
        var cached = loadListState(key);
        if (cached && cached.htmlCache) {
          // Es existiert ein gecachter Zustand, daher können wir ohne Anfrage neu rendern
          renderListFromHTML(cached.htmlCache, {
            resetOffset: false,
            scrollY: cached.scrollY || 0,
          });
          offset = cached.offset;
          showLoadMoreButton();
        } else {
          // Kein Cache vorhanden, deshalb Server anfragen und anschließend standardmäßig positionieren
          var query = new URLSearchParams(global.location.search).toString();
          var urls = buildListUrls(query);
          fetch(urls.fetchUrl)
            .then(function (response) {
              return response.text();
            })
            .then(function (html) {
              renderListFromHTML(html, { resetOffset: true, scrollY: 0 });
              offset = initialOffset;
              showLoadMoreButton();
            })
            .catch(function (error) {
              console.error("Fehler beim Laden der News-Übersicht:", error);
            });
        }
      });
    }

    // Registriert alle Event-Handler
    bindLoadMoreButton();
    handleFilterApply();
    handleFilterUtilities();
    handleCardClicks();
    handlePopState();
    applyFiltersFromURL(new URLSearchParams(global.location.search));


    saveListState(initKey, {
      htmlCache: container.innerHTML,
      scrollY: global.scrollY,
      offset: offset,
    });

    return {
      reloadList: reloadList,
      saveCurrentState: saveCurrentState,
    };
  }

  // Stellt die Initialisierungsfunktion global bereit, damit Seiten sie nutzen können
  global.NewsFeedCore = {
    initNewsFeed: initNewsFeed,
  };
})(window);
