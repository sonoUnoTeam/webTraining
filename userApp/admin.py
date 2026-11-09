from django import forms
from django.contrib import admin
from django.contrib.auth.admin import (
    GroupAdmin as BaseGroupAdmin,
    UserAdmin as BaseUserAdmin,
)
from django.contrib.auth.models import Group, User
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _, ngettext
from unfold.admin import ModelAdmin
from unfold.forms import (
    ActionForm,
    AdminPasswordChangeForm,
    UserChangeForm,
    UserCreationForm,
)
from unfold.widgets import UnfoldAdminSelectWidget

from trainingApp import admin_views
from trainingApp.models import Course, TraineeGroup

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


class TraineeActionForm(ActionForm):
    """Barra de acciones con el grupo de destino de "Mover a grupo" (visible solo con esa acción)."""

    group = forms.ModelChoiceField(
        queryset=TraineeGroup.objects.all(),
        required=False,
        label="",
        empty_label=_("Choose the group…"),
        widget=UnfoldAdminSelectWidget(
            {
                # Mismo estilo que el selector de acciones de Unfold
                "class": ActionForm.base_fields["action"].widget.attrs["class"],
                "aria-label": _("Group to move the trainees to"),
                "x-show": "action === 'move_to_group'",
            }
        ),
    )


@admin.register(Trainee)
class TraineeAdmin(ModelAdmin):
    list_display = (
        "__str__",
        "user",
        "group",
        "visible_courses",
        "age",
        "educationalLevel",
        "occupation",
    )
    list_filter = ("group", "educationalLevel")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )
    list_select_related = ("user", "group")
    autocomplete_fields = ("user",)
    action_form = TraineeActionForm
    actions = ("move_to_group",)
    readonly_fields = ("access_summary",)
    fieldsets = (
        (None, {"fields": ("user", "age", "educationalLevel", "occupation")}),
        (
            _("Access to courses"),
            {
                "fields": ("group", "access_summary"),
                "description": _(
                    "The group decides which courses the trainee sees. To move several "
                    "trainees at once, select them in the list and use "
                    '"Move to group", or edit the trainee group.'
                ),
            },
        ),
    )

    def get_queryset(self, request):
        active_courses = Course.objects.filter(
            state_course=Course.StateCourse.Active
        ).order_by("id")
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                Prefetch(
                    "group__courses",
                    queryset=active_courses,
                    to_attr="active_courses",
                )
            )
        )

    @admin.display(description=_("Courses they see"))
    def visible_courses(self, obj):
        if obj.group is None:
            return _("None: no group")
        courses = obj.group.active_courses
        return ", ".join(str(course) for course in courses) or _("None")

    @admin.display(description=_("Courses and trainings they see"))
    def access_summary(self, obj):
        if obj is None or obj.pk is None:
            return "-"
        return admin_views.group_access_html(obj.group)

    @admin.action(
        description=_("Move to group"),
        permissions=["change"],
    )
    def move_to_group(self, request, queryset):
        group_id = request.POST.get("group")
        group = (
            TraineeGroup.objects.filter(pk=group_id).first()
            if group_id and group_id.isdigit()
            else None
        )
        if group is None:
            self.message_user(
                request,
                _("Choose the group to move the trainees to."),
                level="warning",
            )
            return
        count = queryset.update(group=group)
        self.message_user(
            request,
            ngettext(
                '%(count)d trainee moved to "%(group)s".',
                '%(count)d trainees moved to "%(group)s".',
                count,
            )
            % {"count": count, "group": group},
        )
