"""
Verificaciones del contenido cargado en el admin: detectan lo que dejaría incompleto un curso
antes de que lo vea un trainee (preguntas sin sonido o sin respuesta correcta, textos sin
traducir, trainings inactivos, etc.).

Cada función revisa solo su nivel (no recorre los hijos) y devuelve una lista de `Issue`.
Esperan las relaciones ya cargadas con prefetch_related para no hacer una consulta por elemento.
"""

from collections import namedtuple

from django.utils.translation import gettext as _
from modeltranslation.settings import AVAILABLE_LANGUAGES

from .models import Course, TrainingBlock

ERROR = "error"
WARNING = "warning"

Issue = namedtuple("Issue", "level message")


def missing_languages(values_by_language):
    return ", ".join(
        lang.upper() for lang, value in values_by_language.items() if not value
    )


def question_issues(question):
    issues = []
    choices = list(question.choice_set.all())
    if not question.deploy_sound:
        issues.append(Issue(ERROR, _("No sound.")))
    if len(choices) < 2:
        issues.append(Issue(ERROR, _("Fewer than two options.")))
    elif sum(choice.correctChoice for choice in choices) != 1:
        issues.append(Issue(ERROR, _("It must have exactly one correct option.")))

    languages = missing_languages(
        {lang: getattr(question, f"question_{lang}") for lang in AVAILABLE_LANGUAGES}
    )
    if languages:
        issues.append(
            Issue(
                WARNING,
                _("Question text missing in %(languages)s.") % {"languages": languages},
            )
        )
    for choice in choices:
        languages = missing_languages(
            {lang: getattr(choice, f"choice_{lang}") for lang in AVAILABLE_LANGUAGES}
        )
        if languages:
            issues.append(
                Issue(
                    WARNING,
                    _("Options without text in %(languages)s.")
                    % {"languages": languages},
                )
            )
            break
    return issues


def block_issues(block):
    if (
        block.state_block == TrainingBlock.StateBlock.Active
        and not block.trainingquestion_set.all()
    ):
        return [Issue(WARNING, _("Active block without questions: trainees skip it."))]
    return []


def training_issues(training):
    active_with_questions = [
        block
        for block in training.trainingblock_set.all()
        if block.state_block == TrainingBlock.StateBlock.Active
        and block.trainingquestion_set.all()
    ]
    if not active_with_questions:
        return [Issue(ERROR, _("No active block with questions."))]
    return []


def course_issues(course, course_trainings):
    """`course_trainings`: los CourseTraining del curso en orden, con su training."""
    issues = []
    if not course_trainings:
        issues.append(Issue(ERROR, _("The course has no trainings.")))
    if course.final_exam_id and any(
        ct.training_id == course.final_exam_id for ct in course_trainings
    ):
        issues.append(
            Issue(ERROR, _("The final exam is also one of the course trainings."))
        )
    trainings = [ct.training for ct in course_trainings] + (
        [course.final_exam] if course.final_exam else []
    )
    for training in trainings:
        if training.state_training != training.StateTraining.Active:
            issues.append(
                Issue(
                    WARNING,
                    _('"%(training)s" is inactive: trainees do not see it.')
                    % {"training": training},
                )
            )
    if course.state_course != Course.StateCourse.Active:
        issues.append(Issue(WARNING, _("The course is inactive.")))
    if not course.groups.exists():
        issues.append(
            Issue(WARNING, _("No group assigned: no trainee can see the course."))
        )
    return issues
