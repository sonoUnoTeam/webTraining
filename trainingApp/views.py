from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, Http404
from django.views import View
from django.views.generic import ListView
from django.db import models
from .forms import QuestionForm,CommentForm
from .models import Training, TrainingQuestion, TrainingQuestionAnswer, TraineeTraining, TrainingBlock, Choice, Comment,TrainingBlockAnswer, Course, CourseTraining, TraineeCourse
from . import rules
from userApp.models import Trainee
from django.utils import timezone
from django.utils.translation import gettext as _

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from operator import attrgetter
from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse

#TESTING
class CourseList(ListView):
    model = Course 
    template_name = "trainingApp/course_list.html"
    context_object_name = "course_list"
    paginate_by = 5
    
    def get_queryset(self):
        try:
            trainee = Trainee.objects.get(user = self.request.user)
        except Trainee.DoesNotExist:
            messages.error(self.request, _("You need to be a trainee to access trainings."))
            return Course.objects.none()
        queryset = Course.objects.filter(state_course = 'Active', groups__in=[trainee.group]).order_by('id')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            trainee = Trainee.objects.get(user_id=user.id)
        except Trainee.DoesNotExist:
            return context
        
        context['course_progress'] = {}
        for course in context['course_list']:
            try:
                trainee_course = TraineeCourse.objects.get(trainee=trainee, course=course)
                context['course_progress'][course.id] = {
                    'state': trainee_course.state,
                    'current_training_index': trainee_course.current_training_index,
                    'exam_passed': trainee_course.exam_passed
                }
                course.status = trainee_course.get_state_display()
                
                # Calcular estadísticas del curso
                total_trainings = rules.course_trainings(course).count()
                course.total_trainings = total_trainings

                # Calcular duración total del curso
                total_duration = rules.course_trainings(course).aggregate(
                    total=models.Sum('training__estimatedDuration')
                )['total'] or 0
                course.total_duration = total_duration
                
                if total_trainings > 0:
                    completed_trainings = TraineeTraining.objects.filter(
                        trainee=trainee,
                        training__coursetraining__course=course
                    ).exclude(
                        state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
                    ).values('training').distinct().count()
                    course.completed_count = completed_trainings
                    course.progress_percentage = round((completed_trainings / total_trainings) * 100)
                else:
                    course.completed_count = 0
                    course.progress_percentage = 0
                
                # Última actividad
                last_training = TraineeTraining.objects.filter(
                    trainee=trainee,
                    training__coursetraining__course=course
                ).order_by('-pub_date').first()
                if last_training:
                    course.last_activity = last_training.pub_date
                else:
                    course.last_activity = None
                
                # Fecha de inicio
                course.started_date = trainee_course.created_at if hasattr(trainee_course, 'created_at') else None
                
                # Dificultad (puedes ajustar esto según tu modelo)
                if hasattr(course, 'difficulty'):
                    difficulty_map = {'easy': 'easy', 'medium': 'medium', 'hard': 'hard'}
                    course.difficulty_level = difficulty_map.get(course.difficulty.lower(), 'medium')
                    course.difficulty_display = course.get_difficulty_display() if hasattr(course, 'get_difficulty_display') else course.difficulty
                else:
                    course.difficulty_level = 'medium'
                    course.difficulty_display = _('Medium')
                    
            except TraineeCourse.DoesNotExist:
                context['course_progress'][course.id] = {
                    'state': 'Not Started',
                    'current_training_index': 0,
                    'exam_passed': False
                }
                course.status = _("Not Started")
                course.progress_percentage = 0
                course.total_trainings = rules.course_trainings(course).count()
                course.completed_count = 0
                course.last_activity = None
                course.started_date = None
                course.difficulty_level = 'medium'
                course.difficulty_display = _('Medium')

                # Calcular duración total para cursos no iniciados
                total_duration = rules.course_trainings(course).aggregate(
                    total=models.Sum('training__estimatedDuration')
                )['total'] or 0
                course.total_duration = total_duration
        
        return context


