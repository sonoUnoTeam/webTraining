import os

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.urls import path
from django.utils.translation import ngettext
from . import admin_views
from .models import Training, TrainingQuestion, Choice, ChoiceSet, ChoiceSetOption, TrainingBlock, TraineeTraining, TrainingQuestionAnswer, Comment, TrainingBlockAnswer, TraineeGroup, CourseTraining, Course, TraineeCourse
from adminsortable2.admin import CustomInlineFormSet, SortableAdminBase, SortableInlineAdminMixin, SortableTabularInline
from import_export.admin import ExportActionMixin
from import_export import resources  # Importa resources desde import_export
from import_export.fields import Field
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from modeltranslation.settings import AVAILABLE_LANGUAGES
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.http import HttpResponseRedirect


# Mixin para controlar la paginación desde un parámetro GET (?per_page=10|50|100)
class PaginationMixin:
    per_page_choices = (10, 50, 100)
    default_list_per_page = 20

    def changelist_view(self, request, extra_context=None):
        # Obtener el valor de paginación de la sesión
        session_key = f'admin_per_page_{self.model._meta.app_label}_{self.model._meta.model_name}'
        per_page_i = request.session.get(session_key)

        # Establecer list_per_page si es un valor válido
        if per_page_i in self.per_page_choices:
            self.list_per_page = per_page_i
        elif not hasattr(self, 'list_per_page'):
            self.list_per_page = self.default_list_per_page

        if extra_context is None:
            extra_context = {}
        extra_context['per_page_choices'] = self.per_page_choices
        extra_context['current_per_page'] = getattr(self, 'list_per_page', self.default_list_per_page)
        extra_context['request'] = request

        # Llamar al método padre con el contexto correcto
        return super().changelist_view(request, extra_context=extra_context)


class TranslationMediaMixin:
    """
    Pestañas EN/ES de modeltranslation. Su JS necesita jQuery y jQuery UI globales; el admin
    usa su propia copia (django.jQuery), por eso se carga otra desde un CDN con versión fija.
    """
    class Media:
        js = (
            'https://cdnjs.cloudflare.com/ajax/libs/jquery/3.7.1/jquery.min.js',
            'https://cdnjs.cloudflare.com/ajax/libs/jqueryui/1.13.3/jquery-ui.min.js',
            'modeltranslation/js/tabbed_translation_fields.js',
        )
        css = {
            'all': ('modeltranslation/css/tabbed_translation_fields.css',),
        }


class SortableTranslationTabularInline(SortableInlineAdminMixin, TranslationTabularInline):
    """Inline tabular con pestañas EN/ES y orden por arrastre (campo `order` del modelo)."""
    template = SortableTabularInline.template


def object_page_url(model_admin, route, name, view):
    """URL de una página propia sobre un objeto (`<id>/route/`), con login y layout del admin."""
    opts = model_admin.model._meta
    return path(
        f'<int:object_id>/{route}/',
        model_admin.admin_site.admin_view(lambda request, object_id: view(request, object_id, model_admin)),
        name=f'{opts.app_label}_{opts.model_name}_{name}',
    )


AUDIO_MIME_TYPES = {'.mp3': 'audio/mpeg', '.wav': 'audio/wav'}


def audio_preview_html(sound):
    if not sound:
        return '-'
    mime_type = AUDIO_MIME_TYPES.get(os.path.splitext(sound.name)[1].lower(), '')
    return format_html('<audio controls preload="none"><source src="{}" type="{}"></audio>', sound.url, mime_type)


def image_preview_html(image):
    if not image:
        return '-'
    return format_html('<img src="{}" alt="" style="max-height: 60px; max-width: 120px;">', image.url)


class MediaPreviewMixin:
    """Reproductor de audio y miniatura de imagen de una pregunta (campos de solo lectura)."""

    @admin.display(description=_('Audio preview'))
    def audio_preview(self, obj):
        return audio_preview_html(obj.deploy_sound) if obj else '-'

    @admin.display(description=_('Image preview'))
    def image_preview(self, obj):
        return image_preview_html(obj.deploy_image) if obj else '-'


