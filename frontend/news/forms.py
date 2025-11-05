from typing import Any, Callable, Iterable, cast

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.utils import timezone
from django.utils.safestring import mark_safe

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
    "inhaltskategorien": {
        "label": "Kategorien",
        "emoji_key": "categories",
        "queryset": lambda: InhaltsKategorie.objects.order_by("name"),
    },
    "zielgruppen": {
        "label": "Zielgruppen",
        "emoji_key": "audiences",
        "queryset": lambda: Zielgruppe.objects.order_by("name"),
    },
    "standorte": {
        "label": "Standorte",
        "emoji_key": "locations",
        "queryset": lambda: Standort.objects.order_by("name"),
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


class UserCreationForm2(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "password1", "password2")


# Formular für Benutzerpräferenzen
class PreferencesForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "standorte",
            "inhaltskategorien",
            "quellen",
            "zielgruppen",
            "include_rundmail",
            "include_sammel_rundmail",
        ]
        widgets = {
            "standorte": forms.CheckboxSelectMultiple(),
            "inhaltskategorien": forms.CheckboxSelectMultiple(),
            "quellen": forms.CheckboxSelectMultiple(),
            "zielgruppen": forms.CheckboxSelectMultiple(),
            "include_rundmail": forms.CheckboxInput(),
            "include_sammel_rundmail": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ordered_sources = (
            []
        )  # Filled with quellen and Rundmail options for the template

        # Emojis holen
        emoji_data = get_objects_with_emojis()
        emoji_mappings = {
            key: build_emoji_lookup(emoji_data, key)
            for key in ("categories", "audiences", "locations", "sources")
        }

        for field_name in ("inhaltskategorien", "zielgruppen", "standorte"):
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
        quellen_queryset = (
            self.fields["quellen"].queryset.exclude(rundmail_filter).order_by("name")  # type: ignore[attr-defined]
        )
        quellen_objs = [
            obj for obj in quellen_queryset if not isinstance(obj, Rundmail)
        ]
        self.fields["quellen"].choices = build_emoji_choices(
            quellen_objs, emoji_mappings["sources"]
        )

        # Weitere Label setzen
        self.fields["quellen"].label = "Quellen"
        self.fields["include_rundmail"].label = "📧 Rundmails"
        self.fields["include_sammel_rundmail"].label = "📧 Sammel-Rundmails"

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

        quelle_sort_lookup = {str(obj.pk): obj.name for obj in quellen_objs}
        combined_options: list[dict[str, str]] = []

        for checkbox in self["quellen"]:  # type: ignore[misc]
            raw_value = getattr(checkbox, "choice_value", None)
            if raw_value is None:
                raw_value = getattr(checkbox, "value", "")
            if raw_value in (None, "") and hasattr(checkbox, "data"):
                raw_value = checkbox.data.get("value", "")  # type: ignore[assignment]
            sort_key = quelle_sort_lookup.get(str(raw_value), checkbox.choice_label)
            combined_options.append(
                {
                    "label": checkbox.choice_label,
                    "id": checkbox.id_for_label,
                    "input_html": mark_safe(checkbox.tag()),
                    "sort_key": sort_key.lower(),
                }
            )

        for field_name in ("include_rundmail", "include_sammel_rundmail"):
            bound_field = self[field_name]
            combined_options.append(
                {
                    "label": bound_field.label,
                    "id": bound_field.id_for_label,
                    "input_html": mark_safe(bound_field.as_widget()),
                    "sort_key": bound_field.label.lower(),
                }
            )

        combined_options.sort(key=lambda option: option["sort_key"])
        for option in combined_options:
            option.pop("sort_key", None)

        self.ordered_sources = combined_options

    def save(self, commit=True):
        user: User = super().save(commit=False)
        if commit:
            user.save()
            user.standorte.set(self.cleaned_data["standorte"])
            user.inhaltskategorien.set(self.cleaned_data["inhaltskategorien"])
            user.quellen.set(self.cleaned_data["quellen"])
            user.zielgruppen.set(self.cleaned_data["zielgruppen"])
            user.include_rundmail = self.cleaned_data["include_rundmail"]
            user.include_sammel_rundmail = self.cleaned_data["include_sammel_rundmail"]
            user.save()

        return user


class TrustedUserApplicationForm(forms.ModelForm):
    class Meta:
        model = TrustedUserApplication
        fields = ["motivation"]
        widgets = {
            "motivation": forms.Textarea(attrs={"rows": 6}),
        }
        labels = {
            "motivation": "Warum möchtest du als Trusted Account News einreichen?",
        }


class TrustedNewsSubmissionForm(forms.Form):
    titel = forms.CharField(
        label="Titel",
        max_length=255,
    )
    text = forms.CharField(
        label="Text",
        widget=forms.Textarea(attrs={"rows": 12}),
    )
    link = forms.URLField(
        label="Optionale Quelle (Link)",
        required=False,
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
        emoji_data = get_objects_with_emojis()
        emoji_mappings = {
            key: build_emoji_lookup(emoji_data, key)
            for key in ("categories", "audiences", "locations")
        }

        for field_name in ("inhaltskategorien", "zielgruppen", "standorte"):
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

    def clean_inhaltskategorien(self):
        categories = self.cleaned_data["inhaltskategorien"]
        if not categories:
            raise forms.ValidationError("Bitte wähle mindestens eine Kategorie aus.")
        return categories

    def clean_zielgruppen(self):
        audiences = self.cleaned_data["zielgruppen"]
        if not audiences:
            raise forms.ValidationError("Bitte wähle mindestens eine Zielgruppe aus.")
        return audiences

    def clean_standorte(self):
        locations = self.cleaned_data["standorte"]
        if not locations:
            raise forms.ValidationError("Bitte wähle mindestens einen Standort aus.")
        return locations

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
