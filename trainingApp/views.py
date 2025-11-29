from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from django.views import View
from django.views.generic import ListView
from .forms import QuestionForm,CommentForm
from .models import Training, Deploy, DeployAnswer, TraineeTraining, Block, Choice, Comment,BlockAnswer
from userApp.models import Trainee
from django.utils import timezone
from django.utils.translation import gettext as _

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from operator import attrgetter
from datetime import datetime, timedelta
from django.contrib.auth.mixins import LoginRequiredMixin  #LoginRequiredMixin se utiliza como un mixin para requerir que un usuario esté autenticado antes de acceder a una vista específica.
from django.urls import reverse


#Vista para ver la lista de trainings
class TrainingList(ListView):
    model = Training 
    template_name = "trainingApp/training_List.html"
    context_object_name = "training_list"
    paginate_by = 5  # Especifica la cantidad de objetos por página
    
    def get_queryset(self):
        try:
            trainee = Trainee.objects.get(user = self.request.user)
        except Trainee.DoesNotExist:
            messages.error(self.request, _("You need to be a trainee to access trainings."))
            return Training.objects.none()
        # Filtra los objetos TraineeTraining por training_id y user_id
        queryset = Training.objects.filter(state_training = 'Active',groups__in=[trainee.group]).order_by('id') #el subfijo __in indica que estamos buscando coincidencias en una lista de valores. 
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        try:
            trainee = Trainee.objects.get(user_id=user.id)
        except Trainee.DoesNotExist:
            return context
        
        # Añado un diccionario al context donde esta el id de cada training con la cantidad de veces realizado por el trainee
        context['num_trainee_trainings'] = {training.id: training.get_num_trainee_trainings(trainee.id)      for training in context['training_list']}
        
        # Traducir las dificultades antes de pasarlas al contexto
        for training in context['training_list']:
            training.difficulty = _(training.get_difficulty_display())
            
        return context
    
class BlockDeployList(ListView):
    model = Block
    template_name = "trainingApp/block_deploy_list.html"
    context_object_name = "block_list"
    paginate_by = 5  # Especifica la cantidad de objetos por página
   
    def get_queryset(self):
        # Obtén el training_id de la URL
        training_id = self.kwargs['training_id']

        # Filtra los objetos TraineeTraining por training_id y user_id
        queryset = Block.objects.filter(
            training=training_id,
        )
        queryset = queryset.order_by('id')
        return queryset
    
    # El metodo dispatch se llama cada vez que se accede a la vista, antes de que se llame al método correspondiente (get, post, etc.),
    def dispatch(self, request, *args, **kwargs):
        # Obtén el training_id de la URL
        training_id = self.kwargs['training_id']

        # Llama a la función initialize_trainee_training
        self.initialize_trainee_training(request, training_id)

        return super().dispatch(request, *args, **kwargs)

    def initialize_trainee_training(self, request, training_id):
        # Verifica si es la primera vez que el trainee ingresa al entrenamiento
        if f'current_trainee_training_id_{training_id}' not in request.session:
            usuario = request.user
            try:
                trainee= Trainee.objects.get(user_id=usuario.id)
            except Trainee.DoesNotExist:
                messages.error(request, _("You need to be a trainee to access trainings."))
                return redirect('home')
            # Se crea un nuevo objeto TraineeTraining y se guarda en la base de datos
            trainee_training = TraineeTraining.objects.create(
                trainee=trainee,
                training=get_object_or_404(Training, pk=training_id),
                pub_date=timezone.now(),
                state = "in_progress"
            )
            # Almacena el ID del TraineeTraining en la sesión
            request.session[f'current_trainee_training_id_{training_id}'] = trainee_training.id
            # Se guarda el tiempo de inicio del training
            request.session[f'start_time_{training_id}'] = datetime.now().isoformat()
            
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener el training_id de la URL
        training_id = self.kwargs['training_id']

        # Obtengo el current_trainee_training de la sesión
        current_trainee_training = self.request.session.get(f'current_trainee_training_id_{training_id}')

        # Verificar si current_trainee_training está presente en la sesión
        if current_trainee_training is None:
            # Manejar el caso en que current_trainee_training no está en la sesión
            raise ValueError("current_trainee_training no está presente en la sesión.")

        # Inicializar el diccionario states_blocks
        states_blocks_answers = {}

        # Iterar sobre los bloques en context['block_list']
        for block in context['block_list']:
            try:
                # Intentar obtener el BlockAnswer asociado al Block
                blockAnswer = BlockAnswer.objects.get(trainee_Training=current_trainee_training, block=block.id)
                states_blocks_answers[f'{block.id}'] = blockAnswer.state_block
            except BlockAnswer.DoesNotExist:
                # Si no se encuentra un BlockAnswer asociado al Block, establecer el estado como "not started"
                states_blocks_answers[f'{block.id}'] =  _('not started')

        # Añadir el diccionario states_blocks al contexto
        context['states_blocks_answers'] = states_blocks_answers 
          
        # Añadir la clase BlockAnswer a context
        context['BlockAnswer'] = BlockAnswer 
        return context


