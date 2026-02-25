from django.contrib import admin
from .models import Training, TrainingQuestion, Choice, TrainingBlock, TraineeTraining, TrainingQuestionAnswer, Comment, TrainingBlockAnswer, TraineeGroup, CourseTraining, Course, TraineeCourse
from import_export.admin import ExportActionMixin
from import_export import resources  # Importa resources desde import_export
from import_export.fields import Field
from modeltranslation.admin import TranslationAdmin
from django.utils.html import format_html
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

#Clase que define cómo se importarán/exportarán los objetos TrainingQuestionAnswer.
class TrainingQuestionAnswerResource(resources.ModelResource): 
    #Se usa el campo block_answer para llegar al user_name
    username = Field(column_name='username',attribute='block_answer')
    deploy = Field(column_name='deploy', attribute='deploy')
    
    class Meta:
        model = TrainingQuestionAnswer
        fields = ('id', 'selectedChoice', 'deploy', 'block_answer','username')
        export_order=fields

    #Metodo que sirve para transformar y formatear el valor de un campo específico antes de que se exporte a un formato externo
    def dehydrate_username(self,obj):
        return str(obj.block_answer.trainee_Training.trainee.user.username)
    
    def dehydrate_selectedChoice(self,obj):
        return str(obj.selectedChoice.choice)
    
#Clases que permiten que el modelo TrainingQuestionAnswer tenga acciones de exportación en el panel de administración y permite tambien su personalizacion.
class TrainingQuestionAnswerAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class= TrainingQuestionAnswerResource
    
class TrainingQuestionResource(resources.ModelResource):
    class Meta:
        model = TrainingQuestion
        fields = ('id','question',)
        
        

#Clases que heredan de admin.ModelAdmin gestionan el estilo en el admin
class TrainingAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ('id','name_training','view_blocks','view_courses','difficulty','state_training','estimatedDuration','attempts_allowed','pub_date')
    list_display_links = ('name_training',)
    list_filter = ('difficulty','state_training','groups')
    search_fields = ('name_training',)
    ordering = ('-pub_date',)

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
    
    class Media:
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'https://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.min.js',
            'modeltranslation/js/tabbed_translation_fields.js',
        )
        css = {
            'all': (
                'modeltranslation/css/tabbed_translation_fields.css',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css',  # Nuevo estilo añadido
            ),
        }
        
class TrainingBlockAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ('id','name_block','view_deploys', 'training', 'state_block','estimed_duration_block',)
    list_display_links = ('name_block',)
    list_filter = ('state_block','training')
    search_fields = ('name_block','description')
    list_select_related = ('training',)
    autocomplete_fields = ('training',)
    
    class Media:
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'https://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.min.js',
            'modeltranslation/js/tabbed_translation_fields.js',
        )
        css = {
            'all': (
                'modeltranslation/css/tabbed_translation_fields.css',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css',  # Nuevo estilo añadido
            ),
        }

    def view_deploys(self,obj):
        """Link to the Deploy changelist filtered by this block."""
        try:
            count = obj.trainingquestion_set.count()
        except Exception:
            count = 0
        url = reverse('admin:trainingApp_trainingquestion_changelist') + f'?block__id__exact={obj.id}'
        return format_html('<a href="{}">Deploys ({})</a>', url, count)
    view_deploys.short_description = 'Deploys'
        
class TrainingQuestionAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ('id','question','view_choices','block','has_media')
    list_filter = ('block__training','block')
    search_fields = ('question','block__name_block')
    ordering = ('block','id')

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
    
    class Media:
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'https://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.min.js',
            'modeltranslation/js/tabbed_translation_fields.js',
        )
        css = {
            'all': (
                'modeltranslation/css/tabbed_translation_fields.css',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css',  
            ),
        }

class ChoiceAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ('id','choice','deploy','correctChoice')
    list_filter = ('correctChoice','deploy')
    search_fields = ('choice',)
    
    class Media:
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'https://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.min.js',
            'modeltranslation/js/tabbed_translation_fields.js',
        )
        css = {
            'all': (
                'modeltranslation/css/tabbed_translation_fields.css',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css',  
            ),
        }

