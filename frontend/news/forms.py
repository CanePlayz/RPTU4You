from django import forms
from django.contrib.auth.forms import UserCreationForm

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
        ]
        widgets = {
            "standorte": forms.CheckboxSelectMultiple(),
            "inhaltskategorien": forms.CheckboxSelectMultiple(),
            "quellen": forms.CheckboxSelectMultiple(),
            "zielgruppen": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Emojis holen
        emoji_data = get_objects_with_emojis()

        # Hilfsfunktion: Emoji nach Name suchen
        def get_emoji(name, emoji_list):
            for entry in emoji_list:
                if entry["name"] == name:
                    return entry["emoji"]
            return ""

        # Standorte-Choices mit Emoji
        standorte_objs = list(self.fields["standorte"].queryset)  # type: ignore
        # Liste aus Tupeln mit PK des Objekts und Name mit Emoji
        self.fields["standorte"].choices = [
            (obj.pk, f"{get_emoji(obj.name, emoji_data['locations'])} {obj.name}")
            for obj in standorte_objs
        ]

        # Inhaltskategorien-Choices mit Emoji
        inhaltskategorien_objs = list(self.fields["inhaltskategorien"].queryset)  # type: ignore
        self.fields["inhaltskategorien"].choices = [
            (obj.pk, f"{get_emoji(obj.name, emoji_data['categories'])} {obj.name}")
            for obj in inhaltskategorien_objs
        ]

        # Zielgruppen-Choices mit Emoji
        zielgruppen_objs = list(self.fields["zielgruppen"].queryset)  # type: ignore
        self.fields["zielgruppen"].choices = [
            (obj.pk, f"{get_emoji(obj.name, emoji_data['audiences'])} {obj.name}")
            for obj in zielgruppen_objs
        ]

        # Quellen-Choices mit Emoji
        quellen_objs = list(self.fields["quellen"].queryset)  # type: ignore
        self.fields["quellen"].choices = [
            (obj.pk, f"{get_emoji(obj.name, emoji_data['sources'])} {obj.name}")
            for obj in quellen_objs
        ]

        # Label setzen
        self.fields["standorte"].label = "Standorte"
        self.fields["inhaltskategorien"].label = "Inhaltskategorien"
        self.fields["quellen"].label = "Quellen"
        self.fields["zielgruppen"].label = "Zielgruppen"

        # Standardwerte auf Präferenzen des Benutzers setzen
        user: User = self.instance

        if user and user.pk:
            self.fields["standorte"].initial = user.standorte.all()
            self.fields["inhaltskategorien"].initial = user.inhaltskategorien.all()
            self.fields["quellen"].initial = user.quellen.all()
            self.fields["zielgruppen"].initial = user.zielgruppen.all()

    def save(self, commit=True):
        user: User = super().save(commit=False)
        if commit:
            user.save()
            user.standorte.set(self.cleaned_data["standorte"])
            user.inhaltskategorien.set(self.cleaned_data["inhaltskategorien"])
            user.quellen.set(self.cleaned_data["quellen"])
            user.zielgruppen.set(self.cleaned_data["zielgruppen"])

        return user
