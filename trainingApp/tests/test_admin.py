"""
Admin de contenido: páginas, inlines con opciones, validaciones, orden, rol "Content editor"
y páginas propias (estructura del curso, carga masiva, vista previa, duplicar).
"""

import io
import shutil
import tempfile

from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation
from PIL import Image

from trainingApp.models import (
    Choice,
    TraineeTraining,
    Training,
    TrainingQuestion,
    TrainingQuestionAnswer,
)
from trainingApp.tests.factories import (
    PASSWORD,
    add_block,
    make_choice_set,
    make_course,
    make_group,
    make_training,
    simple_static_storage,
)


def admin_url(model_name, action, *args):
    return reverse(f"admin:trainingApp_{model_name}_{action}", args=args)


def form_data(response):
    """Datos POST equivalentes a enviar sin cambios el formulario del admin y sus inlines."""
    data = {}

    def add(form):
        for name, field in form.fields.items():
            if isinstance(field, forms.FileField):
                continue
            bound = form[name]
            value = bound.value()
            if value is None or value is False:
                continue
            if value is True:
                value = "on"
            elif isinstance(value, (list, tuple)):
                value = [str(v) for v in value]
            data[bound.html_name] = value

    add(response.context["adminform"].form)
    for inline in response.context["inline_admin_formsets"]:
        add(inline.formset.management_form)
        for form in inline.formset.forms:
            add(form)
    return data


def add_inline_form(data, prefix, values):
    """Agrega una fila nueva al inline `prefix` con `values` (nombres de campo sin prefijo)."""
    index = int(data[f"{prefix}-TOTAL_FORMS"])
    data[f"{prefix}-TOTAL_FORMS"] = str(index + 1)
    for name, value in values.items():
        data[f"{prefix}-{index}-{name}"] = value


@simple_static_storage
class ContentAdminTestCase(TestCase):

    def setUp(self):
        self.client.force_login(
            User.objects.create_superuser("admin", "admin@example.com", PASSWORD)
        )
        self.choice_set = make_choice_set(
            "Star / Galaxy", [("Star", "Estrella"), ("Galaxy", "Galaxia")]
        )
        self.training = make_training("T", blocks=1, questions_per_block=2)
        self.block = self.training.trainingblock_set.get()
        self.group = make_group()

    def assert_saved(self, response):
        if response.status_code == 302:
            return
        errors = [response.context["adminform"].form.errors]
        for inline in response.context["inline_admin_formsets"]:
            errors.append((inline.formset.errors, inline.formset.non_form_errors()))
        self.fail(f"form not saved: {errors}")