class TraineeTrainingAdmin(admin.ModelAdmin):
    list_display = ('id','training','trainee','course','pub_date','state','time_spent')
    list_filter = ('state','training','course')
    search_fields = ('trainee__user__username','training__name_training','course__name_course')
    raw_id_fields = ('trainee','training','course')


class TrainingQuestionAnswerAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_class= TrainingQuestionAnswerResource
    list_display = ('id','deploy','get_trainee_username','selectedChoice')
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
    search_fields = ('trainee__user__username','training__name_training','comment_aditional')

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


class CourseAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ('id', 'name_course', 'view_trainings', 'required_average_score', 'state_course', 'pub_date')
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
    
    def get_readonly_fields(self, request, obj=None):
        # Mostrar un mensaje informativo sobre el orden automático
        return super().get_readonly_fields(request, obj)
    
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

    class Media:
        js = (
            'https://ajax.googleapis.com/ajax/libs/jquery/1.9.1/jquery.min.js',
            'https://ajax.googleapis.com/ajax/libs/jqueryui/1.10.2/jquery-ui.min.js',
            'modeltranslation/js/tabbed_translation_fields.js',
        )
        css = {
            'all': (
                'modeltranslation/css/tabbed_translation_fields.css',
                'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css',
            ),
        }


class TraineeCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'trainee', 'course', 'state', 'current_training_index', 'exam_passed', 'pub_date')
    list_filter = ('state', 'course', 'exam_passed')
    search_fields = ('trainee__user__username', 'course__name_course')
    raw_id_fields = ('trainee', 'course')


class TrainingBlockInline(admin.TabularInline):
    """Show Blocks inside the Training change page for quick overview and edits."""
    model = TrainingBlock
    fields = ('name_block','state_block','estimed_duration_block')
    extra = 0
    show_change_link = True
    ordering = ('id',)

# Attach inline to TrainingAdmin so Blocks are grouped on the Training change page
TrainingAdmin.inlines = getattr(TrainingAdmin, 'inlines', ()) + (TrainingBlockInline,)


class TrainingQuestionInline(admin.TabularInline):
    """Show Deploys inside the Block change page for quick overview and edits."""
    model = TrainingQuestion
    fields = ('question','deploy_image','deploy_sound')
    extra = 0
    show_change_link = True
    ordering = ('id',)

# Attach TrainingQuestionInline to TrainingBlockAdmin so Deploys are grouped on the Block change page
TrainingBlockAdmin.inlines = getattr(TrainingBlockAdmin, 'inlines', ()) + (TrainingQuestionInline,)


class ChoiceInline(admin.TabularInline):
    """Show Choices inside the Deploy change page for quick overview and edits."""
    model = Choice
    fields = ('choice','correctChoice')
    extra = 0
    show_change_link = True
    ordering = ('id',)

# Attach ChoiceInline to TrainingQuestionAdmin so Choices are grouped on the Deploy change page
TrainingQuestionAdmin.inlines = getattr(TrainingQuestionAdmin, 'inlines', ()) + (ChoiceInline,)


class CourseTrainingInline(admin.TabularInline):
    """Show CourseTrainings inside the Course change page for quick overview and edits."""
    model = CourseTraining
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
                'Trainings',
                'Training blocks',
                'Training questions',
                'Choices',
                'Trainee trainings',
                'Training block answers',
                'Training question answers',
                'Comments',
                'Trainee groups',
                'Courses',
                'Trainee courses',
            ]
            models = app.get('models', [])
            name_map = {m['name']: m for m in models}
            ordered = [name_map[n] for n in desired if n in name_map]
            remaining = [m for m in models if m['name'] not in desired]
            app['models'] = ordered + remaining
    return app_list

# Reemplazamos el método de la clase AdminSite
admin.AdminSite.get_app_list = _custom_get_app_list