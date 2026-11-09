import os

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.forms import BaseInlineFormSet
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _, ngettext
from import_export import resources  # Importa resources desde import_export
from import_export.admin import ExportActionMixin
from import_export.fields import Field
from modeltranslation.admin import TabbedTranslationAdmin, TranslationStackedInline
from modeltranslation.settings import AVAILABLE_LANGUAGES, DEFAULT_LANGUAGE
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import display
from unfold.widgets import UnfoldAdminSelect2MultipleWidget, UnfoldAdminSelectWidget

from userApp.models import Trainee

from . import admin_views
from .models import (
    Choice,
    ChoiceSet,
    ChoiceSetOption,
    Comment,
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


# Mixin para controlar la paginación desde un parámetro GET (?per_page=10|50|100)
class PaginationMixin:
    per_page_choices = (10, 50, 100)
    default_list_per_page = 20

    def changelist_view(self, request, extra_context=None):
        # Obtener el valor de paginación de la sesión
        session_key = (
            f"admin_per_page_{self.model._meta.app_label}_{self.model._meta.model_name}"
        )
        per_page_i = request.session.get(session_key)

        # Establecer list_per_page si es un valor válido
        if per_page_i in self.per_page_choices:
            self.list_per_page = per_page_i
        elif not hasattr(self, "list_per_page"):
            self.list_per_page = self.default_list_per_page

        if extra_context is None:
            extra_context = {}
        extra_context["per_page_choices"] = self.per_page_choices
        extra_context["current_per_page"] = getattr(
            self, "list_per_page", self.default_list_per_page
        )
        extra_context["request"] = request

        # Llamar al método padre con el contexto correcto
        return super().changelist_view(request, extra_context=extra_context)


class TranslatedModelAdmin(ModelAdmin, TabbedTranslationAdmin):
    """Admin de Unfold con los campos traducibles en pestañas EN/ES (modeltranslation)."""

    warn_unsaved_form = True


class OrderableInlineMixin:
    """Filas que se ordenan arrastrándolas (campo `order`); el script mantiene el botón "Agregar" al final."""

    ordering_field = "order"
    hide_ordering_field = True

    class Media:
        js = ("trainingApp/admin/inline_ordering.js",)


class TranslatedStackedInline(
    OrderableInlineMixin, StackedInline, TranslationStackedInline
):
    """Inline de Unfold con pestañas EN/ES y elementos ordenables; cada elemento es una tarjeta (filas con muchos campos)."""


def localized(field_name):
    """Campos por idioma de un campo traducible, p. ej. ('choice_en', 'choice_es')."""
    return tuple(f"{field_name}_{lang}" for lang in AVAILABLE_LANGUAGES)


class LanguageColumnsTabularInline(OrderableInlineMixin, TabularInline):
    """
    Inline tabular con una columna por idioma ("Texto (EN)", "Texto (ES)") en lugar de las pestañas de
    modeltranslation, que no se arman en las filas agregadas con "Agregar ... adicional" del markup de
    Unfold (la fila nueva quedaba con los campos corridos). `translated_fields` son los campos
    traducibles de la tabla; el del idioma por defecto es obligatorio, como con las pestañas.
    """

    translated_fields = ()

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        for name in self.translated_fields:
            for lang in AVAILABLE_LANGUAGES:
                if formfield and db_field.name == f"{name}_{lang}":
                    # "Texto (EN)": con corchetes ("[en]") el JS de modeltranslation los borra de los encabezados
                    formfield.label = f"{capfirst(self.model._meta.get_field(name).verbose_name)} ({lang.upper()})"
                    formfield.required = lang == DEFAULT_LANGUAGE
        return formfield


def object_page_url(model_admin, route, name, view):
    """URL de una página propia sobre un objeto (`<id>/route/`), con login y layout del admin."""
    opts = model_admin.model._meta
    return path(
        f"<int:object_id>/{route}/",
        model_admin.admin_site.admin_view(
            lambda request, object_id: view(request, object_id, model_admin)
        ),
        name=f"{opts.app_label}_{opts.model_name}_{name}",
    )


def changelist_link(model_name, filter_query, count):
    """Cantidad de elementos relacionados como enlace a su lista filtrada."""
    url = reverse(f"admin:trainingApp_{model_name}_changelist") + f"?{filter_query}"
    return format_html('<a href="{}">{}</a>', url, count)


STATUS_LABELS = {"Active": "success", "Inactive": "danger"}
ATTEMPT_LABELS = {
    TraineeTraining.StateTraineeTraining.PASSED: "success",
    TraineeTraining.StateTraineeTraining.FAILED: "danger",
    TraineeTraining.StateTraineeTraining.IN_PROGRESS: "warning",
}
AUDIO_MIME_TYPES = {".mp3": "audio/mpeg", ".wav": "audio/wav"}


def audio_preview_html(sound):
    if not sound:
        return "-"
    mime_type = AUDIO_MIME_TYPES.get(os.path.splitext(sound.name)[1].lower(), "")
    return format_html(
        '<audio controls preload="none"><source src="{}" type="{}"></audio>',
        sound.url,
        mime_type,
    )


class MediaPreviewMixin:
    """Reproductor del audio de una pregunta (campo de solo lectura; la imagen ya muestra su miniatura)."""

    @admin.display(description=_("Listen"))
    def audio_preview(self, obj):
        return audio_preview_html(obj.deploy_sound) if obj else "-"


# Clase que define cómo se importarán/exportarán los objetos TrainingQuestionAnswer.
class TrainingQuestionAnswerResource(resources.ModelResource):
    # Se usa el campo block_answer para llegar al user_name
    username = Field(column_name="username", attribute="block_answer")
    deploy = Field(column_name="deploy", attribute="deploy")

    class Meta:
        model = TrainingQuestionAnswer
        fields = (
            "id",
            "selectedChoice",
            "is_correct",
            "deploy",
            "block_answer",
            "username",
        )
        export_order = fields

    # Metodo que sirve para transformar y formatear el valor de un campo específico antes de que se exporte a un formato externo
    def dehydrate_username(self, obj):
        return str(obj.block_answer.trainee_Training.trainee.user.username)

    def dehydrate_selectedChoice(self, obj):
        return str(obj.selectedChoice.choice)

    # Formato fijo ("Deploy <id>: <texto>") para no romper los análisis existentes si cambia el __str__ de la pregunta
    def dehydrate_deploy(self, obj):
        if obj.deploy.question:
            return f"Deploy {obj.deploy.id}: {obj.deploy.question}"
        return f"Deploy {obj.deploy.id}"


class TrainingQuestionResource(resources.ModelResource):
    class Meta:
        model = TrainingQuestion
        fields = (
            "id",
            "question",
        )


# Clases que heredan de ModelAdmin (Unfold) gestionan el estilo en el admin
class TrainingAdmin(TranslatedModelAdmin):
    list_display = (
        "name_training",
        "view_blocks",
        "view_courses",
        "difficulty",
        "status",
        "estimatedDuration",
        "attempts_allowed",
        "pub_date",
    )
    list_display_links = ("name_training",)
    list_filter = ("difficulty", "state_training")
    search_fields = ("name_training",)
    ordering = ("-pub_date",)
    actions = ("duplicate_trainings",)

    def get_urls(self):
        return [
            object_page_url(self, "preview", "preview", admin_views.training_preview)
        ] + super().get_urls()

    def get_queryset(self, request):
        # Cantidades de las columnas en la misma consulta (distinct: son dos relaciones múltiples)
        return (
            super()
            .get_queryset(request)
            .annotate(
                block_count=Count("trainingblock", distinct=True),
                course_count=Count("courses", distinct=True),
            )
        )

    @admin.action(
        description=_(
            "Duplicate selected trainings (with blocks, questions and options)"
        ),
        permissions=["add"],
    )
    def duplicate_trainings(self, request, queryset):
        for training in queryset:
            training.duplicate()
        count = queryset.count()
        self.message_user(
            request,
            ngettext(
                "%(count)d training duplicated.",
                "%(count)d trainings duplicated.",
                count,
            )
            % {"count": count},
        )

    @display(description=_("Status"), label=STATUS_LABELS, ordering="state_training")
    def status(self, obj):
        return obj.state_training, obj.get_state_training_display()

    @admin.display(description=_("Blocks"))
    def view_blocks(self, obj):
        return changelist_link(
            "trainingblock", f"training__id__exact={obj.id}", obj.block_count
        )

    @admin.display(description=_("Courses"))
    def view_courses(self, obj):
        return changelist_link(
            "course", f"trainings__id__exact={obj.id}", obj.course_count
        )


class TrainingBlockAdmin(TranslatedModelAdmin):
    list_display = (
        "name_block",
        "view_questions",
        "training",
        "order",
        "status",
        "estimed_duration_block",
    )
    list_display_links = ("name_block",)
    list_filter = ("state_block", "training")
    search_fields = ("name_block", "description")
    list_select_related = ("training",)
    autocomplete_fields = ("training", "default_choice_set")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "training",
                    "name_block",
                    "description",
                    "state_block",
                    "estimed_duration_block",
                ),
            },
        ),
        (
            _("Defaults for new questions"),
            {
                "fields": ("default_question", "default_choice_set"),
                "description": _(
                    "New questions of this block start with this text and copy the options of this set. "
                    "Then you only upload the sound and pick the correct option."
                ),
            },
        ),
    )

    def get_urls(self):
        return [
            object_page_url(
                self, "bulk-upload", "bulk_upload", admin_views.block_bulk_upload
            )
        ] + super().get_urls()

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(question_count=Count("trainingquestion"))
        )

    def response_add(self, request, obj, post_url_continue=None):
        """Creado desde "Agregar bloque" de un entrenamiento (?training=<id>): volver a ese entrenamiento."""
        response = super().response_add(request, obj, post_url_continue)
        if not request.GET.get("training") or {"_continue", "_popup"} & set(
            request.POST
        ):
            return response
        if "_addanother" in request.POST:
            return HttpResponseRedirect(admin_views.add_block_url(obj.training_id))
        return HttpResponseRedirect(
            reverse("admin:trainingApp_training_change", args=[obj.training_id])
        )

    @display(description=_("Status"), label=STATUS_LABELS, ordering="state_block")
    def status(self, obj):
        return obj.state_block, obj.get_state_block_display()

    @admin.display(description=_("Questions"))
    def view_questions(self, obj):
        return changelist_link(
            "trainingquestion", f"block__id__exact={obj.id}", obj.question_count
        )


