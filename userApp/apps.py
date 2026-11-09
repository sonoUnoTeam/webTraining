from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UserappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "userApp"
    verbose_name = _("Trainees")

    def ready(self):
        # Importar las señales para conectar sus handlers; si fallan, que falle el arranque
        # en vez de quedar desconectadas en silencio
        import userApp.signals  # noqa: F401
