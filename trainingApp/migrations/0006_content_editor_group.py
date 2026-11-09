# Crea el grupo de Django "Content editor": usuarios staff que arman cursos desde el admin
# sin ver resultados de los trainees ni usuarios. Los usuarios se asignan a mano en el admin.
#
# Idempotente: get_or_create del grupo y agrega permisos; reverse no hace nada.

from django.contrib.auth.management import create_permissions
from django.db import migrations

GROUP_NAME = "Content editor"
CONTENT_MODELS = (
    "course",
    "coursetraining",
    "training",
    "trainingblock",
    "trainingquestion",
    "choice",
    "choiceset",
    "choicesetoption",
)
VIEW_ONLY_MODELS = ("traineegroup",)


def create_content_editor_group(apps, schema_editor):
    # Los permisos se crean en post_migrate: en una base nueva todavía no existen
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    codenames = [
        f"{action}_{model}"
        for model in CONTENT_MODELS
        for action in ("add", "change", "delete", "view")
    ]
    codenames += [f"view_{model}" for model in VIEW_ONLY_MODELS]

    group, _ = Group.objects.get_or_create(name=GROUP_NAME)
    group.permissions.add(
        *Permission.objects.filter(
            content_type__app_label="trainingApp", codename__in=codenames
        )
    )


class Migration(migrations.Migration):

    dependencies = [
        ("trainingApp", "0005_backfill_content_structure"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        migrations.RunPython(create_content_editor_group, migrations.RunPython.noop),
    ]
