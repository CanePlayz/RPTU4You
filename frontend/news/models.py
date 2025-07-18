from django.contrib.auth.models import AbstractUser
from django.db import models

# News


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

    class Meta:  # type: ignore[no-redef]
        verbose_name_plural = "Fachschaften"


class Rundmail(Quelle):
    rundmail_id = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name

    class Meta:  # type: ignore[no-redef]
        verbose_name_plural = "Rundmails"


class InterneWebsite(Quelle):
    def __str__(self):
        return self.name

    class Meta:  # type: ignore[no-redef]
        verbose_name_plural = "Interne Websites"


class ExterneWebsite(Quelle):
    def __str__(self):
        return self.name

    class Meta:  # type: ignore[no-redef]
        verbose_name_plural = "Externe Websites"


class EmailVerteiler(Quelle):
    def __str__(self):
        return self.name

    class Meta:  # type: ignore[no-redef]
        verbose_name_plural = "Email-Verteiler"


class Standort(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Standorte"


class InhaltsKategorie(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Inhaltskategorien"


class Zielgruppe(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Zielgruppen"


class News(models.Model):
    id = models.AutoField(primary_key=True)

    link = models.URLField(
        max_length=1000
    )  # max_length=1000 ist notwendig, da URLField standardmäßig auf 200 Zeichen begrenzt ist
    # Dieser Titel wird nicht in der UI angezeigt, sondern ist nur für die Identifikation in der Datenbank gedacht
    titel = models.CharField()
    erstellungsdatum = models.DateTimeField()

    standorte = models.ManyToManyField(Standort, blank=True)
    kategorien = models.ManyToManyField(InhaltsKategorie, blank=True)
    zielgruppe = models.ManyToManyField(Zielgruppe, blank=True)

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

    is_cleaned_up = models.BooleanField(default=False)

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
    name = models.CharField(max_length=30, unique=True)
    name_englisch = models.CharField(max_length=30, unique=True)
    code = models.CharField(max_length=5, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Sprachen"


class Text(models.Model):
    news = models.ForeignKey(News, on_delete=models.CASCADE, related_name="texte")
    text = models.TextField()
    titel = models.CharField()
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


# User


class User(AbstractUser):
    id = models.AutoField(primary_key=True)

    standorte = models.ManyToManyField(Standort, blank=True)
    fachschaften = models.ManyToManyField(Fachschaft, blank=True)
    präferenzen = models.ManyToManyField(InhaltsKategorie, blank=True)
    zielgruppe = models.ManyToManyField(Zielgruppe, blank=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name_plural = "User"


# Kalender


REPEAT_CHOICES = [
    ("none", "Keine"),
    ("daily", "Täglich"),
    ("weekly", "Wöchentlich"),
    ("monthly", "Monatlich"),
    ("yearly", "Jährlich"),
]


class CalendarEvent(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField()
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
    repeat = models.CharField(max_length=10, choices=REPEAT_CHOICES, default="none")
    repeat_until = models.DateTimeField(null=True, blank=True)
    group = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Kalendereinträge"


class OpenAITokenUsage(models.Model):
    date = models.DateField(unique=True)
    used_tokens = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.date}: {self.used_tokens} tokens"

    class Meta:
        verbose_name_plural = "OpenAI Token Usage"
        ordering = ["-date"]
