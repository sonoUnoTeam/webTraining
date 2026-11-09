"""
Grupos de trainees: un trainee puede estar en varios grupos y ve la unión de sus cursos;
grupo por defecto; asignación de cursos y trainees desde el admin (página del grupo,
acciones "Agregar a grupo" / "Quitar de grupo", columnas).
"""

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from trainingApp import rules
from trainingApp.models import Course, TraineeGroup

from .factories import (
    PASSWORD,
    make_course,
    make_group,
    make_trainee,
    make_training,
    simple_static_storage,
)
from .test_admin import form_data


def make_default_group(name="Default"):
    group = make_group(name)
    group.is_default = True
    group.save()
    return group


def groups_of(trainee):
    return set(trainee.groups.all())


class DefaultGroupTests(TestCase):
    def test_get_default_creates_the_group_when_there_is_none(self):
        group = TraineeGroup.get_default()

        self.assertTrue(group.is_default)
        self.assertEqual(TraineeGroup.get_default(), group)

    def test_only_one_group_is_the_default(self):
        first = make_default_group("First")
        second = make_default_group("Second")

        first.refresh_from_db()
        self.assertFalse(first.is_default)
        self.assertEqual(TraineeGroup.get_default(), second)

    def test_the_default_cannot_be_unmarked_without_choosing_another(self):
        group = make_default_group()
        group.is_default = False

        with self.assertRaises(ValidationError):
            group.full_clean()

    def test_deleting_a_group_sends_trainees_without_other_group_to_the_default(self):
        default = make_default_group()
        workshop, school = make_group("Workshop"), make_group("School")
        only_workshop = make_trainee("ana", workshop)
        also_school = make_trainee("bob", [workshop, school])

        workshop.delete()

        self.assertEqual(groups_of(only_workshop), {default})
        self.assertEqual(groups_of(also_school), {school})


class VisibleCoursesTests(TestCase):
    def setUp(self):
        self.group = make_group("A")
        self.trainee = make_trainee("ana", self.group)
        self.training = make_training("T")

    def test_only_active_courses_of_the_group(self):
        visible = make_course("Visible", [self.training], groups=[self.group])
        inactive = make_course("Inactive", [self.training], groups=[self.group])
        inactive.state_course = Course.StateCourse.Inactive
        inactive.save()
        make_course("Other group", [self.training], groups=[make_group("B")])

        self.assertEqual(list(rules.visible_courses(self.trainee)), [visible])

    def test_union_of_the_courses_of_all_their_groups(self):
        other = make_group("B")
        mine = make_course("Mine", [self.training], groups=[self.group])
        from_other = make_course("From B", [self.training], groups=[other])
        shared = make_course("Shared", [self.training], groups=[self.group, other])
        self.trainee.groups.add(other)

        self.assertEqual(
            list(rules.visible_courses(self.trainee)), [mine, from_other, shared]
        )
        self.assertTrue(rules.can_view_course(self.trainee, from_other))

    def test_without_groups_no_course_is_visible(self):
        # Un curso sin grupos no debe aparecerle a un trainee sin grupos
        make_course("No groups", [self.training])
        trainee = make_trainee("nogroup", None)

        self.assertEqual(list(rules.visible_courses(trainee)), [])


@simple_static_storage
class CourseVisibilityViewsTests(TestCase):
    def setUp(self):
        self.group = make_group("A")
        self.trainee = make_trainee("ana", self.group)
        self.course = make_course(
            "Sonification 101", [make_training("T")], groups=[self.group]
        )
        self.client.login(username="ana", password=PASSWORD)

    def test_inactive_course_cannot_be_opened_by_url(self):
        self.course.state_course = Course.StateCourse.Inactive
        self.course.save()

        response = self.client.get(
            reverse("trainingApp:course_detail", args=[self.course.id])
        )

        self.assertRedirects(
            response,
            reverse("trainingApp:course_list"),
            fetch_redirect_response=False,
        )

    def test_a_second_group_adds_its_courses_to_the_list(self):
        other = make_group("B")
        make_course("Advanced", [make_training("T2")], groups=[other])
        self.trainee.groups.add(other)

        response = self.client.get(reverse("trainingApp:course_list"))

        self.assertContains(response, "Advanced")
        self.assertContains(response, "Sonification 101")


