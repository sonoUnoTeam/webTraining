from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, Http404
from django.views import View
from django.views.generic import ListView
from django.db import models
from .forms import QuestionForm,CommentForm
from .models import Training, TrainingQuestion, TrainingQuestionAnswer, TraineeTraining, TrainingBlock, Choice, Comment,TrainingBlockAnswer, Course, CourseTraining, TraineeCourse
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
                total_trainings = CourseTraining.objects.filter(course=course).count()
                course.total_trainings = total_trainings
                
                # Calcular duración total del curso
                total_duration = CourseTraining.objects.filter(
                    course=course
                ).aggregate(
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
                course.total_trainings = CourseTraining.objects.filter(course=course).count()
                course.completed_count = 0
                course.last_activity = None
                course.started_date = None
                course.difficulty_level = 'medium'
                course.difficulty_display = _('Medium')
                
                # Calcular duración total para cursos no iniciados
                total_duration = CourseTraining.objects.filter(
                    course=course
                ).aggregate(
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
        # Orden por el campo order de CourseTraining (secuencial absoluto)
        course_trainings = CourseTraining.objects.filter(course_id=course_id).select_related('training').order_by('order')
        return course_trainings

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


class TrainingBlockDeployList(ListView):
    model = TrainingBlock
    template_name = "trainingApp/block_deploy_list.html"
    context_object_name = "block_list"
    paginate_by = 5
   
    def get_queryset(self):
        course_id = self.kwargs['course_id']
        training_id = self.kwargs['training_id']
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)
        if not (course.trainings.filter(id=training_id).exists() or course.final_exam_id == training_id):
            return TrainingBlock.objects.none()
        
        queryset = TrainingBlock.objects.filter(
            training__id=training_id,
        )
        queryset = queryset.order_by('id')
        return queryset
    
    def dispatch(self, request, *args, **kwargs):
        course_id = self.kwargs['course_id']
        training_id = self.kwargs['training_id']
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)
        if not (course.trainings.filter(id=training_id).exists() or course.final_exam_id == training_id):
            raise Http404("Training not in course")

        trainee = Trainee.objects.get(user_id=request.user.id)
        
        # Contar intentos completados (passed o failed)
        completed_attempts = TraineeTraining.objects.filter(
            trainee=trainee,
            training=training,
            course=course
        ).exclude(
            state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
        ).count()
        
        # Verificar si hay un intento en progreso
        in_progress_attempts = TraineeTraining.objects.filter(
            trainee=trainee,
            training=training,
            course=course,
            state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
        ).count()
        
        # Verificar si ya avanzó al siguiente training (bloquear intentos)
        # Usar el orden secuencial por el campo 'order'
        course_trainings = CourseTraining.objects.filter(course=course).select_related('training').order_by('order')
        
        current_position = None
        for idx, ct in enumerate(course_trainings):
            if ct.training.id == training_id:
                current_position = idx
                break
        
        # Si hay un training siguiente en el orden secuencial y tiene intentos, bloquear este
        # Pero no aplicar para el examen final
        if course.final_exam_id != training_id and current_position is not None and current_position < len(course_trainings) - 1:
            next_training = course_trainings[current_position + 1]
            has_next_attempts = TraineeTraining.objects.filter(
                trainee=trainee,
                training=next_training.training,
                course=course
            ).exclude(
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).exists()
            
            if has_next_attempts:
                messages.error(request, _("You cannot retry this training because you have already started the next one."))
                return redirect('trainingApp:course_detail', course_id=course_id)
        
        # Verificar límite de intentos
        if completed_attempts >= training.attempts_allowed and in_progress_attempts == 0:
            messages.error(request, _("You have reached the maximum number of attempts for this training."))
            return redirect('trainingApp:course_detail', course_id=course_id)
        
        if in_progress_attempts > 0:
            # Permitir continuar el intento en progreso
            pass
        elif completed_attempts < training.attempts_allowed:
            # Permitir iniciar nuevo intento
            pass
        else:
            messages.error(request, _("Cannot start this training."))
            return redirect('trainingApp:course_detail', course_id=course_id)

        self.initialize_trainee_training(request, course_id, training_id)

        return super().dispatch(request, *args, **kwargs)

    def initialize_trainee_training(self, request, course_id, training_id):
        session_key = f'current_trainee_training_id_{course_id}_{training_id}'
        start_time_key = f'start_time_{course_id}_{training_id}'
        
        # Verifica si es la primera vez que el trainee ingresa al entrenamiento
        if session_key not in request.session:
            usuario = request.user
            try:
                trainee= Trainee.objects.get(user_id=usuario.id)
            except Trainee.DoesNotExist:
                messages.error(request, _("You need to be a trainee to access trainings."))
                return redirect('home')
            course = get_object_or_404(Course, id=course_id)
            training = get_object_or_404(Training, pk=training_id)
            
            # Check if there is an in_progress training
            in_progress = TraineeTraining.objects.filter(
                trainee=trainee,
                training=training,
                course=course,
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).first()
            trainee_course = TraineeCourse.objects.get(trainee=trainee, course=course)
            
            if in_progress:
                trainee_training = in_progress
            else:
                # Si es el examen final, bloquear todos los entrenamientos con intentos restantes
                # Esto se logra simplemente iniciando el examen, ya que la lógica de bloqueo
                # en course_detail verifica si existe algún intento del siguiente training
                # (incluido in_progress)
                
                # Create new
                trainee_training = TraineeTraining.objects.create(
                    trainee_course=trainee_course,
                    trainee=trainee,
                    training=training,
                    course=course,
                    pub_date=timezone.now(),
                    state=TraineeTraining.StateTraineeTraining.IN_PROGRESS,
                    is_final_exam_attempt=(course.final_exam_id == training_id)
                )
                # Se guarda el tiempo de inicio del training
                request.session[start_time_key] = timezone.now().isoformat()
                
                # Update course state if starting first training
                if trainee_course.state == TraineeCourse.StateTraineeCourse.Not_Started:
                    trainee_course.state = TraineeCourse.StateTraineeCourse.In_Progress
                    trainee_course.save()
            
            # Almacena el ID del TraineeTraining en la sesión
            request.session[session_key] = trainee_training.id
        
        # Asegurarse de que start_time esté en sesión incluso si session_key ya existía
        if start_time_key not in request.session:
            trainee_training_id = request.session.get(session_key)
            if trainee_training_id:
                try:
                    trainee_training = TraineeTraining.objects.get(pk=trainee_training_id)
                    # Usar la fecha de publicación del trainee_training como tiempo de inicio
                    request.session[start_time_key] = trainee_training.pub_date.isoformat()
                except TraineeTraining.DoesNotExist:
                    pass
            
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        course_id = self.kwargs['course_id']
        training_id = self.kwargs['training_id']

        session_key = f'current_trainee_training_id_{course_id}_{training_id}'
        current_trainee_training = self.request.session.get(session_key)

        if current_trainee_training is None:
            raise ValueError("current_trainee_training no está presente en la sesión.")

        states_blocks_answers = {}

        for block in context['block_list']:
            block_answer = (
                TrainingBlockAnswer.objects
                .filter(trainee_Training=current_trainee_training, block=block.id)
                .order_by('-id')
                .first()
            )
            if block_answer:
                states_blocks_answers[f'{block.id}'] = block_answer.state_block
            else:
                states_blocks_answers[f'{block.id}'] =  _('not started')

        context['states_blocks_answers'] = states_blocks_answers 
        context['TrainingBlockAnswer'] = TrainingBlockAnswer 
        context['course_id'] = course_id
        context['training_id'] = training_id
        return context


