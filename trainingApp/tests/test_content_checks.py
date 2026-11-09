"""Verificaciones del contenido que muestra la estructura del curso en el admin."""

from django.test import TestCase

from trainingApp import content_checks
from trainingApp.content_checks import ERROR, WARNING
from trainingApp.models import (
    Choice,
    CourseTraining,
    Training,
    TrainingBlock,
    TrainingQuestion,
)
from trainingApp.tests.factories import (
    add_block,
    make_course,
    make_group,
    make_training,
)


def levels_and_messages(issues):
    return [(issue.level, issue.message) for issue in issues]


class QuestionIssuesTests(TestCase):

    def setUp(self):
        self.block = add_block(make_training("T", blocks=0), "B", questions=0)
        self.question = TrainingQuestion.objects.create(
            block=self.block,
            question_en="Star?",
            question_es="¿Estrella?",
            deploy_sound="trainingApp/sound/x.mp3",
        )

    def add_choices(self, *correct_flags):
        for i, correct in enumerate(correct_flags):
            Choice.objects.create(
                deploy=self.question,
                choice_en=f"o{i}",
                choice_es=f"o{i}",
                correctChoice=correct,
            )

    def test_complete_question_has_no_issues(self):
        self.add_choices(True, False)
        self.assertEqual(content_checks.question_issues(self.question), [])

    def test_missing_sound_and_options(self):
        self.question.deploy_sound = ""
        issues = levels_and_messages(content_checks.question_issues(self.question))
        self.assertIn((ERROR, "No sound."), issues)
        self.assertIn((ERROR, "Fewer than two options."), issues)

    def test_correct_option_count(self):
        for flags in ((True, True), (False, False)):
            with self.subTest(flags=flags):
                self.question.choice_set.all().delete()
                self.add_choices(*flags)
                issues = levels_and_messages(
                    content_checks.question_issues(self.question)
                )
                self.assertIn(
                    (ERROR, "It must have exactly one correct option."), issues
                )

    def test_missing_translations(self):
        self.question.question_es = ""
        self.add_choices(True, False)
        Choice.objects.filter(deploy=self.question).update(choice_es="")
        issues = levels_and_messages(content_checks.question_issues(self.question))
        self.assertIn((WARNING, "Question text missing in ES."), issues)
        self.assertIn((WARNING, "Options without text in ES."), issues)


class BlockAndTrainingIssuesTests(TestCase):

    def test_active_block_without_questions(self):
        training = make_training("T", blocks=0)
        empty = add_block(training, "Empty", questions=0)
        self.assertEqual(content_checks.block_issues(empty)[0].level, WARNING)
        empty.state_block = TrainingBlock.StateBlock.inactive
        self.assertEqual(content_checks.block_issues(empty), [])

    def test_training_needs_an_active_block_with_questions(self):
        training = make_training("T", blocks=0)
        add_block(training, "Inactive", questions=1, state="Inactive")
        self.assertEqual(content_checks.training_issues(training)[0].level, ERROR)
        add_block(training, "Active", questions=1)
        self.assertEqual(content_checks.training_issues(training), [])


class CourseIssuesTests(TestCase):

    def course_issues(self, course):
        course_trainings = list(
            CourseTraining.objects.filter(course=course).select_related("training")
        )
        return levels_and_messages(
            content_checks.course_issues(course, course_trainings)
        )

    def test_ready_course_has_no_issues(self):
        course = make_course("C", [make_training("T")], groups=[make_group()])
        self.assertEqual(self.course_issues(course), [])

    def test_course_problems(self):
        inactive = make_training("Inactive", state=Training.StateTraining.inactive)
        course = make_course("C", [inactive], final_exam=inactive)
        issues = self.course_issues(course)
        self.assertIn(
            (ERROR, "The final exam is also one of the course trainings."), issues
        )
        self.assertIn(
            (WARNING, '"Inactive" is inactive: trainees do not see it.'), issues
        )
        self.assertIn(
            (WARNING, "No group assigned: no trainee can see the course."), issues
        )
        self.assertIn(
            (ERROR, "The course has no trainings."),
            self.course_issues(make_course("Empty", [])),
        )
