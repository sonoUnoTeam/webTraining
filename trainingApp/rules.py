"""
Reglas de acceso y progreso de un trainee dentro de un curso.

Centraliza las validaciones que antes estaban repartidas entre las vistas, para que
entrar directo por URL a cualquier paso del training aplique las mismas reglas que la UI.
"""
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import Course, CourseTraining, Training, TrainingBlock, TrainingBlockAnswer, TraineeTraining, TraineeCourse

IN_PROGRESS = TraineeTraining.StateTraineeTraining.IN_PROGRESS


def active_blocks(training):
    """Bloques activos con al menos una pregunta: son los que hay que completar en un intento."""
    return (
        TrainingBlock.objects
        .filter(training=training, state_block=TrainingBlock.StateBlock.Active, trainingquestion__isnull=False)
        .distinct()
        .order_by('id')
    )


def course_trainings(course):
    """Trainings activos del curso en orden secuencial."""
    return (
        CourseTraining.objects
        .filter(course=course, training__state_training=Training.StateTraining.Active)
        .select_related('training')
        .order_by('order')
    )


def can_view_course(trainee, course):
    """El curso está asignado al grupo del trainee."""
    return trainee.group_id is not None and course.groups.filter(id=trainee.group_id).exists()


def training_in_course(course, training_id):
    return course.final_exam_id == training_id or course.trainings.filter(id=training_id).exists()


def attempts(trainee, course, training):
    return TraineeTraining.objects.filter(trainee=trainee, course=course, training=training)


def finished_attempts(trainee, course, training):
    return attempts(trainee, course, training).exclude(state=IN_PROGRESS)


def final_exam_unlocked(trainee, course):
    """Todos los trainings tienen un intento terminado y el promedio de los mejores puntajes alcanza el mínimo."""
    best_scores = []
    for ct in course_trainings(course):
        best = finished_attempts(trainee, course, ct.training).aggregate(best=Max('score_percentage'))['best']
        if best is None:
            return False
        best_scores.append(float(best))
    average = sum(best_scores) / len(best_scores) if best_scores else 0
    return average >= float(course.required_average_score)


def check_can_attempt(trainee, course, training):
    """
    Devuelve None si el trainee puede iniciar o continuar un intento de `training` en `course`;
    si no, el mensaje de error a mostrar.
    """
    if not can_view_course(trainee, course):
        return _("You do not have access to this course.")
    if not training_in_course(course, training.id):
        return _("This training is not part of the course.")
    if course.state_course != Course.StateCourse.Active or training.state_training != Training.StateTraining.Active:
        return _("This training is not available.")

    if course.final_exam_id == training.id:
        # Una vez iniciado el examen, los requisitos ya no pueden retroceder (los trainings quedan bloqueados)
        if not attempts(trainee, course, training).exists() and not final_exam_unlocked(trainee, course):
            return _("You have not met the requirements to take the final exam yet.")
    else:
        sequence = [ct.training for ct in course_trainings(course)]
        position = next((i for i, t in enumerate(sequence) if t.id == training.id), None)
        if position is None:
            return _("This training is not available.")
        # El training anterior debe tener al menos un intento terminado (aprobado o no)
        if position > 0 and not finished_attempts(trainee, course, sequence[position - 1]).exists():
            return _("You must complete the previous training first.")
        # Haber empezado el siguiente training o el examen final bloquea los reintentos
        if position < len(sequence) - 1 and attempts(trainee, course, sequence[position + 1]).exists():
            return _("You cannot retry this training because you have already started the next one.")
        if course.final_exam_id and attempts(trainee, course, course.final_exam).exists():
            return _("You cannot retry this training because you have already started the final exam.")

    has_in_progress = attempts(trainee, course, training).filter(state=IN_PROGRESS).exists()
    if not has_in_progress and finished_attempts(trainee, course, training).count() >= training.attempts_allowed:
        return _("You have reached the maximum number of attempts for this training.")
    return None


def attempt_session_keys(course_id, training_id):
    return f'current_trainee_training_id_{course_id}_{training_id}', f'start_time_{course_id}_{training_id}'


def start_or_resume_attempt(request, trainee, course, training):
    """
    Devuelve el intento en progreso (lo crea si no existe) y lo registra en la sesión.
    Ignora IDs de sesión que apunten a intentos ajenos o ya terminados.
    """
    session_key, start_time_key = attempt_session_keys(course.id, training.id)
    in_progress = attempts(trainee, course, training).filter(state=IN_PROGRESS)

    session_attempt_id = request.session.get(session_key)
    trainee_training = in_progress.filter(pk=session_attempt_id).first() if session_attempt_id else None
    if trainee_training is None:
        trainee_training = in_progress.order_by('-pub_date').first()

    if trainee_training is None:
        trainee_course, _created = TraineeCourse.objects.get_or_create(trainee=trainee, course=course)
        trainee_training = TraineeTraining.objects.create(
            trainee_course=trainee_course,
            trainee=trainee,
            training=training,
            course=course,
            pub_date=timezone.now(),
            state=IN_PROGRESS,
            is_final_exam_attempt=(course.final_exam_id == training.id),
        )
        if trainee_course.state == TraineeCourse.StateTraineeCourse.Not_Started:
            trainee_course.state = TraineeCourse.StateTraineeCourse.In_Progress
            trainee_course.save()

    if trainee_training.id != session_attempt_id or start_time_key not in request.session:
        request.session[start_time_key] = trainee_training.pub_date.isoformat()
    request.session[session_key] = trainee_training.id
    return trainee_training


def block_completed(trainee_training, block):
    return TrainingBlockAnswer.objects.filter(
        trainee_Training=trainee_training, block=block, state_block=TrainingBlockAnswer.StateBlockAnswer.Completed
    ).exists()


def all_blocks_completed(trainee_training):
    required = set(active_blocks(trainee_training.training).values_list('id', flat=True))
    completed = set(
        TrainingBlockAnswer.objects
        .filter(trainee_Training=trainee_training, state_block=TrainingBlockAnswer.StateBlockAnswer.Completed)
        .values_list('block_id', flat=True)
    )
    return required <= completed
