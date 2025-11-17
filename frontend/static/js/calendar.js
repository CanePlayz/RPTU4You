// Kalender-UI Logik (Zeit-Picker + FullCalendar Integration)
(() => {
  const TIME_STEP_MINUTES = 30; // Schrittweite für Zeitwerte im Dropdown
  const TIME_OPTIONS = buildTimeOptions(); // Vorberechnete Liste aller anzeigbaren Uhrzeiten
  let openTimeDropdown = null; // Referenz auf das aktuell offene Dropdown

  // Erstellt alle Zeitwerte in 30-Minuten-Schritten (00:00 - 23:30)
  function buildTimeOptions() {
    const times = [];
    for (let h = 0; h < 24; h += 1) {
      for (let m = 0; m < 60; m += TIME_STEP_MINUTES) {
        times.push(String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0"));
      }
    }
    return times;
  }

  // Baut das Dropdown neu auf und markiert die aktuelle Auswahl
  function showTimeDropdown(inputEl, dropdownEl) {
    if (!inputEl || !dropdownEl) {
      return;
    }
    dropdownEl.innerHTML = "";
    TIME_OPTIONS.forEach(time => {
      const optionEl = document.createElement("div");
      optionEl.textContent = time;
      optionEl.className = "calendar-dropdown-option";
      if (inputEl.value === time) {
        optionEl.classList.add("calendar-dropdown-option-active");
      }
      optionEl.addEventListener("mousedown", event => {
        inputEl.value = time;
        hideTimeDropdown(dropdownEl);
        event.preventDefault();
      });
      dropdownEl.appendChild(optionEl);
    });
    if (openTimeDropdown && openTimeDropdown !== dropdownEl) {
      hideTimeDropdown(openTimeDropdown);
    }
    dropdownEl.classList.remove("hidden");
    openTimeDropdown = dropdownEl;
  }

  function hideTimeDropdown(dropdownEl) {
    if (dropdownEl) {
      dropdownEl.classList.add("hidden");
    }
  }

  // Verknüpft Button + Input + Dropdown miteinander
  function setupTimePicker(buttonEl, inputEl, dropdownEl) {
    if (!buttonEl || !inputEl || !dropdownEl) {
      return;
    }
    buttonEl.addEventListener("click", event => {
      showTimeDropdown(inputEl, dropdownEl);
      event.stopPropagation();
    });
  }

  // Klick außerhalb schließt ein geöffnetes Dropdown
  document.addEventListener("click", event => {
    if (openTimeDropdown && !openTimeDropdown.contains(event.target)) {
      hideTimeDropdown(openTimeDropdown);
      openTimeDropdown = null;
    }
  });

  // Wandelt ein Date-Objekt in das yyyy-mm-dd-Format der Input-Felder
  function formatDateInput(dateObj) {
    return [
      dateObj.getFullYear(),
      String(dateObj.getMonth() + 1).padStart(2, "0"),
      String(dateObj.getDate()).padStart(2, "0")
    ].join("-");
  }

  // Wandelt ein Date-Objekt in ein hh:mm-Format um
  function formatTimeInput(dateObj) {
    return [
      String(dateObj.getHours()).padStart(2, "0"),
      String(dateObj.getMinutes()).padStart(2, "0")
    ].join(":");
  }

  // Exponiert Initialisierung für unterschiedliche Locales
  window.initCalendar = function initCalendar(locale = "de") {
    const calendarEl = document.getElementById("calendar");
    const csrfInput = document.getElementById("csrfToken");
    if (!calendarEl || !csrfInput) {
      console.warn("Kalender oder CSRF-Token nicht gefunden, initCalendar wird abgebrochen.");
      return;
    }

    // Alle genutzten DOM-Elemente zentral sammeln, damit keine getElementById-Orgien nötig sind
    const dom = {
      csrfToken: csrfInput.value,
      eventPopup: document.getElementById("eventPopup"),
      openPopupBtn: document.getElementById("openPopup"),
      secondaryPopupBtns: document.querySelectorAll("[data-calendar-open]"),
      closePopupBtn: document.getElementById("closePopup"),
      currentUserId: document.getElementById("currentUserId")?.value || "",
      eventTitle: document.getElementById("eventTitle"),
      eventStartDate: document.getElementById("eventStartDate"),
      eventStartTime: document.getElementById("eventStartTime"),
      eventEndDate: document.getElementById("eventEndDate"),
      eventEndTime: document.getElementById("eventEndTime"),
      eventDescription: document.getElementById("eventDescription"),
      eventRepeat: document.getElementById("eventRepeat"),
      eventRepeatUntil: document.getElementById("eventRepeatUntil"),
      submitBtn: document.getElementById("eventSubmitBtn"),
      eventDeleteBtn: document.getElementById("eventDeleteBtn"),
      repeatOptions: document.getElementById("repeatOptions"),
      toggleRepeatOptions: document.getElementById("toggleRepeatOptions"),
      allInGroupCheckbox: document.getElementById("allInGroupCheckbox"),
      allInGroupContainer: document.getElementById("allInGroupContainer"),
      allDayBtn: document.getElementById("allDayBtn"),
      eventForm: document.getElementById("eventForm"),
      startTimePickerBtn: document.getElementById("startTimePickerBtn"),
      startTimeDropdown: document.getElementById("startTimeDropdown"),
      endTimePickerBtn: document.getElementById("endTimePickerBtn"),
      endTimeDropdown: document.getElementById("endTimeDropdown"),
      icsUploadInput: document.getElementById("icsUpload"),
      exportForm: document.getElementById("exportForm")
    };

    // Zentraler UI-Zustand für Modal/All-Day/ID-Verwaltung
    const state = {
      isAllDay: false,
      editMode: false,
      editingEventId: null
    };

    // Schaltet zwischen Einzeltermin und Ganztagmodus und passt Inputs/Buttons an
    const setAllDayMode = active => {
      if (!dom.allDayBtn || !dom.eventStartTime || !dom.eventEndTime) {
        return;
      }
      state.isAllDay = active;
      const displayStyle = active ? "none" : "";
      dom.eventStartTime.style.display = displayStyle;
      dom.eventEndTime.style.display = displayStyle;
      if (dom.startTimePickerBtn) {
        dom.startTimePickerBtn.style.display = displayStyle;
      }
      if (dom.endTimePickerBtn) {
        dom.endTimePickerBtn.style.display = displayStyle;
      }
      if (active) {
        dom.eventStartTime.value = "00:00";
        dom.eventEndTime.value = "23:59";
        dom.allDayBtn.classList.add("calendar-toggle-active");
        dom.allDayBtn.textContent = "Ganztägig ✓";
      } else {
        dom.allDayBtn.classList.remove("calendar-toggle-active");
        dom.allDayBtn.textContent = "Ganztägig";
      }
    };

    setupTimePicker(dom.startTimePickerBtn, dom.eventStartTime, dom.startTimeDropdown);
    setupTimePicker(dom.endTimePickerBtn, dom.eventEndTime, dom.endTimeDropdown);
    if (dom.allDayBtn) {
      dom.allDayBtn.addEventListener("click", () => setAllDayMode(!state.isAllDay));
    }

    // Sorgt für weiches Einblenden des Modals (Tailwind-Klassen)
    const showPopup = () => {
      if (!dom.eventPopup) {
        return;
      }
      dom.eventPopup.classList.remove("hidden");
      setTimeout(() => dom.eventPopup.classList.add("opacity-100"), 10);
    };

    // Rückwärtsanimation + Reset aller Modus-Zustände
    const hidePopup = () => {
      if (!dom.eventPopup) {
        return;
      }
      dom.eventPopup.classList.remove("opacity-100");
      setTimeout(() => dom.eventPopup.classList.add("hidden"), 200);
      state.editMode = false;
      state.editingEventId = null;
      setAllDayMode(false);
    };

    // "Wiederholen bis" darf nie vor dem Startdatum liegen
    const updateRepeatUntilMin = () => {
      if (!dom.eventRepeatUntil) {
        return;
      }
      dom.eventRepeatUntil.min = dom.eventStartDate?.value || "";
    };
    if (dom.eventStartDate) {
      dom.eventStartDate.addEventListener("change", updateRepeatUntilMin);
    }

    if (dom.toggleRepeatOptions && dom.repeatOptions) {
      dom.toggleRepeatOptions.addEventListener("click", () => {
        const willShow = dom.repeatOptions.classList.contains("hidden");
        dom.repeatOptions.classList.toggle("hidden", !willShow);
        dom.toggleRepeatOptions.classList.toggle("calendar-toggle-active", willShow);
      });
    }

    // Blendt die Serien-Checkbox nur ein, wenn mehrere Events derselben Gruppe zum Nutzer gehören
    const handleGroupCheckboxVisibility = eventData => {
      if (!dom.allInGroupCheckbox || !dom.allInGroupContainer) {
        return;
      }
      dom.allInGroupCheckbox.checked = false;
      if (eventData?.group) {
        fetch(`/api/calendar-events/?group=${encodeURIComponent(eventData.group)}`)
          .then(response => response.json())
          .then(eventsWithGroup => {
            const sameUserEvents = eventsWithGroup.filter(ev => ev.user_id === eventData.user_id);
            const showCheckbox = Array.isArray(sameUserEvents) && sameUserEvents.length > 1;
            dom.allInGroupContainer.classList.toggle("hidden", !showCheckbox);
          })
          .catch(() => dom.allInGroupContainer.classList.add("hidden"));
      } else {
        dom.allInGroupContainer.classList.add("hidden");
      }
    };

    // Beim Bearbeiten sollen Wiederholungsoptionen nicht sichtbar/veränderbar sein
    const setRepeatUIForMode = () => {
      if (!dom.toggleRepeatOptions || !dom.repeatOptions) {
        return;
      }
      if (state.editMode) {
        dom.toggleRepeatOptions.classList.add("hidden");
        dom.repeatOptions.classList.add("hidden");
      } else {
        dom.toggleRepeatOptions.classList.remove("hidden");
        dom.repeatOptions.classList.add("hidden");
        dom.toggleRepeatOptions.classList.remove("calendar-toggle-active");
      }
    };

    // Zentraler Einstieg für "Termin erstellen/bearbeiten" inkl. Feld-Befüllung und UI-Resets
    const openEventPopup = (mode, eventData = null) => {
      state.editMode = mode === "edit";
      state.editingEventId = eventData?.id ?? null;
      setAllDayMode(false);

      if (dom.eventTitle) {
        dom.eventTitle.value = eventData?.title || "";
      }

      if (dom.eventStartDate) {
        if (eventData?.start) {
          const startDate = new Date(eventData.start);
          dom.eventStartDate.value = formatDateInput(startDate);
          if (dom.eventStartTime) {
            dom.eventStartTime.value = formatTimeInput(startDate);
          }
        } else {
          dom.eventStartDate.value = "";
          if (dom.eventStartTime) {
            dom.eventStartTime.value = "";
          }
        }
      }

      if (dom.eventEndDate) {
        if (eventData?.end) {
          const endDate = new Date(eventData.end);
          dom.eventEndDate.value = formatDateInput(endDate);
          if (dom.eventEndTime) {
            dom.eventEndTime.value = formatTimeInput(endDate);
          }
        } else {
          dom.eventEndDate.value = "";
          if (dom.eventEndTime) {
            dom.eventEndTime.value = "";
          }
        }
      }

      const isAllDayEvent = Boolean(eventData && (eventData.all_day || eventData.allDay));
      if (isAllDayEvent) {
        setAllDayMode(true);
      }

      if (dom.eventDescription) {
        dom.eventDescription.value = eventData?.description || "";
      }
      if (dom.eventRepeat) {
        dom.eventRepeat.value = eventData?.repeat || "none";
      }
      if (dom.eventRepeatUntil) {
        dom.eventRepeatUntil.value = eventData?.repeat_until ? eventData.repeat_until.substring(0, 10) : "";
      }
      if (dom.submitBtn) {
        dom.submitBtn.textContent = state.editMode ? "Speichern" : "Hinzufügen";
      }
      const eventPopupTitle = document.getElementById("eventPopupTitle");
      if (eventPopupTitle) {
        eventPopupTitle.textContent = state.editMode ? "Termin bearbeiten" : "Termin erstellen";
      }

      updateRepeatUntilMin();
      setRepeatUIForMode();
      handleGroupCheckboxVisibility(eventData);

      if (dom.eventDeleteBtn) {
        const isOwnEvent = state.editMode && eventData?.user_id === dom.currentUserId;
        dom.eventDeleteBtn.classList.toggle("hidden", !isOwnEvent);
      }

      showPopup();
    };

    // Ermittelt ganztägige Events auch ohne explizites Flag
    function isAllDayByTime(eventObj) {
      if (!eventObj) {
        return false;
      }
      const extended = eventObj.extendedProps || {};
      if (eventObj.allDay || extended.all_day || extended.is_all_day) {
        return true;
      }
      const startDate = eventObj.start;
      const endDate = eventObj.end;
      if (!startDate) {
        return false;
      }
      const startsMidnight = startDate.getHours() === 0 && startDate.getMinutes() === 0;
      if (!startsMidnight) {
        return false;
      }
      if (!endDate) {
        return true;
      }
      const durationMs = endDate.getTime() - startDate.getTime();
      const approxFullDay = durationMs >= 23 * 60 * 60 * 1000;
      const zeroDuration = durationMs <= 60 * 1000;
      const endsLate = endDate.getHours() === 23 && endDate.getMinutes() >= 59;
      const endsMidnightNextDay = endDate.getHours() === 0 && endDate.getMinutes() === 0 && endDate.getDate() !== startDate.getDate();
      return approxFullDay || zeroDuration || endsLate || endsMidnightNextDay;
    }

    // FullCalendar-Instanz inkl. Backend-Integration via REST
    const calendar = new FullCalendar.Calendar(calendarEl, {
      initialView: "dayGridMonth",
      headerToolbar: {
        left: "prev,next today",
        center: "title",
        right: "dayGridMonth,timeGridWeek,timeGridDay"
      },
      height: "auto",
      contentHeight: "auto",
      aspectRatio: 1.75,
      expandRows: false,
      handleWindowResize: true,
      locale,
      allDaySlot: false,
      editable: false,
      events: "/api/calendar-events/",
      eventClick: info => {
        fetch(`/api/calendar-events/${info.event.id}/`, {
          method: "GET",
          headers: { "X-CSRFToken": dom.csrfToken }
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
      dateClick: info => {
        openEventPopup("create", { start: info.dateStr });
      },
      eventDidMount: info => {
        const description = info.event.extendedProps.description || "";
        const titleEl = info.el.querySelector(".fc-event-title");
        if (titleEl) {
          titleEl.innerHTML = `${info.event.title}<br><span class="event-description">${description}</span>`;
        }
        const isAllDayEvent = Boolean(
          info.event.extendedProps?.all_day ||
          info.event.allDay ||
          isAllDayByTime(info.event)
        );
        if (isAllDayEvent) {
          info.el.classList.add("calendar-event-all-day");
          const timeEl = info.el.querySelector(".fc-event-time");
          if (timeEl) {
            timeEl.remove();
          }
        }
        if (info.event.extendedProps.is_global) {
          info.el.classList.add("global-event");
        }
      }
    });
    calendar.render();

    // Alle Buttons registrieren, die den Kalender-Dialog öffnen sollen
    const bindOpenPopupTriggers = () => {
      const triggers = [];
      if (dom.openPopupBtn) {
        triggers.push(dom.openPopupBtn);
      }
      if (dom.secondaryPopupBtns?.length) {
        dom.secondaryPopupBtns.forEach(btn => triggers.push(btn));
      }
      triggers.forEach(btn => {
        btn.addEventListener("click", () => openEventPopup("create"));
      });
    };

    bindOpenPopupTriggers();
    if (dom.closePopupBtn) {
      dom.closePopupBtn.addEventListener("click", hidePopup);
    }

    if (dom.eventForm) {
      // Form-Submit validiert Eingaben und schickt sie an die API
      dom.eventForm.addEventListener("submit", event => {
        event.preventDefault();
        const errors = [];
        if (!dom.eventTitle?.value.trim()) {
          errors.push("Bitte gib einen Titel ein.");
        }
        if (!dom.eventStartDate?.value) {
          errors.push("Bitte wähle ein Startdatum.");
        }
        if (!state.isAllDay && !dom.eventStartTime?.value) {
          errors.push("Bitte wähle eine Startzeit.");
        }
        if (dom.eventEndDate?.value && !state.isAllDay && !dom.eventEndTime?.value) {
          errors.push("Bitte wähle eine Endzeit.");
        }
        if (dom.eventEndDate?.value && dom.eventStartDate?.value && dom.eventEndDate.value < dom.eventStartDate.value) {
          errors.push("Endedatum darf nicht vor dem Startdatum liegen.");
        }
        if (
          dom.eventEndDate?.value &&
          dom.eventStartDate?.value &&
          dom.eventEndDate.value === dom.eventStartDate.value &&
          !state.isAllDay &&
          dom.eventEndTime?.value &&
          dom.eventStartTime?.value &&
          dom.eventEndTime.value < dom.eventStartTime.value
        ) {
          errors.push("Endzeit darf nicht vor der Startzeit liegen.");
        }
        if (errors.length > 0) {
          alert(errors.join("\n"));
          return;
        }

        let start = "";
        if (dom.eventStartDate?.value && (state.isAllDay || dom.eventStartTime?.value)) {
          const timePart = state.isAllDay ? "00:00" : dom.eventStartTime.value;
          start = `${dom.eventStartDate.value}T${timePart}`;
        }
        let end = null;
        if (dom.eventEndDate?.value && (state.isAllDay || dom.eventEndTime?.value)) {
          const timePart = state.isAllDay ? "23:59" : dom.eventEndTime.value;
          end = `${dom.eventEndDate.value}T${timePart}`;
        }

        const payload = {
          title: dom.eventTitle?.value,
          start,
          end,
          description: dom.eventDescription?.value,
          repeat: dom.eventRepeat?.value,
          repeat_until: dom.eventRepeatUntil?.value,
          all_in_group: dom.allInGroupCheckbox?.checked || false
        };
        let url = "/api/calendar-events/";
        let method = "POST";
        if (state.editMode && state.editingEventId) {
          url = `/api/calendar-events/${state.editingEventId}/`;
          method = "PUT";
        }
        fetch(url, {
          method,
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": dom.csrfToken
          },
          body: JSON.stringify(payload)
        })
          .then(response => response.json())
          .then(data => {
            if (data.message) {
              alert(state.editMode ? "Event gespeichert!" : "Event hinzugefügt!");
              calendar.refetchEvents();
              hidePopup();
            } else {
              alert("Fehler: " + data.error);
            }
          })
          .catch(error => console.error("Fehler beim Speichern des Events:", error));
      });
    }

    if (dom.eventDeleteBtn) {
      // Löschen-Button löscht entweder Einzeltermin oder komplette Serie (falls aktiviert)
      dom.eventDeleteBtn.addEventListener("click", () => {
        if (!state.editingEventId) {
          return;
        }
        let url = `/api/calendar-events/${state.editingEventId}/`;
        const params = [];
        if (dom.allInGroupCheckbox?.checked) {
          params.push("all_in_group=true");
        }
        if (params.length > 0) {
          url += "?" + params.join("&");
        }
        const deleteWarning = dom.allInGroupCheckbox?.checked ? " (Alle Termine dieser Serie werden gelöscht!)" : "";
        if (confirm("Willst du dieses Event wirklich löschen?" + deleteWarning)) {
          fetch(url, {
            method: "DELETE",
            headers: { "X-CSRFToken": dom.csrfToken }
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
    }

    if (dom.eventPopup) {
      dom.eventPopup.addEventListener("click", event => {
        if (event.target === dom.eventPopup) {
          hidePopup();
        }
      });
    }
  };
})();