#Vista para ver los deploys de un block y resolverlos
class DeployDetailView(View):
    template_name = 'trainingApp/forms.html'

    def get(self, request, training_id, block_id):
        deploys = Deploy.objects.filter(block=block_id)
        
        current_deploy_index = request.session.get(f'current_deploy_index_{block_id}', 0)
        # Guardar el índice actual en la sesión
        request.session[f'current_deploy_index_{block_id}'] = current_deploy_index
        
        current_deploy = deploys[current_deploy_index]
        
        # Verifica si es la primera vez que el trainee ingresa al entrenamiento
        self.initialize_block(request, block_id, training_id)

        self.form = QuestionForm(instance=current_deploy)
        block = Block.objects.get(pk = block_id)
        return render(request, self.template_name, {'deploy': current_deploy, 'form':self.form, 'block_id':block.id, 'training_id': training_id, 'current_deploy_index':current_deploy_index})
    
    def post(self, request, training_id, block_id):
        deploys = Deploy.objects.filter(block=block_id)
        
        current_deploy_index = request.session.get(f'current_deploy_index_{block_id}', 0)
        current_deploy = deploys[current_deploy_index]
        
        form = QuestionForm(request.POST, instance=current_deploy)
        
        current_block_answer_id =request.session.get(f'current_block_answer_id_{block_id}')
        

        if form.is_valid():
            # Guarda la respuesta del usuario en un nuevo objeto DeployAnswer
            # Obtener el ID de la opción seleccionada
            selected_choice_id = form.cleaned_data['selectedChoice']

            # Obtener el objeto Choice correspondiente
            selected_choice = Choice.objects.get(id=selected_choice_id)
            
            deploy_answer, created = DeployAnswer.objects.get_or_create(   #Get or create busca un objeto y si no lo encuentra lo crea con los atributos en default
                block_answer=BlockAnswer.objects.get(pk=current_block_answer_id),
                deploy=current_deploy,
                defaults={'selectedChoice': selected_choice}
            )
            # Si la respuesta ya existía, actualiza el campo 'selectedChoice'
            if not created:
                # Obtener el ID de la opción seleccionada
                selected_choice_id = form.cleaned_data['selectedChoice']

                # Obtener el objeto Choice correspondiente
                selected_choice = Choice.objects.get(id=selected_choice_id)
                #Sobreescribo la selected_choice
                deploy_answer.selectedChoice = selected_choice
                deploy_answer.save()

            # Avanzar al siguiente deploy
            current_deploy_index += 1
            
            #Si se llega al final del block entonces:
            if current_deploy_index >= deploys.count():
                request.session[f'current_deploy_index_{block_id}'] = 0   
                #Se obtiene el blockAnswer del intento y se cambia el estado a completed
                current_block_answer_id = request.session.get(f'current_block_answer_id_{block_id}')
                block_answer = BlockAnswer.objects.get(pk=current_block_answer_id)
                block_answer.state_block = BlockAnswer.StateBlockAnswer.Completed
                block_answer.save()
                del request.session[f'current_block_answer_id_{block_id}']
                
                current_trainee_training_id = request.session.get(f'current_trainee_training_id_{training_id}')
                all_block_answers = BlockAnswer.objects.filter(trainee_Training= current_trainee_training_id )
                all_blocks = Block.objects.filter(training=training_id,)
                
                # Verifica si todos los objetos en all_block_answer tienen state_block igual a "completed"
                all_completed = all(block_answer.state_block == BlockAnswer.StateBlockAnswer.Completed for block_answer in all_block_answers)
                
                    
                # Verificar si la cantidad de BlockAnswer es igual a la cantidad de Block
                correct_number_of_answers = len(all_block_answers) == len(all_blocks)
                
                # Si todos los blocks tienen state_block igual a "completed", entonces se marca al training como completed y se lo redirecciona a home
                if all_completed and correct_number_of_answers:               
                    trainee_training = TraineeTraining.objects.get(pk=current_trainee_training_id)
                    trainee_training.state = "Completed"
                    trainee_training.save()
                
                    # Logica para el tiempo empleado
                    start_time_str = request.session.get(f'start_time_{training_id}')
                    start_time = datetime.fromisoformat(start_time_str)
                    tiempo_transcurrido = datetime.now() - start_time

                    # Obtener la duración total en segundo
                    duracion_total = tiempo_transcurrido.total_seconds()

                    # Convertir la duración total a un objeto timedelta
                    duracion_timedelta = timedelta(seconds=duracion_total)

                    # Guardar la instancia en la base de datos
                    trainee_training.time_spent = duracion_timedelta
                    trainee_training.save()
                
                    #Se borra de la session los datos temporales
                    del request.session[f'current_deploy_index_{block_id}']
                    del request.session[f'start_time_{training_id}']
                    del request.session[f'current_trainee_training_id_{training_id}']
                
                    training = Training.objects.get(pk=training_id) 
                    messages.success(request, _("You have completed: %(training)s") % {"training": training.name_training})
                    return HttpResponseRedirect(reverse('trainingApp:comment', args=[training_id]))
                
                #Si completo el Block pero aun quedan mas por completar entonces lo redirecciona a la lista de blocks
                else : 
                    return HttpResponseRedirect(reverse('trainingApp:block_deploy_list', args=[training_id]))
                
            #Si todavia no llega al final del Block entonces    
            else:
                # Guardar el índice actual en la sesión
                request.session[f'current_deploy_index_{block_id}'] = current_deploy_index
                print("Todavia no termino el block")

                return HttpResponseRedirect(reverse('trainingApp:forms', args=[training_id,block_id]))

        else:
            # Si el formulario no es válido, renderizar la plantilla con el formulario nuevamente,
            # resaltando lo que falta para poder enviarlo.
            block = Block.objects.get(pk = block_id)
            return render(request, self.template_name, {'deploy': current_deploy, 'form':form, 'block_id':block.id, 'training_id': training_id, 'current_deploy_index':current_deploy_index})
        
        
    def initialize_block(self, request, block_id,training_id):
        # Verifica si es la primera vez que el trainee ingresa al block
        if f'current_block_answer_id_{block_id}' not in request.session:
            current_trainee_training = self.request.session.get(f'current_trainee_training_id_{training_id}')

            # Se crea un nuevo objeto BlockAnswer y se guarda en la base de datos
            block_answer = BlockAnswer.objects.create(
                trainee_Training= get_object_or_404(TraineeTraining, pk=current_trainee_training),
                block= get_object_or_404(Block, pk=block_id),
                state_block = BlockAnswer.StateBlockAnswer.in_progress
            )

            # Almacena el ID del BlockAnswer en la sesión
            request.session[f'current_block_answer_id_{block_id}'] = block_answer.id