class TrainingQuestionAdminForm(forms.ModelForm):
    apply_choice_set = forms.ModelChoiceField(
        queryset=ChoiceSet.objects.all(),
        required=False,
        label=_("Copy options from set"),
        help_text=_(
            "Creates this question's options from the set. Afterwards, mark the correct one."
        ),
        widget=UnfoldAdminSelectWidget,
    )


class TrainingQuestionAdmin(MediaPreviewMixin, TranslatedModelAdmin):
    form = TrainingQuestionAdminForm
    list_display = ("question", "audio_preview", "view_options", "block", "order")
    list_filter = ("block__training", "block")
    search_fields = ("question", "block__name_block")
    list_select_related = ("block__training",)
    ordering = ("block", "order", "id")
    readonly_fields = ("audio_preview",)
    autocomplete_fields = ("block",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(option_count=Count("choice"))

    def get_fieldsets(self, request, obj=None):
        # replace_orig_field expande 'question' a sus campos por idioma, como hace modeltranslation con `fieldsets`
        main_fields = self.replace_orig_field(
            ("block", "question", ("deploy_sound", "audio_preview"), "deploy_image")
        )
        fieldsets = [(None, {"fields": main_fields})]
        # Copiar un conjunto solo tiene sentido mientras la pregunta no tiene opciones
        if obj is None or not obj.choice_set.exists():
            fieldsets.append((_("Options"), {"fields": ("apply_choice_set",)}))
        return fieldsets

    def get_changeform_initial_data(self, request):
        """Con ?block=<id> (enlaces "Add question") la pregunta arranca con los defaults del bloque."""
        initial = super().get_changeform_initial_data(request)
        block_id = str(initial.get("block", ""))
        block = (
            TrainingBlock.objects.filter(pk=block_id).first()
            if block_id.isdigit()
            else None
        )
        if block:
            for lang in AVAILABLE_LANGUAGES:
                initial.setdefault(
                    f"question_{lang}", getattr(block, f"default_question_{lang}")
                )
            initial.setdefault("apply_choice_set", block.default_choice_set_id)
        return initial

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        choice_set = form.cleaned_data.get("apply_choice_set")
        question = form.instance
        if choice_set and not question.choice_set.exists():
            question.apply_choice_set(choice_set)
            request.choice_set_applied = True
            messages.warning(
                request,
                _('Options copied from "%(set)s". Mark the correct option and save.')
                % {"set": choice_set},
            )

    def response_add(self, request, obj, post_url_continue=None):
        # Después de copiar opciones se vuelve a la pregunta para marcar la correcta
        if getattr(request, "choice_set_applied", False):
            return HttpResponseRedirect(
                reverse("admin:trainingApp_trainingquestion_change", args=[obj.pk])
            )
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if getattr(request, "choice_set_applied", False):
            return HttpResponseRedirect(
                reverse("admin:trainingApp_trainingquestion_change", args=[obj.pk])
            )
        return super().response_change(request, obj)

    @admin.display(description=_("Options"))
    def view_options(self, obj):
        return changelist_link(
            "choice", f"deploy__id__exact={obj.id}", obj.option_count
        )


class ChoiceAdmin(TranslatedModelAdmin):
    list_display = ("choice", "deploy", "correctChoice")
    list_filter = ("correctChoice", "deploy")
    search_fields = ("choice",)

    def has_module_permission(self, request):
        # Las opciones se editan desde su pregunta: se oculta del menú pero sigue accesible por enlace
        return False


class ChoiceSetOptionInline(LanguageColumnsTabularInline):
    model = ChoiceSetOption
    translated_fields = ("text",)
    fields = (*localized("text"), "order")
    extra = 0


class ChoiceSetAdmin(TranslatedModelAdmin):
    list_display = ("name", "options_summary", "blocks_using")
    list_display_links = ("name",)
    search_fields = ("name",)
    inlines = (ChoiceSetOptionInline,)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related("options", "trainingblock_set")
        )

    @admin.display(description=_("Options"))
    def options_summary(self, obj):
        return " / ".join(option.text for option in obj.options.all())

    @admin.display(description=_("Blocks using it by default"))
    def blocks_using(self, obj):
        return len(obj.trainingblock_set.all())


