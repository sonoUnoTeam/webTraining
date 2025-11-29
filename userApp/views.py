from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from .forms import SignupForm,UserUpdateForm,TraineeUpdateForm
from django.contrib import messages
from .models import Trainee
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin  #LoginRequiredMixin se utiliza como un mixin para requerir que un usuario esté autenticado antes de acceder a una vista específica.
from django.contrib.auth.views import PasswordChangeView, PasswordResetDoneView
from django.urls import reverse_lazy
from trainingApp.models import Group
from django.core.mail import send_mail
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from dotenv import load_dotenv
import os
import logging
import smtplib
from django.contrib.auth import REDIRECT_FIELD_NAME, get_user_model
from django.urls import reverse_lazy
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth.forms import PasswordResetForm
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordContextMixin
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.edit import FormView

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

##Logica de users 
def home(request):
    return render(request, 'home.html')

@transaction.atomic
def signup(request):
    if request.method == 'GET':
        form = SignupForm()
        return render(request, 'userApp/signup.html', {"form": form})
    else:
        form = SignupForm(request.POST)
        if form.is_valid():
            # Verificar si el email ya fue usado por otro usuario
            email = form.cleaned_data.get('email')
            if email and User.objects.filter(email__iexact=email).exists():
                messages.error(request, _("The email entered is already registered."))
                return render(request, 'userApp/signup.html', {"form": form})

            user = form.save()
            # Crear el objeto Trainee y se relaciona con el usuario y al grupo por defecto
            group_defect, created = Group.objects.get_or_create(name_group='Group Defect')
            trainee = Trainee(
                    user=user,
                    age=form.cleaned_data['age'],
                    educationalLevel=form.cleaned_data['educationalLevel'],
                    occupation=form.cleaned_data['occupation'],
                    group=group_defect
                )
            trainee.save()
            login(request, user)
            messages.success(request, _("User created successfully"))
            return redirect('home')
        
        else:
            messages.error(request, _("Error creating user"))
            return render(request, 'userApp/signup.html', {"form": form})
import traceback        
def activate(request, uidb64, token):
    try:
        #Decodifico la uid y verifico que el usuario exista
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        print(traceback.format_exc())
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, _("Your account has been activated successfully."))
        return redirect('home')
    else:
        messages.error(request, _("Error activating account"))
        return redirect('home')
        
@login_required
def signout(request):
    logout(request)
    return redirect('home')


def signin(request):
    if request.method == 'GET':
        return render(request, 'userApp/signin.html', {"form": AuthenticationForm})
    else:
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user is None:
            messages.error(request, _("Username or Password incorrect"))
            return render(request, 'userApp/signin.html', {"form": AuthenticationForm})
        else:
            login(request, user)
            messages.success(request, _("You are logged in as %(username)s") % {"username": request.POST['username']})
            return redirect('trainingApp:training_List')

#Vista para modificar datos del user y trainee
class ProfileView(LoginRequiredMixin, View):
    login_url = 'signup' # Esta propiedad especifica la URL a la cual se redirigirá a los usuarios no autenticados cuando intenten acceder a la vista protegida por este mixin.
    template_name = "userApp/profile.html"

    def get(self, request, username):
        user = User.objects.get(username= username)
        try:
            trainee = Trainee.objects.get(user_id=user.id)
        except Trainee.DoesNotExist:
            messages.error(request, _("You need to be a trainee to access this page."))
            return redirect('home')
        
        # Crea una instancia del formulario combinado y pasa el objeto user y Trainee como instancia
        userform = UserUpdateForm(instance=user)
        traineeform = TraineeUpdateForm(instance=trainee)

        return render(request, self.template_name, {"userform": userform, "traineeform": traineeform})

    def post(self, request, username):
        user = User.objects.get(username= username)
        try:
            trainee = Trainee.objects.get(user_id=user.id)
        except Trainee.DoesNotExist:
            messages.error(request, _("You need to be a trainee to access this page."))
            return redirect('home')

        # Crea una instancia del formulario combinado y pasa el objeto Trainee como instancia
        userform = UserUpdateForm(request.POST, instance=user)
        traineeform = TraineeUpdateForm(request.POST,instance=trainee)
        
        if userform.is_valid() and traineeform.is_valid():
            userform.save()
            traineeform.save()
            messages.success(request, _("Your profile has been updated"))
            return redirect('userApp:profile', user.username)  # Redirige a la página de perfil después de guardar los cambios

        else:
            messages.error(request, _("error"))
            return redirect('userApp:profile', user.username) 