#Funcion que retrocede un deploy             
def backDeploy(request, training_id, block_id):
        current_deploy_index = request.session.get(f'current_deploy_index_{block_id}')
        # Retrocedo al anterior deploy
        current_deploy_index = current_deploy_index -1
        #Si no hay deploy al que retroceder entonces se manda a la lista de blocks
        if current_deploy_index <0 :
            return redirect('trainingApp:block_deploy_list', training_id=training_id)
        else:
            # Guardar el índice actual en la sesión
            request.session[f'current_deploy_index_{block_id}'] = current_deploy_index
            return redirect('trainingApp:forms', training_id=training_id, block_id=block_id)


#Vista de todos los intentos realizados por el trainee para un training
class ReviewListTT(ListView):
    model = TraineeTraining 
    template_name = "trainingApp/review_list_tt.html"
    context_object_name = "trainee_training_list"
    paginate_by = 10  # Especifica la cantidad de objetos por página
    
    def get_queryset(self):
        # Obtén el training_id de la URL
        training_id = self.kwargs['training_id']
        
        try:
            trainee = Trainee.objects.get(user=self.request.user)
        except Trainee.DoesNotExist:
            messages.error(self.request, _("You need to be a trainee to access this page."))
            return TraineeTraining.objects.none()
        
        # Filtra los objetos TraineeTraining por training_id y user_id
        queryset = TraineeTraining.objects.filter(
            training_id=training_id,
            trainee_id=trainee.id,
            state = "Completed"
        )
           # Agregar un campo 'item_number' a cada objeto TraineeTraining
        for i, trainee_training in enumerate(queryset, start=1):
            trainee_training.item_number = i
            
         # Ordenar el queryset por el campo 'item_number' de forma descendente
        queryset = sorted(queryset, key=attrgetter('item_number'), reverse=True)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
