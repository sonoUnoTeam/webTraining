"""
Helpers para construir datos de prueba y simular a un trainee respondiendo trainings.

Convenciones: cada pregunta tiene una opción correcta ("right") y una incorrecta ("wrong");
los puntajes por defecto son 70 % para aprobar trainings, examen final y promedio requerido.
"""
from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse

from userApp.models import Trainee
from trainingApp.models import (
    Choice,
    Course,
    CourseTraining,
    TraineeCourse,
    TraineeGroup,
    TraineeTraining,
    Training,
    TrainingBlock,
    TrainingBlockAnswer,
    TrainingQuestion,
    TrainingQuestionAnswer,
)

PASSWORD = 'Sono-Training-2026'

# Con DEBUG=False whitenoise exige el manifest de collectstatic, que en CI se genera después de los tests
simple_static_storage = override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)


def make_group(name='Group A'):
    return TraineeGroup.objects.create(name_group=name, description='')


def make_trainee(username, group, password=PASSWORD):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@example.com')
    return Trainee.objects.create(user=user, occupation='Tester', group=group)


def make_training(name, *, attempts_allowed=2, passing_score=70, blocks=1, questions_per_block=2, state='Active'):
    training = Training.objects.create(
        name_training=name, attempts_allowed=attempts_allowed, passing_score=passing_score, state_training=state
    )
    for b in range(blocks):
        add_block(training, f'{name} B{b + 1}', questions=questions_per_block)
    return training


def add_block(training, name, *, questions=2, state='Active'):
    block = TrainingBlock.objects.create(name_block=name, description='', training=training, state_block=state)
    for q in range(questions):
        question = TrainingQuestion.objects.create(block=block, question=f'{name} Q{q + 1}')
        Choice.objects.create(deploy=question, choice='right', correctChoice=True)
        Choice.objects.create(deploy=question, choice='wrong', correctChoice=False)
    return block


def make_course(name, trainings, *, groups=(), final_exam=None, required_average_score=70, final_exam_passing_score=70):
    course = Course.objects.create(
        name_course=name,
        description='',
        final_exam=final_exam,
        required_average_score=required_average_score,
        final_exam_passing_score=final_exam_passing_score,
    )
    course.groups.set(groups)
    for training in trainings:
        CourseTraining.objects.create(course=course, training=training)
    return course


def questions_of(training):
    """Preguntas de los bloques activos en el orden en que las presenta el flujo."""
    return list(
        TrainingQuestion.objects
        .filter(block__training=training, block__state_block='Active')
        .order_by('block_id', 'id')
    )


# --- Datos creados directamente (tests unitarios) ---

def make_attempt(trainee, course, training, *, state=TraineeTraining.StateTraineeTraining.FAILED, score=0):
    trainee_course, _ = TraineeCourse.objects.get_or_create(trainee=trainee, course=course)
    return TraineeTraining.objects.create(
        trainee_course=trainee_course,
        trainee=trainee,
        training=training,
        course=course,
        pub_date=trainee_course.pub_date,
        state=state,
        score_percentage=score,
        is_final_exam_attempt=(course.final_exam_id == training.id),
    )


def record_answer(attempt, question, correct):
    block_answer, _ = TrainingBlockAnswer.objects.get_or_create(
        trainee_Training=attempt, block=question.block, defaults={'state_block': 'Completed'}
    )
    choice = Choice.objects.get(deploy=question, correctChoice=correct)
    return TrainingQuestionAnswer.objects.create(block_answer=block_answer, deploy=question, selectedChoice=choice)


# --- Simulación por HTTP (tests de integración) ---

def answer_training(client, course, training, answers=True):
    """
    Recorre el training como lo haría el trainee: abre la lista de bloques y responde cada
    pregunta de cada bloque (GET + POST). `answers` es un bool para todas las preguntas o una
    lista de bools en el orden de `questions_of(training)`. Devuelve la última respuesta HTTP.
    """
    response = client.get(reverse('trainingApp:block_deploy_list', args=[course.id, training.id]))
    if response.status_code != 200:
        return response

    questions = questions_of(training)
    if isinstance(answers, bool):
        answers = [answers] * len(questions)
    assert len(answers) == len(questions), 'answers must match the number of questions'

    for question, correct in zip(questions, answers):
        url = reverse('trainingApp:forms', args=[course.id, training.id, question.block_id])
        page = client.get(url)
        assert page.status_code == 200, f'question page returned {page.status_code}'
        choice = Choice.objects.get(deploy=question, correctChoice=correct)
        response = client.post(url, {'selectedChoice': choice.id})
    return response
