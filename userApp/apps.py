from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class UserappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'userApp'
    verbose_name = _('Trainees')
    
    def ready(self):
        # Import signals to ensure signal handlers are connected
        try:
            import userApp.signals  # noqa: F401
        except Exception:
            # Avoid raising exceptions at import time; Django will show errors elsewhere
            pass
