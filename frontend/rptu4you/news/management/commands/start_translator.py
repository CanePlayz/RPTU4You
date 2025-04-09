from django.core.management.base import BaseCommand

from ...scheduler import start


class Command(BaseCommand):
    help = "Startet den Scheduler für die Übersetzung von Artikeln."

    def handle(self, *args, **kwargs):
        print("Starte Translator-Scheduler...")
        print()
        start()
