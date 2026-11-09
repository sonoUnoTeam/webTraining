"""
Páginas propias dentro del admin para armar cursos: estructura del curso, carga masiva de
preguntas en un bloque y vista previa de un training como lo ve el trainee.

Se registran desde `get_urls()` de los ModelAdmin (admin.py), así que usan el login, los
permisos y el layout del admin. Cada vista recibe el ModelAdmin que la registra.
"""

import os

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.validators import FileExtensionValidator, validate_image_file_extension
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.translation import gettext as _, gettext_lazy
from modeltranslation.settings import AVAILABLE_LANGUAGES
from unfold.widgets import UnfoldAdminSelectWidget, UnfoldAdminTextInputWidget

from . import content_checks, rules
from .models import (
    ChoiceSet,
    Course,
    CourseTraining,
    Training,
    TrainingBlock,
    TrainingQuestion,
)


def admin_context(model_admin, request, title, **extra):
    return {
        **model_admin.admin_site.each_context(request),
        "opts": model_admin.model._meta,
        "title": title,
        **extra,
    }


# --- Estructura del curso ---


def question_tree(question):
    return {
        "question": question,
        "choices": list(question.choice_set.all()),
        "issues": content_checks.question_issues(question),
    }


def block_tree(block):
    return {
        "block": block,
        "add_question_url": reverse("admin:trainingApp_trainingquestion_add")
        + f"?block={block.pk}",
        "issues": content_checks.block_issues(block),
        "questions": [
            question_tree(question) for question in block.trainingquestion_set.all()
        ],
    }


def add_block_url(training_id):
    """Formulario de bloque nuevo con el entrenamiento ya elegido (al guardar vuelve al entrenamiento)."""
    return reverse("admin:trainingApp_trainingblock_add") + f"?training={training_id}"


def training_tree(training, is_final_exam=False):
    return {
        "training": training,
        "is_final_exam": is_final_exam,
        "add_block_url": add_block_url(training.pk),
        "issues": content_checks.training_issues(training),
        "blocks": [block_tree(block) for block in training.trainingblock_set.all()],
    }


def count_issues(trees, level):
    """Cuenta los problemas de un nivel en todo el árbol (trainings, bloques y preguntas)."""
    total = 0
    for training in trees:
        total += sum(issue.level == level for issue in training["issues"])
        for block in training["blocks"]:
            total += sum(issue.level == level for issue in block["issues"])
            for question in block["questions"]:
                total += sum(issue.level == level for issue in question["issues"])
    return total


def course_structure(request, course_id, model_admin):
    course = get_object_or_404(model_admin.get_queryset(request), pk=course_id)
    if not model_admin.has_view_permission(request, course):
        raise PermissionDenied
    course_trainings = list(
        CourseTraining.objects.filter(course=course)
        .select_related("training")
        .order_by("order", "id")
    )
    training_ids = [ct.training_id for ct in course_trainings] + (
        [course.final_exam_id] if course.final_exam_id else []
    )
    trainings = Training.objects.filter(pk__in=training_ids).prefetch_related(
        "trainingblock_set__trainingquestion_set__choice_set"
    )
    trainings_by_id = {training.pk: training for training in trainings}

    trees = [training_tree(trainings_by_id[ct.training_id]) for ct in course_trainings]
    if course.final_exam_id:
        trees.append(
            training_tree(trainings_by_id[course.final_exam_id], is_final_exam=True)
        )

    course_issues = content_checks.course_issues(course, course_trainings)
    context = admin_context(
        model_admin,
        request,
        _('Structure of "%(course)s"') % {"course": course},
        course=course,
        course_groups=course.groups.annotate(member_count=Count("trainee")),
        course_issues=course_issues,
        trainings=trees,
        error_count=count_issues(trees, content_checks.ERROR)
        + sum(i.level == content_checks.ERROR for i in course_issues),
        warning_count=count_issues(trees, content_checks.WARNING)
        + sum(i.level == content_checks.WARNING for i in course_issues),
    )
    return TemplateResponse(request, "admin/trainingApp/course/structure.html", context)


# --- Acceso de los grupos ---


def course_access(course):
    """Lo que ve un trainee del curso: si está activo, sus trainings activos en orden y el examen final."""
    final_exam = course.final_exam
    if final_exam and final_exam.state_training != Training.StateTraining.Active:
        final_exam = None
    return {
        "course": course,
        "active": course.state_course == Course.StateCourse.Active,
        "trainings": [ct.training for ct in rules.course_trainings(course)],
        "final_exam": final_exam,
    }


def group_access_html(group):
    """
    Resumen legible de qué ve un grupo: cada curso asignado con su secuencia de trainings.
    Los cursos inactivos se listan marcados porque siguen asignados aunque no se vean.
    """
    courses = []
    if group is not None and group.pk:
        courses = [
            course_access(course)
            for course in group.courses.select_related("final_exam").order_by("id")
        ]
    return render_to_string(
        "admin/trainingApp/traineegroup/access_summary.html",
        {"group": group, "courses": courses},
    )