class CourseDetailView(ListView):
    model = CourseTraining
    template_name = "trainingApp/course_detail.html"
    context_object_name = "course_trainings"
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        course_id = self.kwargs['course_id']
        user = request.user
        try:
            trainee = Trainee.objects.get(user_id=user.id)
            course = Course.objects.get(id=course_id)
            if not rules.can_view_course(trainee, course):
                messages.error(request, _("You do not have access to this course."))
                return redirect('trainingApp:course_list')
            TraineeCourse.objects.get_or_create(
                trainee=trainee,
                course=course,
                defaults={
                    'state': TraineeCourse.StateTraineeCourse.Not_Started,
                    'current_training_index': 0,
                    'exam_passed': False,
                    'pub_date': timezone.now()
                }
            )
        except Trainee.DoesNotExist:
            messages.error(request, _("You need to be a trainee to access this page."))
            return redirect('home')
        except Course.DoesNotExist:
            raise Http404("Course not found")

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        # Orden por el campo order de CourseTraining (secuencial absoluto), solo trainings activos
        return rules.course_trainings(course_id)

    def get_context_data(self, **kwargs):
        """
        Prepara el contexto para la vista de detalle del curso.
        
        Este método construye un contexto completo con información sobre:
        - El curso y sus trainings
        - El progreso del trainee en cada training
        - Los intentos realizados y puntajes obtenidos
        - La disponibilidad de cada training según el progreso secuencial
        - El estado del examen final y sus requisitos
        """
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs['course_id']
        course = Course.objects.get(id=course_id)
        # Variable: course - Información básica del curso (nombre, descripción, etc.)
        context['course'] = course

        user = self.request.user
        trainee = Trainee.objects.get(user_id=user.id)
        trainee_course = TraineeCourse.objects.get(trainee=trainee, course=course)
        # Variable: trainee_course - Relación trainee-curso (estado general, índice actual)
        context['trainee_course'] = trainee_course

        # ============================================
        # PROCESAMIENTO DE TRAININGS SECUENCIALES
        # ============================================
        # Para cada training del curso, se calcula:
        # - Si está habilitado (enabled): depende de si completó el anterior
        # - Mejor intento (best_attempt/best_score): para mostrar el mejor resultado
        # - Último intento (last_attempt/last_score): para comparar con el mejor
        # - Intentos completados (completed_attempts): para validar límites
        # - Si está bloqueado (is_locked_by_next): si avanzó al siguiente sin agotar intentos
        # - Si puede reintentar (can_retry): si tiene intentos disponibles y no avanzó
        
        for idx, ct in enumerate(context['course_trainings']):
            if idx == 0:
                # Atributo: ct.enabled - El primer training siempre está disponible
                ct.enabled = True
            else:
                # Atributo: ct.enabled - Los siguientes se habilitan si el anterior tiene al menos un intento
                # Esto permite avanzar incluso si se desaprobó el training anterior
                previous_ct = context['course_trainings'][idx - 1]
                ct.enabled = TraineeTraining.objects.filter(
                    trainee=trainee,
                    training=previous_ct.training,
                    course=course
                ).exclude(
                    state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
                ).exists()
            
            # Atributo: ct.completed - Indica si tiene al menos un intento completado (usado en lógica)
            # NOTA: Este atributo NO debe usarse para determinar si aprobó, usar best_attempt.state
            ct.completed = TraineeTraining.objects.filter(
                trainee=trainee, 
                training=ct.training, 
                course=course
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).exists()
            
            # Atributo: ct.best_attempt - El intento con mayor puntaje (para mostrar mejor resultado)
            # Atributo: ct.best_score - Porcentaje del mejor intento
            best_attempt = TraineeTraining.objects.filter(
                trainee=trainee,
                training=ct.training,
                course=course
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).order_by('-score_percentage').first()
            
            ct.best_score = best_attempt.score_percentage if best_attempt else None
            ct.best_attempt = best_attempt
            
            # Atributo: ct.last_attempt - El intento más reciente (para comparar evolución)
            # Atributo: ct.last_score - Porcentaje del último intento
            last_attempt = TraineeTraining.objects.filter(
                trainee=trainee,
                training=ct.training,
                course=course
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).order_by('-pub_date').first()
            
            ct.last_score = last_attempt.score_percentage if last_attempt else None
            ct.last_attempt = last_attempt
            
            # Atributo: ct.completed_attempts - Número de intentos finalizados (para validar límites)
            ct.completed_attempts = TraineeTraining.objects.filter(
                trainee=trainee,
                training=ct.training,
                course=course
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).count()
            
            # ============================================
            # VALIDACIÓN DE BLOQUEOS Y REINTENTOS
            # ============================================
            # Atributo: ct.is_locked_by_next - True si avanzó al siguiente y no puede reintentar este
            # Atributo: ct.previous_has_retries - True si el anterior tiene reintentos disponibles
            # Atributo: ct.can_retry - True si puede hacer más intentos (no bloqueado y bajo el límite)
            ct.is_locked_by_next = False
            ct.previous_has_retries = False
            
            # Verificar si el examen final ha sido iniciado (bloquea todos los trainings)
            has_final_exam_attempt = False
            if course.final_exam:
                has_final_exam_attempt = TraineeTraining.objects.filter(
                    trainee=trainee,
                    training=course.final_exam,
                    course=course
                ).exists()
            
            if idx < len(context['course_trainings']) - 1:
                next_ct = context['course_trainings'][idx + 1]
                # Verificar si ya hay intentos del siguiente training (bloquea el actual)
                has_next_attempts = TraineeTraining.objects.filter(
                    trainee=trainee,
                    training=next_ct.training,
                    course=course
                ).exists()  # Cualquier intento (incluido in_progress) bloquea el anterior
                
                # Bloquear si avanzó al siguiente O si inició el examen final
                ct.is_locked_by_next = has_next_attempts or has_final_exam_attempt
                ct.can_retry = not has_next_attempts and not has_final_exam_attempt and ct.completed_attempts < ct.training.attempts_allowed
                
                # Verificar si el training anterior tiene reintentos disponibles (para advertencia)
                if idx > 0:
                    prev_ct = context['course_trainings'][idx - 1]
                    prev_completed = TraineeTraining.objects.filter(
                        trainee=trainee,
                        training=prev_ct.training,
                        course=course
                    ).exclude(
                        state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
                    ).count()
                    ct.previous_has_retries = prev_completed < prev_ct.training.attempts_allowed and prev_completed > 0
            else:
                # Para el último training, el examen final lo bloquea si fue iniciado
                ct.can_retry = ct.completed_attempts < ct.training.attempts_allowed and not has_final_exam_attempt
                ct.is_locked_by_next = has_final_exam_attempt
                
                # Verificar si el training anterior tiene reintentos disponibles
                if idx > 0:
                    prev_ct = context['course_trainings'][idx - 1]
                    prev_completed = TraineeTraining.objects.filter(
                        trainee=trainee,
                        training=prev_ct.training,
                        course=course
                    ).exclude(
                        state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
                    ).count()
                    ct.previous_has_retries = prev_completed < prev_ct.training.attempts_allowed and prev_completed > 0
            
            # Atributo: ct.position - Número de posición del training en la secuencia (1, 2, 3...)
            ct.position = idx + 1

        # ============================================
        # DICCIONARIOS DE INFORMACIÓN DE INTENTOS
        # ============================================
        # Variable: num_trainee_trainings - Dict {training_id: cantidad_de_intentos}
        # Variable: training_attempts_info - Dict con info detallada de cada training
        num_trainee_trainings = {}
        training_attempts_info = {}
        for ct in context['course_trainings']:
            completed_count = TraineeTraining.objects.filter(
                trainee=trainee, 
                training=ct.training, 
                course=course
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).count()
            # Guardar cuenta de intentos por ID de training
            num_trainee_trainings[ct.training.id] = completed_count
            
            # Guardar información completa para uso posterior
            training_attempts_info[ct.training.id] = {
                'completed': completed_count,
                'best_score': ct.best_score,
                'can_retry': ct.can_retry,
                'is_passed': ct.completed
            }
        
        # ============================================
        # INFORMACIÓN DEL EXAMEN FINAL
        # ============================================
        if course.final_exam:
            # Contar intentos del examen final
            exam_completed = TraineeTraining.objects.filter(
                trainee=trainee, 
                training=course.final_exam, 
                course=course
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).count()
            num_trainee_trainings[course.final_exam.id] = exam_completed
            
            # Variable: final_exam_attempt - Mejor intento del examen final (None si no lo ha intentado)
            final_exam_attempt = TraineeTraining.objects.filter(
                trainee=trainee,
                training=course.final_exam,
                course=course,
                is_final_exam_attempt=True
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).order_by('-score_percentage').first()
            
            context['final_exam_attempt'] = final_exam_attempt
            
        context['num_trainee_trainings'] = num_trainee_trainings
        context['training_attempts_info'] = training_attempts_info

        # ============================================
        # CÁLCULO DE PROMEDIO Y REQUISITOS
        # ============================================
        # Variable: average_score - Promedio de los mejores puntajes de cada training
        # Usado para determinar si puede tomar el examen final
        best_scores = []
        for ct in context['course_trainings']:
            if ct.best_score is not None:
                best_scores.append(float(ct.best_score))
        
        average_score = sum(best_scores) / len(best_scores) if best_scores else 0
        context['average_score'] = round(average_score, 2)
        
        # Variable: all_completed - True si todos los trainings tienen al menos un intento
        # Variable: meets_average_requirement - True si el promedio cumple el mínimo requerido
        # Variable: can_take_final_exam - True si cumple ambos requisitos anteriores
        all_trainings_attempted = all(
            TraineeTraining.objects.filter(
                trainee=trainee,
                training=ct.training,
                course=course
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).exists()
            for ct in context['course_trainings']
        )
        
        meets_average_requirement = average_score >= float(course.required_average_score)
        
        context['all_completed'] = all_trainings_attempted
        context['meets_average_requirement'] = meets_average_requirement
        context['can_take_final_exam'] = all_trainings_attempted and meets_average_requirement

        # Variable: has_trainings_with_retries - True si hay trainings con intentos sin agotar
        # Usado para mostrar advertencia al iniciar examen final (bloqueará esos reintentos)
        has_trainings_with_retries = any(
            ct.completed_attempts < ct.training.attempts_allowed and ct.completed_attempts > 0
            for ct in context['course_trainings']
        )
        context['has_trainings_with_retries'] = has_trainings_with_retries
        
        # ============================================
        # RESUMEN DE VARIABLES DE CONTEXTO
        # ============================================
        # course: Objeto Course con info del curso
        # trainee_course: Relación TraineeCourse (estado general)
        # course_trainings: QuerySet con CourseTraining, cada uno tiene atributos extra:
        #   - enabled: bool - Si puede iniciarse
        #   - completed: bool - Si tiene intentos finalizados
        #   - best_attempt: TraineeTraining - Mejor intento
        #   - best_score: float - Puntaje del mejor intento
        #   - last_attempt: TraineeTraining - Último intento
        #   - last_score: float - Puntaje del último intento
        #   - completed_attempts: int - Número de intentos realizados
        #   - is_locked_by_next: bool - Si está bloqueado por avanzar
        #   - can_retry: bool - Si puede reintentar
        #   - previous_has_retries: bool - Si el anterior tiene reintentos
        #   - position: int - Posición en secuencia
        # num_trainee_trainings: dict - {training_id: num_intentos}
        # training_attempts_info: dict - Info detallada por training
        # final_exam_attempt: TraineeTraining o None - Mejor intento del examen
        # average_score: float - Promedio de mejores puntajes
        # all_completed: bool - Todos los trainings intentados
        # meets_average_requirement: bool - Promedio suficiente
        # can_take_final_exam: bool - Puede tomar examen final
        # has_trainings_with_retries: bool - Hay reintentos disponibles
        # ============================================
        
        return context


