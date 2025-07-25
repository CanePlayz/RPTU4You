// Aktuell geladener Offset (wir starten mit 20, weil 20 beim ersten Rendern schon vorhanden sind)
let offset = 20;
const limit = 20;

// In diesem Objekt speichern wir den Zustand des News-Feeds,
// damit wir ihn bei einem "Zurück" (popstate) wiederherstellen können
let newsFeedState = {
  htmlCache: '',   // hier speichern wir den gerenderten HTML-Inhalt der News-Liste
  scrollY: 0       // Scrollposition vor dem Klick auf ein Detailobjekt
};

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
      newsFeedState.htmlCache = document.querySelector('#news-container').innerHTML;
      newsFeedState.scrollY = window.scrollY;

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
      history.back();  // löst popstate aus
      return;
    }
  });

  // ----------------------------------------------
  // 4. Zurück-Button (Browser oder manuell) → popstate
  // ----------------------------------------------
  window.addEventListener('popstate', (event) => {
    const state = event.state;

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
      // Benutzer springt zurück zur News-Übersicht
      document.querySelector('#news-container').innerHTML = newsFeedState.htmlCache;
      window.scrollTo(0, newsFeedState.scrollY);
      bindLoadMoreButton(); // Button neu anbinden
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
      // Browser-URL aktualisieren
      history.pushState({}, '', urls.newUrl);
      // AJAX-Inhalt laden
      fetch(urls.fetchUrl)
        .then(resp => resp.text())
        .then(html => {
          newsContainer.innerHTML = html;
          offset = 20; // Reset Offset
          window.scrollTo(0, 0);
          bindLoadMoreButton(); // Button neu binden nach Filter
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
  }
});
