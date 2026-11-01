"""
Admin de contenido: páginas, inlines con opciones, validaciones, orden, rol "Content editor"
y páginas propias (estructura del curso, carga masiva, vista previa, duplicar).
"""
import shutil
import tempfile

from django import forms
from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from trainingApp.models import Choice, TraineeTraining, Training, TrainingQuestion
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
    return reverse(f'admin:trainingApp_{model_name}_{action}', args=args)


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
                value = 'on'
            elif isinstance(value, (list, tuple)):
                value = [str(v) for v in value]
            data[bound.html_name] = value

    add(response.context['adminform'].form)
    for inline in response.context['inline_admin_formsets']:
        add(inline.formset.management_form)
        for form in inline.formset.forms:
            add(form)
    return data


def add_inline_form(data, prefix, values):
    """Agrega una fila nueva al inline `prefix` con `values` (nombres de campo sin prefijo)."""
    index = int(data[f'{prefix}-TOTAL_FORMS'])
    data[f'{prefix}-TOTAL_FORMS'] = str(index + 1)
    for name, value in values.items():
        data[f'{prefix}-{index}-{name}'] = value


@simple_static_storage
class ContentAdminTestCase(TestCase):

    def setUp(self):
        self.client.force_login(User.objects.create_superuser('admin', 'admin@example.com', PASSWORD))
        self.choice_set = make_choice_set('Star / Galaxy', [('Star', 'Estrella'), ('Galaxy', 'Galaxia')])
        self.training = make_training('T', blocks=1, questions_per_block=2)
        self.block = self.training.trainingblock_set.get()
        self.group = make_group()

    def assert_saved(self, response):
        if response.status_code == 302:
            return
        errors = [response.context['adminform'].form.errors]
        for inline in response.context['inline_admin_formsets']:
            errors.append((inline.formset.errors, inline.formset.non_form_errors()))
        self.fail(f'form not saved: {errors}')


class AdminPagesTests(ContentAdminTestCase):

    def test_content_pages_render(self):
        course = make_course('C', [self.training], groups=[self.group])
        question = self.block.trainingquestion_set.first()
        urls = [admin_url(model, 'changelist') for model in ('course', 'training', 'trainingblock', 'trainingquestion', 'choiceset')]
        urls += [admin_url(model, 'add') for model in ('course', 'training', 'trainingblock', 'trainingquestion', 'choiceset')]
        urls += [
            admin_url('course', 'change', course.pk),
            admin_url('training', 'change', self.training.pk),
            admin_url('trainingblock', 'change', self.block.pk),
            admin_url('trainingquestion', 'change', question.pk),
            admin_url('choiceset', 'change', self.choice_set.pk),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_choices_hidden_from_menu_but_reachable(self):
        index = self.client.get(reverse('admin:index'))
        self.assertNotContains(index, admin_url('choice', 'changelist'))
        self.assertContains(index, admin_url('choiceset', 'changelist'))
        self.assertEqual(self.client.get(admin_url('choice', 'changelist')).status_code, 200)

    def test_inlines_show_both_languages(self):
        response = self.client.get(admin_url('trainingblock', 'change', self.block.pk))
        self.assertContains(response, 'trainingquestion_set-0-question_en')
        self.assertContains(response, 'trainingquestion_set-0-question_es')

    def test_question_add_with_block_starts_from_block_defaults(self):
        self.block.default_question_en = 'Star or galaxy?'
        self.block.default_choice_set = self.choice_set
        self.block.save()
        response = self.client.get(admin_url('trainingquestion', 'add') + f'?block={self.block.pk}')
        form = response.context['adminform'].form
        self.assertEqual(form['question_en'].value(), 'Star or galaxy?')
        self.assertEqual(str(form['apply_choice_set'].value()), str(self.choice_set.pk))


class BlockQuestionsInlineTests(ContentAdminTestCase):

    def setUp(self):
        super().setUp()
        self.block.default_question_en = 'Star or galaxy?'
        self.block.default_question_es = '¿Estrella o galaxia?'
        self.block.default_choice_set = self.choice_set
        self.block.save()
        self.url = admin_url('trainingblock', 'change', self.block.pk)

    def test_new_question_copies_block_options_with_correct_one(self):
        data = form_data(self.client.get(self.url))
        galaxy = self.choice_set.options.get(text_en='Galaxy')
        add_inline_form(data, 'trainingquestion_set', {
            'question_en': 'Star or galaxy?', 'question_es': '¿Estrella o galaxia?', 'correct_option': str(galaxy.pk),
        })
        self.assert_saved(self.client.post(self.url, data))
        question = self.block.trainingquestion_set.last()
        self.assertEqual(question.order, 3)
        choices = list(question.choice_set.values_list('choice_en', 'choice_es', 'correctChoice'))
        self.assertEqual(choices, [('Star', 'Estrella', False), ('Galaxy', 'Galaxia', True)])

    def test_new_question_requires_correct_option(self):
        data = form_data(self.client.get(self.url))
        add_inline_form(data, 'trainingquestion_set', {'question_en': 'Other text', 'question_es': ''})
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.block.trainingquestion_set.count(), 2)

    def test_existing_question_changes_correct_option(self):
        question = self.block.trainingquestion_set.first()
        wrong = question.choice_set.get(correctChoice=False)
        response = self.client.get(self.url)
        data = form_data(response)
        data['trainingquestion_set-0-correct_option'] = str(wrong.pk)
        self.assert_saved(self.client.post(self.url, data))
        self.assertEqual(question.choice_set.get(correctChoice=True), wrong)

    def test_questions_reordered_by_order_field(self):
        first, second = self.block.trainingquestion_set.all()
        data = form_data(self.client.get(self.url))
        data['trainingquestion_set-0-order'] = '2'
        data['trainingquestion_set-1-order'] = '1'
        self.assert_saved(self.client.post(self.url, data))
        self.assertEqual(list(self.block.trainingquestion_set.all()), [second, first])