class TraineeTrainingAdmin(ModelAdmin):
    list_display = (
        "trainee",
        "training",
        "course",
        "result",
        "score_percentage",
        "pub_date",
        "time_spent",
    )
    list_filter = ("state", "is_final_exam_attempt", "training", "course")
    search_fields = (
        "trainee__user__username",
        "training__name_training",
        "course__name_course",
    )
    list_select_related = ("trainee__user", "training", "course")
    raw_id_fields = ("trainee", "training", "course")

    @display(description=_("Result"), label=ATTEMPT_LABELS, ordering="state")
    def result(self, obj):
        return obj.state, obj.get_state_display()


# Clase que permite que el modelo TrainingQuestionAnswer tenga acciones de exportación en el panel de administración
class TrainingQuestionAnswerAdmin(ExportActionMixin, ModelAdmin):
    resource_class = TrainingQuestionAnswerResource
    list_display = ("deploy", "get_trainee_username", "selectedChoice", "is_correct")
    list_filter = ("is_correct",)
    search_fields = (
        "deploy__question",
        "block_answer__trainee_Training__trainee__user__username",
    )
    list_select_related = (
        "block_answer__trainee_Training__trainee__user",
        "selectedChoice",
        "deploy",
    )
    # Un <select> listaría todos los bloques respondidos, preguntas y opciones (con consultas por cada uno)
    raw_id_fields = ("block_answer", "deploy", "selectedChoice")

    @admin.display(description=_("Trainee"))
    def get_trainee_username(self, obj):
        try:
            return obj.block_answer.trainee_Training.trainee.user.username
        except AttributeError:
            return None


