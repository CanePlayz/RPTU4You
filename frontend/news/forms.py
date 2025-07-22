from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import *


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
