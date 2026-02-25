from django.apps import AppConfig

class UserappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'userApp'
    
    def ready(self):
        # Import signals to ensure signal handlers are connected
        try:
            import userApp.signals  # noqa: F401
        except Exception:
            # Avoid raising exceptions at import time; Django will show errors elsewhere
            pass
