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

    rolle = models.CharField(max_length=20, choices=rollen, blank=True)
    standorte = models.ManyToManyField(Standort, blank=True)
    fachschaften = models.ManyToManyField(Fachschaft, blank=True)
    präferenzen = models.ManyToManyField(Kategorie, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name_plural = "User"


class News(models.Model):
    link = models.URLField()
    titel = models.CharField(max_length=255)
    erstellungsdatum = models.DateTimeField()

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
        constraints = [
            models.UniqueConstraint(
                fields=["titel", "erstellungsdatum"],
                name="unique_news_titel_erstellungsdatum",
            )
        ]


class Sprache(models.Model):
    name = models.CharField(max_length=10, unique=True)
    code = models.CharField(max_length=5, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Sprachen"


class Text(models.Model):
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name="texte")
    text = models.TextField()
    titel = models.CharField(max_length=255)
    sprache = models.ForeignKey(Sprache, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.news.titel} - {self.sprache.name}"

    class Meta:
        verbose_name_plural = "Texte"
        constraints = [
            models.UniqueConstraint(
                fields=["news", "sprache"], name="unique_news_sprache"
            )
        ]


class CalendarEvent(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start = models.DateTimeField()
    end = models.DateTimeField(blank=True, null=True)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="calendar_events",
        null=True,
        blank=True,
    )
    is_global = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Kalendereinträge"
