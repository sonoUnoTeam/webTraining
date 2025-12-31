from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, Http404
from django.views import View
from django.views.generic import ListView
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
            except TraineeCourse.DoesNotExist:
                context['course_progress'][course.id] = {
                    'state': 'Not Started',
                    'current_training_index': 0,
                    'exam_passed': False
                }
                course.status = _("Not Started")
        
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
        return CourseTraining.objects.filter(course_id=course_id).order_by('order')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs['course_id']
        course = Course.objects.get(id=course_id)
        context['course'] = course

        user = self.request.user
        trainee = Trainee.objects.get(user_id=user.id)
        trainee_course = TraineeCourse.objects.get(trainee=trainee, course=course)
        context['trainee_course'] = trainee_course

        for ct in context['course_trainings']:
            if ct.order == 1:
                ct.enabled = True
            else:
                previous_order = ct.order - 1
                previous_ct = CourseTraining.objects.get(course=course, order=previous_order)
                ct.enabled = TraineeTraining.objects.filter(trainee=trainee, training=previous_ct.training, course=course, state="Completed").exists()
            ct.completed = TraineeTraining.objects.filter(trainee=trainee, training=ct.training, course=course, state="Completed").exists()

        num_trainee_trainings = {}
        for ct in context['course_trainings']:
            num_trainee_trainings[ct.training.id] = TraineeTraining.objects.filter(trainee=trainee, training=ct.training, course=course, state="Completed").count()
        
        if course.final_exam:
            num_trainee_trainings[course.final_exam.id] = TraineeTraining.objects.filter(trainee=trainee, training=course.final_exam, course=course, state="Completed").count()
        context['num_trainee_trainings'] = num_trainee_trainings

        context['all_completed'] = all(ct.completed for ct in context['course_trainings'])

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
        completed_attempts = TraineeTraining.objects.filter(
            trainee=trainee,
            training=training,
            course=course,
            state="Completed"
        ).count()
        in_progress_attempts = TraineeTraining.objects.filter(
            trainee=trainee,
            training=training,
            course=course,
            state="in_progress"
        ).count()
        
        if completed_attempts >= training.attempts_allowed:
            messages.error(request, _("You have reached the maximum number of attempts for this training."))
            return redirect('trainingApp:course_detail', course_id=course_id)
        if in_progress_attempts > 0:
            # Allow continuing the in_progress one
            pass
        elif completed_attempts < training.attempts_allowed:
            # Allow starting new
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
                state="in_progress"
            ).first()
            trainee_course = TraineeCourse.objects.get(trainee=trainee, course=course)
            
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
                    state="in_progress"
                )
                # Se guarda el tiempo de inicio del training
                request.session[start_time_key] = datetime.now().isoformat()
                
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
                state="in_progress"
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
                    state="in_progress"
                )
                # Se guarda el tiempo de inicio del training
                request.session[start_time_key] = datetime.now().isoformat()
                
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

        self.form = QuestionForm(instance=current_deploy)
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
                    trainee_training.state = "Completed"
                    trainee_training.save()
                
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
                
                    trainee = Trainee.objects.get(user=self.request.user)
                
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
                    messages.success(request, _("You have completed: %(training)s") % {"training": training.name_training})
                    
                    if courses_as_exam.exists():
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
        
        queryset = TraineeTraining.objects.filter(
            training_id=training_id,
            course_id=course_id,
            trainee_id=trainee.id,
            state = "Completed"
        )
        for i, trainee_training in enumerate(queryset, start=1):
            trainee_training.item_number = i
            
        queryset = sorted(queryset, key=attrgetter('item_number'), reverse=True)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs['course_id']
        training_id = self.kwargs['training_id']
        context['course_id'] = course_id
        context['training_id'] = training_id
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
                more_liked = commentform.cleaned_data['more_liked'],
                least_liked = commentform.cleaned_data['least_liked'],
                stars = commentform.cleaned_data['stars'],
                comment_aditional= commentform.cleaned_data['comment_aditional'],
            )
            return HttpResponseRedirect(reverse('trainingApp:course_detail', args=[course_id]))

        else:
            messages.error(request, _("error"))
            return HttpResponseRedirect(reverse('trainingApp:course_detail', args=[course_id]))

