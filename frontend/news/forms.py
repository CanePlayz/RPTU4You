import re
from typing import Any, Callable, Final, Iterable, cast

from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.db.models import Q
from django.utils import timezone, translation
from django.utils.safestring import mark_safe
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from .models import (
    EmailVerteiler,
    ExterneWebsite,
    Fachschaft,
    InhaltsKategorie,
    InterneWebsite,
    Rundmail,
    Standort,
    TrustedAccountQuelle,
    TrustedUserApplication,
    User,
    Zielgruppe,
)
from .util.category_registry import (
    LanguageCode,
    get_audience_category_emoji_map,
    get_content_category_emoji_map,
    get_location_emoji_map,
    get_source_emoji_map,
)

# Setup, um Formular-Komponenten in wiederverwendbarer Weise zu definieren
EmojiFieldConfig = dict[str, Any]


EMOJI_FIELD_CONFIG: dict[str, EmojiFieldConfig] = {
    "standorte": {
        "label": _("Standorte"),
        "emoji_key": "locations",
        "queryset": lambda: Standort.objects.order_by("name"),
    },
    "inhaltskategorien": {
        "label": _("Kategorien"),
        "emoji_key": "categories",
        "queryset": lambda: InhaltsKategorie.objects.order_by("name"),
    },
    "zielgruppen": {
        "label": _("Zielgruppen"),
        "emoji_key": "audiences",
        "queryset": lambda: Zielgruppe.objects.order_by("name"),
    },
}


# Funktionen zum Aufbau von Emoji-Labels und Choices
def load_emoji_mappings() -> dict[str, dict[str, str]]:
    """Lädt die Emoji-Mappings für die angeforderten Kategorien über die Registry."""
    language_code = cast(LanguageCode, translation.get_language()) or ""
    return {
        "locations": get_location_emoji_map(language_code),
        "categories": get_content_category_emoji_map(language_code),
        "audiences": get_audience_category_emoji_map(language_code),
        "sources": get_source_emoji_map(language_code),
    }


def label_with_emoji(obj: Any, mapping: dict[str, str]) -> str:
    """Gibt den Objektnamen mit vorangestelltem Emoji zurück."""
    name = getattr(obj, "name", str(obj))
    emoji = mapping.get(name, "").strip()
    return f"{emoji} {name}" if emoji else name


def build_emoji_choices(
    objs: Iterable[Any], mapping: dict[str, str]
) -> list[tuple[Any, str]]:
    """Erzeugt Choice-Liste bestehend aus Tupeln aus Primärschlüssel und mit Emoji versehenen Label."""
    choices: list[tuple[Any, str]] = []
    for obj in objs:
        pk = getattr(obj, "pk", None)
        if pk is None:
            continue
        # Label mit Emoji erstellen
        label = label_with_emoji(obj, mapping)
        # Zusätzliche Behandlung für TrustedAccountQuelle
        if mapping.get(getattr(obj, "name", ""), "") == "":
            try:
                from .models import TrustedAccountQuelle

                if isinstance(obj, TrustedAccountQuelle):
                    name = getattr(obj, "name", str(obj))
                    label = f"👤 {name}"
            except Exception:
                pass

        choices.append((pk, label))
    return choices


# Hilfsfunktionen für Formulare
def ensure_widget_has_class(field: forms.Field, css_class: str = "form-field") -> None:
    """Sorgt dafür, dass die Widget-Attribute die gewünschte CSS-Klasse enthalten."""
    classes = field.widget.attrs.get("class", "").split()
    if css_class not in classes:
        classes.append(css_class)
        field.widget.attrs["class"] = " ".join(classes)


def get_localized_field_value(obj: Any, field_name: str) -> str:
    """Gibt den Wert des angegebenen Feldes in der aktuellen Sprache zurück."""
    language_code = get_language()
    translated_attr = f"{field_name}_{language_code}"
    translated_value = getattr(obj, translated_attr, None)
    return str(translated_value)


class UserCreationForm2(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "password1", "password2")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            ensure_widget_has_class(field)


# Formular für Benutzernamenänderung
class UsernameChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username"]
        labels = {"username": _("Benutzername")}
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": "form-field",
                    "required": True,
                }
            )
        }

    def clean_username(self) -> str:
        username = self.cleaned_data.get("username", "").strip()
        if not username:
            raise forms.ValidationError(
                _("Bitte gib einen gültigen Benutzernamen ein.")
            )
        if username == self.instance.username:
            raise forms.ValidationError(
                _("Dieser Benutzername wird bereits von dir verwendet.")
            )
        if (
            User.objects.filter(username__iexact=username)
            .exclude(pk=self.instance.pk)
            .exists()
        ):
            raise forms.ValidationError(_("Dieser Benutzername ist bereits vergeben."))
        return username


# Formular für Passwortänderung mit angepasstem Styling
class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            ensure_widget_has_class(field)


