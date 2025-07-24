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
  const loadMoreBtn = document.getElementById('load-more');

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
  // 3. Klick auf "Mehr laden" → lade weitere News
  // ----------------------------------------------
  document.getElementById('load-more')?.addEventListener('click', () => {
    const formData = new FormData(filterForm);
    const params = new URLSearchParams();
    for (const [key, value] of formData.entries()) {
      params.append(key, value);
    }
    const query = params.toString();

    fetch(`/news/partial/?offset=${offset}&limit=${limit}&${query}`)
      .then(resp => resp.text())
      .then(html => {
        document.querySelector('#news-container').insertAdjacentHTML('beforeend', html);
        offset += limit;
      });
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
      // Benutzer springt zurück zur News-Übersicht (mit Filter berücksichtigen)
      const urlParams = window.location.search;
      fetch(`/news/partial${urlParams}`)
        .then(resp => resp.text())
        .then(html => {
          document.querySelector('#news-container').innerHTML = html;
          window.scrollTo(0, 0);
          loadMoreBtn?.classList.remove('hidden');
        });
    }
  });

  // ----------------------------------------------
  // 5. Filter anwenden per Button
  // ----------------------------------------------
  const filterForm = document.getElementById('news-filter-form');
  const filterButton = document.getElementById('apply-filter-btn');
  const newsContainer = document.getElementById('news-container');

  if (filterForm && filterButton) {
    filterButton.addEventListener('click', () => {
      const formData = new FormData(filterForm);
      const params = new URLSearchParams();
      for (const [key, value] of formData.entries()) {
        params.append(key, value);
      }

      const query = params.toString();
      const newUrl = `/news/?${query}`;
      const fetchUrl = `/news/partial?${query}`;

      // Browser-URL aktualisieren
      history.pushState({}, '', newUrl);

      // AJAX-Inhalt laden
      fetch(fetchUrl)
        .then(resp => resp.text())
        .then(html => {
          newsContainer.innerHTML = html;
          offset = 20; // Reset Offset
          window.scrollTo(0, 0);
        })
        .catch(err => {
          console.error('Fehler beim Laden der gefilterten News:', err);
        });
    });
  }
});
