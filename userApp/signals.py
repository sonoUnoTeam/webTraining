from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging

from .models import Trainee

logger = logging.getLogger(__name__)

try:
    from trainingApp.models import Group
except Exception:
    Group = None

User = get_user_model()


@receiver(post_save, sender=User)
def create_trainee_for_superuser(sender, instance, created, **kwargs):
    """Create a Trainee whenever a superuser is created via createsuperuser.

    This handler only runs on newly created users and only creates a Trainee
    for users where `is_superuser` is True. If a Trainee already exists, it
    will not create a duplicate.
    """
    if not created:
        return

    if not getattr(instance, "is_superuser", False):
        return

    try:
        group = None
        if Group is not None:
            group, _ = Group.objects.get_or_create(
                name_group="Group Defect",
                defaults={"description": "Default group for superusers"},
            )

        Trainee.objects.get_or_create(
            user=instance,
            defaults={
                "occupation": "Administrator",
                "group": group,
            },
        )
    except Exception as e:
        # Log but don't break the user creation flow
        logger.exception("Failed creating Trainee for superuser %s: %s", instance, e)
