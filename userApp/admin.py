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

# Acciones de la lista de trainees que usan el selector de grupo de la barra de acciones
GROUP_ACTIONS = ("add_to_group", "remove_from_group")


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


class TraineeActionForm(ActionForm):
    """Barra de acciones con el grupo de "Agregar a grupo" / "Quitar de grupo" (visible solo con esas acciones)."""

    group = forms.ModelChoiceField(
        queryset=TraineeGroup.objects.all(),
        required=False,
        label="",
        empty_label=_("Choose the group…"),
        widget=UnfoldAdminSelectWidget(
            {
                # Mismo estilo que el selector de acciones de Unfold
                "class": ActionForm.base_fields["action"].widget.attrs["class"],
                "aria-label": _("Trainee group for the action"),
                "x-show": f"{list(GROUP_ACTIONS)}.includes(action)",
            }
        ),
    )


@admin.register(Trainee)
class TraineeAdmin(ModelAdmin):
    list_display = (
        "__str__",
        "user",
        "groups_summary",
        "visible_courses",
        "age",
        "educationalLevel",
        "occupation",
    )
    list_filter = ("groups", "educationalLevel")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
    )
    list_select_related = ("user",)
    autocomplete_fields = ("user", "groups")
    action_form = TraineeActionForm
    actions = GROUP_ACTIONS
    readonly_fields = ("access_summary",)
    fieldsets = (
        (None, {"fields": ("user", "age", "educationalLevel", "occupation")}),
        (
            _("Access to courses"),
            {
                "fields": ("groups", "access_summary"),
                "description": _(
                    "The trainee sees the courses of all their groups. To change the groups of "
                    'several trainees at once, select them in the list and use "Add to group" or '
                    '"Remove from group", or edit the trainee group.'
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
                "groups",
                Prefetch(
                    "groups__courses",
                    queryset=active_courses,
                    to_attr="active_courses",
                ),
            )
        )

    @admin.display(description=_("Trainee groups"))
    def groups_summary(self, obj):
        return ", ".join(str(group) for group in obj.groups.all()) or _("None")

    @admin.display(description=_("Courses they see"))
    def visible_courses(self, obj):
        groups = obj.groups.all()
        if not groups:
            return _("None: no group")
        # Unión de los cursos activos de sus grupos, sin repetir y en orden de id
        courses = {
            course.pk: course for group in groups for course in group.active_courses
        }
        return ", ".join(str(courses[pk]) for pk in sorted(courses)) or _("None")

    @admin.display(description=_("Courses and trainings they see"))
    def access_summary(self, obj):
        if obj is None or obj.pk is None:
            return "-"
        # render_to_string devuelve HTML seguro (plantilla con autoescape)
        return admin_views.trainee_access_html(obj)

    def chosen_group(self, request):
        group_id = request.POST.get("group", "")
        group = (
            TraineeGroup.objects.filter(pk=group_id).first()
            if group_id.isdigit()
            else None
        )
        if group is None:
            self.message_user(
                request, _("Choose the trainee group for the action."), level="warning"
            )
        return group

    @admin.action(description=_("Add to group"), permissions=["change"])
    def add_to_group(self, request, queryset):
        group = self.chosen_group(request)
        if group is None:
            return
        trainees = list(queryset)
        group.members.add(*trainees)
        self.message_user(
            request,
            ngettext(
                '%(count)d trainee added to "%(group)s".',
                '%(count)d trainees added to "%(group)s".',
                len(trainees),
            )
            % {"count": len(trainees), "group": group},
        )

    @admin.action(description=_("Remove from group"), permissions=["change"])
    def remove_from_group(self, request, queryset):
        group = self.chosen_group(request)
        if group is None:
            return
        trainee_ids = list(queryset.values_list("pk", flat=True))
        if group.is_default:
            # Los que no tienen otro grupo volverían al grupo por defecto: se dejan como están
            only_here = group.members_without_other_group(trainee_ids)
            trainee_ids = [pk for pk in trainee_ids if pk not in only_here]
            if only_here:
                self.message_user(
                    request,
                    ngettext(
                        "%(count)d trainee has no other group and stays in the default group.",
                        "%(count)d trainees have no other group and stay in the default group.",
                        len(only_here),
                    )
                    % {"count": len(only_here)},
                    level="warning",
                )
        removed = group.members.filter(pk__in=trainee_ids).count()
        group.members.remove(*trainee_ids)
        moved = TraineeGroup.add_default_to_groupless(trainee_ids)
        self.message_user(
            request,
            ngettext(
                '%(count)d trainee removed from "%(group)s".',
                '%(count)d trainees removed from "%(group)s".',
                removed,
            )
            % {"count": removed, "group": group},
        )
        if moved:
            self.message_user(
                request,
                ngettext(
                    '%(count)d trainee had no other group and went to the default group "%(group)s".',
                    '%(count)d trainees had no other group and went to the default group "%(group)s".',
                    len(moved),
                )
                % {"count": len(moved), "group": TraineeGroup.get_default()},
            )
