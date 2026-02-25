
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm, UserChangeForm, SetPasswordForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from .models import Trainee

class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label=_("New password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter new password'),
            'autocomplete': 'new-password'
        })
    )
    new_password2 = forms.CharField(
        label=_("New password confirmation"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm new password'),
            'autocomplete': 'new-password'
        })
    )

class SigninForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your username'),
            'autofocus': True
        })
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password'),
            'autocomplete': 'current-password'
        })
    )

class SignupForm(UserCreationForm):
    age = forms.IntegerField(
        initial=18,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your age')
        })
    )
    educationalLevel = forms.ChoiceField(
        choices=Trainee.EducationalLevel.choices,
        initial=Trainee.EducationalLevel.High_School,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    occupation = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your occupation')
        })
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2', 'age', 'educationalLevel', 'occupation']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Choose a username')
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your first name')
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your last name')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter your email address')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super(SignupForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Choose a username')
        })
        self.fields['first_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Enter your first name')
        })
        self.fields['last_name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Enter your last name')
        })
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Enter your email address')
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Create a password')
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Confirm your password')
        })
        
class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        required=True,
        label=_('First Name'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your first name')
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        label=_('Last Name'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your last name')
        })
    )
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email address')
        })
    )

    class Meta:
        model = User
        fields = ['username','first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Username')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super(UserUpdateForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'readonly': True
        })
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
    age = forms.IntegerField(
        required=True,
        label=_('Age'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your age')
        })
    )
    occupation = forms.CharField(
        max_length=50,
        required=True,
        label=_('Occupation'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your occupation')
        })
    )

    class Meta:
        model = Trainee
        fields = ['age', 'educationalLevel', 'occupation']
        widgets = {
            'educationalLevel': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
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
