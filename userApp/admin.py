from django.contrib import admin
from django.contrib.auth.admin import (
    GroupAdmin as BaseGroupAdmin,
    UserAdmin as BaseUserAdmin,
)
from django.contrib.auth.models import Group, User
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Trainee

# Usuarios y roles con los formularios de Unfold para que tengan el mismo estilo que el resto del admin
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(Trainee)
class TraineeAdmin(ModelAdmin):
    list_display = ("__str__", "user", "group", "age", "educationalLevel", "occupation")
    list_filter = ("group", "educationalLevel")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )
    list_select_related = ("user", "group")
    autocomplete_fields = ("user",)
