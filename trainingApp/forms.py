from django import forms
from .models import TrainingQuestionAnswer,Choice,Comment

#primer tipo de formulario
class QuestionForm(forms.ModelForm):

    class Meta:
        model = TrainingQuestionAnswer
        fields = ['selectedChoice']
        
    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)

        # Obtener las opciones del deploy
        choices = Choice.objects.filter(deploy_id=self.instance.id)

        # Configuración del campo selectedChoice con las distintas opciones
        options = [(choice.id, choice.choice) for choice in choices]
        
        self.fields['selectedChoice'] = forms.ChoiceField(
            choices=options,
            widget=forms.RadioSelect(),
        )
        
class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ['course_rating', 'training_method', 'explanations', 'stars']    
        widgets = {
            'course_rating': forms.RadioSelect(),
            'training_method': forms.RadioSelect(),
            'explanations': forms.RadioSelect(),
            'stars': forms.RadioSelect(),
        }       
    
    def __init__(self, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        
        # Configurar valores predeterminados para RadioSelect
        self.fields['course_rating'].initial = Comment.CourseRating.INTERESTING
        self.fields['training_method'].initial = Comment.TrainingMethod.NOVEL
        self.fields['explanations'].initial = Comment.Explanations.VERY_USEFUL
        self.fields['stars'].initial = '1'

        # Eliminar opciones en blanco de los RadioSelect
        self.fields['course_rating'].widget.choices = [choice for choice in self.fields['course_rating'].widget.choices if choice[0] != ""]
        self.fields['training_method'].widget.choices = [choice for choice in self.fields['training_method'].widget.choices if choice[0] != ""]
        self.fields['explanations'].widget.choices = [choice for choice in self.fields['explanations'].widget.choices if choice[0] != ""]
        self.fields['stars'].widget.choices = [choice for choice in self.fields['stars'].widget.choices if choice[0] != ""]