class CommentAdmin(ModelAdmin):
    list_display = ("training", "get_trainee_username", "stars", "pub_date")
    list_filter = ("stars", "training")
    search_fields = ("trainee__user__username", "training__name_training")

    @admin.display(description=_("Trainee"))
    def get_trainee_username(self, obj):
        try:
            return obj.trainee.user.username
        except AttributeError:
            return None


class TrainingBlockAnswerAdmin(ModelAdmin):
    list_display = ("block", "trainee_Training", "state_block")
    list_filter = ("state_block", "block")
    search_fields = ("trainee_Training__trainee__user__username", "block__name_block")


def trainee_label(trainee):
    """ "Ana Pérez (ana) · Grupo A": el grupo actual avisa que agregarlo lo saca de ese grupo."""
    full_name = trainee.user.get_full_name()
    name = (
        f"{full_name} ({trainee.user.username})" if full_name else trainee.user.username
    )
    return f"{name} · {trainee.group or _('no group')}"


class TraineeMultipleChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        return trainee_label(obj)


class TraineeGroupAdminForm(forms.ModelForm):
    """
    El grupo se arma desde su propia página: qué cursos ve y qué trainees lo integran.
    Los cursos son la relación `Course.groups` vista desde el grupo; los miembros, los
    `Trainee.group` que apuntan a él. Ambos se guardan en `TraineeGroupAdmin.save_related`.
    """

    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.order_by("name_course"),
        required=False,
        label=_("Courses"),
        help_text=_(
            "The trainees of this group see these courses (only the active ones)."
        ),
        widget=UnfoldAdminSelect2MultipleWidget,
    )
    members = TraineeMultipleChoiceField(
        queryset=Trainee.objects.select_related("user", "group").order_by(
            "user__username"
        ),
        required=False,
        label=_("Trainees"),
        help_text=_(
            "Type to search. A trainee belongs to only one group: adding them here moves them "
            "out of their current group. Trainees removed from this group go to the default group."
        ),
        widget=UnfoldAdminSelect2MultipleWidget,
    )

    class Meta:
        model = TraineeGroup
        fields = ("name_group", "description", "is_default")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Los campos pueden faltar si el usuario no tiene permiso para editarlos (get_form)
        if self.instance.pk and "courses" in self.fields:
            self.fields["courses"].initial = self.instance.courses.all()
        if self.instance.pk and "members" in self.fields:
            self.fields["members"].initial = self.instance.trainee_set.all()

    def clean(self):
        cleaned_data = super().clean()
        members = cleaned_data.get("members")
        # self.instance todavía tiene los valores guardados: se copian del form después de clean()
        if self.instance.pk and self.instance.is_default and members is not None:
            kept = {trainee.pk for trainee in members}
            if self.instance.trainee_set.exclude(pk__in=kept).exists():
                self.add_error(
                    "members",
                    _(
                        "Trainees cannot be removed from the default group: "
                        "add them to another group instead."
                    ),
                )
        return cleaned_data


