from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.utils.safestring import mark_safe

from .models import *
from .util.filter_objects import get_objects_with_emojis


class UserCreationForm2(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "password1", "password2")


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

        # Hilfsfunktion: Emoji nach Name suchen
        def get_emoji(name, emoji_list):
            for entry in emoji_list:
                if entry["name"] == name:
                    return entry["emoji"]
            return ""

        # Standorte-Choices mit Emoji
        standorte_queryset = self.fields["standorte"].queryset.order_by("name")  # type: ignore[attr-defined]
        standorte_objs = list(standorte_queryset)
        self.fields["standorte"].choices = [
            (obj.pk, f"{get_emoji(obj.name, emoji_data['locations'])} {obj.name}")
            for obj in standorte_objs
        ]

        # Inhaltskategorien-Choices mit Emoji
        inhaltskategorien_queryset = self.fields["inhaltskategorien"].queryset.order_by("name")  # type: ignore[attr-defined]
        inhaltskategorien_objs = list(inhaltskategorien_queryset)
        self.fields["inhaltskategorien"].choices = [
            (obj.pk, f"{get_emoji(obj.name, emoji_data['categories'])} {obj.name}")
            for obj in inhaltskategorien_objs
        ]

        # Zielgruppen-Choices mit Emoji
        zielgruppen_queryset = self.fields["zielgruppen"].queryset.order_by("name")  # type: ignore[attr-defined]
        zielgruppen_objs = list(zielgruppen_queryset)
        self.fields["zielgruppen"].choices = [
            (obj.pk, f"{get_emoji(obj.name, emoji_data['audiences'])} {obj.name}")
            for obj in zielgruppen_objs
        ]

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
        self.fields["quellen"].choices = [
            (obj.pk, f"{get_emoji(obj.name, emoji_data['sources'])} {obj.name}")
            for obj in quellen_objs
        ]

        # Label setzen
        self.fields["standorte"].label = "Standorte"
        self.fields["inhaltskategorien"].label = "Inhaltskategorien"
        self.fields["quellen"].label = "Quellen"
        self.fields["zielgruppen"].label = "Zielgruppen"
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
