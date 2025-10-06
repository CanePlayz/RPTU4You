// Aktuell geladener Offset (wir starten mit 20, weil 20 beim ersten Rendern schon vorhanden sind)
let offset = 20;
const limit = 20;

// In diesem Objekt speichern wir den Zustand des News-Feeds,
// damit wir ihn bei einem "Zurück" (popstate) wiederherstellen können
let newsFeedState = {
  htmlCache: '',   // hier speichern wir den gerenderten HTML-Inhalt der News-Liste
  scrollY: 0,       // Scrollposition vor dem Klick auf ein Detailobjekt
  offset: 20    // aktueller Offset für "Mehr laden"
};

// Neuer: Zustände pro URL speichern
let pageState = {}; // key = URL (z.B. /news/?location=A), value = { htmlCache, scrollY }

// Starte nach dem Laden der Seite
document.addEventListener('DOMContentLoaded', () => {
  const filterForm = document.getElementById('news-filter-form');
  const newsContainer = document.getElementById('news-container');

  // ---------- Helpers: Locale-Präfix & Key-Kanonisierung ----------
  function getLocalePrefix() {
    // z. B. "/de"
    const m = window.location.pathname.match(/^\/([a-z]{2})(?=\/)/i);
    return m ? `/${m[1]}` : '';
  }

  function newsBase() {
    // z. B. "/de/news/"
    return `${getLocalePrefix()}/news/`.replace(/\/{2,}/g, '/');
  }

  function canonicalKey(pathname, search) {
    const path = pathname.endsWith('/') ? pathname : `${pathname}/`;
    const q = new URLSearchParams(search).toString();
    return q ? `${path}?${q}` : path;
  }

  // Initialen Verlaufseintrag setzen, damit event.state nicht null ist
  const initKey = canonicalKey(window.location.pathname, window.location.search);
  if (!history.state) {
    history.replaceState({ type: 'list', key: initKey }, '', initKey);
  }

  // Hilfsfunktion zum Erstellen der Filter-URLs
  function buildFilterUrls(form) {
    const formData = new FormData(form);
    const params = new URLSearchParams();
    for (const [key, value] of formData.entries()) {
      params.append(key, value);
    }
    const query = params.toString();
    const base = newsBase();
    return {
      newUrl: query ? `${base}?${query}` : base,
      fetchUrl: query ? `${base}partial?${query}` : `${base}partial`
    };
  }


  function bindLoadMoreButton() {
    const loadMoreBtn = document.getElementById('load-more');
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', () => {
        const urls = buildFilterUrls(filterForm);

        // deaktivieren, um mehrfaches Klicken zu verhindern
        loadMoreBtn.disabled = true;

        const sep = urls.fetchUrl.includes('?') ? '&' : '?';
        fetch(`${urls.fetchUrl}${sep}offset=${offset}&limit=${limit}`)
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

            // Zustand aktualisieren
            const key = canonicalKey(window.location.pathname, window.location.search);
            const updated = {
              htmlCache: newsContainer.innerHTML,
              scrollY: window.scrollY,
              offset: offset
            };
            pageState[key] = updated;
            sessionStorage.setItem(key, JSON.stringify(updated));

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
      const currentKey = canonicalKey(window.location.pathname, window.location.search);
      const stateObj = {
        htmlCache: document.querySelector('#news-container').innerHTML,
        scrollY: window.scrollY,
        offset: offset
      };
      pageState[currentKey] = stateObj;
      sessionStorage.setItem(currentKey, JSON.stringify(stateObj));

      // Neuen Zustand für die Detailansicht in den Verlauf einfügen
      history.pushState({ type: 'detail', id: newsId, keyPrevUrl: currentKey }, '', `${newsBase()}${newsId}/`);

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
      // Prüfe, ob ein Verlaufseintrag für die vorherige Übersicht existiert
      const keyPrevUrl = history.state?.keyPrevUrl;
      const hasOverviewState = keyPrevUrl && (pageState[keyPrevUrl] || sessionStorage.getItem(keyPrevUrl));

      // Wenn ja, dann zurück navigieren
      if (hasOverviewState) {
        history.back();
      } else {
        // Ansonsten zur Basis-Übersicht navigieren
        window.location.href = keyPrevUrl || newsBase();
      }
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
      fetch(`${newsBase()}${state.id}/?partial=true`)
        .then(resp => resp.text())
        .then(html => {
          document.querySelector('#news-container').innerHTML = html;
          window.scrollTo(0, 0);
          const loadMoreBtn = document.getElementById('load-more');
          loadMoreBtn?.classList.add('hidden');

        });
    } else {
      // Benutzer springt zurück zu einer Listen-Ansicht
      const currentKey = canonicalKey(window.location.pathname, window.location.search);
      const cached =
        pageState[currentKey] ||
        JSON.parse(sessionStorage.getItem(currentKey) || 'null');

      if (cached) {
        document.querySelector('#news-container').innerHTML = cached.htmlCache;
        window.scrollTo(0, cached.scrollY);
        offset = cached.offset || 20;
        bindLoadMoreButton();
      } else {
        const qs = urlParams.toString();
        fetch(`${newsBase()}partial${qs ? `?${qs}` : ''}`)
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
            scrollY: 0,
            offset: offset
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
});