#Vista para modificar password
class MyPasswordChangeView(PasswordChangeView):
    template_name= "userApp/passwordChange.html"
    success_url = reverse_lazy('userApp:passwordResetDone')  #la URL a la que se redirigirá al usuario después de cambiar exitosamente la contrasena.
    
#Vista una vez modificada la password exisitamente
class MyPasswordResetDoneView(PasswordResetDoneView):
    template_name= "userApp/password_change_done.html"

class CustomPasswordResetView(PasswordResetView):
    email_template_name = "registration/password_reset_email.html"
    extra_email_context = None
    form_class = PasswordResetForm
    from_email = None
    html_email_template_name = None
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("userApp:password_reset_done")
    template_name = "registration/password_reset_form.html"
    title = _("Password reset")
    token_generator = default_token_generator

    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def form_valid(self, form):
        # Validación: comprobar si el email ingresado está registrado
        email = form.cleaned_data.get('email')
        if not get_user_model()._default_manager.filter(email__iexact=(email or '')).exists():
            messages.error(self.request, _("The email entered is not registered."))
            return self.form_invalid(form)

        opts = {
            "use_https": self.request.is_secure(),
            "token_generator": self.token_generator,
            "from_email": self.from_email,
            "email_template_name": self.email_template_name,
            "subject_template_name": self.subject_template_name,
            "request": self.request,
            "html_email_template_name": self.html_email_template_name,
            "extra_email_context": self.extra_email_context,
        }
        try:
            form.save(**opts)
        except (ConnectionRefusedError, smtplib.SMTPAuthenticationError, smtplib.SMTPException, Exception) as e:
            logger = logging.getLogger(__name__)
            logger.exception("Error sending password reset email: %s", e)
            messages.error(
                self.request,
                _(
                    "An error occurred while trying to send the email, contact the administrator."
                ),
            )
            return super().form_valid(form)

        return super().form_valid(form)
    
    
INTERNAL_RESET_SESSION_TOKEN = "_password_reset_token"
UserModel = get_user_model()    
class CustomPasswordResetConfirmView(PasswordContextMixin, FormView):
    form_class = SetPasswordForm
    post_reset_login = False
    post_reset_login_backend = None
    reset_url_token = "set-password"
    success_url = reverse_lazy("userApp:password_reset_complete")
    template_name = "registration/password_reset_confirm.html"
    title = _("Enter new password")
    token_generator = default_token_generator

    @method_decorator(sensitive_post_parameters())
    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        if "uidb64" not in kwargs or "token" not in kwargs:
            raise ImproperlyConfigured(
                "The URL path must contain 'uidb64' and 'token' parameters."
            )

        self.validlink = False
        self.user = self.get_user(kwargs["uidb64"])

        if self.user is not None:
            token = kwargs["token"]
            if token == self.reset_url_token:
                session_token = self.request.session.get(INTERNAL_RESET_SESSION_TOKEN)
                if self.token_generator.check_token(self.user, session_token):
                    # If the token is valid, display the password reset form.
                    self.validlink = True
                    return super().dispatch(*args, **kwargs)
            else:
                if self.token_generator.check_token(self.user, token):
                    # Store the token in the session and redirect to the
                    # password reset form at a URL without the token. That
                    # avoids the possibility of leaking the token in the
                    # HTTP Referer header.
                    self.request.session[INTERNAL_RESET_SESSION_TOKEN] = token
                    redirect_url = self.request.path.replace(
                        token, self.reset_url_token
                    )
                    return HttpResponseRedirect(redirect_url)

        # Display the "Password reset unsuccessful" page.
        return self.render_to_response(self.get_context_data())

    def get_user(self, uidb64):
        try:
            # urlsafe_base64_decode() decodes to bytestring
            uid = urlsafe_base64_decode(uidb64).decode()
            user = UserModel._default_manager.get(pk=uid)
        except (
            TypeError,
            ValueError,
            OverflowError,
            UserModel.DoesNotExist,
            ValidationError,
        ):
            user = None
        return user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.user
        return kwargs

    def form_valid(self, form):
        user = form.save()
        del self.request.session[INTERNAL_RESET_SESSION_TOKEN]
        if self.post_reset_login:
            auth_login(self.request, user, self.post_reset_login_backend)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.validlink:
            context["validlink"] = True
        else:
            context.update(
                {
                    "form": None,
                    "title": _("Password reset unsuccessful"),
                    "validlink": False,
                }
            )
        return context