@simple_static_storage
class TraineeGroupAdminTests(TestCase):
    def setUp(self):
        self.client.force_login(
            User.objects.create_superuser("admin", "admin@example.com", PASSWORD)
        )
        # El superusuario recibe un Trainee en el grupo por defecto (signal)
        self.default = TraineeGroup.get_default()
        self.group = make_group("Workshop")
        self.training = make_training("T")
        self.course = make_course("Sonification 101", [self.training])
        self.ana = make_trainee("ana", self.default)
        self.bob = make_trainee("bob", self.group)

    def change_url(self, group):
        return reverse("admin:trainingApp_traineegroup_change", args=[group.pk])

    def run_action(self, action, trainees, group=None):
        data = {"action": action, "_selected_action": [str(t.pk) for t in trainees]}
        if group is not None:
            data["group"] = str(group.pk)
        return self.client.post(reverse("admin:userApp_trainee_changelist"), data)

    def test_pages_render_with_courses_members_and_access_summary(self):
        self.course.groups.add(self.group)
        for url in (
            reverse("admin:trainingApp_traineegroup_changelist"),
            reverse("admin:trainingApp_traineegroup_add"),
            self.change_url(self.group),
            reverse("admin:userApp_trainee_changelist"),
            reverse("admin:userApp_trainee_change", args=[self.bob.pk]),
            reverse("admin:trainingApp_course_changelist"),
            reverse("admin:trainingApp_course_structure", args=[self.course.pk]),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

        page = self.client.get(self.change_url(self.group))
        self.assertContains(page, "Sonification 101")
        self.assertContains(page, "1. T")

    def test_assign_courses_and_trainees_from_the_group_page(self):
        url = self.change_url(self.group)
        data = form_data(self.client.get(url))
        data["courses"] = [str(self.course.pk)]
        data["members"] = [str(self.ana.pk), str(self.bob.pk)]

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(self.course.groups.all()), [self.group])
        # Agregarla al taller no la saca del grupo por defecto
        self.assertEqual(groups_of(self.ana), {self.default, self.group})

    def test_trainees_left_without_groups_go_to_the_default_group(self):
        self.ana.groups.add(self.group)
        url = self.change_url(self.group)
        data = form_data(self.client.get(url))
        data["members"] = []

        self.assertEqual(self.client.post(url, data).status_code, 302)

        self.assertEqual(groups_of(self.bob), {self.default})
        self.assertEqual(groups_of(self.ana), {self.default})

    def test_trainees_without_other_group_cannot_leave_the_default_group(self):
        url = self.change_url(self.default)
        data = form_data(self.client.get(url))
        data["members"] = []

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("members", response.context["adminform"].form.errors)

    def test_trainees_with_another_group_can_leave_the_default_group(self):
        self.ana.groups.add(self.group)
        url = self.change_url(self.default)
        data = form_data(self.client.get(url))
        data["members"] = [
            pk for pk in data["members"] if pk != str(self.ana.pk)
        ]  # el admin (superusuario) se queda

        self.assertEqual(self.client.post(url, data).status_code, 302)

        self.assertEqual(groups_of(self.ana), {self.group})

    def test_the_default_group_cannot_be_deleted(self):
        response = self.client.get(
            reverse("admin:trainingApp_traineegroup_delete", args=[self.default.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_add_selected_trainees_to_a_group(self):
        response = self.run_action("add_to_group", [self.ana], self.group)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(groups_of(self.ana), {self.default, self.group})

    def test_remove_selected_trainees_from_a_group(self):
        self.ana.groups.add(self.group)

        self.run_action("remove_from_group", [self.ana, self.bob], self.group)

        self.assertEqual(groups_of(self.ana), {self.default})
        # Bob no tenía otro grupo: vuelve al grupo por defecto
        self.assertEqual(groups_of(self.bob), {self.default})

    def test_remove_from_the_default_group_keeps_trainees_without_other_group(self):
        self.run_action("remove_from_group", [self.ana], self.default)

        self.assertEqual(groups_of(self.ana), {self.default})

    def test_group_action_without_choosing_a_group_changes_nothing(self):
        self.run_action("add_to_group", [self.ana])

        self.assertEqual(groups_of(self.ana), {self.default})

    def test_course_list_links_to_the_trainees_of_its_groups(self):
        self.course.groups.add(self.group)

        response = self.client.get(reverse("admin:trainingApp_course_changelist"))
        trainees = self.client.get(
            reverse("admin:userApp_trainee_changelist")
            + f"?groups__id__in={self.group.pk}"
        )

        self.assertContains(response, "Workshop")
        self.assertEqual(list(trainees.context["cl"].result_list), [self.bob])

    def test_trainee_page_shows_courses_of_all_their_groups(self):
        self.course.groups.add(self.group)
        make_course("Default course", [self.training], groups=[self.default])
        self.ana.groups.add(self.group)

        page = self.client.get(
            reverse("admin:userApp_trainee_change", args=[self.ana.pk])
        )

        self.assertContains(page, "Sonification 101")
        self.assertContains(page, "Default course")


@simple_static_storage
class ContentEditorGroupPageTests(TestCase):
    def test_editor_sees_the_courses_of_a_group_but_not_its_trainees(self):
        editor = User.objects.create_user(
            "editor", "editor@example.com", PASSWORD, is_staff=True
        )
        editor.groups.add(Group.objects.get(name="Content editor"))
        self.client.force_login(editor)
        group = make_group("Workshop")
        make_trainee("secret-trainee", group)
        make_course("Sonification 101", [make_training("T")], groups=[group])

        response = self.client.get(
            reverse("admin:trainingApp_traineegroup_change", args=[group.pk])
        )

        self.assertContains(response, "Sonification 101")
        self.assertNotContains(response, "secret-trainee")
