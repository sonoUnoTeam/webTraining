"""
Migración de datos 0005_backfill_content_structure: se arma contenido con el esquema anterior
(0003), se migra y se verifica orden, is_correct, ChoiceSets sembrados y defaults de bloque.
"""
import contextlib
import importlib
import io

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

MIGRATE_FROM = [('trainingApp', '0003_normalize_legacy_choice_values')]
MIGRATE_TO = [('trainingApp', '0005_backfill_content_structure')]
backfill_module = importlib.import_module('trainingApp.migrations.0005_backfill_content_structure')

STAR_GALAXY = [('Star', 'Estrella'), ('Galaxy', 'Galaxia')]


def migrate(targets):
    executor = MigrationExecutor(connection)
    with contextlib.redirect_stdout(io.StringIO()):
        executor.migrate(targets)
    return executor.loader.project_state(targets).apps


class BackfillContentStructureTests(TransactionTestCase):

    def setUp(self):
        old_apps = migrate(MIGRATE_FROM)
        self.build_old_content(old_apps)
        self.apps = migrate(MIGRATE_TO)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        with contextlib.redirect_stdout(io.StringIO()):
            executor.migrate(executor.loader.graph.leaf_nodes())

    def build_old_content(self, apps):
        Training = apps.get_model('trainingApp', 'Training')
        TrainingBlock = apps.get_model('trainingApp', 'TrainingBlock')
        TrainingQuestion = apps.get_model('trainingApp', 'TrainingQuestion')
        Choice = apps.get_model('trainingApp', 'Choice')

        training = Training.objects.create(name_training='T', name_training_en='T')
        # Bloque cuyas preguntas comparten consigna y opciones
        self.shared_block_id = TrainingBlock.objects.create(name_block='Shared', description='', training=training).id
        self.mixed_block_id = TrainingBlock.objects.create(name_block='Mixed', description='', training=training).id
        # Comparten opciones pero no consigna: reciben el conjunto sin consigna por defecto
        self.same_options_block_id = TrainingBlock.objects.create(name_block='Same options', description='', training=training).id
        # Consigna común solo en español (sin texto en inglés)
        self.spanish_only_block_id = TrainingBlock.objects.create(name_block='Spanish only', description='', training=training).id

        def add_question(block_id, texts, options, correct_index):
            question = TrainingQuestion.objects.create(block_id=block_id, question_en=texts[0], question_es=texts[1])
            for i, (text_en, text_es) in enumerate(options):
                Choice.objects.create(
                    deploy=question, choice=text_en, choice_en=text_en, choice_es=text_es, correctChoice=(i == correct_index)
                )
            return question

        star_or_galaxy = ('Star or galaxy?', '¿Estrella o galaxia?')
        self.shared_questions = [add_question(self.shared_block_id, star_or_galaxy, STAR_GALAXY, i % 2) for i in range(3)]
        # Conjuntos usados una sola vez o con una opción vacía: no generan ChoiceSet
        add_question(self.mixed_block_id, ('Function?', '¿Función?'), [('Sine', 'Seno'), ('Square', 'Cuadrada')], 0)
        add_question(self.mixed_block_id, ('Tones?', '¿Tonos?'), [('4', '4'), ('', '')], 0)
        add_question(self.mixed_block_id, ('Tones?', '¿Tonos?'), [('4', '4'), ('', '')], 0)
        add_question(self.same_options_block_id, ('Is it a star?', '¿Es una estrella?'), STAR_GALAXY, 0)
        add_question(self.same_options_block_id, ('Is it a galaxy?', '¿Es una galaxia?'), STAR_GALAXY, 1)
        add_question(self.spanish_only_block_id, (None, '¿Cuántos tonos?'), [('1', '1'), ('2', '2')], 0)
        add_question(self.spanish_only_block_id, (None, '¿Cuántos tonos?'), [('3', '3'), ('4', '4')], 0)

        self.correct_answer_id, self.incorrect_answer_id = self.build_old_answers(apps, training)

    def build_old_answers(self, apps, training):
        User = apps.get_model('auth', 'User')
        Trainee = apps.get_model('userApp', 'Trainee')
        Course = apps.get_model('trainingApp', 'Course')
        TraineeCourse = apps.get_model('trainingApp', 'TraineeCourse')
        TraineeTraining = apps.get_model('trainingApp', 'TraineeTraining')
        TrainingBlockAnswer = apps.get_model('trainingApp', 'TrainingBlockAnswer')
        TrainingQuestionAnswer = apps.get_model('trainingApp', 'TrainingQuestionAnswer')
        Choice = apps.get_model('trainingApp', 'Choice')

        trainee = Trainee.objects.create(user=User.objects.create(username='u'), occupation='Tester')
        course = Course.objects.create(name_course='C', name_course_en='C', description='')
        trainee_course = TraineeCourse.objects.create(trainee=trainee, course=course)
        attempt = TraineeTraining.objects.create(
            trainee_course=trainee_course, trainee=trainee, training=training, course=course, pub_date=timezone.now()
        )
        block_answer = TrainingBlockAnswer.objects.create(trainee_Training=attempt, block_id=self.shared_block_id)
        question = self.shared_questions[0]
        answer_ids = []
        for correct in (True, False):
            choice = Choice.objects.get(deploy_id=question.id, correctChoice=correct)
            answer_ids.append(
                TrainingQuestionAnswer.objects.create(block_answer=block_answer, deploy_id=question.id, selectedChoice=choice).id
            )
        return answer_ids

    def model(self, name):
        return self.apps.get_model('trainingApp', name)

    def test_order_follows_creation_order(self):
        TrainingBlock = self.model('TrainingBlock')
        TrainingQuestion = self.model('TrainingQuestion')
        Choice = self.model('Choice')
        self.assertEqual(list(TrainingBlock.objects.order_by('id').values_list('order', flat=True)), [1, 2, 3, 4])
        orders = TrainingQuestion.objects.filter(block_id=self.shared_block_id).order_by('id').values_list('order', flat=True)
        self.assertEqual(list(orders), [1, 2, 3])
        choice_orders = Choice.objects.filter(deploy_id=self.shared_questions[0].id).order_by('id').values_list('order', flat=True)
        self.assertEqual(list(choice_orders), [1, 2])

    def test_is_correct_copied_from_selected_choice(self):
        TrainingQuestionAnswer = self.model('TrainingQuestionAnswer')
        self.assertIs(TrainingQuestionAnswer.objects.get(id=self.correct_answer_id).is_correct, True)
        self.assertIs(TrainingQuestionAnswer.objects.get(id=self.incorrect_answer_id).is_correct, False)

    def test_choice_set_created_only_for_repeated_complete_options(self):
        ChoiceSet = self.model('ChoiceSet')
        self.assertEqual(ChoiceSet.objects.count(), 1)
        choice_set = ChoiceSet.objects.get()
        self.assertEqual((choice_set.name_en, choice_set.name_es), ('Star / Galaxy', 'Estrella / Galaxia'))
        options = list(choice_set.options.order_by('order').values_list('order', 'text_en', 'text_es'))
        self.assertEqual(options, [(1, 'Star', 'Estrella'), (2, 'Galaxy', 'Galaxia')])

    def test_block_defaults_only_when_shared_by_all_questions(self):
        TrainingBlock = self.model('TrainingBlock')
        shared = TrainingBlock.objects.get(id=self.shared_block_id)
        self.assertEqual(shared.default_choice_set.name_en, 'Star / Galaxy')
        self.assertEqual((shared.default_question_en, shared.default_question_es), ('Star or galaxy?', '¿Estrella o galaxia?'))
        mixed = TrainingBlock.objects.get(id=self.mixed_block_id)
        self.assertIsNone(mixed.default_choice_set_id)
        self.assertFalse(mixed.default_question_en)

    def test_block_defaults_without_shared_default_language_text(self):
        # La columna base default_question es NOT NULL: queda vacía cuando no hay consigna común en inglés
        TrainingBlock = self.model('TrainingBlock')
        same_options = TrainingBlock.objects.get(id=self.same_options_block_id)
        self.assertEqual(same_options.default_choice_set.name_en, 'Star / Galaxy')
        self.assertEqual(same_options.default_question, '')
        self.assertFalse(same_options.default_question_en)
        self.assertFalse(same_options.default_question_es)
        spanish_only = TrainingBlock.objects.get(id=self.spanish_only_block_id)
        self.assertIsNone(spanish_only.default_choice_set_id)
        self.assertEqual((spanish_only.default_question, spanish_only.default_question_es), ('', '¿Cuántos tonos?'))
        self.assertFalse(spanish_only.default_question_en)

    def test_backfill_is_idempotent(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            backfill_module.backfill(self.apps, None)
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(self.model('ChoiceSet').objects.count(), 1)