class DeployDetailView(View):
    template_name = 'trainingApp/forms.html'

    def dispatch(self, request, *args, **kwargs):
        course_id = self.kwargs.get('course_id') or kwargs.get('course_id')
        training_id = self.kwargs.get('training_id') or kwargs.get('training_id')
        
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)
        if not (course.trainings.filter(id=training_id).exists() or course.final_exam_id == training_id):
            raise Http404("Training not in course")
        
        self.initialize_trainee_training(request, course_id, training_id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def initialize_trainee_training(self, request, course_id, training_id):
        session_key = f'current_trainee_training_id_{course_id}_{training_id}'
        start_time_key = f'start_time_{course_id}_{training_id}'
        
        # Verifica si es la primera vez que el trainee ingresa al entrenamiento
        if session_key not in request.session:
            usuario = request.user
            try:
                trainee = Trainee.objects.get(user_id=usuario.id)
            except Trainee.DoesNotExist:
                messages.error(request, _("You need to be a trainee to access trainings."))
                return redirect('home')
            course = get_object_or_404(Course, id=course_id)
            training = get_object_or_404(Training, pk=training_id)
            
            # Check if there is an in_progress training
            in_progress = TraineeTraining.objects.filter(
                trainee=trainee,
                training=training,
                course=course,
                state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
            ).first()
            trainee_course, created = TraineeCourse.objects.get_or_create(
                trainee=trainee,
                course=course,
                defaults={
                    'state': TraineeCourse.StateTraineeCourse.Not_Started,
                    'current_training_index': 0,
                    'exam_passed': False,
                    'pub_date': timezone.now()
                }
            )
            
            if in_progress:
                trainee_training = in_progress
            else:
                # Create new
                trainee_training = TraineeTraining.objects.create(
                    trainee_course=trainee_course,
                    trainee=trainee,
                    training=training,
                    course=course,
                    pub_date=timezone.now(),
                    state=TraineeTraining.StateTraineeTraining.IN_PROGRESS
                )
                # Se guarda el tiempo de inicio del training
                request.session[start_time_key] = timezone.now().isoformat()
                
                # Update course state if starting first training
                if trainee_course.state == TraineeCourse.StateTraineeCourse.Not_Started:
                    trainee_course.state = TraineeCourse.StateTraineeCourse.In_Progress
                    trainee_course.save()
            
            # Almacena el ID del TraineeTraining en la sesión
            request.session[session_key] = trainee_training.id
        
        # Asegurarse de que start_time esté en sesión incluso si session_key ya existía
        if start_time_key not in request.session:
            trainee_training_id = request.session.get(session_key)
            if trainee_training_id:
                try:
                    trainee_training = TraineeTraining.objects.get(pk=trainee_training_id)
                    # Usar la fecha de publicación del trainee_training como tiempo de inicio
                    request.session[start_time_key] = trainee_training.pub_date.isoformat()
                except TraineeTraining.DoesNotExist:
                    pass

    def get(self, request, course_id, training_id, block_id):
        deploys = TrainingQuestion.objects.filter(block=block_id)
        
        session_key = f'current_deploy_index_{course_id}_{training_id}_{block_id}'
        current_deploy_index = request.session.get(session_key, 0)
        # Guardar el índice actual en la sesión
        request.session[session_key] = current_deploy_index
        
        current_deploy = deploys[current_deploy_index]
        deploys_count = deploys.count()
        
        # Verifica si es la primera vez que el trainee ingresa al entrenamiento
        self.initialize_block(request, course_id, training_id, block_id)

        # Verificar si ya existe una respuesta guardada para este deploy
        block_answer_session_key = f'current_block_answer_id_{course_id}_{training_id}_{block_id}'
        current_block_answer_id = request.session.get(block_answer_session_key)
        
        initial_data = {}
        if current_block_answer_id:
            block_answer_obj = TrainingBlockAnswer.objects.get(pk=current_block_answer_id)
            deploy_answer = TrainingQuestionAnswer.objects.filter(
                block_answer=block_answer_obj,
                deploy=current_deploy
            ).first()
            
            if deploy_answer and deploy_answer.selectedChoice:
                initial_data['selectedChoice'] = deploy_answer.selectedChoice.id

        self.form = QuestionForm(instance=current_deploy, initial=initial_data)
        block = TrainingBlock.objects.get(pk = block_id)
        return render(request, self.template_name, {
            'deploy': current_deploy,
            'form': self.form,
            'block_id': block.id,
            'course_id': course_id,
            'training_id': training_id,
            'current_deploy_index': current_deploy_index,
            'deploys_count': deploys_count,
        })
    
    def post(self, request, course_id, training_id, block_id):
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)
        deploys = TrainingQuestion.objects.filter(block=block_id)
        
        session_key = f'current_deploy_index_{course_id}_{training_id}_{block_id}'
        current_deploy_index = request.session.get(session_key, 0)
        current_deploy = deploys[current_deploy_index]
        
        form = QuestionForm(request.POST, instance=current_deploy)
        
        block_answer_session_key = f'current_block_answer_id_{course_id}_{training_id}_{block_id}'
        current_block_answer_id =request.session.get(block_answer_session_key)
        

        if form.is_valid():
            selected_choice_id = form.cleaned_data['selectedChoice']
            selected_choice = Choice.objects.get(id=selected_choice_id)
            
            block_answer_obj = TrainingBlockAnswer.objects.get(pk=current_block_answer_id)
            deploy_answer = TrainingQuestionAnswer.objects.filter(
                block_answer=block_answer_obj,
                deploy=current_deploy
            ).first()
            
            if deploy_answer:
                deploy_answer.selectedChoice = selected_choice
                deploy_answer.save()
            else:
                deploy_answer = TrainingQuestionAnswer.objects.create(
                    block_answer=block_answer_obj,
                    deploy=current_deploy,
                    selectedChoice=selected_choice
                )

            current_deploy_index += 1
            
            if current_deploy_index >= deploys.count():
                request.session[session_key] = 0   
                current_block_answer_id = request.session.get(block_answer_session_key)
                block_answer = TrainingBlockAnswer.objects.get(pk=current_block_answer_id)
                block_answer.state_block = TrainingBlockAnswer.StateBlockAnswer.Completed
                block_answer.save()
                del request.session[block_answer_session_key]
                
                trainee_training_session_key = f'current_trainee_training_id_{course_id}_{training_id}'
                current_trainee_training_id = request.session.get(trainee_training_session_key)
                all_block_answers = TrainingBlockAnswer.objects.filter(trainee_Training= current_trainee_training_id )
                all_blocks = TrainingBlock.objects.filter(training=training_id,)
                
                all_completed = all(block_answer.state_block == TrainingBlockAnswer.StateBlockAnswer.Completed for block_answer in all_block_answers)
                
                correct_number_of_answers = len(all_block_answers) == len(all_blocks)
                
                if all_completed and correct_number_of_answers:               
                    trainee_training = TraineeTraining.objects.get(pk=current_trainee_training_id)
                    
                    # Lógica para calcular el tiempo empleado
                    start_time_session_key = f'start_time_{course_id}_{training_id}'
                    start_time_str = request.session.get(start_time_session_key)
                    
                    if start_time_str:
                        start_time = datetime.fromisoformat(start_time_str)
                        if timezone.is_naive(start_time):
                            start_time = timezone.make_aware(start_time)
                    else:
                        start_time = trainee_training.pub_date
                    
                    end_time = timezone.now()
                    
                    tiempo_transcurrido = end_time - start_time
                    duracion_total = tiempo_transcurrido.total_seconds()
                    duracion_timedelta = timedelta(seconds=duracion_total)

                    trainee_training.time_spent = duracion_timedelta
                    trainee_training.save()
                    
                    # Calcular puntuación y actualizar estado (passed/failed)
                    trainee_training.update_score_and_state()
                
                    trainee = Trainee.objects.get(user=self.request.user)
                
                    # Si aprobó el training, actualizar progreso del curso
                    if trainee_training.state == TraineeTraining.StateTraineeTraining.PASSED:
                        courses_as_exam = Course.objects.filter(final_exam=training)
                        for course_exam in courses_as_exam:
                            try:
                                trainee_course = TraineeCourse.objects.get(trainee=trainee, course=course_exam)
                                trainee_course.exam_passed = True
                                trainee_course.state = TraineeCourse.StateTraineeCourse.Completed
                                trainee_course.save()
                            except TraineeCourse.DoesNotExist:
                                pass
                        
                        try:
                            trainee_course = TraineeCourse.objects.get(trainee=trainee, course=course)
                            trainee_course.current_training_index += 1
                            trainee_course.save()
                        except TraineeCourse.DoesNotExist:
                            pass
                    
                    del request.session[session_key]
                    del request.session[start_time_session_key]
                    del request.session[trainee_training_session_key]
                    
                    training = Training.objects.get(pk=training_id)
                    
                    # Mensaje personalizado según si aprobó o no
                    if trainee_training.state == TraineeTraining.StateTraineeTraining.PASSED:
                        messages.success(
                            request, 
                            _("Congratulations! You passed '%(training)s' with %(score)s%%") % {
                                "training": training.name_training,
                                "score": trainee_training.score_percentage
                            }
                        )
                    else:
                        messages.warning(
                            request,
                            _("You completed '%(training)s' with %(score)s%%. You need %(passing)s%% to pass. You can retry if attempts are available.") % {
                                "training": training.name_training,
                                "score": trainee_training.score_percentage,
                                "passing": training.passing_score
                            }
                        )
                    
                    courses_as_exam = Course.objects.filter(final_exam=training)
                    if courses_as_exam.exists() and trainee_training.state == TraineeTraining.StateTraineeTraining.PASSED:
                        return HttpResponseRedirect(reverse('trainingApp:comment', args=[course_id, training_id]))
                    else:
                        return HttpResponseRedirect(reverse('trainingApp:course_detail', args=[course_id]))
                else : 
                    return HttpResponseRedirect(reverse('trainingApp:block_deploy_list', args=[course_id, training_id]))
                
            else:
                request.session[session_key] = current_deploy_index
                print("Todavia no termino el block")

                return HttpResponseRedirect(reverse('trainingApp:forms', args=[course_id, training_id, block_id]))

        else:
            block = TrainingBlock.objects.get(pk = block_id)
            deploys_count = deploys.count()
            return render(request, self.template_name, {
                'deploy': current_deploy,
                'form': form,
                'block_id': block.id,
                'course_id': course_id,
                'training_id': training_id,
                'current_deploy_index': current_deploy_index,
                'deploys_count': deploys_count,
            })
        
        
    def initialize_block(self, request, course_id, training_id, block_id):
        block_answer_session_key = f'current_block_answer_id_{course_id}_{training_id}_{block_id}'
        # Verifica si es la primera vez que el trainee ingresa al block
        if block_answer_session_key not in request.session:
            trainee_training_session_key = f'current_trainee_training_id_{course_id}_{training_id}'
            current_trainee_training = self.request.session.get(trainee_training_session_key)

            trainee_training = get_object_or_404(TraineeTraining, pk=current_trainee_training)
            block = get_object_or_404(TrainingBlock, pk=block_id)

            # Buscar si existe un TrainingBlockAnswer en progreso para este trainee_training y block
            block_answer = TrainingBlockAnswer.objects.filter(
                trainee_Training=trainee_training,
                block=block,
                state_block=TrainingBlockAnswer.StateBlockAnswer.in_progress
            ).order_by('-id').first()
            
            # Si no existe, crear uno nuevo
            if not block_answer:
                block_answer = TrainingBlockAnswer.objects.create(
                    trainee_Training=trainee_training,
                    block=block,
                    state_block=TrainingBlockAnswer.StateBlockAnswer.in_progress
                )

            # Almacena el ID del BlockAnswer en la sesión
            request.session[block_answer_session_key] = block_answer.id

