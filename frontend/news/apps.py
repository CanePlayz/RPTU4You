from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news"

    """ def ready(self):
        from .util.monitoring import start_monitoring

        start_monitoring() """
