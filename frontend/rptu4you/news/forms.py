from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Fachschaft, Kategorie, Standort, User


class UserCreationForm2(UserCreationForm):
    class Meta:
        model = User
        fields = ("username", "password1", "password2")


class PreferencesForm(forms.ModelForm):
    # Manuelle Felder, die nicht im Model sind
    YES_NO_CHOICES = [
        (True, "Ja"),
        (False, "Nein"),
    ]

    stellenangebote = forms.BooleanField(
        widget=forms.RadioSelect(choices=YES_NO_CHOICES), required=False
    )
    uni_infos = forms.BooleanField(
        widget=forms.RadioSelect(choices=YES_NO_CHOICES), required=False
    )
    events = forms.BooleanField(
        widget=forms.RadioSelect(choices=YES_NO_CHOICES), required=False
    )
    externe_news = forms.BooleanField(
        widget=forms.RadioSelect(choices=YES_NO_CHOICES), required=False
    )
    umfragen = forms.BooleanField(
        widget=forms.RadioSelect(choices=YES_NO_CHOICES), required=False
    )

    class Meta:
        model = User

        # Felder aus dem Model, die im Formular angezeigt werden sollen
        fields = [
            "rolle",
            "standorte",
            "fachschaften",
        ]

        # Darstellung der Felder überschreiben
        widgets = {
            "rolle": forms.RadioSelect(attrs={"required": True}),
            "standorte": forms.CheckboxSelectMultiple,
            "fachschaften": forms.CheckboxSelectMultiple,
        }

    # Mapping: Formularfeld -> Kategorie-Name
    PREF_FELDER = {
        "stellenangebote": "Stellenangebot",
        "uni_infos": "Uni-Info",
        "events": "Event",
        "externe_news": "Externe News",
        "umfragen": "Umfrage",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Stanardwerte der Präferenzen setzen
        user_pref_names = set(self.instance.präferenzen.values_list("name", flat=True))
        for field_name, category_name in self.PREF_FELDER.items():
            self.initial[field_name] = category_name in user_pref_names

    def save(self, commit=True) -> User:
        user = super().save(commit=False)

        # Nutzerdaten und M2M-Felder speichern
        if commit:
            user.save()
            self.save_m2m()

        # Präferenzen aktualisieren
        for field_name, category_name in self.PREF_FELDER.items():
            selected = self.cleaned_data.get(field_name) is True
            pref_obj, _ = Kategorie.objects.get_or_create(name=category_name)

            if selected:
                user.präferenzen.add(pref_obj)
            else:
                user.präferenzen.remove(pref_obj)

        return user