#Funcion que retrocede un deploy             
def backDeploy(request, course_id, training_id, block_id):
        session_key = f'current_deploy_index_{course_id}_{training_id}_{block_id}'
        current_deploy_index = request.session.get(session_key)
        current_deploy_index = current_deploy_index -1
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
    
    def get_queryset(self):
        trainee_training_id = self.kwargs['trainee_training_id']
        
        # Filtra los objetos BlockAnswer por trainee_training_id
        queryset = TrainingBlockAnswer.objects.filter(
            trainee_Training= trainee_training_id,
        )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trainee_training_id = self.kwargs['trainee_training_id']
        trainee_training = TraineeTraining.objects.get(pk=trainee_training_id)
        context['training_id'] = trainee_training.training.id
        context['course_id'] = trainee_training.course.id
        return context


class ReviewDeploy(View):
    template_name = 'trainingApp/review_deploy.html'
    
    def get(self, request, block_answer_id):
        deploys_answer = TrainingQuestionAnswer.objects.filter(block_answer=block_answer_id)
        deploys = [deploy_answer.deploy for deploy_answer in deploys_answer]
        
        current_deploy_index_review = request.session.get(f'current_deploy_index_review_{block_answer_id}', 0)
        current_deploy_review = deploys[current_deploy_index_review]
        current_deploy_answer = deploys_answer[current_deploy_index_review]
        choices = Choice.objects.filter(deploy_id = current_deploy_review.id)
        return render(request, self.template_name, {'deploy': current_deploy_review, 'choices':choices, 'deploy_answer':current_deploy_answer})
    
    def post(self, request, block_answer_id): 
        block_answer= TrainingBlockAnswer.objects.get(pk=block_answer_id)
        deploys_answer = TrainingQuestionAnswer.objects.filter(block_answer=block_answer_id)
        deploys = [deploy_answer.deploy for deploy_answer in deploys_answer]
        
        current_deploy_index_review = request.session.get(f'current_deploy_index_review_{block_answer_id}', 0)
        current_deploy_index_review += 1
        if current_deploy_index_review >= len(deploys):
            request.session[f'current_deploy_index_review_{block_answer_id}'] = 0  
            return redirect('trainingApp:review_block',block_answer.trainee_Training.id)
        
        request.session[f'current_deploy_index_review_{block_answer_id}'] = current_deploy_index_review
        return redirect('trainingApp:review_deploy', block_answer_id=block_answer_id)


