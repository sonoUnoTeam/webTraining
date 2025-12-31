"""
Script para cargar entrenamientos de muestra en la base de datos.
Crea dos entrenamientos: "Entrenamiento de muestra" y "Funciones Matemáticas Básicas"
"""
import os
import django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'webTraining.settings')
django.setup()

from trainingApp.models import Training, TrainingBlock, TrainingQuestion, Choice

def create_sample_trainings():
    print("=== Creando entrenamientos de muestra ===\n")
    
    # ==========================================
    # ENTRENAMIENTO 1: Entrenamiento de muestra
    # ==========================================
    print("1. Creando 'Entrenamiento de muestra'...")
    training1, created = Training.objects.get_or_create(
        name_training='Entrenamiento de muestra',
        defaults={
            'difficulty': 'Easy',
            'estimatedDuration': 15,
            'attempts_allowed': 50,
            'state_training': 'Active',
        }
    )
    
    if created:
        print("   ✓ Training creado")
    else:
        print("   ℹ Training ya existía, actualizando...")
        training1.difficulty = 'Easy'
        training1.estimatedDuration = 15
        training1.attempts_allowed = 50
        training1.state_training = 'Active'
        training1.save()
    
    # Bloque de muestra
    block1, created = TrainingBlock.objects.get_or_create(
        training=training1,
        name_block='Bloque muestra',
        defaults={
            'description': 'Bloque para mostrar la dinámica de los entrenamientos',
            'estimed_duration_block': 15,
            'state_block': 'Active',
        }
    )
    print(f"   ✓ Bloque '{block1.name_block}' {'creado' if created else 'actualizado'}")
    
    # Preguntas del bloque muestra
    questions_data = [
        {
            'question': '¿Ha detectado sonido?',
            'deploy_sound': 'trainingApp/sound/noise.wav',
            'choices': [
                ('si', False),
                ('no', True),
                ('tal vez', False),
            ]
        },
        {
            'question': '¿Ha detectado sonido?',
            'deploy_image': 'trainingApp/images/SNR40.300-320.png',
            'deploy_sound': 'trainingApp/sound/sound-noise.300-320.SNR40.wav',
            'choices': [
                ('si', True),
                ('no', False),
                ('tal vez', False),
            ]
        },
        {
            'question': '¿Ha detectado sonido?',
            'deploy_sound': 'trainingApp/sound/sound-noise.260-280.SNR85.wav',
            'choices': [
                ('si', True),
                ('no', False),
                ('tal vez', False),
            ]
        },
    ]
    
    for q_data in questions_data:
        question, created = TrainingQuestion.objects.get_or_create(
            block=block1,
            question=q_data['question'],
            deploy_sound=q_data.get('deploy_sound', ''),
            defaults={
                'deploy_image': q_data.get('deploy_image', ''),
            }
        )
        
        if created:
            print(f"   ✓ Pregunta creada: {q_data['question'][:30]}...")
            # Crear choices
            for choice_text, is_correct in q_data['choices']:
                Choice.objects.create(
                    deploy=question,
                    choice=choice_text,
                    correctChoice=is_correct
                )
            print(f"      → {len(q_data['choices'])} opciones creadas")
    
    print(f"\n✓ Entrenamiento '{training1.name_training}' completado\n")
    
    # ==========================================
    # ENTRENAMIENTO 2: Funciones Matemáticas Básicas
    # ==========================================
    print("2. Creando 'Funciones Matemáticas Básicas'...")
    training2, created = Training.objects.get_or_create(
        name_training='Funciones Matemáticas Básicas',
        defaults={
            'difficulty': 'Easy',
            'estimatedDuration': 20,
            'attempts_allowed': 5,
            'state_training': 'Active',
        }
    )
    
    if created:
        print("   ✓ Training creado")
    else:
        print("   ℹ Training ya existía, actualizando...")
        training2.difficulty = 'Easy'
        training2.estimatedDuration = 20
        training2.attempts_allowed = 5
        training2.state_training = 'Active'
        training2.save()
    
    # Bloque: Funciones Lineales
    block2, created = TrainingBlock.objects.get_or_create(
        training=training2,
        name_block='Funciones Lineales',
        defaults={
            'description': 'Identificación de funciones lineales básicas',
            'estimed_duration_block': 10,
            'state_block': 'Active',
        }
    )
    print(f"   ✓ Bloque '{block2.name_block}' {'creado' if created else 'actualizado'}")
    
    # Preguntas de funciones lineales
    linear_questions = [
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_sound': 'trainingApp/sound/fc-constante_sound.mp3',
            'choices': [
                ('Creciente', False),
                ('Constante', True),
                ('Decreciente', False),
                ('Triangular', False),
                ('Sierra', False),
                ('Pulso', False),
            ]
        },
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_sound': 'trainingApp/sound/creciente_sound.mp3',
            'choices': [
                ('Creciente', True),
                ('Constante', False),
                ('Decreciente', False),
                ('Triangular', False),
                ('Sierra', False),
                ('Pulso', False),
            ]
        },
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_sound': 'trainingApp/sound/decreciente_sound.mp3',
            'choices': [
                ('Creciente', False),
                ('Constante', False),
                ('Decreciente', True),
                ('Triangular', False),
                ('Sierra', False),
                ('Pulso', False),
            ]
        },
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_sound': 'trainingApp/sound/triangular_sound.mp3',
            'choices': [
                ('Creciente', False),
                ('Constante', False),
                ('Decreciente', False),
                ('Triangular', True),
                ('Sierra', False),
                ('Pulso', False),
            ]
        },
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_sound': 'trainingApp/sound/sierra_sound.mp3',
            'choices': [
                ('Creciente', False),
                ('Constante', False),
                ('Decreciente', False),
                ('Triangular', False),
                ('Sierra', True),
                ('Pulso', False),
            ]
        },
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_sound': 'trainingApp/sound/cuadrada_sound.mp3',
            'choices': [
                ('Creciente', False),
                ('Constante', False),
                ('Decreciente', False),
                ('Triangular', False),
                ('Sierra', False),
                ('Pulso', True),
            ]
        },
    ]
    
    for q_data in linear_questions:
        question, created = TrainingQuestion.objects.get_or_create(
            block=block2,
            question=q_data['question'],
            deploy_sound=q_data['deploy_sound'],
            defaults={
                'deploy_image': '',
            }
        )
        
        if created:
            print(f"   ✓ Pregunta creada: {q_data['deploy_sound'].split('/')[-1]}")
            # Crear choices
            for choice_text, is_correct in q_data['choices']:
                Choice.objects.create(
                    deploy=question,
                    choice=choice_text,
                    correctChoice=is_correct
                )
            print(f"      → {len(q_data['choices'])} opciones creadas")
    
    # Bloque: Funciones Curvas
    block3, created = TrainingBlock.objects.get_or_create(
        training=training2,
        name_block='Funciones Curvas',
        defaults={
            'description': 'Funciones polinómicas y trigonométricas',
            'estimed_duration_block': 10,
            'state_block': 'Active',
        }
    )
    print(f"   ✓ Bloque '{block3.name_block}' {'creado' if created else 'actualizado'}")
    
    # Preguntas de funciones curvas
    curve_questions = [
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_image': 'trainingApp/images/cuadratica2plot.png',
            'deploy_sound': 'trainingApp/sound/cuadratica2_sound.mp3',
            'choices': [
                ('Cuadrática', True),
                ('Cúbica', False),
                ('Seno', False),
                ('Coseno', False),
            ]
        },
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_image': 'trainingApp/images/cubicaplot.png',
            'deploy_sound': 'trainingApp/sound/cubica_sound.mp3',
            'choices': [
                ('Cuadrática', False),
                ('Cúbica', True),
                ('Seno', False),
                ('Coseno', False),
            ]
        },
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_image': 'trainingApp/images/senoplot.png',
            'deploy_sound': 'trainingApp/sound/seno_sound.mp3',
            'choices': [
                ('Cuadrática', False),
                ('Cúbica', False),
                ('Seno', True),
                ('Coseno', False),
            ]
        },
        {
            'question': 'Identifica la función mostrada como:',
            'deploy_image': 'trainingApp/images/cosenoplot.png',
            'deploy_sound': 'trainingApp/sound/coseno_sound.mp3',
            'choices': [
                ('Cuadrática', False),
                ('Cúbica', False),
                ('Seno', False),
                ('Coseno', True),
            ]
        },
    ]
    
    for q_data in curve_questions:
        question, created = TrainingQuestion.objects.get_or_create(
            block=block3,
            question=q_data['question'],
            deploy_sound=q_data['deploy_sound'],
            defaults={
                'deploy_image': q_data.get('deploy_image', ''),
            }
        )
        
        if created:
            print(f"   ✓ Pregunta creada: {q_data['deploy_sound'].split('/')[-1]}")
            # Crear choices
            for choice_text, is_correct in q_data['choices']:
                Choice.objects.create(
                    deploy=question,
                    choice=choice_text,
                    correctChoice=is_correct
                )
            print(f"      → {len(q_data['choices'])} opciones creadas")
    
    print(f"\n✓ Entrenamiento '{training2.name_training}' completado\n")
    
    # Resumen final
    print("\n" + "="*50)
    print("RESUMEN DE ENTRENAMIENTOS CREADOS")
    print("="*50)
    print(f"\n1. {training1.name_training}")
    print(f"   - Bloques: {training1.trainingblock_set.count()}")
    print(f"   - Preguntas: {TrainingQuestion.objects.filter(block__training=training1).count()}")
    print(f"   - Opciones: {Choice.objects.filter(deploy__block__training=training1).count()}")
    
    print(f"\n2. {training2.name_training}")
    print(f"   - Bloques: {training2.trainingblock_set.count()}")
    print(f"   - Preguntas: {TrainingQuestion.objects.filter(block__training=training2).count()}")
    print(f"   - Opciones: {Choice.objects.filter(deploy__block__training=training2).count()}")
    
    print("\n" + "="*50)
    print("✓ ¡Proceso completado exitosamente!")
    print("="*50)


if __name__ == '__main__':
    try:
        create_sample_trainings()
    except Exception as e:
        print(f"\n✗ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
