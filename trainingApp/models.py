import datetime
from django.db import models
from userApp.models import Trainee
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Sum, Max
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_delete
from django.dispatch import receiver

class TraineeGroup(models.Model):
    name_group = models.CharField(max_length=100)
    description = models.CharField(max_length=300)
    
    def __str__(self):
        return f"Group_Id: {self.id}, name_group: {self.name_group}"
    
class Training(models.Model):
    #Enumeracion para el tipo de entrenamiento
    class TrainingType(models.TextChoices):
        Easy = 'Easy', _('Easy')
        Intemediate = 'Intermediate', _('Intermediate')
        Advanced = 'Advanced', _('Advanced')
        
    class StateTraining(models.TextChoices):
        Active = 'Active', _('Active')
        inactive = 'Inactive', _('Inactive')
        
    name_training = models.CharField(max_length=200)
    pub_date = models.DateTimeField("upload date", auto_now_add=True)
    modificationDate = models.DateTimeField(auto_now= True)
    difficulty = models.CharField(
        max_length=20,
        choices=TrainingType.choices,
        default=TrainingType.Easy
    )
    estimatedDuration = models.IntegerField(default=0)
    state_training= models.CharField(
        max_length=20,
        choices=StateTraining.choices,
        default=StateTraining.Active
    )
    #Atributo que gestiona la cantidad de veces que se puede realizar el training
    attempts_allowed = models.IntegerField(default=1)
    groups = models.ManyToManyField(TraineeGroup)
    
    def was_published_recently(self):
        return self.pub_date >=timezone.now() - datetime.timedelta(days=1)
    def __str__(self):
        return self.name_training
    
    #Metodo que trae la cantidad de veces que se realizo un training por un trainee especifico
    def get_num_trainee_trainings(self, trainee_id):
        return TraineeTraining.objects.filter(training=self, trainee_id=trainee_id).count()
    @property
    def total_estimated_duration(self):
        """
        Calcula y devuelve la suma de los estimatedDuration de todos los bloques asociados a este entrenamiento.
        """
        return self.trainingblock_set.aggregate(total_duration=Sum('estimed_duration_block'))['total_duration'] or 0