# --- Carga masiva de preguntas en un bloque ---


class MultipleFileInput(forms.ClearableFileInput):
    # Input visible (no el de Unfold, que muestra un solo nombre de archivo)
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        super().__init__({"class": "bulk-upload-files", **(attrs or {})})


class MultipleFileField(forms.FileField):
    """Campo de varios archivos (patrón de la documentación de Django). Devuelve una lista."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]
        cleaned = single_file_clean(data, initial)
        return [cleaned] if cleaned else []


def file_stem(uploaded_file):
    return os.path.splitext(os.path.basename(uploaded_file.name))[0].lower()


class BulkUploadForm(forms.Form):
    sounds = MultipleFileField(
        label=gettext_lazy("Sounds"),
        validators=[FileExtensionValidator(allowed_extensions=["mp3", "wav"])],
        help_text=gettext_lazy(
            "One question is created per sound (mp3 or wav), ordered by file name."
        ),
    )
    images = MultipleFileField(
        label=gettext_lazy("Images"),
        required=False,
        validators=[validate_image_file_extension],
        help_text=gettext_lazy(
            "Optional. Each image is assigned to the sound with the same file name (x.mp3 ↔ x.png)."
        ),
    )
    choice_set = forms.ModelChoiceField(
        label=gettext_lazy("Choice set"),
        queryset=ChoiceSet.objects.all(),
        required=False,
        widget=UnfoldAdminSelectWidget,
        help_text=gettext_lazy(
            "Its options are copied to every question. Afterwards, mark the correct option of each one."
        ),
    )

    def __init__(self, *args, block, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["choice_set"].initial = block.default_choice_set_id
        for lang in AVAILABLE_LANGUAGES:
            self.fields[f"question_{lang}"] = forms.CharField(
                label=gettext_lazy("Question text (%(language)s)")
                % {"language": lang.upper()},
                max_length=255,
                required=False,
                initial=getattr(block, f"default_question_{lang}"),
                widget=UnfoldAdminTextInputWidget,
            )

    def clean(self):
        cleaned_data = super().clean()
        sound_stems = {file_stem(sound) for sound in cleaned_data.get("sounds", [])}
        unmatched = [
            image.name
            for image in cleaned_data.get("images", [])
            if file_stem(image) not in sound_stems
        ]
        if unmatched:
            raise forms.ValidationError(
                _("These images do not match any sound: %(names)s.")
                % {"names": ", ".join(unmatched)}
            )
        return cleaned_data


def create_questions(block, form):
    """Crea una pregunta por sonido con su imagen, la consigna y las opciones del conjunto elegido."""
    images = {file_stem(image): image for image in form.cleaned_data["images"]}
    choice_set = form.cleaned_data["choice_set"]
    created = []
    with transaction.atomic():
        for sound in sorted(
            form.cleaned_data["sounds"], key=lambda uploaded: uploaded.name.lower()
        ):
            question = TrainingQuestion(
                block=block,
                deploy_sound=sound,
                deploy_image=images.get(file_stem(sound), ""),
            )
            for lang in AVAILABLE_LANGUAGES:
                setattr(
                    question, f"question_{lang}", form.cleaned_data[f"question_{lang}"]
                )
            question.fill_from_block_defaults()
            question.save()
            if choice_set:
                question.apply_choice_set(choice_set)
            created.append(question)
    return created


def block_bulk_upload(request, block_id, model_admin):
    block = get_object_or_404(TrainingBlock, pk=block_id)
    if not (
        model_admin.has_change_permission(request, block)
        and request.user.has_perm("trainingApp.add_trainingquestion")
    ):
        raise PermissionDenied

    if request.method == "POST":
        form = BulkUploadForm(request.POST, request.FILES, block=block)
        if form.is_valid():
            created = create_questions(block, form)
            messages.success(
                request,
                _("%(count)d questions created. Mark the correct option of each one.")
                % {"count": len(created)},
            )
            return redirect("admin:trainingApp_trainingblock_change", block.pk)
    else:
        form = BulkUploadForm(block=block)

    context = admin_context(
        model_admin,
        request,
        _('Upload questions to "%(block)s"') % {"block": block.name_block},
        training_block=block,
        form=form,
        original=block,
    )
    return TemplateResponse(
        request, "admin/trainingApp/trainingblock/bulk_upload.html", context
    )


# --- Vista previa de un training ---


def training_preview(request, training_id, model_admin):
    training = get_object_or_404(model_admin.get_queryset(request), pk=training_id)
    if not model_admin.has_view_permission(request, training):
        raise PermissionDenied
    # Mismos bloques que recorre el trainee: activos y con preguntas, en orden
    blocks = rules.active_blocks(training).prefetch_related(
        "trainingquestion_set__choice_set"
    )
    context = admin_context(
        model_admin,
        request,
        _('Preview of "%(training)s"') % {"training": training},
        training=training,
        original=training,
        blocks=blocks,
        show_correct=request.GET.get("show_correct") == "1",
    )
    return TemplateResponse(request, "admin/trainingApp/training/preview.html", context)
