from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

class Trainee(models.Model):
    #Enumeracion para el nivel educativo del user
    class EducationalLevel(models.TextChoices):
        Primary_School = 'Primary School', _('Primary School')
        High_School = 'High School', _('High School')
        Associate  = 'Associate', _('Associate')
        University  = 'University', _('University')
        Doctoral_Student  = 'Doctoral Student', _('Doctoral Student')
        Magister  = 'Magister', _('Magister')
        Doctor  = 'Doctor', _('Doctor')

    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name=_('user'))
    age =  models.IntegerField(default=18, verbose_name=_('Age'))
    educationalLevel = models.CharField(
        max_length=50,
        choices=EducationalLevel.choices,
        default=EducationalLevel.High_School,
        verbose_name=_('Educational Level')
    )
    occupation = models.CharField(max_length=50, verbose_name=_('Occupation'))
    group =  models.ForeignKey(
        'trainingApp.TraineeGroup', on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('trainee group')
    )

    class Meta:
        verbose_name = _('trainee')
        verbose_name_plural = _('trainees')

    def __str__(self):
        return self.user.get_full_name() or self.user.username