# Formular für Benutzerpräferenzen
class PreferencesForm(forms.ModelForm):
    # Verbindung zum User-Modell und Definition der Felder
    class Meta:
        model = User
        fields = [
            "standorte",
            "inhaltskategorien",
            "zielgruppen",
            "quellen",
            "include_rundmail",
            "include_sammel_rundmail",
        ]
        widgets = {
            "include_rundmail": forms.CheckboxInput(),
            "include_sammel_rundmail": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordered_sources: list[dict[str, str]] = []

        # Emojis über die Category Registry holen
        emoji_mappings = load_emoji_mappings()

        # Formularfelder konfigurieren
        for field_name in ("standorte", "inhaltskategorien", "zielgruppen"):
            config = EMOJI_FIELD_CONFIG[field_name]
            queryset_builder = cast(Callable[[], Iterable[Any]], config["queryset"])
            field = cast(forms.ModelMultipleChoiceField, self.fields[field_name])
            queryset = queryset_builder()
            objects = list(queryset)
            field.queryset = queryset
            field.label = config["label"]
            field.widget = forms.CheckboxSelectMultiple()
            field.choices = build_emoji_choices(
                objects, emoji_mappings[config["emoji_key"]]
            )

        # Quellen-Choices mit Emoji, ohne Rundmail-Objekte
        rundmail_filter = (
            Q(name__iexact="Rundmail")
            | Q(name__startswith="Sammel-Rundmail")
            | Q(name__startswith="Stellenangebote Sammel-Rundmail")
        )
        # Rundmails und Sammel-Rundmails aus dem Quellen-Queryset entfernen
        quellen_field = cast(forms.ModelMultipleChoiceField, self.fields["quellen"])

        # Quellen-Objekte werden so gesammelt, damit die einzelnen Modelltypen erhalten bleiben und TrustedAccountQuelle das passende Emoji erhalten kann
        quellen_objs = []
        quellen_objs.extend(list(Fachschaft.objects.all()))
        quellen_objs.extend(list(InterneWebsite.objects.all()))
        quellen_objs.extend(list(ExterneWebsite.objects.all()))
        quellen_objs.extend(list(EmailVerteiler.objects.all()))
        quellen_objs.extend(list(TrustedAccountQuelle.objects.all()))

        # Basis-Queryset ohne Rundmail-Objekte erstellen
        base_queryset = quellen_field.queryset.exclude(rundmail_filter).order_by("name")
        quellen_field.queryset = base_queryset

        # Quellen-Field mit Emoji-Labels und Checkbox-Widget konfigurieren
        quellen_field.widget = forms.CheckboxSelectMultiple()
        quellen_field.choices = build_emoji_choices(
            quellen_objs, emoji_mappings["sources"]
        )

        # Weitere Label setzen
        self.fields["quellen"].label = _("Quellen")
        self.fields["include_rundmail"].label = _("📧 Rundmails")
        self.fields["include_sammel_rundmail"].label = _("📧 Sammel-Rundmails")

        # Standardwerte auf Präferenzen des Benutzers setzen
        user: User = self.instance

        if user and user.pk:
            self.fields["standorte"].initial = user.standorte.all()
            self.fields["inhaltskategorien"].initial = user.inhaltskategorien.all()
            self.fields["quellen"].initial = user.quellen.all()
            self.fields["zielgruppen"].initial = user.zielgruppen.all()
            self.fields["include_rundmail"].initial = user.include_rundmail
            self.fields["include_sammel_rundmail"].initial = (
                user.include_sammel_rundmail
            )

        # Quellen-Optionen sortieren (Checkboxes + Rundmail-Optionen)
        # Sortierschlüssel vorbereiten
        quelle_sort_lookup = {
            str(obj.pk): get_localized_field_value(obj, "name") for obj in quellen_objs
        }

        # Für alle Checkboxen im Quellen-Field
        for checkbox in self["quellen"]:  # type: ignore[misc]
            # Choice-Wert extrahieren
            # Mithilfe des Raw-Value können wir in quelle_sort_lookup nach dem Sortierschlüssel für das zu dem Feld gehörenden Objekt suchen
            raw_value = getattr(checkbox, "choice_value", None)
            if raw_value is None:
                raw_value = getattr(checkbox, "value", "")
            if raw_value in (None, "") and hasattr(checkbox, "data"):
                raw_value = checkbox.data.get("value", "")  # type: ignore[assignment]
            choice_label = str(checkbox.choice_label)
            # Sortierschlüssel aus quelle_sort_lookup holen
            sort_source = quelle_sort_lookup.get(str(raw_value), choice_label)
            # Dictionary mit Label, ID, HTML-Input und Sortierschlüssel erstellen
            self.ordered_sources.append(
                {
                    "label": choice_label,
                    "id": checkbox.id_for_label,
                    "input_html": mark_safe(checkbox.tag()),
                    "sort_key": sort_source,
                }
            )

        # Rundmail-Optionen hinzufügen
        for field_name in ("include_rundmail", "include_sammel_rundmail"):
            bound_field = self[field_name]
            label = str(bound_field.label)
            self.ordered_sources.append(
                {
                    "label": label,
                    "id": bound_field.id_for_label,
                    "input_html": mark_safe(bound_field.as_widget()),
                    "sort_key": label[2:],  # Emoji entfernen für Sortierung
                }
            )

        # Optionen nach Sortierschlüssel sortieren
        self.ordered_sources.sort(key=lambda option: option["sort_key"])
        for option in self.ordered_sources:
            option.pop("sort_key", None)

    def save(self, commit: bool = True) -> User:
        user: User = super().save(commit=False)
        user.include_rundmail = self.cleaned_data["include_rundmail"]
        user.include_sammel_rundmail = self.cleaned_data["include_sammel_rundmail"]
        if commit:
            user.save()
            user.standorte.set(self.cleaned_data["standorte"])
            user.inhaltskategorien.set(self.cleaned_data["inhaltskategorien"])
            user.quellen.set(self.cleaned_data["quellen"])
            user.zielgruppen.set(self.cleaned_data["zielgruppen"])

        return user


# Formular für die Auswahl der bevorzugten Sprache
class LanguagePreferenceForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["preferred_language"]
        labels = {"preferred_language": _("Bevorzugte Sprache ändern")}
        widgets = {
            "preferred_language": forms.Select(
                attrs={
                    "class": "form-field",
                }
            )
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        preferred_language_field = self.fields["preferred_language"]
        preferred_language_field.choices = settings.LANGUAGES
        ensure_widget_has_class(preferred_language_field)


class TrustedUserApplicationForm(forms.ModelForm):
    class Meta:
        model = TrustedUserApplication
        fields = ["motivation"]
        widgets = {
            "motivation": forms.Textarea(
                attrs={
                    "cols": 30,
                    "rows": 6,
                    "class": "form-field",
                }
            ),
        }
        labels = {
            "motivation": _("Warum möchtest du als Trusted Account News einreichen?"),
        }


class TrustedNewsSubmissionForm(forms.Form):
    # Formularfelder definieren
    titel = forms.CharField(
        label=_("Titel"),
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-field",
            }
        ),
    )
    text = forms.CharField(
        label=_("Text"),
        widget=forms.Textarea(
            attrs={
                "rows": 12,
                "class": "form-field",
            }
        ),
    )
    link = forms.URLField(
        label=_("Optionale Quelle (Link)"),
        required=False,
        widget=forms.URLInput(
            attrs={
                "class": "form-field",
            }
        ),
    )
    inhaltskategorien = forms.ModelMultipleChoiceField(
        queryset=InhaltsKategorie.objects.none(),
    )
    zielgruppen = forms.ModelMultipleChoiceField(
        queryset=Zielgruppe.objects.none(),
    )
    standorte = forms.ModelMultipleChoiceField(
        queryset=Standort.objects.none(),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Emoji-Daten über die Category Registry holen
        emoji_mappings = load_emoji_mappings()

        # Formularfelder mit Emoji-Labels und -Choices versehen
        for field_name in ("standorte", "inhaltskategorien", "zielgruppen"):
            config = EMOJI_FIELD_CONFIG[field_name]
            queryset_builder = cast(Callable[[], Iterable[Any]], config["queryset"])
            field = cast(forms.ModelMultipleChoiceField, self.fields[field_name])
            queryset = queryset_builder()
            objects = list(queryset)
            field.queryset = queryset
            field.label = config["label"]
            field.widget = forms.CheckboxSelectMultiple()
            field.choices = build_emoji_choices(
                objects, emoji_mappings[config["emoji_key"]]
            )

    # Validierung der Mehrfachauswahl-Felder
    def clean_inhaltskategorien(self):
        categories = self.cleaned_data["inhaltskategorien"]
        if not categories:
            raise forms.ValidationError(_("Bitte wähle mindestens eine Kategorie aus."))
        return categories

    def clean_zielgruppen(self):
        audiences = self.cleaned_data["zielgruppen"]
        if not audiences:
            raise forms.ValidationError(
                _("Bitte wähle mindestens eine Zielgruppe aus.")
            )
        return audiences

    def clean_standorte(self):
        locations = self.cleaned_data["standorte"]
        if not locations:
            raise forms.ValidationError(_("Bitte wähle mindestens einen Standort aus."))
        return locations

    # Vom Nutzer eingegebene Daten in für receive_news.py geeignetes Format umwandeln
    def build_payload(self, user: User) -> dict[str, Any]:
        cleaned = self.cleaned_data
        submission_time = timezone.now().strftime("%d.%m.%Y %H:%M:%S")
        link_input = (cleaned["link"] or "").strip()
        link = link_input if link_input else None
        return {
            "titel": cleaned["titel"],
            "text": cleaned["text"],
            "link": link,
            "standorte": [location.name for location in cleaned["standorte"]],
            "quelle_typ": "Trusted Account",
            "quelle_name": user.username,
            "trusted_user_id": user.pk,
            "erstellungsdatum": submission_time,
            "manual_inhaltskategorien": [
                category.name for category in cleaned["inhaltskategorien"]
            ],
            "manual_zielgruppen": [
                zielgruppe.name for zielgruppe in cleaned["zielgruppen"]
            ],
        }
