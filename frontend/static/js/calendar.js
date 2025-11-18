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

  function parseIsoDate(value) {
    if (!value) {
      return null;
    }
    const parsed = new Date(value);
    if (!Number.isNaN(parsed?.getTime?.())) {
      return parsed;
    }
    // Browser-Kompatibilität: Bricht Mikrosekunden auf 3 Stellen herunter
    const normalized = value.replace(/(\.\d{3})\d+/, "$1");
    const fallback = new Date(normalized);
    return Number.isNaN(fallback?.getTime?.()) ? null : fallback;
  }

  function getIsoTime(inputEl, fallbackElementId) {
    if (inputEl?.value) {
      return inputEl.value;
    }
    if (fallbackElementId) {
      const fallbackEl = document.getElementById(fallbackElementId);
      if (fallbackEl) {
        if (fallbackEl.value) {
          return fallbackEl.value;
        }
        if (fallbackEl.textContent) {
          return fallbackEl.textContent.trim();
        }
      }
    }
    return "";
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
      eventStartTimeField: document.getElementById("eventStartTimeField"),
      eventEndDate: document.getElementById("eventEndDate"),
      eventEndTime: document.getElementById("eventEndTime"),
      eventEndTimeField: document.getElementById("eventEndTimeField"),
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
      exportForm: document.getElementById("exportForm"),
      readOnlyNotice: document.getElementById("calendarReadOnlyNotice"),
      toast: document.getElementById("calendarToast"),
      toastTitle: document.getElementById("calendarToastTitle"),
      toastMessage: document.getElementById("calendarToastMessage"),
      toastCloseBtn: document.getElementById("calendarToastClose"),
      confirmModal: document.getElementById("calendarConfirm"),
      confirmMessage: document.getElementById("calendarConfirmMessage"),
      confirmSubmitBtn: document.getElementById("calendarConfirmSubmit"),
      confirmCancelBtn: document.getElementById("calendarConfirmCancel"),
      confirmCloseBtn: document.getElementById("calendarConfirmClose"),
      translationsEl: document.getElementById("calendarTranslations")
    };

    const hasDomTranslationEl = Boolean(dom.translationsEl);
    let translationDatasetCache = null;
    let translationDatasetInitialized = false;
    const resolveTranslationDataset = () => {
      if (!translationDatasetInitialized) {
        translationDatasetInitialized = true;
        const sourceEl = document.getElementById("calendarTranslations");
        if (!sourceEl || !sourceEl.dataset) {
          translationDatasetCache = null;
        } else {
          translationDatasetCache = sourceEl.dataset;
        }
      }
      return translationDatasetCache;
    };

    const getTranslation = (key, fallback = "") => {
      const dataset = resolveTranslationDataset();
      if (!dataset) {
        return fallback;
      }
      return dataset[key] || fallback;
    };

    // (Popup uses native inputs; no localization helpers required here)

    // Zentraler UI-Zustand für Modal/All-Day/ID-Verwaltung
    const state = {
      isAllDay: false,
      editMode: false,
      editingEventId: null,
      readOnlyMode: false
    };

    // Toast-Komponenten
    const toastTypeClasses = [
      "calendar-toast--success",
      "calendar-toast--error",
      "calendar-toast--info",
      "calendar-toast--warning"
    ];
    const defaultToastTitles = {
      success: "Erfolg",
      error: "Fehler",
      info: "Hinweis",
      warning: "Hinweis"
    };
    let toastTimeoutId = null;

    const hideToast = () => {
      if (!dom.toast) {
        return;
      }
      dom.toast.classList.add("hidden");
      dom.toast.setAttribute("aria-hidden", "true");
      if (toastTimeoutId) {
        clearTimeout(toastTimeoutId);
        toastTimeoutId = null;
      }
    };

    const showToast = ({ type = "info", title = "", message = "", duration = 4500 } = {}) => {
      if (!dom.toast || !dom.toastTitle || !dom.toastMessage) {
        if (typeof window !== "undefined" && typeof window.alert === "function") {
          window.alert(message || title || "");
        }
        return;
      }
      const normalizedType = ["success", "error", "warning", "info"].includes(type) ? type : "info";
      toastTypeClasses.forEach(cls => dom.toast.classList.remove(cls));
      dom.toast.classList.add(`calendar-toast--${normalizedType}`);
      dom.toastTitle.textContent = title || defaultToastTitles[normalizedType] || "";
      dom.toastMessage.textContent = message || "";
      dom.toast.classList.remove("hidden");
      dom.toast.setAttribute("aria-hidden", "false");
      if (toastTimeoutId) {
        clearTimeout(toastTimeoutId);
      }
      if (duration > 0) {
        toastTimeoutId = window.setTimeout(() => {
          hideToast();
        }, duration);
      }
    };

    if (dom.toastCloseBtn) {
      dom.toastCloseBtn.addEventListener("click", () => hideToast());
    }

    const showConfirmDialog = ({
      message = "",
      confirmLabel = "OK",
      cancelLabel = "Abbrechen"
    } = {}) => {
      if (!dom.confirmModal || !dom.confirmMessage) {
        if (typeof window !== "undefined" && typeof window.confirm === "function") {
          return Promise.resolve(window.confirm(message || ""));
        }
        return Promise.resolve(false);
      }

      dom.confirmMessage.textContent = message || "";
      if (dom.confirmSubmitBtn) {
        dom.confirmSubmitBtn.textContent = confirmLabel;
      }
      if (dom.confirmCancelBtn) {
        dom.confirmCancelBtn.textContent = cancelLabel;
      }
      dom.confirmModal.classList.remove("hidden");
      dom.confirmModal.setAttribute("aria-hidden", "false");

      return new Promise(resolve => {
        const cleanup = result => {
          if (dom.confirmModal) {
            dom.confirmModal.classList.add("hidden");
            dom.confirmModal.setAttribute("aria-hidden", "true");
            dom.confirmModal.removeEventListener("click", onOverlayClick, true);
          }
          document.removeEventListener("keydown", onEsc, true);
          dom.confirmSubmitBtn?.removeEventListener("click", onConfirm, true);
          dom.confirmCancelBtn?.removeEventListener("click", onCancel, true);
          dom.confirmCloseBtn?.removeEventListener("click", onCancel, true);
          resolve(result);
        };

        const onConfirm = () => cleanup(true);
        const onCancel = () => cleanup(false);
        const onOverlayClick = event => {
          if (!event.target.closest || !event.target.closest(".calendar-confirm__panel")) {
            cleanup(false);
          }
        };
        const onEsc = event => {
          if (event.key === "Escape" || event.key === "Esc") {
            cleanup(false);
          }
        };

        dom.confirmModal.addEventListener("click", onOverlayClick, true);
        document.addEventListener("keydown", onEsc, true);
        dom.confirmSubmitBtn?.addEventListener("click", onConfirm, true);
        dom.confirmCancelBtn?.addEventListener("click", onCancel, true);
        dom.confirmCloseBtn?.addEventListener("click", onCancel, true);
      });
    };

    // Flyout-Element zum Anzeigen von vollständigem Titel + Beschreibung bei Hover
    const flyoutEl = document.createElement("div");
    flyoutEl.className = "calendar-event-flyout hidden";
    document.body.appendChild(flyoutEl);

    // Kleiner HTML-Escape-Helfer, um Markup-Injektion zu vermeiden
    function escapeHtml(str) {
      if (!str) return "";
      return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    // Schaltet zwischen Einzeltermin und Ganztagmodus und passt Inputs/Buttons an
    const setAllDayMode = active => {
      if (!dom.allDayBtn || !dom.eventStartTime || !dom.eventEndTime) {
        return;
      }
      state.isAllDay = active;
      const displayStyle = active ? "none" : "";
      const toggleTimeField = (fieldEl, inputEl, pickerBtn, dropdownEl) => {
        if (fieldEl) {
          fieldEl.style.display = displayStyle;
        } else if (inputEl) {
          inputEl.style.display = displayStyle;
        }
        if (!fieldEl && pickerBtn) {
          pickerBtn.style.display = displayStyle;
        }
        if (dropdownEl) {
          dropdownEl.classList.add("hidden");
        }
      };
      toggleTimeField(dom.eventStartTimeField, dom.eventStartTime, dom.startTimePickerBtn, dom.startTimeDropdown);
      toggleTimeField(dom.eventEndTimeField, dom.eventEndTime, dom.endTimePickerBtn, dom.endTimeDropdown);
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

    const toggleElementDisabledState = (element, readOnly) => {
      if (!element) {
        return;
      }
      element.disabled = readOnly;
      element.classList.toggle("calendar-field-disabled", readOnly);
    };

    const setFormReadOnly = readOnly => {
      state.readOnlyMode = readOnly;
      const fields = [
        dom.eventTitle,
        dom.eventStartDate,
        dom.eventStartTime,
        dom.eventEndDate,
        dom.eventEndTime,
        dom.eventDescription,
        dom.eventRepeat,
        dom.eventRepeatUntil,
        dom.allInGroupCheckbox
      ];
      fields.forEach(field => toggleElementDisabledState(field, readOnly));
      if (dom.allDayBtn) {
        dom.allDayBtn.disabled = readOnly;
        dom.allDayBtn.classList.toggle("calendar-toggle-disabled", readOnly);
      }
      if (dom.submitBtn) {
        dom.submitBtn.classList.toggle("hidden", readOnly);
      }
      if (dom.readOnlyNotice) {
        dom.readOnlyNotice.classList.toggle("hidden", !readOnly);
      }
    };

    // Sorgt für weiches Einblenden des Modals (Tailwind-Klassen)
    const showPopup = () => {
      if (!dom.eventPopup) {
        return;
      }
      dom.eventPopup.classList.remove("hidden");
      setTimeout(() => dom.eventPopup.classList.add("opacity-100"), 10);
      // Escape schließen aktivieren
      try { document.addEventListener('keydown', closeOnEsc); } catch (e) { /* ignore */ }
    };

    // Rückwärtsanimation + Reset aller Modus-Zustände
    const hidePopup = () => {
      if (!dom.eventPopup) {
        return;
      }
      dom.eventPopup.classList.remove("opacity-100");
      // UI-State erst zurücksetzen, wenn das Modal weg ist
      setTimeout(() => {
        dom.eventPopup.classList.add("hidden");
        state.editMode = false;
        state.editingEventId = null;
        setFormReadOnly(false);
        setAllDayMode(false);
        try { document.removeEventListener('keydown', closeOnEsc); } catch (e) { /* ignore */ }
      }, 200);
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

    // popup inputs remain standard HTML date/time inputs

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
      if (state.readOnlyMode || state.editMode) {
        dom.toggleRepeatOptions.classList.add("hidden");
        dom.repeatOptions.classList.add("hidden");
      } else {
        dom.toggleRepeatOptions.classList.remove("hidden");
        dom.repeatOptions.classList.add("hidden");
        dom.toggleRepeatOptions.classList.remove("calendar-toggle-active");
      }
    };

    // Zentraler Einstieg für "Termin erstellen/bearbeiten" inkl. Feld-Befüllung und UI-Resets
    const openEventPopup = (mode, eventData = null, options = {}) => {
      const readOnlyMode = Boolean(options.readOnly);
      state.editMode = mode === "edit" && !readOnlyMode;
      state.editingEventId = eventData?.id ?? null;
      setAllDayMode(false);
      setFormReadOnly(readOnlyMode);

      if (dom.eventTitle) {
        dom.eventTitle.value = eventData?.title || "";
      }

      let parsedStartDate = null;
      if (dom.eventStartDate) {
        parsedStartDate = parseIsoDate(eventData?.start);
        if (parsedStartDate) {
          dom.eventStartDate.value = formatDateInput(parsedStartDate);
          if (dom.eventStartTime) {
            dom.eventStartTime.value = formatTimeInput(parsedStartDate);
          }
        } else {
          dom.eventStartDate.value = "";
          if (dom.eventStartTime) {
            dom.eventStartTime.value = "";
          }
        }
      }

      if (dom.eventEndDate) {
        const hasEndValue = Boolean(eventData?.end);
        const parsedEndDate = parseIsoDate(eventData?.end);
        if (parsedEndDate) {
          dom.eventEndDate.value = formatDateInput(parsedEndDate);
          if (dom.eventEndTime) {
            dom.eventEndTime.value = formatTimeInput(parsedEndDate);
          }
        } else if (hasEndValue) {
          const isoValue = String(eventData.end);
          const datePart = isoValue.slice(0, 10);
          const timePart = isoValue.split("T")[1] || "";
          dom.eventEndDate.value = datePart;
          if (dom.eventEndTime) {
            dom.eventEndTime.value = timePart.slice(0, 5);
          }
        } else {
          dom.eventEndDate.value = parsedStartDate ? formatDateInput(parsedStartDate) : "";
          if (dom.eventEndTime) {
            dom.eventEndTime.value = dom.eventStartTime?.value || "";
          }
        }
      }

      // Herausfinden, ob es sich um ein ganztägiges Event handelt
      const inferAllDayFromTimes = (evt) => {
        if (!evt) return false;
        if (evt.all_day || evt.allDay || evt.is_all_day) return true;
        try {
          const s = evt.start ? new Date(evt.start) : null;
          const e = evt.end ? new Date(evt.end) : null;
          if (!s) return false;
          const startsMidnight = s.getHours() === 0 && s.getMinutes() === 0;
          if (!startsMidnight) return false;
          if (!e) return true;
          const durationMs = e.getTime() - s.getTime();
          const approxFullDay = durationMs >= 23 * 60 * 60 * 1000;
          const endsLate = e.getHours() === 23 && e.getMinutes() >= 59;
          const endsMidnightNextDay = e.getHours() === 0 && e.getMinutes() === 0 && e.getDate() !== s.getDate();
          return approxFullDay || endsLate || endsMidnightNextDay;
        } catch (err) {
          return false;
        }
      };

      const isAllDayEvent = inferAllDayFromTimes(eventData);
      setAllDayMode(Boolean(isAllDayEvent));

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
        if (readOnlyMode) {
          eventPopupTitle.textContent = "Termin anzeigen";
        } else {
          eventPopupTitle.textContent = state.editMode ? "Termin bearbeiten" : "Termin erstellen";
        }
      }

      updateRepeatUntilMin();
      setRepeatUIForMode();
      if (!readOnlyMode) {
        handleGroupCheckboxVisibility(eventData);
      } else if (dom.allInGroupContainer) {
        dom.allInGroupContainer.classList.add("hidden");
      }

      if (dom.eventDeleteBtn) {
        // Ensure we compare IDs as strings to avoid type-mismatch (number vs string)
        const eventUserId = eventData?.user_id == null ? null : String(eventData.user_id);
        const currentUserId = dom.currentUserId == null ? "" : String(dom.currentUserId);
        const isOwnEvent = !readOnlyMode && state.editMode && eventUserId && (eventUserId === currentUserId);
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
        right: "dayGridMonth,timeGridWeek"
      },
      contentHeight: "auto",
      /* aspectRatio: 2.5, // Höhe = Breite / aspectRatio */
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
            const isReadOnly = Boolean(data.is_global);
            openEventPopup(isReadOnly ? "view" : "edit", data, { readOnly: isReadOnly });
          });
      },
      dateClick: info => {
        openEventPopup("create", { start: info.dateStr });
      },
      eventDidMount: info => {
        const descriptionText = (info.event.extendedProps.description || "").trim();
        if (descriptionText) {
          info.el.setAttribute("data-event-description", descriptionText);
        } else {
          info.el.removeAttribute("data-event-description");
        }
        const frameEl = info.el.querySelector(".fc-event-main-frame");
        if (frameEl && !frameEl.querySelector(".calendar-event-indicator")) {
          const indicator = document.createElement("span");
          indicator.className = "calendar-event-indicator";
          if (info.event.extendedProps.is_global) {
            indicator.classList.add("calendar-event-indicator-global");
          } else {
            indicator.classList.add("calendar-event-indicator-private");
          }
          frameEl.prepend(indicator);
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
        // Formatiere die Zeit entsprechend der aktuellen Locale (de/en/es/fr)
        try {
          const timeEl = info.el.querySelector(".fc-event-time");
          if (timeEl && !isAllDayEvent) {
            const start = info.event.start instanceof Date ? info.event.start : new Date(info.event.start);
            if (!isNaN(start.getTime())) {
              const df = new Intl.DateTimeFormat(locale, { hour: '2-digit', minute: '2-digit' });
              timeEl.textContent = df.format(start);
            }
          }
        } catch (e) {
          // Ignoriere nicht-kritische Fehler bei der Zeit-Formatierung
        }
        if (info.event.extendedProps.is_global) {
          info.el.classList.add("global-event");
        }
        // Hänge Hover-/Focus-Handler an, um Flyout mit vollständigem Titel und Beschreibung anzuzeigen
        try {
          const title = info.event.title || "";
          const description = info.event.extendedProps?.description || "";
          info.el.dataset.eventTitle = title;
          info.el.dataset.eventDescription = description;

          const showFlyout = () => {
            flyoutEl.innerHTML = `
              <div class="calendar-event-flyout__title">${escapeHtml(title)}</div>
              <div class="calendar-event-flyout__desc">${escapeHtml(description)}</div>
            `;
            flyoutEl.classList.remove("hidden");
            // reset positioning so measurements work
            flyoutEl.style.left = "0px";
            flyoutEl.style.top = "0px";
            flyoutEl.style.display = "block";
            const rect = info.el.getBoundingClientRect();
            const flyoutW = flyoutEl.offsetWidth;
            const flyoutH = flyoutEl.offsetHeight;
            let left = window.scrollX + rect.left;
            if (left + flyoutW + 8 > window.scrollX + window.innerWidth) {
              left = window.scrollX + window.innerWidth - flyoutW - 8;
            }
            let top = window.scrollY + rect.bottom + 8;
            if (top + flyoutH > window.scrollY + window.innerHeight) {
              top = window.scrollY + rect.top - flyoutH - 8;
            }
            flyoutEl.style.left = left + "px";
            flyoutEl.style.top = top + "px";
          };

          const hideFlyout = () => {
            flyoutEl.classList.add("hidden");
            flyoutEl.style.display = "none";
          };

          info.el.addEventListener("mouseenter", showFlyout);
          info.el.addEventListener("mouseleave", hideFlyout);
          info.el.addEventListener("focus", showFlyout);
          info.el.addEventListener("blur", hideFlyout);
        } catch (e) {
          // Ignoriere nicht-kritische Fehler
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
        if (state.readOnlyMode) {
          showToast({
            type: "warning",
            title: getTranslation("toastReadonlyTitle", "Nur Anzeige"),
            message: getTranslation("toastReadonlyMessage", "Öffentliche Termine können nicht bearbeitet werden."),
            duration: 5000
          });
          return;
        }
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
        const inferredEndDate = dom.eventEndDate?.value || (dom.eventEndTime?.value ? dom.eventStartDate?.value : "");
        if (inferredEndDate && !state.isAllDay && !dom.eventEndTime?.value) {
          errors.push("Bitte wähle eine Endzeit.");
        }
        if (inferredEndDate && dom.eventStartDate?.value && inferredEndDate < dom.eventStartDate.value) {
          errors.push("Endedatum darf nicht vor dem Startdatum liegen.");
        }
        if (
          inferredEndDate &&
          dom.eventStartDate?.value &&
          inferredEndDate === dom.eventStartDate.value &&
          !state.isAllDay
        ) {
          const startIso = getIsoTime(dom.eventStartTime, 'eventStartTimeIso');
          const endIso = getIsoTime(dom.eventEndTime, 'eventEndTimeIso');
          if (startIso && endIso && endIso < startIso) {
            errors.push("Endzeit darf nicht vor der Startzeit liegen.");
          }
        }
        if (errors.length > 0) {
          showToast({
            type: "error",
            title: getTranslation("toastValidationTitle", "Bitte Eingaben prüfen"),
            message: errors.join("\n")
          });
          return;
        }

        let start = "";
        if (dom.eventStartDate?.value && (state.isAllDay || dom.eventStartTime?.value)) {
          const timePart = state.isAllDay ? "00:00" : dom.eventStartTime.value;
          start = `${dom.eventStartDate.value}T${timePart}`;
        }
        let end = null;
        const resolvedEndDate = dom.eventEndDate?.value || (state.isAllDay || dom.eventEndTime?.value ? dom.eventStartDate?.value : "");
        if (resolvedEndDate && (state.isAllDay || dom.eventEndTime?.value)) {
          const timePart = state.isAllDay ? "23:59" : dom.eventEndTime.value;
          end = `${resolvedEndDate}T${timePart}`;
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
              showToast({
                type: "success",
                title: state.editMode
                  ? getTranslation("toastUpdateSuccessTitle", "Termin aktualisiert")
                  : getTranslation("toastCreateSuccessTitle", "Termin erstellt"),
                message: data.message
              });
              calendar.refetchEvents();
              hidePopup();
            } else {
              showToast({
                type: "error",
                title: getTranslation("toastErrorTitle", "Fehler"),
                message: data.error ? String(data.error) : getTranslation("toastUnknownErrorMessage", "Unbekannter Fehler.")
              });
            }
          })
          .catch(error => {
            console.error("Fehler beim Speichern des Events:", error);
            showToast({
              type: "error",
              title: getTranslation("toastNetworkTitle", "Netzwerkfehler"),
              message: getTranslation("toastNetworkMessage", "Event konnte nicht gespeichert werden. Bitte versuche es erneut.")
            });
          });
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
        const confirmMessage = dom.allInGroupCheckbox?.checked
          ? "Willst du dieses Event wirklich löschen?\nAlle Termine dieser Serie werden ebenfalls gelöscht."
          : "Willst du dieses Event wirklich löschen?";
        showConfirmDialog({
          message: confirmMessage,
          confirmLabel: "Löschen",
          cancelLabel: "Abbrechen"
        }).then(confirmed => {
          if (!confirmed) {
            return;
          }
          fetch(url, {
            method: "DELETE",
            headers: { "X-CSRFToken": dom.csrfToken }
          })
            .then(response => response.json())
            .then(data => {
              if (data.success) {
                showToast({
                  type: "success",
                  title: getTranslation("toastDeleteSuccessTitle", "Gelöscht"),
                  message: getTranslation("toastDeleteSuccessMessage", "Event wurde gelöscht.")
                });
                calendar.refetchEvents();
                hidePopup();
              } else {
                showToast({
                  type: "error",
                  title: getTranslation("toastDeleteErrorTitle", "Löschen fehlgeschlagen"),
                  message: data.error ? String(data.error) : getTranslation("toastDeleteErrorMessage", "Unbekannter Fehler beim Löschen.")
                });
              }
            })
            .catch(error => {
              console.error("Fehler:", error);
              showToast({
                type: "error",
                title: getTranslation("toastNetworkTitle", "Netzwerkfehler"),
                message: getTranslation("toastDeleteNetworkMessage", "Event konnte nicht gelöscht werden. Bitte versuche es erneut.")
              });
            });
        });
      });
    }

    if (dom.eventPopup) {
      dom.eventPopup.addEventListener("click", event => {
        // Wenn der Klick außerhalb des Panels (z.B. auf das Overlay) ist, schließe das Popup
        if (!event.target.closest || !event.target.closest('.calendar-modal__panel')) {
          hidePopup();
        }
      });
    }

    // Handler wird bei Anzeige registriert; definiert hier für removeEventListener im hidePopup
    function closeOnEsc(e) {
      if (e.key === 'Escape' || e.key === 'Esc') {
        hidePopup();
      }
    }
  };
})();
