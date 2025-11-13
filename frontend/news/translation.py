from modeltranslation.translator import TranslationOptions, translator

from .models import (
    EmailVerteiler,
    ExterneWebsite,
    Fachschaft,
    InhaltsKategorie,
    InterneWebsite,
    Quelle,
    Rundmail,
    Standort,
    TrustedAccountQuelle,
    Zielgruppe,
)


class QuelleTranslation(TranslationOptions):
    fields = ("name",)


class QuelleChildTranslation(TranslationOptions):
    pass


class StandortTranslation(TranslationOptions):
    fields = ("name",)


class InhaltsKategorieTranslation(TranslationOptions):
    fields = ("name",)


class ZielgruppeTranslation(TranslationOptions):
    fields = ("name",)


translator.register(Quelle, QuelleTranslation)
translator.register(Rundmail, QuelleChildTranslation)
translator.register(Fachschaft, QuelleChildTranslation)
translator.register(InterneWebsite, QuelleChildTranslation)
translator.register(ExterneWebsite, QuelleChildTranslation)
translator.register(EmailVerteiler, QuelleChildTranslation)
translator.register(TrustedAccountQuelle, QuelleChildTranslation)
translator.register(Standort, StandortTranslation)
translator.register(InhaltsKategorie, InhaltsKategorieTranslation)
translator.register(Zielgruppe, ZielgruppeTranslation)