class CommentView(LoginRequiredMixin, View):
    login_url = 'signup'
    template_name = "trainingApp/comment_form.html"

    def get(self, request, course_id, training_id):
        user = self.request.user
        try:
            trainee = Trainee.objects.get(user_id= user.id)
        except Trainee.DoesNotExist:
            messages.error(request, _("You need to be a trainee to access this page."))
            return redirect('home')
        
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)
        if not (course.trainings.filter(id=training_id).exists() or course.final_exam_id == training_id):
            raise Http404("Training not in course")
        
        commentform = CommentForm()

        return render(request, self.template_name, {"form": commentform, "course_id": course_id, "training_id": training_id})

    def post(self, request, course_id, training_id):
        user = self.request.user
        try:
            trainee = Trainee.objects.get(user_id= user.id)
        except Trainee.DoesNotExist:
            messages.error(request, _("You need to be a trainee to access this page."))
            return redirect('home')
        
        course = get_object_or_404(Course, id=course_id)
        training = get_object_or_404(Training, id=training_id)
        if not (course.trainings.filter(id=training_id).exists() or course.final_exam_id == training_id):
            raise Http404("Training not in course")
        
        commentform = CommentForm(request.POST)
        
        if commentform.is_valid():
            comment = Comment.objects.create(
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