class TraineeGroupAdmin(ModelAdmin):
    form = TraineeGroupAdminForm
    list_display = (
        "name_group",
        "is_default",
        "view_members",
        "courses_summary",
        "description",
    )
    list_display_links = ("name_group",)
    search_fields = ("name_group", "description")
    readonly_fields = ("access_summary", "courses_display", "members_display")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(member_count=Count("trainee", distinct=True))
            .prefetch_related("courses")
        )

    def can_edit_courses(self, request, obj):
        return self.has_change_permission(request, obj) and request.user.has_perm(
            "trainingApp.change_course"
        )

    def can_edit_members(self, request, obj):
        return self.has_change_permission(request, obj) and request.user.has_perm(
            "userApp.change_trainee"
        )

    def get_fieldsets(self, request, obj=None):
        # Sin permiso para cambiarlos, cursos y trainees se muestran como texto; sin permiso para
        # ver trainees (rol "Content editor") la sección de miembros no aparece
        courses_field = (
            "courses" if self.can_edit_courses(request, obj) else "courses_display"
        )
        access_fields = (courses_field, "access_summary") if obj else (courses_field,)
        if self.can_edit_members(request, obj):
            members_fields = ("members",)
        elif request.user.has_perm("userApp.view_trainee"):
            members_fields = ("members_display",)
        else:
            members_fields = ()
        fieldsets = (
            (None, {"fields": ("name_group", "description", "is_default")}),
            (
                _("What the group sees"),
                {
                    "fields": access_fields,
                    "description": _(
                        "Trainees only see the active courses assigned to their group, "
                        "and inside each course its active trainings in order."
                    ),
                },
            ),
        )
        if members_fields:
            fieldsets += ((_("Who is in the group"), {"fields": members_fields}),)
        return fieldsets

    def get_form(self, request, obj=None, change=False, **kwargs):
        # Los campos que no están en los fieldsets (sin permiso) no se validan ni se guardan
        form = super().get_form(request, obj, change, **kwargs)
        if not self.can_edit_courses(request, obj):
            form.base_fields.pop("courses", None)
        if not self.can_edit_members(request, obj):
            form.base_fields.pop("members", None)
        return form

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        group = form.instance
        if "courses" in form.cleaned_data:
            group.courses.set(form.cleaned_data["courses"])
        if "members" in form.cleaned_data:
            self.save_members(request, group, form.cleaned_data["members"])

    def save_members(self, request, group, members):
        selected = {trainee.pk for trainee in members}
        current = set(group.trainee_set.values_list("pk", flat=True))
        added, removed = selected - current, current - selected
        if added:
            Trainee.objects.filter(pk__in=added).update(group=group)
        if removed:
            default_group = TraineeGroup.get_default()
            Trainee.objects.filter(pk__in=removed).update(group=default_group)
            messages.info(
                request,
                ngettext(
                    '%(count)d trainee moved to the default group "%(group)s".',
                    '%(count)d trainees moved to the default group "%(group)s".',
                    len(removed),
                )
                % {"count": len(removed), "group": default_group},
            )

    def has_delete_permission(self, request, obj=None):
        # El grupo por defecto recibe a los usuarios nuevos y a los de los grupos borrados
        if obj is not None and obj.is_default:
            return False
        return super().has_delete_permission(request, obj)

    @admin.display(description=_("Trainees"), ordering="member_count")
    def view_members(self, obj):
        url = (
            reverse("admin:userApp_trainee_changelist") + f"?group__id__exact={obj.id}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.member_count)

    @admin.display(description=_("Courses"))
    def courses_summary(self, obj):
        courses = list(obj.courses.all())
        if not courses:
            return _("None: sees no course")
        return ", ".join(
            (
                str(course)
                if course.state_course == Course.StateCourse.Active
                else _("%(course)s (inactive)") % {"course": course}
            )
            for course in courses
        )

    @admin.display(description=_("Courses"))
    def courses_display(self, obj):
        return self.courses_summary(obj) if obj and obj.pk else "-"

    @admin.display(description=_("Trainees"))
    def members_display(self, obj):
        if not obj or not obj.pk:
            return "-"
        trainees = obj.trainee_set.select_related("user").order_by("user__username")
        return ", ".join(str(trainee) for trainee in trainees) or "-"

    @admin.display(description=_("Courses and trainings they see"))
    def access_summary(self, obj):
        # render_to_string devuelve HTML seguro (plantilla con autoescape)
        return admin_views.group_access_html(obj)


def final_position(obj):
    """Posición 1..n del training dentro de su curso."""
    if not obj.pk or not obj.course_id:
        return "-"
    ordered_ids = list(
        CourseTraining.objects.filter(course_id=obj.course_id)
        .order_by("order", "id")
        .values_list("id", flat=True)
    )
    return (
        format_html("<strong>#{}</strong>", ordered_ids.index(obj.id) + 1)
        if obj.id in ordered_ids
        else "-"
    )


class CourseAdmin(TranslatedModelAdmin):
    list_display = (
        "name_course",
        "view_trainings",
        "groups_summary",
        "view_trainees",
        "status",
        "pub_date",
        "view_structure",
    )
    list_filter = ("state_course", "groups")
    list_display_links = ("name_course",)
    search_fields = ("name_course", "description")
    ordering = ("-pub_date",)
    autocomplete_fields = ("groups",)

    fieldsets = (
        (
            _("General information"),
            {"fields": ("name_course", "description", "state_course")},
        ),
        (
            _("Who sees the course"),
            {
                "fields": ("groups",),
                "description": _(
                    "Trainees see the course if it is active and their group is in this list. "
                    "You can also assign courses from each trainee group."
                ),
            },
        ),
        (
            _("Final exam"),
            {
                "fields": (
                    "final_exam",
                    "required_average_score",
                    "final_exam_passing_score",
                ),
                "description": _(
                    "Configure the final exam, the minimum average to unlock it and the score to pass it."
                ),
            },
        ),
    )

    def get_queryset(self, request):
        # distinct: el filtro por grupos (relación múltiple) multiplicaría las filas del conteo
        return (
            super()
            .get_queryset(request)
            .annotate(
                training_count=Count("trainings", distinct=True),
                trainee_count=Count("groups__trainee", distinct=True),
            )
            .prefetch_related("groups")
        )

    @display(description=_("Status"), label=STATUS_LABELS, ordering="state_course")
    def status(self, obj):
        return obj.state_course, obj.get_state_course_display()

    @admin.display(description=_("Groups"))
    def groups_summary(self, obj):
        groups = obj.groups.all()
        return ", ".join(str(group) for group in groups) or _("None: nobody sees it")

    @admin.display(description=_("Trainees in its groups"), ordering="trainee_count")
    def view_trainees(self, obj):
        # Trainees de los grupos del curso (lo ven solo si además el curso está activo)
        if not obj.trainee_count:
            return 0
        group_ids = ",".join(str(group.pk) for group in obj.groups.all())
        url = (
            reverse("admin:userApp_trainee_changelist") + f"?group__id__in={group_ids}"
        )
        return format_html('<a href="{}">{}</a>', url, obj.trainee_count)

    @admin.display(description=_("Trainings"))
    def view_trainings(self, obj):
        return changelist_link(
            "training", f"courses__id__exact={obj.id}", obj.training_count
        )

    @admin.display(description=_("Structure"))
    def view_structure(self, obj):
        # Botón de Unfold (no un enlace de texto) para que se vea como la acción principal de la fila
        return render_to_string(
            "unfold/components/button.html",
            {
                "href": reverse("admin:trainingApp_course_structure", args=[obj.pk]),
                "variant": "default",
                "children": format_html(
                    '<span class="material-symbols-outlined">account_tree</span> {}',
                    _("View structure"),
                ),
            },
        )

    def get_urls(self):
        return [
            object_page_url(
                self, "structure", "structure", admin_views.course_structure
            )
        ] + super().get_urls()


class TraineeCourseAdmin(ModelAdmin):
    list_display = (
        "trainee",
        "course",
        "state",
        "current_training_index",
        "exam_passed",
        "pub_date",
    )
    list_filter = ("state", "course", "exam_passed")
    search_fields = ("trainee__user__username", "course__name_course")
    raw_id_fields = ("trainee", "course")


class TrainingBlockInline(OrderableInlineMixin, TabularInline):
    """
    Bloques en la página del entrenamiento: resumen para ordenarlos (arrastrando), abrirlos o borrarlos.
    Se crean y editan en su propia página, con todos los campos y EN/ES: el botón "Agregar bloque" de
    la plantilla abre ese formulario con el entrenamiento ya elegido.
    """

    model = TrainingBlock
    template = "admin/trainingApp/training/blocks_inline.html"
    fields = (
        "block_name",
        "state_block",
        "estimed_duration_block",
        "question_count",
        "order",
    )
    readonly_fields = (
        "block_name",
        "state_block",
        "estimed_duration_block",
        "question_count",
    )
    extra = 0
    show_change_link = True

    def get_queryset(self, request):
        return (
            super().get_queryset(request).annotate(questions=Count("trainingquestion"))
        )

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description=_("name"))
    def block_name(self, obj):
        return obj.name_block

    @admin.display(description=_("Questions"))
    def question_count(self, obj):
        return obj.questions