class TrainingBlock(models.Model):
    class StateBlock(models.TextChoices):
        Active = 'Active', _('Active')
        inactive = 'Inactive', _('Inactive')
        
    name_block = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    estimed_duration_block = models.IntegerField(default=0)
    state_block= models.CharField(
        max_length=20,
        choices=StateBlock.choices,
        default=StateBlock.Active
    )
    training = models.ForeignKey(Training, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"BlockID: {self.id}, Name Block: {self.name_block}, Training: {self.training.name_training}"
    
    
class TrainingQuestion(models.Model):
    block = models.ForeignKey(TrainingBlock, on_delete=models.CASCADE, null=True)
    question = models.CharField(max_length=100, null=True)
    deploy_image = models.ImageField(upload_to="trainingApp/images", blank=True)
    deploy_sound = models.FileField(upload_to="trainingApp/sound", blank=True)
    #Respuesta correcta
    #correct_answer = models.CharField(max_length=100, null=True) 

    def __str__(self):
        if self.question:
            return f"Deploy {self.id}: {self.question}"
        return f"Deploy {self.id}"


class Choice(models.Model):
    deploy = models.ForeignKey(TrainingQuestion, on_delete=models.CASCADE)
    choice = models.CharField(max_length=100, null=True)
    correctChoice = models.BooleanField(default=False)
    def __str__(self):
        # Mostrar una etiqueta concisa: id + texto de la opción (+ marcar si es correcta)
        text = self.choice or ''
        suffix = ' (correct)' if self.correctChoice else ''
        return f"Choice {self.id}: {text}{suffix}"
    
    
class TraineeTraining(models.Model):
    # Foreign Key al progreso del trainee en el curso (padre)
    trainee_course = models.ForeignKey('TraineeCourse', on_delete=models.CASCADE, related_name='trainee_trainings')
    # Foreign Key de training
    training = models.ForeignKey(Training, on_delete=models.PROTECT)
    # Foreign Key de trainee 
    trainee = models.ForeignKey(Trainee, on_delete=models.CASCADE)
    # Foreign Key de course
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    pub_date = models.DateTimeField("upload date")
    state = models.CharField(max_length=100,default="in_progress")
    time_spent = models.DurationField(null=True, blank=True)
    
    class Meta:
        pass
    
    def __str__(self):
        return f"T.T_Id: {self.id}, Name Training: {self.training.name_training}, Name Trainee: {self.trainee.user.first_name}, Course: {self.course.name_course}"
    
class TrainingBlockAnswer(models.Model):
    class StateBlockAnswer(models.TextChoices):
        in_progress = 'In progress', _('In progress')
        Completed = 'Completed', _('Completed')
        
    state_block= models.CharField(
        max_length=20,
        choices=StateBlockAnswer.choices,
        default=StateBlockAnswer.in_progress
    )
    trainee_Training = models.ForeignKey(TraineeTraining, on_delete=models.CASCADE)
    block = models.ForeignKey(TrainingBlock, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Block_Answer_Id: {self.id}, Name block: {self.block.name_block}"


#Clase para guardar la respuesta del usuario de cada deploy
class TrainingQuestionAnswer(models.Model):
    
    #foreing Key de B.A
    block_answer = models.ForeignKey(TrainingBlockAnswer, on_delete=models.CASCADE, null=True)
    #foreing Key de deploy
    deploy = models.ForeignKey(TrainingQuestion, on_delete=models.CASCADE)
    #Respuesta a deploy
    #user_response = models.CharField(max_length=50, null=True)
    
    #foreing Key de choice seleccionada
    selectedChoice = models.ForeignKey(Choice, on_delete=models.CASCADE)

    def __str__(self):
        return f"Deploy_Answer_Id: {self.id}"
    
    
class Comment(models.Model):
    #Enumeracion para el tipo de entrenamiento
    class MostLiked(models.TextChoices):
        WELL_EXPLAINED = 'Well explained', _('Well explained')
        INTERESTING = 'Interesting', _('Interesting')
        EASY_TO_UNDERSTAND = 'Easy to understand', _('Easy to understand')

    class LeastLiked(models.TextChoices):
        TOO_DIFFICULT = 'Too difficult', _('Too difficult')
        NOT_INTERESTING = 'Not interesting', _('Not interesting')
        POORLY_EXPLAINED = 'Poorly explained', _('Poorly explained')
        CONFUSING = 'Confusing', _('Confusing')
        REPETITIVE = 'Repetitive', _('Repetitive')

    #foreing Key de training
    training = models.ForeignKey(Training, on_delete=models.CASCADE)
    #foreing Key de trainee
    trainee = models.ForeignKey(Trainee, on_delete=models.CASCADE)
    more_liked =  models.CharField(
        max_length=20,
        choices=MostLiked.choices,
        blank=False,
        null=False,
    )
    least_liked = models.CharField(
        max_length=20,
        choices=LeastLiked.choices,
        blank=False,
        null=False,
    )
    comment_aditional = models.CharField(max_length=500)
    stars = models.IntegerField(
        choices=[(i, i) for i in range(1, 6)],
        blank=False,
        null=False,
        )
    pub_date = models.DateTimeField("upload date")
    
    def __str__(self):
        return f"Comment_Id: {self.id}, Training: {self.training.name_training}, Trainee: {self.trainee.user.first_name}"


# Modelo para la tabla intermedia de Course y Training
class CourseTraining(models.Model):
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    training = models.ForeignKey(Training, on_delete=models.CASCADE)
    order = models.PositiveIntegerField()  # Orden del training en el curso

    class Meta:
        unique_together = (('course', 'training'), ('course', 'order'))  # Un training no puede repetirse en el mismo curso, y order único por curso
        ordering = ['order']

    def save(self, *args, **kwargs):
        if not self.order:
            max_order = CourseTraining.objects.filter(course=self.course).exclude(pk=self.pk).aggregate(Max('order'))['order__max'] or 0
            self.order = max_order + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Course: {self.course.name_course}, Training: {self.training.name_training}, Order: {self.order}"


# Modelo para Course
class Course(models.Model):
    class StateCourse(models.TextChoices):
        Active = 'Active', _('Active')
        Inactive = 'Inactive', _('Inactive')

    name_course = models.CharField(max_length=200)
    description = models.CharField(max_length=500)
    pub_date = models.DateTimeField("upload date", auto_now_add=True)
    modification_date = models.DateTimeField(auto_now=True)
    state_course = models.CharField(
        max_length=20,
        choices=StateCourse.choices,
        default=StateCourse.Active
    )
    groups = models.ManyToManyField(TraineeGroup)  # Grupos que pueden acceder al curso
    trainings = models.ManyToManyField(Training, through=CourseTraining, related_name='courses')
    final_exam = models.ForeignKey(Training, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses_as_final_exam')

    def __str__(self):
        return self.name_course

@receiver(post_delete, sender=CourseTraining)
def reorder_course_trainings(sender, instance, **kwargs):
    course = instance.course
    trainings = course.coursetraining_set.order_by('order')
    for i, ct in enumerate(trainings, 1):
        if ct.order != i:
            ct.order = i
            ct.save()
            
# Modelo para el progreso del trainee en un curso
class TraineeCourse(models.Model):
    class StateTraineeCourse(models.TextChoices):
        Not_Started = 'Not Started', _('Not Started')
        In_Progress = 'In Progress', _('In Progress')
        Completed = 'Completed', _('Completed')
        Failed = 'Failed', _('Failed')

    trainee = models.ForeignKey(Trainee, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    state = models.CharField(
        max_length=20,
        choices=StateTraineeCourse.choices,
        default=StateTraineeCourse.Not_Started
    )
    current_training_index = models.PositiveIntegerField(default=0)  # Índice del training actual habilitado
    exam_passed = models.BooleanField(default=False)
    pub_date = models.DateTimeField("start date", auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('trainee', 'course')

    def __str__(self):
        return f"Trainee: {self.trainee.user.first_name}, Course: {self.course.name_course}, State: {self.state}"


