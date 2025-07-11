var eventHideBtn = document.getElementById("eventHideBtn");
var eventUnhideBtn = document.getElementById("eventUnhideBtn");
// Die folgende Datei ist ein Vorschlag für die neue calendar.js, die die gewünschte Funktionalität kapselt.
// Sie kann in calendar.html eingebunden werden (siehe Kommentar unten).
document.addEventListener("DOMContentLoaded", function () {
  var calendarEl = document.getElementById("calendar");
  var csrfToken = document.getElementById("csrfToken").value;
  var eventPopup = document.getElementById("eventPopup");
  var openPopupBtn = document.getElementById("openPopup");
  var closePopupBtn = document.getElementById("closePopup");
  var currentUserId = document.getElementById("currentUserId")?.value || "";

  // Zusätzliche Felder für Bearbeiten
  var editMode = false;
  var editingEventId = null;

  // Popup-Felder
  var eventTitle = document.getElementById("eventTitle");
  var eventStart = document.getElementById("eventStart");
  var eventEnd = document.getElementById("eventEnd");
  var eventDescription = document.getElementById("eventDescription");
  var eventRepeat = document.getElementById("eventRepeat");
  var eventRepeatUntil = document.getElementById("eventRepeatUntil");
  var submitBtn = document.getElementById("eventSubmitBtn");

  // Checkbox für "Alle Termine dieser Serie"
  let allInGroupCheckbox = document.createElement("input");
  allInGroupCheckbox.type = "checkbox";
  allInGroupCheckbox.id = "allInGroupCheckbox";
  let allInGroupLabel = document.createElement("label");
  allInGroupLabel.htmlFor = "allInGroupCheckbox";
  allInGroupLabel.textContent = "Alle Termine dieser Serie bearbeiten/löschen";
  let eventForm = document.getElementById("eventForm");
  eventForm.appendChild(document.createElement("br"));
  eventForm.appendChild(allInGroupCheckbox);
  eventForm.appendChild(allInGroupLabel);

  function openEventPopup(mode, eventData) {
    editMode = mode === "edit";
    editingEventId = eventData ? eventData.id : null;
    if (eventData) {
      eventTitle.value = eventData.title || "";
      eventStart.value = eventData.start ? eventData.start.substring(0, 16) : "";
      eventEnd.value = eventData.end ? eventData.end.substring(0, 16) : "";
      eventDescription.value = eventData.description || "";
      // Frequenz und Wiederholen-bis dürfen beim Bearbeiten nicht mehr geändert werden!
      eventRepeat.value = eventData.repeat || "none";
      eventRepeat.disabled = true;
      eventRepeat.style.display = "none";
      eventRepeatUntil.value = eventData.repeat_until ? eventData.repeat_until.substring(0, 16) : "";
      eventRepeatUntil.disabled = true;
      eventRepeatUntil.style.display = "none";
      submitBtn.textContent = "Speichern";
      if (eventData.group) {
        allInGroupCheckbox.style.display = "inline-block";
        allInGroupLabel.style.display = "inline-block";
        allInGroupCheckbox.checked = false;
      } else {
        allInGroupCheckbox.style.display = "none";
        allInGroupLabel.style.display = "none";
        allInGroupCheckbox.checked = false;
      }
      // Show/hide hide/unhide buttons for global events
      if (eventData.is_global) {
        if (eventData.hidden) {
          eventHideBtn.style.display = "none";
          eventUnhideBtn.style.display = "inline-block";
        } else {
          eventHideBtn.style.display = "inline-block";
          eventUnhideBtn.style.display = "none";
        }
      } else {
        eventHideBtn.style.display = "none";
        eventUnhideBtn.style.display = "none";
      }
    } else {
      eventTitle.value = "";
      eventStart.value = "";
      eventEnd.value = "";
      eventDescription.value = "";
      eventRepeat.value = "none";
      eventRepeat.disabled = false;
      eventRepeat.style.display = "inline-block";
      eventRepeatUntil.value = "";
      eventRepeatUntil.disabled = false;
      eventRepeatUntil.style.display = "inline-block";
      submitBtn.textContent = "Hinzufügen";
      allInGroupCheckbox.style.display = "none";
      allInGroupLabel.style.display = "none";
      allInGroupCheckbox.checked = false;
      eventHideBtn.style.display = "none";
      eventUnhideBtn.style.display = "none";
    }
    eventPopup.style.display = "block";
  }

  function closeEventPopup() {
    eventPopup.style.display = "none";
    editMode = false;
    editingEventId = null;
  }

  var calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: "dayGridMonth",
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "dayGridMonth,timeGridWeek,timeGridDay",
    },
    locale: "de",
    editable: false,
    events: "/api/calendar-events/",
    eventClick: function (info) {
      // Event-Details holen
      fetch(`/api/calendar-events/${info.event.id}/`, {
        method: "GET",
        headers: { "X-CSRFToken": csrfToken }
      })
        .then(response => response.json())
        .then(data => {
          openEventPopup("edit", data);
          // Zeige auch einen Löschen-Button im Popup
          document.getElementById("eventDeleteBtn").style.display =
            data.user_id == currentUserId ? "inline-block" : "none";
        });
    },
    eventDidMount: function (info) {
      var description = info.event.extendedProps.description || "";
      var titleEl = info.el.querySelector(".fc-event-title");
      if (titleEl) {
        titleEl.innerHTML = `${info.event.title}<br><span class=\"event-description\">${description}</span>`;
      }
    },
  });

  calendar.render();

  openPopupBtn.addEventListener("click", function () {
    openEventPopup("create");
    document.getElementById("eventDeleteBtn").style.display = "none";
  });

  closePopupBtn.addEventListener("click", closeEventPopup);

  // Event speichern/erstellen
  document.getElementById("eventForm").addEventListener("submit", function (event) {
    event.preventDefault();
    var payload = {
      title: eventTitle.value,
      start: eventStart.value,
      end: eventEnd.value || null,
      description: eventDescription.value,
      repeat: eventRepeat.value,
      repeat_until: eventRepeatUntil.value,
      all_in_group: allInGroupCheckbox.checked
    };
    var url = "/api/calendar-events/";
    var method = "POST";
    if (editMode && editingEventId) {
      url = `/api/calendar-events/${editingEventId}/`;
      method = "PUT";
    }
    fetch(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken
      },
      body: JSON.stringify(payload)
    })
      .then(response => response.json())
      .then(data => {
        if (data.message) {
          alert(editMode ? "Event gespeichert!" : "Event hinzugefügt!");
          calendar.refetchEvents();
          closeEventPopup();
        } else {
          alert("Fehler: " + data.error);
        }
      })
      .catch(error => console.error("Fehler beim Speichern des Events:", error));
  });

  // Event löschen
  document.getElementById("eventDeleteBtn").addEventListener("click", function () {
    if (!editingEventId) return;
    var url = `/api/calendar-events/${editingEventId}/`;
    var params = [];
    if (allInGroupCheckbox.checked) {
      params.push("all_in_group=true");
    }
    if (params.length > 0) {
      url += "?" + params.join("&");
    }
    if (confirm("Willst du dieses Event wirklich löschen?" + (allInGroupCheckbox.checked ? " (Alle Termine dieser Serie werden gelöscht!)" : ""))) {
      fetch(url, {
        method: "DELETE",
        headers: { "X-CSRFToken": csrfToken }
      })
        .then(response => response.json())
        .then(data => {
          if (data.success) {
            alert("Event gelöscht!");
            calendar.refetchEvents();
            closeEventPopup();
          } else {
            alert("Löschen fehlgeschlagen: " + data.error);
          }
        })
        .catch(error => console.error("Fehler:", error));
    }
  });

});