#Clase que define cómo se importarán/exportarán los objetos TrainingQuestionAnswer.
class TrainingQuestionAnswerResource(resources.ModelResource):
    #Se usa el campo block_answer para llegar al user_name
    username = Field(column_name='username',attribute='block_answer')
    deploy = Field(column_name='deploy', attribute='deploy')

    class Meta:
        model = TrainingQuestionAnswer
        fields = ('id', 'selectedChoice', 'is_correct', 'deploy', 'block_answer','username')
        export_order=fields

    #Metodo que sirve para transformar y formatear el valor de un campo específico antes de que se exporte a un formato externo
    def dehydrate_username(self,obj):
        return str(obj.block_answer.trainee_Training.trainee.user.username)

    def dehydrate_selectedChoice(self,obj):
        return str(obj.selectedChoice.choice)

class TrainingQuestionResource(resources.ModelResource):
    class Meta:
        model = TrainingQuestion
        fields = ('id','question',)



#Clases que heredan de admin.ModelAdmin gestionan el estilo en el admin
class TrainingAdmin(SortableAdminBase, TranslationMediaMixin, TranslationAdmin):
    list_display = ('id','name_training','view_blocks','view_courses','difficulty','state_training','estimatedDuration','attempts_allowed','pub_date')
    list_display_links = ('name_training',)
    list_filter = ('difficulty','state_training')
    search_fields = ('name_training',)
    ordering = ('-pub_date',)
    actions = ('duplicate_trainings',)

    def get_urls(self):
        return [object_page_url(self, 'preview', 'preview', admin_views.training_preview)] + super().get_urls()

    @admin.action(description=_('Duplicate selected trainings (with blocks, questions and options)'), permissions=['add'])
    def duplicate_trainings(self, request, queryset):
        for training in queryset:
            training.duplicate()
        count = queryset.count()
        self.message_user(request, ngettext('%(count)d training duplicated.', '%(count)d trainings duplicated.', count) % {'count': count})

    def view_blocks(self,obj):
        """Link to the Block changelist filtered by this training."""
        try:
            count = obj.trainingblock_set.count()
        except Exception:
            count = 0
        url = reverse('admin:trainingApp_trainingblock_changelist') + f'?training__id__exact={obj.id}'
        return format_html('<a href="{}">Blocks ({})</a>', url, count)
    view_blocks.short_description = 'Blocks'

    def view_courses(self,obj):
        """Link to the Course changelist filtered by this training."""
        try:
            count = obj.courses.count()
        except Exception:
            count = 0
        url = reverse('admin:trainingApp_course_changelist') + f'?trainings__id__exact={obj.id}'
        return format_html('<a href="{}">Courses ({})</a>', url, count)
    view_courses.short_description = 'Courses'

class TrainingBlockAdmin(SortableAdminBase, TranslationMediaMixin, TranslationAdmin):
    list_display = ('id','name_block','view_deploys', 'training', 'order', 'state_block','estimed_duration_block',)
    list_display_links = ('name_block',)
    list_filter = ('state_block','training')
    search_fields = ('name_block','description')
    list_select_related = ('training',)
    autocomplete_fields = ('training', 'default_choice_set')
    fieldsets = (
        (None, {
            'fields': ('training', 'name_block', 'description', 'state_block', 'estimed_duration_block'),
        }),
        (_('Defaults for new questions'), {
            'fields': ('default_question', 'default_choice_set'),
            'description': _('New questions of this block start with this text and copy the options of this set. '
                             'Then you only upload the sound and pick the correct option.'),
        }),
    )

    def get_urls(self):
        return [object_page_url(self, 'bulk-upload', 'bulk_upload', admin_views.block_bulk_upload)] + super().get_urls()

    def view_deploys(self,obj):
        """Link to the Deploy changelist filtered by this block."""
        try:
            count = obj.trainingquestion_set.count()
        except Exception:
            count = 0
        url = reverse('admin:trainingApp_trainingquestion_changelist') + f'?block__id__exact={obj.id}'
        return format_html('<a href="{}">Deploys ({})</a>', url, count)
    view_deploys.short_description = 'Deploys'


class TrainingQuestionAdminForm(forms.ModelForm):
    apply_choice_set = forms.ModelChoiceField(
        queryset=ChoiceSet.objects.all(),
        required=False,
        label=_('Copy options from set'),
        help_text=_('Creates this question\'s options from the set. Afterwards, mark the correct one.'),
    )


