from django.contrib.auth.models import AbstractUser
from django.db import models


class Quelle(models.Model):
    name = models.CharField(unique=True)
    url = models.URLField()

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Quellen"


class Fachschaft(Quelle):
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Fachschaften"


class Rundmail(Quelle):
    rundmail_id = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Rundmails"


class InterneWebsite(Quelle):
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Interne Websites"


class ExterneWebsite(Quelle):
    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Externe Websites"


class Standort(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Standorte"


""" def save(self, *args, **kwargs):
    # Standardwert für standorte nur bei neuen Nutzern setzen
    if not self.pk:  # Wenn der Nutzer neu erstellt wird
        super().save(*args, **kwargs)  # Erst speichern, um eine ID zu bekommen
        kaiserslautern = Standort.objects.get(name="Kaiserslautern")
        self.standorte.add(kaiserslautern)  # Kaiserslautern hinzufügen
    else:
        super().save(*args, **kwargs)  # Bei Updates nur speichern """


class Kategorie(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Kategorien"


class User(AbstractUser):
    rollen = [
        ("Student", "Student"),
        ("Angestellter", "Angestellter"),
    ]

    rolle = models.CharField(max_length=20, choices=rollen)
    standorte = models.ManyToManyField(Standort, blank=True)
    fachschaften = models.ManyToManyField(Fachschaft, blank=True)
    präferenzen = models.ManyToManyField(Kategorie, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name_plural = "User"


class News(models.Model):
    link = models.URLField()
    titel = models.CharField(max_length=255, unique=True)
    erstellungsdatum = models.DateTimeField()
    text = models.TextField()

    standorte = models.ManyToManyField(Standort, blank=True)
    kategorien = models.ManyToManyField(Kategorie, blank=True)

    quelle = models.ForeignKey(Quelle, on_delete=models.CASCADE)
    quelle_typ = models.CharField(
        max_length=35,
        choices=[
            ("Fachschaft", "Fachschaft"),
            ("Externe Website", "Externe Website"),
            ("Sammel-Rundmail", "Sammel-Rundmail"),
            ("Stellenangebote Sammel-Rundmail", "Stellenangebote Sammel-Rundmail"),
            ("Rundmail", "Rundmail"),
            ("Interne Website", "Interne Website"),
        ],
    )

    def __str__(self):
        return self.titel

    class Meta:
        verbose_name_plural = "News"