class AdminPagesTests(ContentAdminTestCase):

    def test_content_pages_render(self):
        course = make_course("C", [self.training], groups=[self.group])
        question = self.block.trainingquestion_set.first()
        urls = [
            admin_url(model, "changelist")
            for model in (
                "course",
                "training",
                "trainingblock",
                "trainingquestion",
                "choiceset",
            )
        ]
        urls += [
            admin_url(model, "add")
            for model in (
                "course",
                "training",
                "trainingblock",
                "trainingquestion",
                "choiceset",
            )
        ]
        urls += [
            admin_url("course", "change", course.pk),
            admin_url("training", "change", self.training.pk),
            admin_url("trainingblock", "change", self.block.pk),
            admin_url("trainingquestion", "change", question.pk),
            admin_url("choiceset", "change", self.choice_set.pk),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_choices_hidden_from_menu_but_reachable(self):
        index = self.client.get(reverse("admin:index"))
        self.assertNotContains(index, admin_url("choice", "changelist"))
        self.assertContains(index, admin_url("choiceset", "changelist"))
        self.assertEqual(
            self.client.get(admin_url("choice", "changelist")).status_code, 200
        )

    def test_orderable_inlines_load_script_that_keeps_add_button_last(self):
        # El arrastre es JS (verificado en navegador); acá se comprueba que cada página con inlines ordenables lo carga
        course = make_course("C", [self.training], groups=[self.group])
        question = self.block.trainingquestion_set.first()
        for url in (
            admin_url("course", "change", course.pk),
            admin_url("training", "change", self.training.pk),
            admin_url("trainingblock", "change", self.block.pk),
            admin_url("trainingquestion", "change", question.pk),
            admin_url("choiceset", "change", self.choice_set.pk),
        ):
            with self.subTest(url=url):
                self.assertContains(
                    self.client.get(url), "trainingApp/admin/inline_ordering.js"
                )

    def test_inlines_show_both_languages(self):
        response = self.client.get(admin_url("trainingblock", "change", self.block.pk))
        self.assertContains(response, "trainingquestion_set-0-question_en")
        self.assertContains(response, "trainingquestion_set-0-question_es")

    def test_question_add_with_block_starts_from_block_defaults(self):
        self.block.default_question_en = "Star or galaxy?"
        self.block.default_choice_set = self.choice_set
        self.block.save()
        response = self.client.get(
            admin_url("trainingquestion", "add") + f"?block={self.block.pk}"
        )
        form = response.context["adminform"].form
        self.assertEqual(form["question_en"].value(), "Star or galaxy?")
        self.assertEqual(str(form["apply_choice_set"].value()), str(self.choice_set.pk))


class BlockQuestionsInlineTests(ContentAdminTestCase):

    def setUp(self):
        super().setUp()
        self.block.default_question_en = "Star or galaxy?"
        self.block.default_question_es = "¿Estrella o galaxia?"
        self.block.default_choice_set = self.choice_set
        self.block.save()
        self.url = admin_url("trainingblock", "change", self.block.pk)

    def test_new_question_copies_block_options_with_correct_one(self):
        data = form_data(self.client.get(self.url))
        galaxy = self.choice_set.options.get(text_en="Galaxy")
        # La fila nueva llega con order=0 (valor inicial del campo oculto): el modelo la ubica al final
        add_inline_form(
            data,
            "trainingquestion_set",
            {
                "question_en": "Star or galaxy?",
                "question_es": "¿Estrella o galaxia?",
                "correct_option": str(galaxy.pk),
                "order": "0",
            },
        )
        self.assert_saved(self.client.post(self.url, data))
        question = self.block.trainingquestion_set.last()
        self.assertEqual(question.order, 3)
        choices = list(
            question.choice_set.values_list("choice_en", "choice_es", "correctChoice")
        )
        self.assertEqual(
            choices, [("Star", "Estrella", False), ("Galaxy", "Galaxia", True)]
        )

    def test_new_question_requires_correct_option(self):
        data = form_data(self.client.get(self.url))
        add_inline_form(
            data,
            "trainingquestion_set",
            {"question_en": "Other text", "question_es": "", "order": "0"},
        )
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.block.trainingquestion_set.count(), 2)

    def test_existing_question_changes_correct_option(self):
        question = self.block.trainingquestion_set.first()
        wrong = question.choice_set.get(correctChoice=False)
        response = self.client.get(self.url)
        data = form_data(response)
        data["trainingquestion_set-0-correct_option"] = str(wrong.pk)
        self.assert_saved(self.client.post(self.url, data))
        self.assertEqual(question.choice_set.get(correctChoice=True), wrong)

    def test_questions_reordered_by_order_field(self):
        first, second = self.block.trainingquestion_set.all()
        data = form_data(self.client.get(self.url))
        data["trainingquestion_set-0-order"] = "2"
        data["trainingquestion_set-1-order"] = "1"
        self.assert_saved(self.client.post(self.url, data))
        self.assertEqual(list(self.block.trainingquestion_set.all()), [second, first])


class QuestionAdminTests(ContentAdminTestCase):

    def setUp(self):
        super().setUp()
        self.question = self.block.trainingquestion_set.first()
        self.url = admin_url("trainingquestion", "change", self.question.pk)

    def post_choices(self, correct_flags):
        data = form_data(self.client.get(self.url))
        for index, correct in enumerate(correct_flags):
            key = f"choice_set-{index}-correctChoice"
            if correct:
                data[key] = "on"
            else:
                data.pop(key, None)
        return self.client.post(self.url, data)

    def test_exactly_one_correct_option_required(self):
        for flags in ([True, True], [False, False]):
            with self.subTest(flags=flags):
                response = self.post_choices(flags)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(
                    response.context["inline_admin_formsets"][
                        0
                    ].formset.non_form_errors()
                )
        self.assert_saved(self.post_choices([False, True]))
        self.assertEqual(
            self.question.choice_set.get(correctChoice=True).choice, "wrong"
        )

    def test_apply_choice_set_to_question_without_options(self):
        question = TrainingQuestion.objects.create(block=self.block, question_en="New")
        url = admin_url("trainingquestion", "change", question.pk)
        data = form_data(self.client.get(url))
        data["apply_choice_set"] = str(self.choice_set.pk)
        response = self.client.post(url, data)
        self.assertRedirects(response, url, fetch_redirect_response=False)
        self.assertEqual(
            list(question.choice_set.values_list("choice_en", flat=True)),
            ["Star", "Galaxy"],
        )
        self.assertNotContains(self.client.get(url), 'name="apply_choice_set"')

    def test_question_image_is_validated_with_pillow(self):
        # El campo del formulario abre el archivo con Pillow: una imagen real pasa y un archivo que no lo es se rechaza
        image = io.BytesIO()
        Image.new("RGB", (4, 3), "white").save(image, "PNG")
        field = TrainingQuestion._meta.get_field("deploy_image").formfield()
        uploaded = field.clean(
            SimpleUploadedFile("graph.png", image.getvalue(), content_type="image/png")
        )
        self.assertEqual((uploaded.image.format, uploaded.image.size), ("PNG", (4, 3)))
        with self.assertRaises(forms.ValidationError):
            field.clean(
                SimpleUploadedFile(
                    "fake.png", b"not an image", content_type="image/png"
                )
            )