class TrainingQuestionAdmin(SortableAdminBase, MediaPreviewMixin, TranslationMediaMixin, TranslationAdmin):
    form = TrainingQuestionAdminForm
    list_display = ('id','question','view_choices','block','order','has_media')
    list_filter = ('block__training','block')
    search_fields = ('question','block__name_block')
    ordering = ('block','order','id')
    readonly_fields = ('audio_preview', 'image_preview')
    autocomplete_fields = ('block',)

    def get_fieldsets(self, request, obj=None):
        # replace_orig_field expande 'question' a sus campos por idioma, como hace modeltranslation con `fieldsets`
        main_fields = self.replace_orig_field(('block', 'question', 'deploy_sound', 'audio_preview', 'deploy_image', 'image_preview'))
        fieldsets = [(None, {'fields': main_fields})]
        # Copiar un conjunto solo tiene sentido mientras la pregunta no tiene opciones
        if obj is None or not obj.choice_set.exists():
            fieldsets.append((_('Options'), {'fields': ('apply_choice_set',)}))
        return fieldsets

    def get_changeform_initial_data(self, request):
        """Con ?block=<id> (enlaces "Add question") la pregunta arranca con los defaults del bloque."""
        initial = super().get_changeform_initial_data(request)
        block_id = str(initial.get('block', ''))
        block = TrainingBlock.objects.filter(pk=block_id).first() if block_id.isdigit() else None
        if block:
            for lang in AVAILABLE_LANGUAGES:
                initial.setdefault(f'question_{lang}', getattr(block, f'default_question_{lang}'))
            initial.setdefault('apply_choice_set', block.default_choice_set_id)
        return initial

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        choice_set = form.cleaned_data.get('apply_choice_set')
        question = form.instance
        if choice_set and not question.choice_set.exists():
            question.apply_choice_set(choice_set)
            request.choice_set_applied = True
            messages.warning(request, _('Options copied from "%(set)s". Mark the correct option and save.') % {'set': choice_set})

    def response_add(self, request, obj, post_url_continue=None):
        # Después de copiar opciones se vuelve a la pregunta para marcar la correcta
        if getattr(request, 'choice_set_applied', False):
            return HttpResponseRedirect(reverse('admin:trainingApp_trainingquestion_change', args=[obj.pk]))
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if getattr(request, 'choice_set_applied', False):
            return HttpResponseRedirect(reverse('admin:trainingApp_trainingquestion_change', args=[obj.pk]))
        return super().response_change(request, obj)

    def has_media(self,obj):
        return bool(obj.deploy_image) or bool(obj.deploy_sound)
    has_media.boolean = True
    has_media.short_description = 'Has media'

    def view_choices(self,obj):
        """Link to the Choice changelist filtered by this deploy."""
        try:
            count = obj.choice_set.count()
        except Exception:
            count = 0
        url = reverse('admin:trainingApp_choice_changelist') + f'?deploy__id__exact={obj.id}'
        return format_html('<a href="{}">Choices ({})</a>', url, count)
    view_choices.short_description = 'Choices'

class ChoiceAdmin(TranslationMediaMixin, TranslationAdmin):
    list_display = ('id','choice','deploy','correctChoice')
    list_filter = ('correctChoice','deploy')
    search_fields = ('choice',)

    def has_module_permission(self, request):
        # Las opciones se editan desde su pregunta: se oculta del menú pero sigue accesible por enlace
        return False


class ChoiceSetOptionInline(SortableTranslationTabularInline):
    model = ChoiceSetOption
    fields = ('text',)
    extra = 0