def get_trainee(request):
    """Trainee del usuario logueado, o None (dejando el mensaje de error)."""
    trainee = Trainee.objects.filter(user=request.user).first()
    if trainee is None:
        messages.error(request, _("You need to be a trainee to access trainings."))
    return trainee


class TrainingBlockDeployList(ListView):
    model = TrainingBlock
    template_name = "trainingApp/block_deploy_list.html"
    context_object_name = "block_list"
    paginate_by = 5

    def dispatch(self, request, *args, **kwargs):
        course_id = self.kwargs['course_id']
        training_id = self.kwargs['training_id']
        self.course = get_object_or_404(Course, id=course_id)
        self.training = get_object_or_404(Training, id=training_id)
        if not rules.training_in_course(self.course, training_id):
            raise Http404("Training not in course")

        trainee = get_trainee(request)
        if trainee is None:
            return redirect('home')

        # Grupo, estado, secuencia, bloqueos y límite de intentos
        error = rules.check_can_attempt(trainee, self.course, self.training)
        if error:
            messages.error(request, error)
            return redirect('trainingApp:course_detail', course_id=course_id)

        self.trainee_training = rules.start_or_resume_attempt(request, trainee, self.course, self.training)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return rules.active_blocks(self.training)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        states_blocks_answers = {}
        for block in context['block_list']:
            block_answer = (
                TrainingBlockAnswer.objects
                .filter(trainee_Training=self.trainee_training, block=block)
                .order_by('-id')
                .first()
            )
            if block_answer:
                states_blocks_answers[f'{block.id}'] = block_answer.state_block
            else:
                states_blocks_answers[f'{block.id}'] = _('not started')

        context['states_blocks_answers'] = states_blocks_answers
        context['TrainingBlockAnswer'] = TrainingBlockAnswer
        context['course_id'] = self.course.id
        context['training_id'] = self.training.id
        return context


