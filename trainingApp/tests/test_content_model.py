"""Estructura de contenido: orden automático, conjuntos de opciones y protección de las respuestas."""

from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from trainingApp.models import (
    Choice,
    CourseTraining,
    TrainingBlock,
    TrainingQuestion,
    TrainingQuestionAnswer,
)
from trainingApp.tests.factories import (
    PASSWORD,
    add_block,
    answer_training,
    make_attempt,
    make_choice_set,
    make_course,
    make_group,
    make_trainee,
    make_training,
    record_answer,
    simple_static_storage,
)


class AutoOrderTests(TestCase):

    def test_new_items_go_last_within_their_parent(self):
        training = make_training("T", blocks=2, questions_per_block=3)
        other = make_training("Other", blocks=1)
        self.assertEqual([b.order for b in training.trainingblock_set.all()], [1, 2])
        self.assertEqual(other.trainingblock_set.get().order, 1)
        block = training.trainingblock_set.first()
        self.assertEqual([q.order for q in block.trainingquestion_set.all()], [1, 2, 3])
        self.assertEqual(
            [c.order for c in block.trainingquestion_set.first().choice_set.all()],
            [1, 2],
        )

    def test_explicit_order_is_kept_and_defines_presentation(self):
        training = make_training("T", blocks=0)
        late = TrainingBlock.objects.create(
            training=training, name_block="Late", order=5
        )
        early = TrainingBlock.objects.create(
            training=training, name_block="Early", order=1
        )
        self.assertEqual(list(training.trainingblock_set.all()), [early, late])

    def test_course_trainings_keep_order_after_swapping(self):
        t1, t2 = make_training("T1"), make_training("T2")
        course = make_course("C", [t1, t2])
        first, second = CourseTraining.objects.filter(course=course)
        first.order, second.order = second.order, first.order
        first.save()
        second.save()
        self.assertEqual(
            [ct.training for ct in CourseTraining.objects.filter(course=course)],
            [t2, t1],
        )


class ChoiceSetTests(TestCase):

    def setUp(self):
        self.choice_set = make_choice_set(
            "Star / Galaxy",
            [("Star", "Estrella"), ("Galaxy", "Galaxia"), ("Not sure", "No sé")],
        )
        self.block = add_block(make_training("T", blocks=0), "B", questions=0)
        self.question = TrainingQuestion.objects.create(block=self.block)

    def test_apply_copies_texts_order_and_correct_option(self):
        galaxy = self.choice_set.options.get(text_en="Galaxy")
        self.question.apply_choice_set(self.choice_set, galaxy)
        choices = list(
            self.question.choice_set.values_list(
                "order", "choice_en", "choice_es", "correctChoice"
            )
        )
        self.assertEqual(
            choices,
            [
                (1, "Star", "Estrella", False),
                (2, "Galaxy", "Galaxia", True),
                (3, "Not sure", "No sé", False),
            ],
        )

    def test_apply_replaces_previous_choices(self):
        Choice.objects.create(deploy=self.question, choice_en="old")
        self.question.apply_choice_set(self.choice_set)
        self.assertFalse(self.question.choice_set.filter(choice_en="old").exists())
        self.assertEqual(self.question.choice_set.count(), 3)
        self.assertFalse(self.question.choice_set.filter(correctChoice=True).exists())

    def test_apply_refused_when_question_has_answers(self):
        self.question.apply_choice_set(self.choice_set, self.choice_set.options.first())
        trainee = make_trainee("ana", make_group())
        record_answer(
            make_attempt(trainee, make_course("C", []), self.block.training),
            self.question,
            True,
        )
        with self.assertRaises(ValidationError):
            self.question.apply_choice_set(self.choice_set)
        self.assertEqual(self.question.choice_set.count(), 3)

    def test_fill_from_block_defaults_only_empty_languages(self):
        self.block.default_question_en = "Star or galaxy?"
        self.block.default_question_es = "¿Estrella o galaxia?"
        self.block.save()
        self.question.question_es = "Texto propio"
        self.question.fill_from_block_defaults()
        self.assertEqual(
            (self.question.question_en, self.question.question_es),
            ("Star or galaxy?", "Texto propio"),
        )


class AnswerProtectionTests(TestCase):

    def setUp(self):
        self.training = make_training("T", blocks=1, questions_per_block=1)
        self.question = TrainingQuestion.objects.get(block__training=self.training)
        trainee = make_trainee("ana", make_group())
        self.answer = record_answer(
            make_attempt(trainee, make_course("C", []), self.training),
            self.question,
            False,
        )

    def test_answered_content_cannot_be_deleted(self):
        with self.assertRaises(ProtectedError):
            self.question.delete()
        with self.assertRaises(ProtectedError):
            self.answer.selectedChoice.delete()
        with self.assertRaises(ProtectedError):
            self.question.block.delete()
        self.assertTrue(
            TrainingQuestionAnswer.objects.filter(pk=self.answer.pk).exists()
        )

    def test_is_correct_keeps_value_at_answer_time(self):
        self.assertIs(self.answer.is_correct, False)
        Choice.objects.filter(pk=self.answer.selectedChoice_id).update(
            correctChoice=True
        )
        self.answer.refresh_from_db()
        self.assertIs(self.answer.is_correct, False)


@simple_static_storage
class AnswerFlowTests(TestCase):

    def test_flow_stores_is_correct(self):
        group = make_group()
        trainee = make_trainee("ana", group)
        training = make_training("T", blocks=1, questions_per_block=2)
        course = make_course("C", [training], groups=[group])
        self.client.login(username=trainee.user.username, password=PASSWORD)
        answer_training(self.client, course, training, [True, False])
        answers = TrainingQuestionAnswer.objects.order_by("deploy__order")
        self.assertEqual([a.is_correct for a in answers], [True, False])


class DuplicateTrainingTests(TestCase):

    def test_copies_tree_reusing_files_and_not_courses(self):
        training = make_training("Galaxies", blocks=2, questions_per_block=2)
        training.name_training_es = "Galaxias"
        training.save()
        TrainingQuestion.objects.filter(block__training=training).update(
            deploy_sound="trainingApp/sound/x.mp3"
        )
        make_course("C", [training])

        copy = training.duplicate()

        self.assertEqual(
            (copy.name_training_en, copy.name_training_es),
            ("Galaxies (copy)", "Galaxias (copia)"),
        )
        self.assertFalse(copy.courses.exists())
        self.assertEqual(
            [b.name_block for b in copy.trainingblock_set.all()],
            [b.name_block for b in training.trainingblock_set.all()],
        )
        questions = TrainingQuestion.objects.filter(block__training=copy)
        self.assertEqual(questions.count(), 4)
        self.assertEqual(
            set(questions.values_list("deploy_sound", flat=True)),
            {"trainingApp/sound/x.mp3"},
        )
        self.assertEqual(
            Choice.objects.filter(
                deploy__block__training=copy, correctChoice=True
            ).count(),
            4,
        )
        # El original no cambia
        self.assertEqual(
            TrainingQuestion.objects.filter(block__training=training).count(), 4
        )