class CourseAdminTests(ContentAdminTestCase):

    def course_data(self, url):
        data = form_data(self.client.get(url))
        data["description_en"] = "Description"
        return data

    def test_final_exam_cannot_be_a_course_training(self):
        course = make_course("C", [self.training], groups=[self.group])
        url = admin_url("course", "change", course.pk)
        data = self.course_data(url)
        data["final_exam"] = str(self.training.pk)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            response.context["inline_admin_formsets"][0].formset.non_form_errors()
        )

    def test_course_trainings_reordered(self):
        second_training = make_training("T2")
        course = make_course("C", [self.training, second_training], groups=[self.group])
        url = admin_url("course", "change", course.pk)
        data = self.course_data(url)
        data["coursetraining_set-0-order"] = "2"
        data["coursetraining_set-1-order"] = "1"
        self.assert_saved(self.client.post(url, data))
        self.assertEqual(
            list(course.trainings.order_by("coursetraining__order")),
            [second_training, self.training],
        )


@simple_static_storage
class ContentEditorRoleTests(TestCase):

    def setUp(self):
        editor = User.objects.create_user(
            "editor", "editor@example.com", PASSWORD, is_staff=True
        )
        editor.groups.add(Group.objects.get(name="Content editor"))
        self.client.force_login(editor)

    def test_editor_manages_content(self):
        for model in (
            "course",
            "training",
            "trainingblock",
            "trainingquestion",
            "choiceset",
        ):
            with self.subTest(model=model):
                self.assertEqual(
                    self.client.get(admin_url(model, "add")).status_code, 200
                )

    def test_editor_menu_only_shows_content(self):
        response = self.client.get(reverse("admin:index"))
        self.assertContains(response, admin_url("course", "changelist"))
        self.assertNotContains(response, admin_url("traineetraining", "changelist"))
        self.assertNotContains(response, reverse("admin:auth_user_changelist"))

    def test_editor_cannot_see_results_or_users(self):
        for url in (
            admin_url("traineetraining", "changelist"),
            admin_url("trainingquestionanswer", "changelist"),
            reverse("admin:auth_user_changelist"),
        ):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)


class ChoiceInlineOrderTests(ContentAdminTestCase):

    def test_choices_listed_in_order(self):
        question = add_block(
            self.training, "B2", questions=1
        ).trainingquestion_set.get()
        Choice.objects.filter(deploy=question, choice="wrong").update(order=1)
        Choice.objects.filter(deploy=question, choice="right").update(order=2)
        response = self.client.get(admin_url("trainingquestion", "change", question.pk))
        formset = response.context["inline_admin_formsets"][0].formset
        self.assertEqual(
            [form.instance.choice for form in formset.forms], ["wrong", "right"]
        )