#Vista de todos los blocks de un trainee-training
class ReviewBlock(ListView):
    model = BlockAnswer 
    template_name = "trainingApp/review_block.html"
    context_object_name = "blocks_answers"
    paginate_by = 10  # Especifica la cantidad de objetos por página
    
    def get_queryset(self):
        # Obtén el trainee_training_id de la URL
        trainee_training_id = self.kwargs['trainee_training_id']
        
        # Filtra los objetos BlockAnswer por trainee_training_id
        queryset = BlockAnswer.objects.filter(
            trainee_Training= trainee_training_id,
        )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        trainee_training_id = self.kwargs['trainee_training_id']
        training_id= TraineeTraining.objects.get(pk=trainee_training_id).training.id
        context['training_id'] = training_id
        return context
    
#Vista para ver deploys de un block de una review
class ReviewDeploy(View):
    template_name = 'trainingApp/review_deploy.html'
    
    def get(self, request, block_answer_id):
        deploys_answer = DeployAnswer.objects.filter(block_answer=block_answer_id)
        deploys = [deploy_answer.deploy for deploy_answer in deploys_answer]
        
        #Indice del deploy actual para revision
        current_deploy_index_review = request.session.get(f'current_deploy_index_review_{block_answer_id}', 0)
        #Deploy actual
        current_deploy_review = deploys[current_deploy_index_review]
        #Respuesta asociada al deploy actual
        current_deploy_answer = deploys_answer[current_deploy_index_review]
        #Busco las choices asociadas al deploy actual
        choices = Choice.objects.filter(deploy_id = current_deploy_review.id)
        return render(request, self.template_name, {'deploy': current_deploy_review, 'choices':choices, 'deploy_answer':current_deploy_answer})
    
    def post(self, request, block_answer_id): 
        block_answer= BlockAnswer.objects.get(pk=block_answer_id)
        deploys_answer = DeployAnswer.objects.filter(block_answer=block_answer_id)
        deploys = [deploy_answer.deploy for deploy_answer in deploys_answer]
        
        #Obtengo el indice del deploy actual
        current_deploy_index_review = request.session.get(f'current_deploy_index_review_{block_answer_id}', 0)
        # Avanzar al siguiente deploy
        current_deploy_index_review += 1
        #Si se llega al final del trainings entonces se lo redicciona al home y se resetea el current_deploy_index
        if current_deploy_index_review >= len(deploys):
            request.session[f'current_deploy_index_review_{block_answer_id}'] = 0  
            return redirect('trainingApp:review_block',block_answer.trainee_Training.id)
        
        # Guardar el índice actual en la sesión
        request.session[f'current_deploy_index_review_{block_answer_id}'] = current_deploy_index_review
        return redirect('trainingApp:review_deploy', block_answer_id=block_answer_id)
    
#Vista para realizar un comentario a un trainee
class CommentView(LoginRequiredMixin, View):
    login_url = 'signup' # Esta propiedad especifica la URL a la cual se redirigirá a los usuarios no autenticados
    template_name = "trainingApp/comment_form.html"

    def get(self, request, training_id):
        user = self.request.user
        try:
            trainee = Trainee.objects.get(user_id= user.id)
        except Trainee.DoesNotExist:
            messages.error(request, _("You need to be a trainee to access this page."))
            return redirect('home')
        
        commentform = CommentForm()

        return render(request, self.template_name, {"form": commentform})

    def post(self, request, training_id):
        user = self.request.user
        try:
            trainee = Trainee.objects.get(user_id= user.id)
        except Trainee.DoesNotExist:
            messages.error(request, _("You need to be a trainee to access this page."))
            return redirect('home')
        
        commentform = CommentForm(request.POST)
        
        if commentform.is_valid():
            comment = Comment.objects.create(
                trainee=trainee,
                training=get_object_or_404(Training, pk=training_id),
                pub_date=timezone.now(),
                more_liked = commentform.cleaned_data['more_liked'],
                least_liked = commentform.cleaned_data['least_liked'],
                stars = commentform.cleaned_data['stars'],
                comment_aditional= commentform.cleaned_data['comment_aditional'],
            )
            return HttpResponseRedirect(reverse('home'))

        else:
            messages.error(request, _("error"))
            return HttpResponseRedirect(reverse('home'))