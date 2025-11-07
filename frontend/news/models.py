from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now

# News


class Quelle(models.Model):
    name = models.CharField()
    url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Quellen"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "url"], name="unique_quelle_name_url"
            )
        ]


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


class TrustedAccountQuelle(Quelle):
    def __str__(self):
        return self.name

    class Meta:  # type: ignore[no-redef]
        verbose_name_plural = "Trusted Accounts"


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
        max_length=1000,
        blank=True,
        null=True,
    )  # max_length=1000 ist notwendig, da URLField standardmäßig auf 200 Zeichen begrenzt ist
    # Dieser Titel wird nicht in der UI angezeigt, sondern ist nur für die Identifikation in der Datenbank gedacht
    titel = models.CharField()
    erstellungsdatum = models.DateTimeField()

    standorte = models.ManyToManyField(Standort, blank=True)
    inhaltskategorien = models.ManyToManyField(InhaltsKategorie, blank=True)
    zielgruppen = models.ManyToManyField(Zielgruppe, blank=True)

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
            ("Trusted Account", "Trusted Account"),
        ],
    )

    is_cleaned_up = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=now, editable=False)

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
    quellen = models.ManyToManyField(Quelle, blank=True)
    inhaltskategorien = models.ManyToManyField(InhaltsKategorie, blank=True)
    zielgruppen = models.ManyToManyField(Zielgruppe, blank=True)
    is_trusted = models.BooleanField(default=False)
    include_rundmail = models.BooleanField(
        default=False,
        verbose_name="Rundmails einbeziehen",
    )
    include_sammel_rundmail = models.BooleanField(
        default=False, verbose_name="Sammel-Rundmails einbeziehen"
    )

    def __str__(self):
        return self.username

    class Meta:
        verbose_name_plural = "User"


class TrustedUserApplication(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_DECLINED = "declined"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Ausstehend"),
        (STATUS_APPROVED, "Genehmigt"),
        (STATUS_DECLINED, "Abgelehnt"),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="trusted_applications",
    )
    motivation = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        status_label = dict(self.STATUS_CHOICES).get(self.status, self.status)
        return f"{self.user.username} ({status_label})"

    class Meta:
        verbose_name = "Trusted-User-Bewerbung"
        verbose_name_plural = "Trusted-User-Bewerbungen"
        ordering = ["-created_at"]


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
