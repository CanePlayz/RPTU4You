// Aktuell geladener Offset (wir starten mit 20, weil 20 beim ersten Rendern schon vorhanden sind)
let offset = 20;
const limit = 20;

// In diesem Objekt speichern wir den Zustand des News-Feeds,
// damit wir ihn bei einem "Zurück" (popstate) wiederherstellen können
let newsFeedState = {
  htmlCache: '',   // hier speichern wir den gerenderten HTML-Inhalt der News-Liste
  scrollY: 0       // Scrollposition vor dem Klick auf ein Detailobjekt
};

// Neuer: Zustände pro URL speichern
let pageState = {}; // key = URL (z.B. /news/?location=A), value = { htmlCache, scrollY }

// Starte nach dem Laden der Seite
document.addEventListener('DOMContentLoaded', () => {
  const filterForm = document.getElementById('news-filter-form');
  const newsContainer = document.getElementById('news-container');

  // Hilfsfunktion zum Erstellen der Filter-URLs
  function buildFilterUrls(form) {
    const formData = new FormData(form);
    const params = new URLSearchParams();
    for (const [key, value] of formData.entries()) {
      params.append(key, value);
    }
    const query = params.toString();
    return {
      newUrl: `/news/?${query}`,
      fetchUrl: `/news/partial?${query}`
    };
  }

  function bindLoadMoreButton() {
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', () => {
        const urls = buildFilterUrls(filterForm);

        // deaktivieren, um mehrfaches Klicken zu verhindern
        loadMoreBtn.disabled = true;

        fetch(`${urls.fetchUrl}&offset=${offset}&limit=${limit}`)
          .then(resp => resp.text())
          .then(html => {
            // Temporäres Container-Element zum Parsen des HTMLs
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = html;

            // Entferne alten Button
            loadMoreBtn.remove();
            // Füge nur News (und evtl. neuen Button) ein
            const newContent = tempDiv.children;
            for (const el of newContent) {
              newsContainer.appendChild(el);
            }

            offset += limit;
            bindLoadMoreButton(); // neu binden falls Button nochmal drin
          });
      });
    }
  }

  function applyFiltersFromURL(urlParams, form) {
    // Alle Checkboxen erstmal zurücksetzen
    const checkboxes = form.querySelectorAll('input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = false);

    // Für jedes Parametervorkommen die passenden Checkboxen aktivieren
    for (const [key, value] of urlParams.entries()) {
      const selector = `input[name="${key}"][value="${value}"]`;
      const checkbox = form.querySelector(selector);
      if (checkbox) checkbox.checked = true;
    }
  }

  bindLoadMoreButton(); // initiales Binden beim Seitenladen

  // ---------------------------------------------
  // 1. Klick auf News-Karte -> lade Detailansicht
  // ---------------------------------------------
  document.body.addEventListener('click', (e) => {
    const card = e.target.closest('.news-card');
    if (card) {
      e.preventDefault();
      const newsId = card.dataset.id;

      // Vor dem Wechsel Zustand der Liste sichern
      const currentKey = window.location.pathname + window.location.search;
      const stateObj = {
        htmlCache: document.querySelector('#news-container').innerHTML,
        scrollY: window.scrollY
      };
      pageState[currentKey] = stateObj;
      sessionStorage.setItem(currentKey, JSON.stringify(stateObj));

      // URL aktualisieren, ohne neu zu laden
      history.pushState({ type: 'detail', id: newsId }, '', `/news/${newsId}/`);

      // Lade nur den HTML-Partial-Inhalt der Detailansicht
      fetch(`/news/${newsId}/?partial=true`)
        .then(resp => resp.text())
        .then(html => {
          document.querySelector('#news-container').innerHTML = html;
          window.scrollTo(0, 0);
        });

      // Button "Mehr laden" ausblenden
      const loadMoreBtn = document.getElementById('load-more');
      if (loadMoreBtn) {
        loadMoreBtn.classList.add('hidden');
      }

      return; // Detailklick wurde behandelt
    }

    // ---------------------------------------------
    // 2. Klick auf "Zurück zur Übersicht" im Detail
    // ---------------------------------------------
    if (e.target.id === 'back-to-list') {
      e.preventDefault();
      // Prüfe, ob ein Verlaufseintrag für die Übersicht existiert
      const overviewUrl = '/news/';
      const currentKey = overviewUrl + window.location.search;
      const hasOverviewState =
        pageState[currentKey] ||
        sessionStorage.getItem(currentKey);

      if (hasOverviewState) {
        history.back();  // löst popstate aus
      } else {
        // Kein Verlaufseintrag: explizit zur Übersicht navigieren
        window.location.href = overviewUrl + window.location.search;
      }
      return;
    }
  });

  // ----------------------------------------------
  // 4. Zurück-Button (Browser oder manuell) → popstate
  // ----------------------------------------------
  window.addEventListener('popstate', (event) => {
    const state = event.state;

    const urlParams = new URLSearchParams(window.location.search);
    applyFiltersFromURL(urlParams, filterForm);

    if (state && state.type === 'detail') {
      // Benutzer springt zurück zu einer Detail-Ansicht
      fetch(`/news/${state.id}/?partial=true`)
        .then(resp => resp.text())
        .then(html => {
          document.querySelector('#news-container').innerHTML = html;
          window.scrollTo(0, 0);
          loadMoreBtn?.classList.add('hidden');
        });
    } else {
      const currentKey = window.location.pathname + window.location.search;
      const cached =
        pageState[currentKey] ||
        JSON.parse(sessionStorage.getItem(currentKey) || 'null');

      if (cached) {
        document.querySelector('#news-container').innerHTML = cached.htmlCache;
        window.scrollTo(0, cached.scrollY);
        bindLoadMoreButton();
      } else {
        fetch(`/news/partial?${urlParams.toString()}`)
          .then(resp => resp.text())
          .then(html => {
            document.querySelector('#news-container').innerHTML = html;
            window.scrollTo(0, 0);
            offset = 20;
            bindLoadMoreButton();
          })
          .catch(err => {
            console.error('Fehler beim Laden der News-Übersicht:', err);
          });
      }
    }
  });

  // ----------------------------------------------
  // 5. Filter anwenden per Button
  // ----------------------------------------------
  const filterButton = document.getElementById('apply-filter-btn');

  if (filterForm && filterButton) {
    filterButton.addEventListener('click', () => {
      console.log('Filter angewendet');
      const urls = buildFilterUrls(filterForm);
      const currentKey = urls.newUrl;

      // Browser-URL aktualisieren
      history.pushState({ type: 'list', key: currentKey }, '', urls.newUrl);

      // AJAX-Inhalt laden
      fetch(urls.fetchUrl)
        .then(resp => resp.text())
        .then(html => {
          newsContainer.innerHTML = html;
          offset = 20; // Reset Offset
          window.scrollTo(0, 0);
          bindLoadMoreButton(); // Button neu binden nach Filter

          // Jetzt Zustand speichern
          const stateObj = {
            htmlCache: newsContainer.innerHTML,
            scrollY: 0
          };
          pageState[currentKey] = stateObj;
          sessionStorage.setItem(currentKey, JSON.stringify(stateObj));
        })
        .catch(err => {
          console.error('Fehler beim Laden der gefilterten News:', err);
        });
    });

    // Reset-Button Logik: Alle Checkboxen abwählen, aber kein Reload
    const resetButton = document.getElementById('reset-filter-btn');
    if (resetButton) {
      resetButton.addEventListener('click', () => {
        // Alle Checkboxen im Filter-Formular abwählen
        const checkboxes = filterForm.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
          cb.checked = false;
        });
      });
    }

    // Select-All-Button Logik: Alle Checkboxen auswählen, aber kein Reload
    const selectAllButton = document.getElementById('select-all-btn');
    if (selectAllButton) {
      selectAllButton.addEventListener('click', () => {
        // Alle Checkboxen im Filter-Formular auswählen
        const checkboxes = filterForm.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(cb => {
          cb.checked = true;
        });
      });
    }
  }
  //Filter dropdown mobile version
  const toggle = document.getElementById('filter-button');
  const dropdown = document.getElementById('filter-dropdown');
  const news = document.getElementById('news');

  if (toggle && dropdown) {
      toggle.addEventListener('click', (event) => {
          event.stopPropagation(); // Prevent click from propagating to document
          const filter_is_Hidden = dropdown.classList.contains('max-md:hidden');
          if (filter_is_Hidden) {
              dropdown.classList.remove('max-md:hidden');
              news.classList.add('hidden')
          } else {
              dropdown.classList.add('max-md:hidden');
              news.classList.remove('hidden');
          }
      });

      // Schließt das Dropdown, wenn man außerhalb klickt
      document.addEventListener('click', (event) => {
          if (!dropdown.contains(event.target) && !toggle.contains(event.target)) {
              dropdown.classList.add('max-md:hidden');
              news.classList.remove('hidden')
          }
      });
  } else {
      console.error("Filter button or Filter dropdown not found");
  }

});
