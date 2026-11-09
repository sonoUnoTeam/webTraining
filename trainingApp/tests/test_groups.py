"""
Grupos de trainees: qué cursos ve cada trainee, el grupo por defecto y cómo se asignan
cursos y trainees desde el admin (página del grupo, acción "Mover a grupo", columnas).
"""

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from trainingApp import rules
from trainingApp.models import Course, TraineeGroup
from userApp.models import Trainee

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

    def test_deleting_a_group_moves_its_trainees_to_the_default_group(self):
        default = make_default_group()
        workshop = make_group("Workshop")
        trainee = make_trainee("ana", workshop)

        workshop.delete()

        trainee.refresh_from_db()
        self.assertEqual(trainee.group, default)


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

    def test_without_group_no_course_is_visible(self):
        # Un curso sin grupos no debe aparecerle a un trainee sin grupo
        make_course("No groups", [self.training])
        trainee = make_trainee("nogroup", None)

        self.assertEqual(list(rules.visible_courses(trainee)), [])

    def test_a_course_with_several_groups_is_listed_once(self):
        course = make_course(
            "Shared", [self.training], groups=[self.group, make_group("B")]
        )

        self.assertEqual(list(rules.visible_courses(self.trainee)), [course])


@simple_static_storage
class CourseVisibilityViewsTests(TestCase):
    def setUp(self):
        self.group = make_group("A")
        make_trainee("ana", self.group)
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

    def test_moving_a_trainee_changes_the_courses_they_see(self):
        other = make_group("B")
        make_course("Advanced", [make_training("T2")], groups=[other])
        Trainee.objects.filter(user__username="ana").update(group=other)

        response = self.client.get(reverse("trainingApp:course_list"))

        self.assertContains(response, "Advanced")
        self.assertNotContains(response, "Sonification 101")


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
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.group, self.group)

    def test_trainees_removed_from_a_group_go_to_the_default_group(self):
        url = self.change_url(self.group)
        data = form_data(self.client.get(url))
        data["members"] = []

        self.assertEqual(self.client.post(url, data).status_code, 302)

        self.bob.refresh_from_db()
        self.assertEqual(self.bob.group, self.default)

    def test_trainees_cannot_be_removed_from_the_default_group(self):
        url = self.change_url(self.default)
        data = form_data(self.client.get(url))
        data["members"] = []

        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        self.assertIn("members", response.context["adminform"].form.errors)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.group, self.default)

    def test_the_default_group_cannot_be_deleted(self):
        response = self.client.get(
            reverse("admin:trainingApp_traineegroup_delete", args=[self.default.pk])
        )

        self.assertEqual(response.status_code, 403)

    def test_move_selected_trainees_to_a_group(self):
        response = self.client.post(
            reverse("admin:userApp_trainee_changelist"),
            {
                "action": "move_to_group",
                "_selected_action": [str(self.ana.pk)],
                "group": str(self.group.pk),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.group, self.group)

    def test_move_to_group_without_choosing_a_group_changes_nothing(self):
        self.client.post(
            reverse("admin:userApp_trainee_changelist"),
            {"action": "move_to_group", "_selected_action": [str(self.ana.pk)]},
        )

        self.ana.refresh_from_db()
        self.assertEqual(self.ana.group, self.default)

    def test_course_list_links_to_the_trainees_with_access(self):
        self.course.groups.add(self.group)

        response = self.client.get(reverse("admin:trainingApp_course_changelist"))
        trainees = self.client.get(
            reverse("admin:userApp_trainee_changelist")
            + f"?group__id__in={self.group.pk}"
        )

        self.assertContains(response, "Workshop")
        self.assertEqual(list(trainees.context["cl"].result_list), [self.bob])


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
