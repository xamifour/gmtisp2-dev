from django.apps import AppConfig


class BillingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appshere.billings'

    def ready(self):
        import appshere.billings.signals  # Ensure the signals are registered