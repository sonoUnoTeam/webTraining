# Generated manually to update existing TraineeTraining states from old string format to new enum format

from django.db import migrations


def update_states(apps, schema_editor):
    """
    Migra los estados antiguos al nuevo formato enum:
    - "in_progress" -> "in_progress" (sin cambio)
    - "Completed" -> "passed" (asumiendo que los completados eran aprobados)
    """
    TraineeTraining = apps.get_model('trainingApp', 'TraineeTraining')
    
    # Actualizar registros con estado "Completed" (antiguo) a "passed" (nuevo)
    # Nota: Asumimos que todos los "Completed" eran aprobados
    completed_trainings = TraineeTraining.objects.filter(state="Completed")
    updated_count = completed_trainings.update(state="passed")
    
    print(f"Updated {updated_count} TraineeTraining records from 'Completed' to 'passed'")
    
    # Los registros con "in_progress" ya tienen el valor correcto del enum
    # Los nuevos estados "failed" y "not_started" no existen en datos antiguos


def reverse_update_states(apps, schema_editor):
    """
    Revierte los cambios si es necesario
    """
    TraineeTraining = apps.get_model('trainingApp', 'TraineeTraining')
    
    # Revertir de "passed" a "Completed"
    TraineeTraining.objects.filter(state="passed").update(state="Completed")
    
    print("Reverted TraineeTraining states to old format")


class Migration(migrations.Migration):

    dependencies = [
        ('trainingApp', '0003_traineetraining_best_score_and_more'),
    ]

    operations = [
        migrations.RunPython(update_states, reverse_update_states),
    ]
