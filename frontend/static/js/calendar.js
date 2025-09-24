// Time Picker Dropdowns
  function buildTimeOptions() {
    const times = [];
    for (let h = 0; h < 24; h++) {
      for (let m = 0; m < 60; m += 30) {
        times.push(("0"+h).slice(-2) + ":" + ("0"+m).slice(-2));
      }
    }
    return times;
  }
  function showTimeDropdown(inputEl, dropdownEl) {
    dropdownEl.innerHTML = "";
    const times = buildTimeOptions();
    times.forEach(t => {
      const opt = document.createElement("div");
      opt.textContent = t;
      opt.className = "px-2 py-1 hover:bg-blue-100 cursor-pointer text-sm";
      opt.addEventListener("mousedown", function(e) {
        inputEl.value = t;
        dropdownEl.classList.add("hidden");
        e.preventDefault();
      });
      dropdownEl.appendChild(opt);
    });
    dropdownEl.classList.remove("hidden");
  }
  function hideTimeDropdown(dropdownEl) {
    dropdownEl.classList.add("hidden");
  }
  // Start Time Picker
  var startTimePickerBtn = document.getElementById("startTimePickerBtn");
  var startTimeDropdown = document.getElementById("startTimeDropdown");
  startTimePickerBtn.addEventListener("click", function(e) {
    showTimeDropdown(eventStartTime, startTimeDropdown);
    e.stopPropagation();
  });
  // End Time Picker
  var endTimePickerBtn = document.getElementById("endTimePickerBtn");
  var endTimeDropdown = document.getElementById("endTimeDropdown");
  endTimePickerBtn.addEventListener("click", function(e) {
    showTimeDropdown(eventEndTime, endTimeDropdown);
    e.stopPropagation();
  });
  // Hide dropdowns on click outside
  document.addEventListener("click", function(e) {
    hideTimeDropdown(startTimeDropdown);
    hideTimeDropdown(endTimeDropdown);
  });
  var allDayBtn = document.getElementById("allDayBtn");
  var startTimeRow = document.getElementById("startTimeRow");
  var isAllDay = false;

  function setAllDayMode(active) {
    isAllDay = active;
    var startTimePickerBtn = document.getElementById("startTimePickerBtn");
    var endTimePickerBtn = document.getElementById("endTimePickerBtn");
    if (active) {
      eventStartTime.style.display = "none";
      eventEndTime.style.display = "none";
      if (startTimePickerBtn) startTimePickerBtn.style.display = "none";
      if (endTimePickerBtn) endTimePickerBtn.style.display = "none";
      eventStartTime.value = "00:00";
      eventEndTime.value = "23:59";
      allDayBtn.classList.add("bg-blue-200");
      allDayBtn.textContent = "Ganztägig ✓";
    } else {
      eventStartTime.style.display = "";
      eventEndTime.style.display = "";
      if (startTimePickerBtn) startTimePickerBtn.style.display = "";
      if (endTimePickerBtn) endTimePickerBtn.style.display = "";
      allDayBtn.classList.remove("bg-blue-200");
      allDayBtn.textContent = "Ganztägig";
    }
  }

  allDayBtn.addEventListener("click", function () {
    setAllDayMode(!isAllDay);
  });
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

  // Felder
  var eventTitle = document.getElementById("eventTitle");
  var eventStartDate = document.getElementById("eventStartDate");
  var eventStartTime = document.getElementById("eventStartTime");
  var eventEndDate = document.getElementById("eventEndDate");
  var eventEndTime = document.getElementById("eventEndTime");
  var eventDescription = document.getElementById("eventDescription");
  var eventRepeat = document.getElementById("eventRepeat");
  var eventRepeatUntil = document.getElementById("eventRepeatUntil");
  var submitBtn = document.getElementById("eventSubmitBtn");
  var eventDeleteBtn = document.getElementById("eventDeleteBtn");
  var repeatOptions = document.getElementById("repeatOptions");
  var toggleRepeatOptions = document.getElementById("toggleRepeatOptions");
  var allInGroupCheckbox = document.getElementById("allInGroupCheckbox");
  var allInGroupLabel = document.getElementById("allInGroupLabel");
  var allInGroupContainer = document.getElementById("allInGroupContainer");

  var editMode = false;
  var editingEventId = null;

  // Animation für Popup
  function showPopup() {
    eventPopup.classList.remove("hidden");
    setTimeout(() => {
      eventPopup.classList.add("opacity-100");
    }, 10);
  }
  function hidePopup() {
    eventPopup.classList.remove("opacity-100");
    setTimeout(() => {
      eventPopup.classList.add("hidden");
    }, 200);
    editMode = false;
    editingEventId = null;
  }

  // Toggle Wiederholungsoptionen
  toggleRepeatOptions.addEventListener("click", function () {
    if (repeatOptions.classList.contains("hidden")) {
      repeatOptions.classList.remove("hidden");
      toggleRepeatOptions.classList.add("bg-blue-100");
    } else {
      repeatOptions.classList.add("hidden");
      toggleRepeatOptions.classList.remove("bg-blue-100");
    }
  });

  function openEventPopup(mode, eventData) {
    editMode = mode === "edit";
    editingEventId = eventData ? eventData.id : null;
    // Reset
    eventTitle.value = eventData ? eventData.title || "" : "";
    // Startdatum und Zeit
    if (eventData && eventData.start) {
      const startDT = new Date(eventData.start);
      // Hole Datum und Zeit lokal, damit kein Offset entsteht
      eventStartDate.value = startDT.getFullYear() + "-" + String(startDT.getMonth()+1).padStart(2, '0') + "-" + String(startDT.getDate()).padStart(2, '0');
      eventStartTime.value = String(startDT.getHours()).padStart(2, '0') + ":" + String(startDT.getMinutes()).padStart(2, '0');
    } else {
      eventStartDate.value = "";
      eventStartTime.value = "";
    }
    // Enddatum und Zeit
    if (eventData && eventData.end) {
      const endDT = new Date(eventData.end);
      eventEndDate.value = endDT.getFullYear() + "-" + String(endDT.getMonth()+1).padStart(2, '0') + "-" + String(endDT.getDate()).padStart(2, '0');
      eventEndTime.value = String(endDT.getHours()).padStart(2, '0') + ":" + String(endDT.getMinutes()).padStart(2, '0');
    } else {
      eventEndDate.value = "";
      eventEndTime.value = "";
    }
    // Ganztägig-Status setzen, wenn Startzeit 00:00 und Endzeit 23:59
    if (eventStartTime.value === "00:00" && eventEndTime.value === "23:59") {
      setAllDayMode(true);
    } else {
      setAllDayMode(false);
    }
    eventDescription.value = eventData ? eventData.description || "" : "";
    eventRepeat.value = eventData ? eventData.repeat || "none" : "none";
    eventRepeatUntil.value = eventData && eventData.repeat_until ? eventData.repeat_until.substring(0, 16) : "";
  submitBtn.textContent = editMode ? "Speichern" : "Hinzufügen";
  var eventPopupTitle = document.getElementById("eventPopupTitle");
  eventPopupTitle.textContent = editMode ? "Termin bearbeiten" : "Termin erstellen";

    // Wiederholungsoptionen und Button nur beim Erstellen anzeigen
    if (editMode) {
      toggleRepeatOptions.classList.add("hidden");
      repeatOptions.classList.add("hidden");
    } else {
      toggleRepeatOptions.classList.remove("hidden");
      repeatOptions.classList.add("hidden");
      toggleRepeatOptions.classList.remove("bg-blue-100");
    }

    // Checkbox für Serienbearbeitung: nur anzeigen, wenn group mehrfach vorkommt und user_id gleich ist
    if (eventData && eventData.group && eventData.group !== "" && eventData.group !== null) {
      fetch(`/api/calendar-events/?group=${encodeURIComponent(eventData.group)}`)
        .then(response => response.json())
        .then(eventsWithGroup => {
          // Filtere nach user_id
          const sameUserEvents = eventsWithGroup.filter(ev => ev.user_id === eventData.user_id);
          if (Array.isArray(sameUserEvents) && sameUserEvents.length > 1) {
            allInGroupContainer.classList.remove("hidden");
            allInGroupCheckbox.checked = false;
          } else {
            allInGroupContainer.classList.add("hidden");
            allInGroupCheckbox.checked = false;
          }
        })
        .catch(() => {
          allInGroupContainer.classList.add("hidden");
          allInGroupCheckbox.checked = false;
        });
    } else {
      allInGroupContainer.classList.add("hidden");
      allInGroupCheckbox.checked = false;
    }

    // Löschen-Button nur für eigene Events
    if (editMode && eventData && eventData.user_id == currentUserId) {
      eventDeleteBtn.classList.remove("hidden");
    } else {
      eventDeleteBtn.classList.add("hidden");
    }

    showPopup();
  }

  // FullCalendar
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
      fetch(`/api/calendar-events/${info.event.id}/`, {
        method: "GET",
        headers: { "X-CSRFToken": csrfToken }
      })
        .then(response => response.json())
        .then(data => {
          if (data.is_global) {
            alert("Dies ist ein globaler Termin und kann nicht bearbeitet werden.");
            return;
          }
          openEventPopup("edit", data);
        });
    },
    eventDidMount: function (info) {
      var description = info.event.extendedProps.description || "";
      var startTime = "";
      var endTime = "";
      if (info.event.start) {
        const startDate = new Date(info.event.start);
        startTime = startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      if (info.event.end) {
        const endDate = new Date(info.event.end);
        endTime = endDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
      }
      var timeString = startTime;
      if (endTime) {
        timeString += ' - ' + endTime;
      }
      var titleEl = info.el.querySelector(".fc-event-title");
      if (titleEl) {
        titleEl.innerHTML = `${info.event.title}<br><span class=\"event-description\">${description}</span>`;
      }
      if (info.event.extendedProps.is_global) {
        info.el.classList.add("global-event");
      }
    },
  });
  calendar.render();

  openPopupBtn.addEventListener("click", function () {
    openEventPopup("create");
  });
  closePopupBtn.addEventListener("click", hidePopup);

  // Event speichern/erstellen
  document.getElementById("eventForm").addEventListener("submit", function (event) {
    event.preventDefault();
    // Validierung
    let errors = [];
    if (!eventTitle.value.trim()) {
      errors.push("Bitte gib einen Titel ein.");
    }
    if (!eventStartDate.value) {
      errors.push("Bitte wähle ein Startdatum.");
    }
    if (!isAllDay && !eventStartTime.value) {
      errors.push("Bitte wähle eine Startzeit.");
    }
    if (eventEndDate.value && !isAllDay && !eventEndTime.value) {
      errors.push("Bitte wähle eine Endzeit.");
    }
    if (eventEndDate.value && eventEndDate.value < eventStartDate.value) {
      errors.push("Endedatum darf nicht vor dem Startdatum liegen.");
    }
    if (eventEndDate.value && eventEndDate.value === eventStartDate.value && !isAllDay && eventEndTime.value < eventStartTime.value) {
      errors.push("Endzeit darf nicht vor der Startzeit liegen.");
    }
    if (errors.length > 0) {
      alert(errors.join("\n"));
      return;
    }
    // Baue Start- und End-Datetime aus Datum und Zeit
    let start = "";
    if (eventStartDate.value && (isAllDay || eventStartTime.value)) {
      start = eventStartDate.value + "T" + (isAllDay ? "00:00" : eventStartTime.value);
    }
    let end = null;
    if (eventEndDate.value && (isAllDay || eventEndTime.value)) {
      end = eventEndDate.value + "T" + (isAllDay ? "23:59" : eventEndTime.value);
    }
    var payload = {
      title: eventTitle.value,
      start: start,
      end: end,
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
          hidePopup();
        } else {
          alert("Fehler: " + data.error);
        }
      })
      .catch(error => console.error("Fehler beim Speichern des Events:", error));
  });

  // Event löschen
  eventDeleteBtn.addEventListener("click", function () {
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
            hidePopup();
          } else {
            alert("Löschen fehlgeschlagen: " + data.error);
          }
        })
        .catch(error => console.error("Fehler:", error));
    }
  });

  // Popup schließen bei Klick auf Overlay
  eventPopup.addEventListener("click", function (e) {
    if (e.target === eventPopup) {
      hidePopup();
    }
  });

});

