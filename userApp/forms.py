
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, UserChangeForm
from django.contrib.auth.models import User
from .models import Trainee

class SignupForm(UserCreationForm):
    age = forms.IntegerField(initial=18)
    educationalLevel = forms.ChoiceField(choices=Trainee.EducationalLevel.choices,
                                            initial=Trainee.EducationalLevel.High_School,
                                            widget=forms.RadioSelect(),)
    occupation = forms.CharField(max_length=50)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'age', 'educationalLevel', 'occupation']
        
class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username','first_name', 'last_name', 'email']    
    
    def __init__(self, *args, **kwargs):
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['first_name'].initial = self.instance.first_name
            self.fields['last_name'].initial = self.instance.last_name
            self.fields['email'].initial = self.instance.email   

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

class TraineeUpdateForm(forms.ModelForm):
    age = forms.IntegerField(required=True)
    occupation = forms.CharField(max_length=50, required=True)

    class Meta:
        model = Trainee
        fields = ['age', 'educationalLevel', 'occupation']
        widgets = {
            'educationalLevel': forms.RadioSelect(),
        } 
    def __init__(self, *args, **kwargs):
        super(TraineeUpdateForm, self).__init__(*args, **kwargs)
        if self.instance:
            self.fields['age'].initial = self.instance.age
            self.fields['educationalLevel'].initial = self.instance.educationalLevel
            self.fields['occupation'].initial = self.instance.occupation

    def clean_age(self):
        age = self.cleaned_data.get('age')
        if age is not None and (age < 1 or age > 120):
            raise forms.ValidationError("Age must be between 1 and 120.")
        return age