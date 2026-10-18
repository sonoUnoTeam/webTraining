# Normaliza valores de choices guardados antes de 8b012d7 (2024-08-26), cuando los
# TextChoices pasaron de valores en español ('Activo', 'Inicial', 'En progreso'...) a
# los actuales en inglés sin migrar los datos. Con los filtros por estado de
# trainingApp/rules.py, un bloque o training con 'Activo' queda oculto.
#
# Idempotente: solo toca filas con valores viejos; reverse no hace nada.

from django.db import migrations

LEGACY_VALUES = [
    ('Training', 'state_training', {'Activo': 'Active', 'Inactivo': 'Inactive'}),
    ('Training', 'difficulty', {'Inicial': 'Easy', 'Intermedio': 'Intermediate', 'Avanzado': 'Advanced'}),
    ('TrainingBlock', 'state_block', {'Activo': 'Active', 'Inactivo': 'Inactive'}),
    ('TrainingBlockAnswer', 'state_block', {'En progreso': 'In progress', 'Completo': 'Completed'}),
    # Misma regla que la migración 0004_update_traineetraining_states que se perdió al
    # regenerar las migraciones: los intentos 'Completed' del modelo viejo eran aprobados
    ('TraineeTraining', 'state', {'Completed': 'passed'}),
]


def normalize(apps, schema_editor):
    for model_name, field, mapping in LEGACY_VALUES:
        model = apps.get_model('trainingApp', model_name)
        for old, new in mapping.items():
            updated = model.objects.filter(**{field: old}).update(**{field: new})
            if updated:
                print(f"  {model_name}.{field}: {updated} x '{old}' -> '{new}'")


class Migration(migrations.Migration):

    dependencies = [
        ('trainingApp', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(normalize, migrations.RunPython.noop),
    ]
