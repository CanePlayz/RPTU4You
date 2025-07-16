document.addEventListener("DOMContentLoaded", function() {
  let offset = 0;
  let limit = 10;
  let loading = false;
  let hasMore = true;

  function getSelectedFilters() {
    const standorte = [];
    const kategorien = [];
    const zielgruppen = [];
    document.querySelectorAll('#news-filter-form input[name="standorte"]:checked').forEach(el => standorte.push(el.value));
    document.querySelectorAll('#news-filter-form input[name="kategorien"]:checked').forEach(el => kategorien.push(el.value));
    document.querySelectorAll('#news-filter-form input[name="zielgruppen"]:checked').forEach(el => zielgruppen.push(el.value));
    return { standorte, kategorien, zielgruppen };
  }

  function buildApiUrl(offset, limit) {
    const filters = getSelectedFilters();
    let url = `/api/news/?offset=${offset}&limit=${limit}`;
    filters.standorte.forEach(id => url += `&standort=${id}`);
    filters.kategorien.forEach(id => url += `&kategorie=${id}`);
    filters.zielgruppen.forEach(id => url += `&zielgruppe=${id}`);
    return url;
  }

  function loadNews(reset=false) {
    if (loading || !hasMore) return;
    loading = true;
    document.getElementById("news-loading").style.display = "block";
    if (reset) {
      document.getElementById("news-container").innerHTML = "";
      offset = 0;
      hasMore = true;
      document.getElementById("news-empty").style.display = "none";
    }
    const url = buildApiUrl(offset, limit);
    fetch(url)
      .then(response => response.json())
      .then(data => {
        document.getElementById("news-loading").style.display = "none";
        if (data.news && data.news.length > 0) {
          data.news.forEach(article => {
            const newsItem = document.createElement("li");
            newsItem.classList.add("news-item");
            newsItem.innerHTML = `
              <h3>${article.titel}</h3>
              <p>Erstellt am: ${article.erstellungsdatum}</p>
              <p>Quelle: ${article.quelle_typ || 'Keine Quelle'}</p>
              <p><a href="${article.link}">Link zur Webseite</a></p>
              <a href="/news/${article.id}">Weiterlesen</a>
              <hr>
            `;
            document.getElementById("news-container").appendChild(newsItem);
          });
          offset += data.news.length;
          hasMore = data.news.length === limit;
        } else {
          if (reset) {
            document.getElementById("news-empty").style.display = "block";
          }
          hasMore = false;
        }
        loading = false;
      })
      .catch(err => {
        document.getElementById("news-loading").style.display = "none";
        loading = false;
      });
  }

  // Filter anwenden
  document.getElementById("apply-filter-btn").addEventListener("click", function() {
    loadNews(true);
  });

  // Infinite Scroll
  window.addEventListener("scroll", function() {
    if ((window.innerHeight + window.scrollY) >= (document.body.offsetHeight - 100)) {
      loadNews();
    }
  });

  // Initiales Laden
  loadNews(true);
});