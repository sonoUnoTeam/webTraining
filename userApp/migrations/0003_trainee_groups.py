from django.db import migrations, models


def copy_group_to_groups(apps, schema_editor):
    """Cada trainee conserva su grupo anterior como primer grupo de la relación múltiple."""
    Trainee = apps.get_model("userApp", "Trainee")
    for trainee in Trainee.objects.exclude(group=None).only("id", "group_id"):
        trainee.groups.add(trainee.group_id)


def copy_groups_to_group(apps, schema_editor):
    """Reversa: queda el grupo de menor id (se pierden los demás)."""
    Trainee = apps.get_model("userApp", "Trainee")
    for trainee in Trainee.objects.all():
        first = trainee.groups.order_by("id").first()
        if first is not None:
            trainee.group = first
            trainee.save(update_fields=["group"])


class Migration(migrations.Migration):

    dependencies = [
        ("trainingApp", "0009_trainee_group_default"),
        ("userApp", "0002_descriptive_names"),
    ]

    operations = [
        migrations.AddField(
            model_name="trainee",
            name="groups",
            field=models.ManyToManyField(
                help_text="The trainee sees the active courses of all these groups.",
                related_name="members",
                to="trainingApp.traineegroup",
                verbose_name="trainee groups",
            ),
        ),
        migrations.RunPython(copy_group_to_groups, copy_groups_to_group),
        migrations.RemoveField(model_name="trainee", name="group"),
    ]
