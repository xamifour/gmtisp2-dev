from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'appshere.accounts'

    # def ready(self):
    #     import appshere.accounts.signals  # Ensure the signals are registered