class DeployDetailView(View):
    template_name = 'trainingApp/forms.html'

    def dispatch(self, request, *args, **kwargs):
        course_id = kwargs['course_id']
        training_id = kwargs['training_id']
        self.course = get_object_or_404(Course, id=course_id)
        self.training = get_object_or_404(Training, id=training_id)
        if not rules.training_in_course(self.course, training_id):
            raise Http404("Training not in course")

        trainee = get_trainee(request)
        if trainee is None:
            return redirect('home')

        # Mismas reglas que la lista de bloques: entrar directo por URL no las saltea
        error = rules.check_can_attempt(trainee, self.course, self.training)
        if error:
            messages.error(request, error)
            return redirect('trainingApp:course_detail', course_id=course_id)

        self.block = get_object_or_404(rules.active_blocks(self.training), pk=kwargs['block_id'])
        self.trainee_training = rules.start_or_resume_attempt(request, trainee, self.course, self.training)

        if rules.block_completed(self.trainee_training, self.block):
            messages.info(request, _("You have already completed this block."))
            return redirect('trainingApp:block_deploy_list', course_id=course_id, training_id=training_id)

        self.deploys = list(TrainingQuestion.objects.filter(block=self.block).order_by('id'))
        self.index_key = f'current_deploy_index_{course_id}_{training_id}_{self.block.id}'
        self.block_answer_key = f'current_block_answer_id_{course_id}_{training_id}_{self.block.id}'
        self.block_answer = self.get_block_answer(request)
        return super().dispatch(request, *args, **kwargs)

    def get_block_answer(self, request):
        """TrainingBlockAnswer en progreso de este bloque para el intento actual (lo crea si no existe)."""
        in_progress = TrainingBlockAnswer.objects.filter(
            trainee_Training=self.trainee_training,
            block=self.block,
            state_block=TrainingBlockAnswer.StateBlockAnswer.in_progress,
        )
        session_block_answer_id = request.session.get(self.block_answer_key)
        block_answer = in_progress.filter(pk=session_block_answer_id).first() if session_block_answer_id else None
        if block_answer is None:
            block_answer = in_progress.order_by('-id').first()
        if block_answer is None:
            block_answer = TrainingBlockAnswer.objects.create(
                trainee_Training=self.trainee_training,
                block=self.block,
                state_block=TrainingBlockAnswer.StateBlockAnswer.in_progress,
            )
        request.session[self.block_answer_key] = block_answer.id
        return block_answer

    def current_index(self, request):
        index = request.session.get(self.index_key, 0)
        # Un índice desfasado (sesión vieja, preguntas borradas) vuelve al inicio del bloque
        if not 0 <= index < len(self.deploys):
            index = 0
        return index

    def render_question(self, request, deploy, form, index):
        return render(request, self.template_name, {
            'deploy': deploy,
            'form': form,
            'block_id': self.block.id,
            'course_id': self.course.id,
            'training_id': self.training.id,
            'current_deploy_index': index,
            'deploys_count': len(self.deploys),
        })

    def get(self, request, course_id, training_id, block_id):
        index = self.current_index(request)
        request.session[self.index_key] = index
        current_deploy = self.deploys[index]

        # Precargar la respuesta si ya se había respondido esta pregunta
        initial_data = {}
        deploy_answer = TrainingQuestionAnswer.objects.filter(block_answer=self.block_answer, deploy=current_deploy).first()
        if deploy_answer:
            initial_data['selectedChoice'] = deploy_answer.selectedChoice_id

        form = QuestionForm(instance=current_deploy, initial=initial_data)
        return self.render_question(request, current_deploy, form, index)

    def post(self, request, course_id, training_id, block_id):
        index = self.current_index(request)
        current_deploy = self.deploys[index]

        form = QuestionForm(request.POST, instance=current_deploy)
        if not form.is_valid():
            return self.render_question(request, current_deploy, form, index)

        selected_choice = get_object_or_404(Choice, id=form.cleaned_data['selectedChoice'], deploy=current_deploy)
        deploy_answer = TrainingQuestionAnswer.objects.filter(block_answer=self.block_answer, deploy=current_deploy).first()
        if deploy_answer:
            deploy_answer.selectedChoice = selected_choice
            deploy_answer.save()
        else:
            TrainingQuestionAnswer.objects.create(
                block_answer=self.block_answer,
                deploy=current_deploy,
                selectedChoice=selected_choice
            )

        index += 1
        if index < len(self.deploys):
            request.session[self.index_key] = index
            return redirect('trainingApp:forms', course_id=course_id, training_id=training_id, block_id=block_id)

        # Fin del bloque
        request.session.pop(self.index_key, None)
        request.session.pop(self.block_answer_key, None)
        self.block_answer.state_block = TrainingBlockAnswer.StateBlockAnswer.Completed
        self.block_answer.save()

        if not rules.all_blocks_completed(self.trainee_training):
            return redirect('trainingApp:block_deploy_list', course_id=course_id, training_id=training_id)
        return self.finish_attempt(request)

    def finish_attempt(self, request):
        """Cierra el intento: tiempo empleado, puntaje, estado del curso, mensaje y redirección."""
        trainee_training = self.trainee_training
        session_key, start_time_key = rules.attempt_session_keys(self.course.id, self.training.id)

        start_time_str = request.session.get(start_time_key)
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time)
        else:
            start_time = trainee_training.pub_date
        trainee_training.time_spent = timezone.now() - start_time
        trainee_training.save()

        # Calcular puntuación y actualizar estado (passed/failed)
        trainee_training.update_score_and_state()
        request.session.pop(session_key, None)
        request.session.pop(start_time_key, None)

        passed = trainee_training.state == TraineeTraining.StateTraineeTraining.PASSED
        trainee_course = trainee_training.trainee_course
        if trainee_training.is_final_exam_attempt:
            if passed:
                trainee_course.exam_passed = True
                trainee_course.state = TraineeCourse.StateTraineeCourse.Completed
                trainee_course.completion_date = timezone.now()
            elif rules.finished_attempts(trainee_training.trainee, self.course, self.training).count() >= self.training.attempts_allowed:
                # Examen final desaprobado sin intentos restantes
                trainee_course.state = TraineeCourse.StateTraineeCourse.Failed
                trainee_course.completion_date = timezone.now()
            trainee_course.save()
        elif passed:
            trainee_course.current_training_index += 1
            trainee_course.save()

        # Mensaje personalizado según si aprobó o no
        if passed:
            messages.success(
                request,
                _("Congratulations! You passed '%(training)s' with %(score)s%%") % {
                    "training": self.training.name_training,
                    "score": trainee_training.score_percentage
                }
            )
        else:
            passing_score = self.course.final_exam_passing_score if trainee_training.is_final_exam_attempt else self.training.passing_score
            messages.warning(
                request,
                _("You completed '%(training)s' with %(score)s%%. You need %(passing)s%% to pass. You can retry if attempts are available.") % {
                    "training": self.training.name_training,
                    "score": trainee_training.score_percentage,
                    "passing": passing_score
                }
            )

        if trainee_training.is_final_exam_attempt and passed:
            return redirect('trainingApp:comment', course_id=self.course.id, training_id=self.training.id)
        return redirect('trainingApp:course_detail', course_id=self.course.id)

