from django.contrib.auth.models import AbstractUser
from django.db import models


class Quelle(models.Model):
    name = models.CharField(unique=True)
    url = models.URLField()


class Fachschaft(Quelle):
    pass


class Rundmail(Quelle):
    rundmail_id = models.CharField(max_length=20, unique=True)


class InterneWebsite(Quelle):
    pass


class ExterneWebsite(Quelle):
    pass


class Standort(models.Model):
    name = models.CharField(max_length=100, unique=True)


class Kategorie(models.Model):
    name = models.CharField(max_length=100, unique=True)

    """ stellenangebot = models.BooleanField()
    uni_info = models.BooleanField()
    event = models.BooleanField()
    externe_news = models.BooleanField()
    umfragen = models.BooleanField()
    studierende = models.ManyToManyField(User, blank=True) """


class User(AbstractUser):
    rollen = [
        ("Student", "Student"),
        ("Angestellter", "Angestellter"),
    ]

    rolle = models.CharField(max_length=20, choices=rollen)
    standorte = models.ManyToManyField(Standort, blank=True)
    fachschaften = models.ManyToManyField(Fachschaft, blank=True)
    präferenzen = models.ManyToManyField(Kategorie, blank=True)


class News(models.Model):
    link = models.URLField()
    titel = models.CharField(max_length=255, unique=True)
    erstellungsdatum = models.DateField()
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
