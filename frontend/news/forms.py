import re
from typing import Any, Callable, Iterable, cast

from django import forms
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from .models import (
    InhaltsKategorie,
    Rundmail,
    Standort,
    TrustedUserApplication,
    User,
    Zielgruppe,
)
from .util.filter_objects import get_objects_with_emojis

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
def build_emoji_lookup(emoji_data: dict[str, Any], key: str) -> dict[str, str]:
    """Erstellt ein Mapping von Objektname zu Emoji für die angegebene Emoji-Gruppe. Format: {"Objektname": "Emoji"}."""
    return {
        entry.get("name", ""): entry.get("emoji", "")
        for entry in emoji_data.get(key, [])
        if entry.get("name")
    }


def label_with_emoji(obj: Any, mapping: dict[str, str]) -> str:
    """Gibt den Objektnamen mit vorangestelltem Emoji zurück, falls eines vorhanden ist."""
    name = getattr(obj, "name", str(obj))
    emoji = mapping.get(name, "")
    return f"{emoji} {name}" if emoji else name


def build_emoji_choices(
    objs: Iterable[Any], mapping: dict[str, str]
) -> list[tuple[Any, str]]:
    """Erzeugt Choice-Liste bestehend aus Tupeln aus Primärschlüssel und Emoji-Label."""
    choices: list[tuple[Any, str]] = []
    for obj in objs:
        pk = getattr(obj, "pk", None)
        if pk is None:
            continue
        choices.append((pk, label_with_emoji(obj, mapping)))
    return choices


def ensure_widget_has_class(field: forms.Field, css_class: str = "form-field") -> None:
    """Sorgt dafür, dass die Widget-Attribute die gewünschte CSS-Klasse enthalten."""
    classes = field.widget.attrs.get("class", "").split()
    if css_class not in classes:
        classes.append(css_class)
        field.widget.attrs["class"] = " ".join(classes)


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

        # Emojis holen
        emoji_data = get_objects_with_emojis()
        emoji_mappings = {
            key: build_emoji_lookup(emoji_data, key)
            for key in ("categories", "audiences", "locations", "sources")
        }

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
        quellen_queryset = quellen_field.queryset.exclude(rundmail_filter).order_by(
            "name"
        )  # type: ignore[attr-defined]
        quellen_field.queryset = quellen_queryset
        quellen_objs = [
            obj for obj in quellen_queryset if not isinstance(obj, Rundmail)
        ]
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
        quelle_sort_lookup = {str(obj.pk): obj.name for obj in quellen_objs}

        # Für alle Checkboxen im Quellen-Field
        for checkbox in self["quellen"]:  # type: ignore[misc]
            # Rohwert des Checkbox-Elements ermitteln
            raw_value = getattr(checkbox, "choice_value", None)
            if raw_value is None:
                raw_value = getattr(checkbox, "value", "")
            if raw_value in (None, "") and hasattr(checkbox, "data"):
                raw_value = checkbox.data.get("value", "")  # type: ignore[assignment]
            choice_label = str(checkbox.choice_label)
            # Sortierschlüssel bestimmen
            sort_key = quelle_sort_lookup.get(str(raw_value), choice_label)
            # Dictionary mit Label, ID, HTML-Input und Sortierschlüssel erstellen
            self.ordered_sources.append(
                {
                    "label": choice_label,
                    "id": checkbox.id_for_label,
                    "input_html": mark_safe(checkbox.tag()),
                    "sort_key": str(sort_key).lower(),
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
                    "sort_key": label.lower(),
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
        # Emoji-Daten holen
        emoji_data = get_objects_with_emojis()
        emoji_mappings = {
            key: build_emoji_lookup(emoji_data, key)
            for key in ("categories", "audiences", "locations")
        }

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