#Funcion que retrocede un deploy
def backDeploy(request, course_id, training_id, block_id):
        session_key = f'current_deploy_index_{course_id}_{training_id}_{block_id}'
        current_deploy_index = request.session.get(session_key, 0) - 1
        if current_deploy_index <0 :
            return redirect('trainingApp:block_deploy_list', course_id=course_id, training_id=training_id)
        else:
            request.session[session_key] = current_deploy_index
            return redirect('trainingApp:forms', course_id=course_id, training_id=training_id, block_id=block_id)


class ReviewListTT(ListView):
    model = TraineeTraining
    template_name = "trainingApp/review_list_tt.html"
    context_object_name = "trainee_training_list"
    paginate_by = 10

    def get_queryset(self):
        course_id = self.kwargs['course_id']
        training_id = self.kwargs['training_id']
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)
        if not (course.trainings.filter(id=training_id).exists() or course.final_exam_id == training_id):
            raise Http404("Training not in course")

        try:
            trainee = Trainee.objects.get(user=self.request.user)
        except Trainee.DoesNotExist:
            messages.error(self.request, _("You need to be a trainee to access this page."))
            return TraineeTraining.objects.none()
        if not rules.can_view_course(trainee, course):
            raise Http404("Course not available")

        # Determinar si este training es el examen final del curso
        is_final_exam = course.final_exam_id == training_id

        queryset = TraineeTraining.objects.filter(
            training_id=training_id,
            course_id=course_id,
            trainee_id=trainee.id
        ).exclude(
            state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
        )

        # Filtrar por tipo de intento
        if is_final_exam:
            queryset = queryset.filter(is_final_exam_attempt=True)
        else:
            queryset = queryset.filter(is_final_exam_attempt=False)

        for i, trainee_training in enumerate(queryset, start=1):
            trainee_training.item_number = i

        queryset = sorted(queryset, key=attrgetter('item_number'), reverse=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs['course_id']
        training_id = self.kwargs['training_id']
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)

        context['course_id'] = course_id
        context['training_id'] = training_id
        context['course'] = course
        context['training'] = training

        # Determinar si este training es el examen final del curso
        context['is_final_exam'] = course.final_exam_id == training_id

        return context