# Attach inline to TrainingAdmin so Blocks are grouped on the Training change page
TrainingAdmin.inlines = getattr(TrainingAdmin, "inlines", ()) + (TrainingBlockInline,)


class QuestionInlineFormSet(BaseInlineFormSet):
    """Pasa el bloque padre a cada formulario para ofrecer las opciones de su conjunto por defecto."""

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs["parent_block"] = self.instance
        return kwargs


class QuestionInlineForm(forms.ModelForm):
    """
    Pregunta dentro de la página del bloque con un campo `correct_option`:
    - si la pregunta ya tiene opciones, elige cuál es la correcta;
    - si no tiene y el bloque tiene conjunto por defecto, al guardar se copian sus opciones
      y queda marcada la elegida. La consigna arranca con la del bloque.
    """

    correct_option = forms.ChoiceField(
        label=_("Correct option"), required=False, widget=UnfoldAdminSelectWidget
    )

    def __init__(self, *args, parent_block=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_set = None
        choices = list(self.instance.choice_set.all()) if self.instance.pk else []
        if choices:
            options = [(str(choice.pk), choice.choice) for choice in choices]
            self.fields["correct_option"].initial = next(
                (str(c.pk) for c in choices if c.correctChoice), ""
            )
        elif parent_block is not None and parent_block.default_choice_set_id:
            self.template_set = parent_block.default_choice_set
            options = [
                (str(option.pk), option.text)
                for option in self.template_set.options.all()
            ]
            if not self.instance.pk:
                for lang in AVAILABLE_LANGUAGES:
                    field_name = f"question_{lang}"
                    if field_name in self.fields:
                        self.fields[field_name].initial = getattr(
                            parent_block, f"default_question_{lang}"
                        )
        else:
            options = []
        self.fields["correct_option"].choices = [("", "---------")] + options

    def clean(self):
        cleaned_data = super().clean()
        if (
            self.template_set is not None
            and self.has_changed()
            and not cleaned_data.get("correct_option")
        ):
            self.add_error("correct_option", _("Select the correct option."))
        return cleaned_data

    def save(self, commit=True):
        question = super().save(commit=commit)
        if commit:
            self.save_correct_option()
        else:
            save_m2m = self.save_m2m

            def save_m2m_and_options():
                save_m2m()
                self.save_correct_option()

            self.save_m2m = save_m2m_and_options
        return question

    def save_correct_option(self):
        value = self.cleaned_data.get("correct_option")
        if self.template_set is not None:
            correct = (
                self.template_set.options.filter(pk=value).first() if value else None
            )
            self.instance.apply_choice_set(self.template_set, correct)
        elif value and "correct_option" in self.changed_data:
            self.instance.choice_set.update(correctChoice=False)
            self.instance.choice_set.filter(pk=value).update(correctChoice=True)


class TrainingQuestionInline(MediaPreviewMixin, TranslatedStackedInline):
    """Preguntas en la página del bloque: una tarjeta por pregunta con texto, sonido, imagen y opción correcta."""

    model = TrainingQuestion
    form = QuestionInlineForm
    formset = QuestionInlineFormSet
    fields = (
        "question",
        ("deploy_sound", "audio_preview"),
        "deploy_image",
        "correct_option",
        "order",
    )
    readonly_fields = ("audio_preview",)
    extra = 0
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("choice_set")


# Attach TrainingQuestionInline to TrainingBlockAdmin so Deploys are grouped on the Block change page
TrainingBlockAdmin.inlines = getattr(TrainingBlockAdmin, "inlines", ()) + (
    TrainingQuestionInline,
)


class ChoiceInlineFormSet(BaseInlineFormSet):
    """Si la pregunta tiene opciones: al menos dos y exactamente una correcta."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        kept = [
            form
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get("DELETE")
        ]
        if not kept:
            return
        if len(kept) < 2:
            raise ValidationError(_("A question needs at least two options."))
        if sum(1 for form in kept if form.cleaned_data.get("correctChoice")) != 1:
            raise ValidationError(_("Mark exactly one option as correct."))


class ChoiceInline(LanguageColumnsTabularInline):
    """Show Choices inside the Deploy change page for quick overview and edits."""

    model = Choice
    formset = ChoiceInlineFormSet
    translated_fields = ("choice",)
    fields = (*localized("choice"), "correctChoice", "order")
    extra = 0


# Attach ChoiceInline to TrainingQuestionAdmin so Choices are grouped on the Deploy change page
TrainingQuestionAdmin.inlines = getattr(TrainingQuestionAdmin, "inlines", ()) + (
    ChoiceInline,
)


class CourseTrainingInlineFormSet(BaseInlineFormSet):
    """El examen final no puede ser también uno de los trainings del curso."""

    def clean(self):
        super().clean()
        if any(self.errors) or not self.instance.final_exam_id:
            return
        for form in self.forms:
            training = form.cleaned_data.get("training") if form.cleaned_data else None
            if (
                training
                and not form.cleaned_data.get("DELETE")
                and training.pk == self.instance.final_exam_id
            ):
                raise ValidationError(
                    _("The final exam cannot also be one of the course trainings.")
                )


class CourseTrainingInline(OrderableInlineMixin, TabularInline):
    """Show CourseTrainings inside the Course change page; drag rows to change the order."""

    model = CourseTraining
    formset = CourseTrainingInlineFormSet
    fields = ("training", "get_final_position", "order")
    extra = 0
    show_change_link = True
    autocomplete_fields = ("training",)
    readonly_fields = ("get_final_position",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Ordenar solo por el campo 'order' (orden secuencial)
        return qs.select_related("training").order_by("order", "id")

    @admin.display(description=_("Position"))
    def get_final_position(self, obj):
        return final_position(obj)


# Attach inline to CourseAdmin so CourseTrainings are grouped on the Course change page
CourseAdmin.inlines = getattr(CourseAdmin, "inlines", ()) + (CourseTrainingInline,)


class TrainingCourseInline(TabularInline):
    """Show CourseTrainings inside the Training change page for quick overview and edits."""

    model = CourseTraining
    fields = ("course", "get_final_position")
    extra = 0
    show_change_link = True
    autocomplete_fields = ("course",)
    readonly_fields = ("get_final_position",)
    verbose_name = _("course where it is used")
    verbose_name_plural = _("courses where it is used")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Ordenar solo por el campo 'order' (orden secuencial)
        return qs.select_related("course").order_by("order", "id")

    @admin.display(description=_("Position in the course"))
    def get_final_position(self, obj):
        return final_position(obj)


# Attach inline to TrainingAdmin so CourseTrainings are grouped on the Training change page
TrainingAdmin.inlines = getattr(TrainingAdmin, "inlines", ()) + (TrainingCourseInline,)


admin.site.register(Training, TrainingAdmin)
admin.site.register(TrainingBlock, TrainingBlockAdmin)
admin.site.register(TrainingQuestion, TrainingQuestionAdmin)
admin.site.register(Choice, ChoiceAdmin)
admin.site.register(ChoiceSet, ChoiceSetAdmin)
admin.site.register(TraineeTraining, TraineeTrainingAdmin)
admin.site.register(TrainingQuestionAnswer, TrainingQuestionAnswerAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(TrainingBlockAnswer, TrainingBlockAnswerAdmin)
admin.site.register(TraineeGroup, TraineeGroupAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(TraineeCourse, TraineeCourseAdmin)