class ChoiceSetAdmin(SortableAdminBase, TranslationMediaMixin, TranslationAdmin):
    list_display = ('id', 'name', 'options_summary', 'blocks_using')
    list_display_links = ('name',)
    search_fields = ('name',)
    inlines = (ChoiceSetOptionInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('options', 'trainingblock_set')

    @admin.display(description=_('Options'))
    def options_summary(self, obj):
        return ' / '.join(option.text for option in obj.options.all())

    @admin.display(description=_('Blocks using it by default'))
    def blocks_using(self, obj):
        return len(obj.trainingblock_set.all())


class TraineeTrainingAdmin(admin.ModelAdmin):
    list_display = ('id','training','trainee','course','pub_date','state','time_spent')
    list_filter = ('state','training','course')
    search_fields = ('trainee__user__username','training__name_training','course__name_course')
    raw_id_fields = ('trainee','training','course')


#Clase que permite que el modelo TrainingQuestionAnswer tenga acciones de exportación en el panel de administración
class TrainingQuestionAnswerAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class= TrainingQuestionAnswerResource
    list_display = ('id','deploy','get_trainee_username','selectedChoice','is_correct')
    search_fields = ('deploy__question','block_answer__trainee_Training__trainee__user__username')
    list_select_related = ('block_answer','selectedChoice')

    def get_trainee_username(self,obj):
        try:
            return obj.block_answer.trainee_Training.trainee.user.username
        except Exception:
            return None
    get_trainee_username.short_description = 'Trainee'


class CommentAdmin(admin.ModelAdmin):
    list_display = ('id','training','get_trainee_username','stars','pub_date')
    list_filter = ('stars','training')
    search_fields = ('trainee__user__username','training__name_training')

    def get_trainee_username(self,obj):
        try:
            return obj.trainee.user.username
        except Exception:
            return None
    get_trainee_username.short_description = 'Trainee'


class TrainingBlockAnswerAdmin(admin.ModelAdmin):
    list_display = ('id','block','trainee_Training','state_block')
    list_filter = ('state_block','block')
    search_fields = ('trainee_Training__trainee__user__username','block__name_block')


class TraineeGroupAdmin(admin.ModelAdmin):
    list_display = ('id','name_group','description')
    search_fields = ('name_group',)


class CourseTrainingAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'training', 'get_final_position')
    list_filter = ('course', 'training')
    search_fields = ('course__name_course', 'training__name_training')
    ordering = ('course', 'order')

    def get_final_position(self, obj):
        if not obj.pk or not obj.course_id:
            return '-'
        # Ordenar solo por el campo 'order' (orden secuencial)
        all_trainings = CourseTraining.objects.filter(course=obj.course).select_related('training').order_by('order')
        try:
            position = next(i for i, ct in enumerate(all_trainings, 1) if ct.id == obj.id)
            return format_html('<strong>#{}</strong>', position)
        except StopIteration:
            return '-'
    get_final_position.short_description = 'Final Position'


