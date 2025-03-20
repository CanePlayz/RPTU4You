from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User, Standort, Fachschaft

class UserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')  # Nur Benutzername und Passwort

class PreferencesForm(forms.ModelForm):
    YES_NO_CHOICES = [
        (True, 'Ja'),
        (False, 'Nein'),
    ]

    stellenangebote = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect)
    uni_infos = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect)
    events = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect)
    externe_news = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect)
    umfragen = forms.ChoiceField(choices=YES_NO_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = [
            'rolle', 'standorte', 'fachschaften', 
            'stellenangebote', 'uni_infos', 'events', 
            'externe_news', 'umfragen'
        ]
        widgets = {
            'rolle': forms.RadioSelect(attrs={'required': True}),  # Keine leere Option, Pflichtfeld
            'standorte': forms.CheckboxSelectMultiple,
            'fachschaften': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Standardwert für standorte auf Kaiserslautern setzen, falls leer
        if not self.instance.pk or not self.instance.standorte.exists():
            kaiserslautern = Standort.objects.get(name="Kaiserslautern")
            self.initial['standorte'] = [kaiserslautern.id]