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
        fields = ['more_liked', 'least_liked', 'comment_aditional', 'stars']    
        widgets = {
            'more_liked': forms.RadioSelect(),
            'stars': forms.RadioSelect(),
            'least_liked': forms.RadioSelect(),
        }       
    
    def __init__(self, *args, **kwargs):
        super(CommentForm, self).__init__(*args, **kwargs)
        
        # Configurar valores predeterminados para RadioSelect
        self.fields['more_liked'].initial = Comment.MostLiked.WELL_EXPLAINED
        self.fields['stars'].initial = '1'
        self.fields['least_liked'].initial = Comment.LeastLiked.NOT_INTERESTING

        # Eliminar opciones en blanco de los RadioSelect
        self.fields['more_liked'].widget.choices = [choice for choice in self.fields['more_liked'].widget.choices if choice[0] != ""]
        self.fields['stars'].widget.choices = [choice for choice in self.fields['stars'].widget.choices if choice[0] != ""]
        self.fields['least_liked'].widget.choices = [choice for choice in self.fields['least_liked'].widget.choices if choice[0] != ""]

