from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TrainingappConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "trainingApp"
    verbose_name = _("Courses and results")