class ReviewBlock(ListView):
    model = TrainingBlockAnswer
    template_name = "trainingApp/review_block.html"
    context_object_name = "blocks_answers"
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        # Solo intentos propios y terminados (un intento en curso revelaría las respuestas correctas)
        self.trainee_training = get_object_or_404(
            TraineeTraining.objects.exclude(state=TraineeTraining.StateTraineeTraining.IN_PROGRESS),
            pk=kwargs['trainee_training_id'],
            trainee__user=request.user,
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return TrainingBlockAnswer.objects.filter(trainee_Training=self.trainee_training).order_by('id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['training_id'] = self.trainee_training.training_id
        context['course_id'] = self.trainee_training.course_id
        return context


class ReviewDeploy(View):
    template_name = 'trainingApp/review_deploy.html'

    def dispatch(self, request, *args, **kwargs):
        # Solo bloques de intentos propios y terminados
        self.block_answer = get_object_or_404(
            TrainingBlockAnswer.objects.exclude(trainee_Training__state=TraineeTraining.StateTraineeTraining.IN_PROGRESS),
            pk=kwargs['block_answer_id'],
            trainee_Training__trainee__user=request.user,
        )
        self.deploys_answer = list(
            TrainingQuestionAnswer.objects
            .filter(block_answer=self.block_answer)
            .select_related('deploy', 'selectedChoice')
            .order_by('id')
        )
        if not self.deploys_answer:
            messages.info(request, _("This block has no answers to review."))
            return redirect('trainingApp:review_block', self.block_answer.trainee_Training_id)
        self.index_key = f'current_deploy_index_review_{self.block_answer.id}'
        return super().dispatch(request, *args, **kwargs)

    def current_index(self, request):
        index = request.session.get(self.index_key, 0)
        return index if 0 <= index < len(self.deploys_answer) else 0

    def get(self, request, block_answer_id):
        current_deploy_answer = self.deploys_answer[self.current_index(request)]
        current_deploy_review = current_deploy_answer.deploy
        choices = Choice.objects.filter(deploy_id=current_deploy_review.id)
        return render(request, self.template_name, {'deploy': current_deploy_review, 'choices': choices, 'deploy_answer': current_deploy_answer})

    def post(self, request, block_answer_id):
        current_deploy_index_review = self.current_index(request) + 1
        if current_deploy_index_review >= len(self.deploys_answer):
            request.session[self.index_key] = 0
            return redirect('trainingApp:review_block', self.block_answer.trainee_Training_id)

        request.session[self.index_key] = current_deploy_index_review
        return redirect('trainingApp:review_deploy', block_answer_id=block_answer_id)


class CommentView(LoginRequiredMixin, View):
    login_url = 'userApp:signup'
    template_name = "trainingApp/comment_form.html"

    def get_trainee_and_training(self, request, course_id, training_id):
        """Valida que el trainee tenga acceso al curso y haya terminado el training; si no, 404."""
        trainee = get_object_or_404(Trainee, user=request.user)
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)
        if not (
            rules.can_view_course(trainee, course)
            and rules.training_in_course(course, training_id)
            and rules.finished_attempts(trainee, course, training).exists()
        ):
            raise Http404("Training not available for comments")
        return trainee, training

    def get(self, request, course_id, training_id):
        self.get_trainee_and_training(request, course_id, training_id)
        commentform = CommentForm()

        return render(request, self.template_name, {"form": commentform, "course_id": course_id, "training_id": training_id})

    def post(self, request, course_id, training_id):
        trainee, training = self.get_trainee_and_training(request, course_id, training_id)
        commentform = CommentForm(request.POST)

        if commentform.is_valid():
            Comment.objects.create(
                trainee=trainee,
                training=training,
                pub_date=timezone.now(),
                course_rating=commentform.cleaned_data['course_rating'],
                training_method=commentform.cleaned_data['training_method'],
                explanations=commentform.cleaned_data['explanations'],
                stars=commentform.cleaned_data['stars'],
            )
            return HttpResponseRedirect(reverse('trainingApp:course_detail', args=[course_id]))

        else:
            messages.error(request, _("error"))
            return HttpResponseRedirect(reverse('trainingApp:course_detail', args=[course_id]))


def tutorial(request):
    """Vista para la página de tutorial que explica cómo usar la aplicación"""
    return render(request, 'trainingApp/tutorial.html')