class CourseAdmin(SortableAdminBase, TranslationMediaMixin, TranslationAdmin):
    list_display = ('id', 'name_course', 'view_trainings', 'view_structure', 'required_average_score', 'state_course', 'pub_date')
    list_filter = ('state_course', 'groups')
    list_display_links = ('name_course',)
    search_fields = ('name_course', 'description')
    ordering = ('-pub_date',)

    fieldsets = (
        ('General Information', {
            'fields': ('name_course', 'description', 'state_course', 'groups')
        }),
        ('Final Exam Configuration', {
            'fields': ('final_exam', 'required_average_score', 'final_exam_passing_score'),
            'description': 'Configure the final exam, minimum average score to unlock it, and passing score.'
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Agregar texto de ayuda
        if 'required_average_score' in form.base_fields:
            form.base_fields['required_average_score'].help_text = (
                'Minimum average score (%) from best training attempts required to unlock the final exam. Default: 70%'
            )
        if 'final_exam_passing_score' in form.base_fields:
            form.base_fields['final_exam_passing_score'].help_text = (
                'Minimum score (%) required to pass the final exam. Default: 70%'
            )
        return form

    def view_trainings(self, obj):
        """Link to the Training changelist filtered by this course."""
        try:
            count = obj.trainings.count()
        except Exception:
            count = 0
        url = reverse('admin:trainingApp_training_changelist') + f'?courses__id__exact={obj.id}'
        return format_html('<a href="{}">Trainings ({})</a>', url, count)
    view_trainings.short_description = 'Trainings'

    @admin.display(description=_('Structure'))
    def view_structure(self, obj):
        return format_html('<a href="{}">{}</a>', reverse('admin:trainingApp_course_structure', args=[obj.pk]), _('View'))

    def get_urls(self):
        return [object_page_url(self, 'structure', 'structure', admin_views.course_structure)] + super().get_urls()


class TraineeCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'trainee', 'course', 'state', 'current_training_index', 'exam_passed', 'pub_date')
    list_filter = ('state', 'course', 'exam_passed')
    search_fields = ('trainee__user__username', 'course__name_course')
    raw_id_fields = ('trainee', 'course')


class TrainingBlockInline(SortableTranslationTabularInline):
    """Show Blocks inside the Training change page for quick overview and edits."""
    model = TrainingBlock
    fields = ('name_block','state_block','estimed_duration_block')
    extra = 0
    show_change_link = True

# Attach inline to TrainingAdmin so Blocks are grouped on the Training change page
TrainingAdmin.inlines = getattr(TrainingAdmin, 'inlines', ()) + (TrainingBlockInline,)


class QuestionInlineFormSet(CustomInlineFormSet):
    """Pasa el bloque padre a cada formulario para ofrecer las opciones de su conjunto por defecto."""

    def get_form_kwargs(self, index):
        kwargs = super().get_form_kwargs(index)
        kwargs['parent_block'] = self.instance
        return kwargs


class QuestionInlineForm(forms.ModelForm):
    """
    Pregunta dentro de la página del bloque con un campo `correct_option`:
    - si la pregunta ya tiene opciones, elige cuál es la correcta;
    - si no tiene y el bloque tiene conjunto por defecto, al guardar se copian sus opciones
      y queda marcada la elegida. La consigna arranca con la del bloque.
    """
    correct_option = forms.ChoiceField(label=_('Correct option'), required=False)

    def __init__(self, *args, parent_block=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.template_set = None
        choices = list(self.instance.choice_set.all()) if self.instance.pk else []
        if choices:
            options = [(str(choice.pk), choice.choice) for choice in choices]
            self.fields['correct_option'].initial = next((str(c.pk) for c in choices if c.correctChoice), '')
        elif parent_block is not None and parent_block.default_choice_set_id:
            self.template_set = parent_block.default_choice_set
            options = [(str(option.pk), option.text) for option in self.template_set.options.all()]
            if not self.instance.pk:
                for lang in AVAILABLE_LANGUAGES:
                    field_name = f'question_{lang}'
                    if field_name in self.fields:
                        self.fields[field_name].initial = getattr(parent_block, f'default_question_{lang}')
        else:
            options = []
        self.fields['correct_option'].choices = [('', '---------')] + options

    def clean(self):
        cleaned_data = super().clean()
        if self.template_set is not None and self.has_changed() and not cleaned_data.get('correct_option'):
            self.add_error('correct_option', _('Select the correct option.'))
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
        value = self.cleaned_data.get('correct_option')
        if self.template_set is not None:
            correct = self.template_set.options.filter(pk=value).first() if value else None
            self.instance.apply_choice_set(self.template_set, correct)
        elif value and 'correct_option' in self.changed_data:
            self.instance.choice_set.update(correctChoice=False)
            self.instance.choice_set.filter(pk=value).update(correctChoice=True)


class TrainingQuestionInline(MediaPreviewMixin, SortableTranslationTabularInline):
    """Show Deploys inside the Block change page: text, media and correct option in one row."""
    model = TrainingQuestion
    form = QuestionInlineForm
    formset = QuestionInlineFormSet
    fields = ('question', 'deploy_sound', 'audio_preview', 'deploy_image', 'image_preview', 'correct_option')
    readonly_fields = ('audio_preview', 'image_preview')
    extra = 0
    show_change_link = True

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('choice_set')

# Attach TrainingQuestionInline to TrainingBlockAdmin so Deploys are grouped on the Block change page
TrainingBlockAdmin.inlines = getattr(TrainingBlockAdmin, 'inlines', ()) + (TrainingQuestionInline,)


class ChoiceInlineFormSet(CustomInlineFormSet):
    """Si la pregunta tiene opciones: al menos dos y exactamente una correcta."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        kept = [form for form in self.forms if form.cleaned_data and not form.cleaned_data.get('DELETE')]
        if not kept:
            return
        if len(kept) < 2:
            raise ValidationError(_('A question needs at least two options.'))
        if sum(1 for form in kept if form.cleaned_data.get('correctChoice')) != 1:
            raise ValidationError(_('Mark exactly one option as correct.'))


class ChoiceInline(SortableTranslationTabularInline):
    """Show Choices inside the Deploy change page for quick overview and edits."""
    model = Choice
    formset = ChoiceInlineFormSet
    fields = ('choice','correctChoice')
    extra = 0
    show_change_link = True

# Attach ChoiceInline to TrainingQuestionAdmin so Choices are grouped on the Deploy change page
TrainingQuestionAdmin.inlines = getattr(TrainingQuestionAdmin, 'inlines', ()) + (ChoiceInline,)


class CourseTrainingInlineFormSet(CustomInlineFormSet):
    """El examen final no puede ser también uno de los trainings del curso."""

    def clean(self):
        super().clean()
        if any(self.errors) or not self.instance.final_exam_id:
            return
        for form in self.forms:
            training = form.cleaned_data.get('training') if form.cleaned_data else None
            if training and not form.cleaned_data.get('DELETE') and training.pk == self.instance.final_exam_id:
                raise ValidationError(_('The final exam cannot also be one of the course trainings.'))


class CourseTrainingInline(SortableInlineAdminMixin, admin.TabularInline):
    """Show CourseTrainings inside the Course change page; drag rows to change the order."""
    model = CourseTraining
    formset = CourseTrainingInlineFormSet
    template = SortableTabularInline.template
    fields = ('training', 'get_final_position')
    extra = 0
    show_change_link = True
    autocomplete_fields = ('training',)
    readonly_fields = ('get_final_position',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Ordenar solo por el campo 'order' (orden secuencial)
        return qs.select_related('training').order_by('order')

    def get_final_position(self, obj):
        if not obj.pk or not obj.course_id:
            return '-'
        # Ordenar solo por el campo 'order' (orden secuencial)
        all_trainings = CourseTraining.objects.filter(course=obj.course).select_related('training').order_by('order')
        try:
            position = next(i for i, ct in enumerate(all_trainings, 1) if ct.id == obj.id)
            return format_html('<strong>#{}</strong>', position)
        except StopIteration:
            return '-'
    get_final_position.short_description = 'Final Position'

# Attach inline to CourseAdmin so CourseTrainings are grouped on the Course change page
CourseAdmin.inlines = getattr(CourseAdmin, 'inlines', ()) + (CourseTrainingInline,)


class TrainingCourseInline(admin.TabularInline):
    """Show CourseTrainings inside the Training change page for quick overview and edits."""
    model = CourseTraining
    fields = ('course', 'get_final_position')
    extra = 0
    show_change_link = True
    autocomplete_fields = ('course',)
    readonly_fields = ('get_final_position',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Ordenar solo por el campo 'order' (orden secuencial)
        return qs.select_related('course').order_by('order')

    def get_final_position(self, obj):
        if not obj.pk or not obj.course_id or not obj.training_id:
            return '-'
        # Ordenar solo por el campo 'order' (orden secuencial)
        all_trainings = CourseTraining.objects.filter(course=obj.course).select_related('training').order_by('order')
        try:
            position = next(i for i, ct in enumerate(all_trainings, 1) if ct.id == obj.id)
            return format_html('<strong>#{}</strong>', position)
        except StopIteration:
            return '-'
    get_final_position.short_description = 'Position in Course'

# Attach inline to TrainingAdmin so CourseTrainings are grouped on the Training change page
TrainingAdmin.inlines = getattr(TrainingAdmin, 'inlines', ()) + (TrainingCourseInline,)


admin.site.register(Training,TrainingAdmin)
admin.site.register(TrainingBlock,TrainingBlockAdmin)
admin.site.register(TrainingQuestion,TrainingQuestionAdmin)
admin.site.register(Choice,ChoiceAdmin)
admin.site.register(ChoiceSet,ChoiceSetAdmin)
admin.site.register(TraineeTraining,TraineeTrainingAdmin)
admin.site.register(TrainingQuestionAnswer,TrainingQuestionAnswerAdmin)
admin.site.register(Comment,CommentAdmin)
admin.site.register(TrainingBlockAnswer,TrainingBlockAnswerAdmin)
admin.site.register(TraineeGroup,TraineeGroupAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(TraineeCourse, TraineeCourseAdmin)


# Custom admin ordering for trainingApp models
_original_get_app_list = admin.AdminSite.get_app_list

def _custom_get_app_list(self, request, app_label=None):
    """Devuelve la lista de apps pero reordena los modelos de `trainingApp`.

    La lista `desired` contiene los nombres tal como aparecen en el sidebar
    (campo `name` de cada modelo en la estructura que devuelve Django).
    """
    app_list = _original_get_app_list(self, request, app_label=app_label)
    for app in app_list:
        if app.get('app_label') == 'trainingApp':
            desired = [
                'Courses',
                'Trainings',
                'Training blocks',
                'Training questions',
                'Choice sets',
                'Trainee groups',
                'Trainee courses',
                'Trainee trainings',
                'Training block answers',
                'Training question answers',
                'Comments',
            ]
            models = app.get('models', [])
            name_map = {m['name']: m for m in models}
            ordered = [name_map[n] for n in desired if n in name_map]
            remaining = [m for m in models if m['name'] not in desired]
            app['models'] = ordered + remaining
    return app_list

# Reemplazamos el método de la clase AdminSite
admin.AdminSite.get_app_list = _custom_get_app_list