class CourseStructureTests(ContentAdminTestCase):

    def test_structure_lists_trainings_in_order_with_problems(self):
        exam = make_training("Exam")
        second = make_training("T2")
        course = make_course(
            "C", [self.training, second], groups=[self.group], final_exam=exam
        )
        question = self.block.trainingquestion_set.first()
        response = self.client.get(admin_url("course", "structure", course.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [node["training"] for node in response.context["trainings"]],
            [self.training, second, exam],
        )
        self.assertTrue(response.context["trainings"][-1]["is_final_exam"])
        # Las preguntas de las factories no tienen sonido
        self.assertGreater(response.context["error_count"], 0)
        self.assertContains(
            response, admin_url("trainingquestion", "change", question.pk)
        )
        self.assertContains(
            response, admin_url("trainingblock", "bulk_upload", self.block.pk)
        )

    def test_structure_linked_from_course_pages(self):
        course = make_course("C", [self.training], groups=[self.group])
        structure_url = admin_url("course", "structure", course.pk)
        changelist = self.client.get(admin_url("course", "changelist"))
        self.assertContains(changelist, structure_url)
        self.assertContains(changelist, "View structure")
        self.assertEqual(changelist.context["cl"].list_display[-1], "view_structure")
        self.assertContains(
            self.client.get(admin_url("course", "change", course.pk)), structure_url
        )


class BulkUploadTests(ContentAdminTestCase):

    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.block = add_block(self.training, "Galaxies", questions=0)
        self.block.default_question_en = "Star or galaxy?"
        self.block.default_choice_set = self.choice_set
        self.block.save()
        self.url = admin_url("trainingblock", "bulk_upload", self.block.pk)

    def test_page_starts_with_block_defaults(self):
        form = self.client.get(self.url).context["form"]
        self.assertEqual(form["choice_set"].value(), self.choice_set.pk)
        self.assertEqual(form["question_en"].value(), "Star or galaxy?")

    def test_creates_one_question_per_sound_in_file_name_order(self):
        response = self.client.post(
            self.url,
            {
                "sounds": [
                    SimpleUploadedFile("b.wav", b"b"),
                    SimpleUploadedFile("a.mp3", b"a"),
                ],
                "images": [SimpleUploadedFile("a.png", b"png")],
                "choice_set": self.choice_set.pk,
                "question_en": "Star or galaxy?",
                "question_es": "¿Estrella o galaxia?",
            },
        )
        self.assertRedirects(
            response,
            admin_url("trainingblock", "change", self.block.pk),
            fetch_redirect_response=False,
        )
        first, second = self.block.trainingquestion_set.all()
        self.assertIn("a", first.deploy_sound.name)
        self.assertIn("a", first.deploy_image.name)
        self.assertFalse(second.deploy_image)
        self.assertEqual((first.order, second.order), (1, 2))
        self.assertEqual(first.question_es, "¿Estrella o galaxia?")
        self.assertEqual(
            list(second.choice_set.values_list("choice_en", flat=True)),
            ["Star", "Galaxy"],
        )

    def test_rejects_wrong_extensions_and_unmatched_images(self):
        response = self.client.post(
            self.url,
            {
                "sounds": [SimpleUploadedFile("a.txt", b"a")],
                "images": [SimpleUploadedFile("other.png", b"png")],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(self.block.trainingquestion_set.exists())


class TrainingPreviewAndDuplicateTests(ContentAdminTestCase):

    def test_preview_shows_questions_without_recording_attempts(self):
        response = self.client.get(
            admin_url("training", "preview", self.training.pk) + "?show_correct=1"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "T B1 Q1")
        self.assertContains(response, 'class="correct-option"')
        self.assertFalse(TraineeTraining.objects.exists())

    def test_duplicate_action(self):
        response = self.client.post(
            admin_url("training", "changelist"),
            {
                "action": "duplicate_trainings",
                "_selected_action": [self.training.pk],
            },
        )
        self.assertEqual(response.status_code, 302)
        copy = Training.objects.exclude(pk=self.training.pk).get()
        self.assertEqual(copy.name_training, "T (copy)")
        self.assertEqual(
            TrainingQuestion.objects.filter(block__training=copy).count(), 2
        )


class NavigationAndNamesTests(ContentAdminTestCase):

    def test_sidebar_groups_models_in_sections_with_descriptive_names(self):
        response = self.client.get(reverse("admin:index"))
        for text in (
            "Course content",
            "Trainees and results",
            "Users and permissions",
            "Option sets",
            "Training attempts",
            "Answered blocks",
            "Feedback surveys",
            "Admin roles",
        ):
            with self.subTest(text=text):
                self.assertContains(response, text)

    def test_spanish_admin_uses_translated_names(self):
        # La petición deja activo el español en el hilo: se restaura para los tests siguientes
        self.addCleanup(translation.deactivate)
        response = self.client.get(reverse("admin:index").replace("/en/", "/es/"))
        self.assertContains(response, "Contenido de los cursos")
        self.assertContains(response, "Bloques respondidos")

    def test_export_keeps_deploy_column_format(self):
        from trainingApp.admin import TrainingQuestionAnswerResource
        from trainingApp.tests.factories import (
            make_attempt,
            make_trainee,
            record_answer,
        )

        question = self.block.trainingquestion_set.first()
        trainee = make_trainee("ana", self.group)
        record_answer(
            make_attempt(trainee, make_course("C", [self.training]), self.training),
            question,
            True,
        )
        dataset = TrainingQuestionAnswerResource().export()
        self.assertEqual(
            dataset.dict[0]["deploy"], f"Deploy {question.id}: {question.question}"
        )
        self.assertEqual(str(dataset.dict[0]["is_correct"]), "1")

    def test_export_offers_only_csv_xlsx_and_tsv(self):
        # Sin HTML: tablib 3.5.0 no escapa el contenido exportado y el username lo escribe el trainee
        model_admin = admin.site._registry[TrainingQuestionAnswer]
        extensions = [
            file_format().get_extension()
            for file_format in model_admin.get_export_formats()
        ]
        self.assertEqual(extensions, ["csv", "xlsx", "tsv"])


class TrainingBlocksTests(ContentAdminTestCase):

    def block_add_data(self, **extra):
        return {
            "training": self.training.pk,
            "name_block_en": "Waves",
            "name_block_es": "Ondas",
            "description_en": "",
            "description_es": "",
            "state_block": "Active",
            "estimed_duration_block": "5",
            "default_question_en": "",
            "default_question_es": "",
            "default_choice_set": "",
            "trainingquestion_set-TOTAL_FORMS": "0",
            "trainingquestion_set-INITIAL_FORMS": "0",
            "trainingquestion_set-MIN_NUM_FORMS": "0",
            "trainingquestion_set-MAX_NUM_FORMS": "1000",
            **extra,
        }

    def test_training_page_lists_blocks_without_inline_editing_or_adding(self):
        response = self.client.get(admin_url("training", "change", self.training.pk))
        self.assertNotContains(response, "trainingblock_set-0-name_block_en")
        blocks = next(
            f
            for f in response.context["inline_admin_formsets"]
            if f.formset.prefix == "trainingblock_set"
        )
        self.assertFalse(blocks.has_add_permission)
        self.assertContains(
            response,
            admin_url("trainingblock", "add") + f"?training={self.training.pk}",
        )

    def test_block_created_from_training_returns_to_it(self):
        url = admin_url("trainingblock", "add") + f"?training={self.training.pk}"
        self.assertEqual(
            self.client.get(url).context["adminform"].form["training"].value(),
            str(self.training.pk),
        )
        response = self.client.post(url, self.block_add_data(_save="1"))
        self.assertRedirects(
            response,
            admin_url("training", "change", self.training.pk),
            fetch_redirect_response=False,
        )
        self.assertTrue(
            self.training.trainingblock_set.filter(name_block_es="Ondas").exists()
        )
        response = self.client.post(
            url, self.block_add_data(_addanother="1", name_block_en="More")
        )
        self.assertRedirects(response, url, fetch_redirect_response=False)

    def test_blocks_reordered_from_training_page(self):
        second = add_block(self.training, "Second", questions=0)
        first = self.training.trainingblock_set.exclude(pk=second.pk).get()
        url = admin_url("training", "change", self.training.pk)
        data = form_data(self.client.get(url))
        data["name_training_en"] = "T"
        data["trainingblock_set-0-order"] = "1"
        data["trainingblock_set-1-order"] = "0"
        self.assert_saved(self.client.post(url, data))
        self.assertEqual(list(self.training.trainingblock_set.all()), [second, first])


class ChoiceLanguageColumnsTests(ContentAdminTestCase):

    def setUp(self):
        super().setUp()
        self.question = self.block.trainingquestion_set.first()
        self.url = admin_url("trainingquestion", "change", self.question.pk)

    def test_columns_per_language(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Text (EN)")
        self.assertContains(response, "Text (ES)")

    def test_new_option_row_requires_default_language_text(self):
        data = form_data(self.client.get(self.url))
        add_inline_form(
            data, "choice_set", {"choice_en": "", "choice_es": "Tal vez", "order": "0"}
        )
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        data["choice_set-2-choice_en"] = "Maybe"
        self.assert_saved(self.client.post(self.url, data))
        self.assertEqual(self.question.choice_set.last().choice_es, "Tal vez")