class QuestionAdminTests(ContentAdminTestCase):

    def setUp(self):
        super().setUp()
        self.question = self.block.trainingquestion_set.first()
        self.url = admin_url('trainingquestion', 'change', self.question.pk)

    def post_choices(self, correct_flags):
        data = form_data(self.client.get(self.url))
        for index, correct in enumerate(correct_flags):
            key = f'choice_set-{index}-correctChoice'
            if correct:
                data[key] = 'on'
            else:
                data.pop(key, None)
        return self.client.post(self.url, data)

    def test_exactly_one_correct_option_required(self):
        for flags in ([True, True], [False, False]):
            with self.subTest(flags=flags):
                response = self.post_choices(flags)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['inline_admin_formsets'][0].formset.non_form_errors())
        self.assert_saved(self.post_choices([False, True]))
        self.assertEqual(self.question.choice_set.get(correctChoice=True).choice, 'wrong')

    def test_apply_choice_set_to_question_without_options(self):
        question = TrainingQuestion.objects.create(block=self.block, question_en='New')
        url = admin_url('trainingquestion', 'change', question.pk)
        data = form_data(self.client.get(url))
        data['apply_choice_set'] = str(self.choice_set.pk)
        response = self.client.post(url, data)
        self.assertRedirects(response, url, fetch_redirect_response=False)
        self.assertEqual(list(question.choice_set.values_list('choice_en', flat=True)), ['Star', 'Galaxy'])
        self.assertNotContains(self.client.get(url), 'name="apply_choice_set"')


class CourseAdminTests(ContentAdminTestCase):

    def course_data(self, url):
        data = form_data(self.client.get(url))
        data['description_en'] = 'Description'
        return data

    def test_final_exam_cannot_be_a_course_training(self):
        course = make_course('C', [self.training], groups=[self.group])
        url = admin_url('course', 'change', course.pk)
        data = self.course_data(url)
        data['final_exam'] = str(self.training.pk)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['inline_admin_formsets'][0].formset.non_form_errors())

    def test_course_trainings_reordered(self):
        second_training = make_training('T2')
        course = make_course('C', [self.training, second_training], groups=[self.group])
        url = admin_url('course', 'change', course.pk)
        data = self.course_data(url)
        data['coursetraining_set-0-order'] = '2'
        data['coursetraining_set-1-order'] = '1'
        self.assert_saved(self.client.post(url, data))
        self.assertEqual(list(course.trainings.order_by('coursetraining__order')), [second_training, self.training])


@simple_static_storage
class ContentEditorRoleTests(TestCase):

    def setUp(self):
        editor = User.objects.create_user('editor', 'editor@example.com', PASSWORD, is_staff=True)
        editor.groups.add(Group.objects.get(name='Content editor'))
        self.client.force_login(editor)

    def test_editor_manages_content(self):
        for model in ('course', 'training', 'trainingblock', 'trainingquestion', 'choiceset'):
            with self.subTest(model=model):
                self.assertEqual(self.client.get(admin_url(model, 'add')).status_code, 200)

    def test_editor_cannot_see_results_or_users(self):
        for url in (admin_url('traineetraining', 'changelist'), admin_url('trainingquestionanswer', 'changelist'),
                    reverse('admin:auth_user_changelist')):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)


class ChoiceInlineOrderTests(ContentAdminTestCase):

    def test_choices_listed_in_order(self):
        question = add_block(self.training, 'B2', questions=1).trainingquestion_set.get()
        Choice.objects.filter(deploy=question, choice='wrong').update(order=1)
        Choice.objects.filter(deploy=question, choice='right').update(order=2)
        response = self.client.get(admin_url('trainingquestion', 'change', question.pk))
        formset = response.context['inline_admin_formsets'][0].formset
        self.assertEqual([form.instance.choice for form in formset.forms], ['wrong', 'right'])


class CourseStructureTests(ContentAdminTestCase):

    def test_structure_lists_trainings_in_order_with_problems(self):
        exam = make_training('Exam')
        second = make_training('T2')
        course = make_course('C', [self.training, second], groups=[self.group], final_exam=exam)
        question = self.block.trainingquestion_set.first()
        response = self.client.get(admin_url('course', 'structure', course.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual([node['training'] for node in response.context['trainings']], [self.training, second, exam])
        self.assertTrue(response.context['trainings'][-1]['is_final_exam'])
        # Las preguntas de las factories no tienen sonido
        self.assertGreater(response.context['error_count'], 0)
        self.assertContains(response, admin_url('trainingquestion', 'change', question.pk))
        self.assertContains(response, admin_url('trainingblock', 'bulk_upload', self.block.pk))

    def test_structure_linked_from_course_pages(self):
        course = make_course('C', [self.training], groups=[self.group])
        structure_url = admin_url('course', 'structure', course.pk)
        self.assertContains(self.client.get(admin_url('course', 'changelist')), structure_url)
        self.assertContains(self.client.get(admin_url('course', 'change', course.pk)), structure_url)


class BulkUploadTests(ContentAdminTestCase):

    def setUp(self):
        super().setUp()
        media_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media_root, ignore_errors=True)
        media_override = override_settings(MEDIA_ROOT=media_root)
        media_override.enable()
        self.addCleanup(media_override.disable)
        self.block = add_block(self.training, 'Galaxies', questions=0)
        self.block.default_question_en = 'Star or galaxy?'
        self.block.default_choice_set = self.choice_set
        self.block.save()
        self.url = admin_url('trainingblock', 'bulk_upload', self.block.pk)

    def test_page_starts_with_block_defaults(self):
        form = self.client.get(self.url).context['form']
        self.assertEqual(form['choice_set'].value(), self.choice_set.pk)
        self.assertEqual(form['question_en'].value(), 'Star or galaxy?')

    def test_creates_one_question_per_sound_in_file_name_order(self):
        response = self.client.post(self.url, {
            'sounds': [SimpleUploadedFile('b.wav', b'b'), SimpleUploadedFile('a.mp3', b'a')],
            'images': [SimpleUploadedFile('a.png', b'png')],
            'choice_set': self.choice_set.pk,
            'question_en': 'Star or galaxy?',
            'question_es': '¿Estrella o galaxia?',
        })
        self.assertRedirects(response, admin_url('trainingblock', 'change', self.block.pk), fetch_redirect_response=False)
        first, second = self.block.trainingquestion_set.all()
        self.assertIn('a', first.deploy_sound.name)
        self.assertIn('a', first.deploy_image.name)
        self.assertFalse(second.deploy_image)
        self.assertEqual((first.order, second.order), (1, 2))
        self.assertEqual(first.question_es, '¿Estrella o galaxia?')
        self.assertEqual(list(second.choice_set.values_list('choice_en', flat=True)), ['Star', 'Galaxy'])

    def test_rejects_wrong_extensions_and_unmatched_images(self):
        response = self.client.post(self.url, {
            'sounds': [SimpleUploadedFile('a.txt', b'a')],
            'images': [SimpleUploadedFile('other.png', b'png')],
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(self.block.trainingquestion_set.exists())


class TrainingPreviewAndDuplicateTests(ContentAdminTestCase):

    def test_preview_shows_questions_without_recording_attempts(self):
        response = self.client.get(admin_url('training', 'preview', self.training.pk) + '?show_correct=1')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'T B1 Q1')
        self.assertContains(response, 'class="correct-option"')
        self.assertFalse(TraineeTraining.objects.exists())

    def test_duplicate_action(self):
        response = self.client.post(admin_url('training', 'changelist'), {
            'action': 'duplicate_trainings', '_selected_action': [self.training.pk],
        })
        self.assertEqual(response.status_code, 302)
        copy = Training.objects.exclude(pk=self.training.pk).get()
        self.assertEqual(copy.name_training, 'T (copy)')
        self.assertEqual(TrainingQuestion.objects.filter(block__training=copy).count(), 2)
