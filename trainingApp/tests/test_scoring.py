"""Tests unitarios del cálculo de puntaje y estado de un intento (TraineeTraining)."""
from decimal import Decimal

from django.test import TestCase

from trainingApp.models import TraineeTraining

from .factories import add_block, make_attempt, make_course, make_group, make_trainee, make_training, questions_of, record_answer

PASSED = TraineeTraining.StateTraineeTraining.PASSED
FAILED = TraineeTraining.StateTraineeTraining.FAILED
IN_PROGRESS = TraineeTraining.StateTraineeTraining.IN_PROGRESS


class CalculateScoreTests(TestCase):
    def setUp(self):
        group = make_group()
        self.trainee = make_trainee('ana', group)
        self.training = make_training('T1', blocks=2, questions_per_block=2)  # 4 preguntas
        self.course = make_course('C', [self.training], groups=[group])
        self.attempt = make_attempt(self.trainee, self.course, self.training, state=IN_PROGRESS)
        self.questions = questions_of(self.training)

    def test_counts_correct_answers_over_all_questions(self):
        for question, correct in zip(self.questions, [True, True, True, False]):
            record_answer(self.attempt, question, correct)

        score = self.attempt.calculate_score()

        self.assertEqual(score, {'percentage': 75.0, 'correct_answers': 3, 'incorrect_answers': 1, 'total_questions': 4})

    def test_unanswered_questions_count_as_incorrect(self):
        record_answer(self.attempt, self.questions[0], True)

        score = self.attempt.calculate_score()

        self.assertEqual(score['percentage'], 25.0)
        self.assertEqual(score['incorrect_answers'], 3)

    def test_last_answer_wins_when_a_question_is_answered_twice(self):
        for question in self.questions:
            record_answer(self.attempt, question, False)
        record_answer(self.attempt, self.questions[0], True)

        self.assertEqual(self.attempt.calculate_score()['correct_answers'], 1)

    def test_inactive_blocks_are_ignored(self):
        inactive = add_block(self.training, 'Inactive', questions=3, state='Inactive')
        for question in self.questions:
            record_answer(self.attempt, question, True)
        record_answer(self.attempt, inactive.trainingquestion_set.first(), False)

        score = self.attempt.calculate_score()

        self.assertEqual(score['total_questions'], 4)
        self.assertEqual(score['percentage'], 100.0)

    def test_training_without_questions_scores_zero(self):
        empty = make_training('Empty', blocks=0)
        attempt = make_attempt(self.trainee, self.course, empty, state=IN_PROGRESS)

        self.assertEqual(attempt.calculate_score()['percentage'], 0)

    def test_percentage_is_rounded_to_two_decimals(self):
        training = make_training('Thirds', questions_per_block=3)
        attempt = make_attempt(self.trainee, self.course, training, state=IN_PROGRESS)
        record_answer(attempt, questions_of(training)[0], True)

        self.assertEqual(attempt.calculate_score()['percentage'], 33.33)


class UpdateScoreAndStateTests(TestCase):
    def setUp(self):
        group = make_group()
        self.trainee = make_trainee('ana', group)
        self.training = make_training('T1', questions_per_block=10, passing_score=70)
        self.exam = make_training('Exam', questions_per_block=10)
        self.course = make_course('C', [self.training], groups=[group], final_exam=self.exam, final_exam_passing_score=90)

    def finish_attempt(self, training, correct_count):
        attempt = make_attempt(self.trainee, self.course, training, state=IN_PROGRESS)
        for i, question in enumerate(questions_of(training)):
            record_answer(attempt, question, i < correct_count)
        attempt.update_score_and_state()
        attempt.refresh_from_db()
        return attempt

    def test_passes_when_score_equals_passing_score(self):
        attempt = self.finish_attempt(self.training, 7)

        self.assertEqual(attempt.state, PASSED)
        self.assertEqual(attempt.score_percentage, Decimal('70.00'))
        self.assertEqual((attempt.correct_answers, attempt.incorrect_answers), (7, 3))

    def test_fails_below_passing_score(self):
        self.assertEqual(self.finish_attempt(self.training, 6).state, FAILED)

    def test_final_exam_uses_course_passing_score(self):
        attempt = self.finish_attempt(self.exam, 8)  # 80 %: aprobaría con 70, no con 90

        self.assertTrue(attempt.is_final_exam_attempt)
        self.assertEqual(attempt.state, FAILED)

    def test_best_score_is_shared_but_answer_counts_are_per_attempt(self):
        first = self.finish_attempt(self.training, 9)
        second = self.finish_attempt(self.training, 4)
        first.refresh_from_db()

        self.assertEqual(first.best_score, Decimal('90.00'))
        self.assertEqual(second.best_score, Decimal('90.00'))
        self.assertEqual((first.correct_answers, first.incorrect_answers), (9, 1))
        self.assertEqual((second.correct_answers, second.incorrect_answers), (4, 6))

    def test_in_progress_attempts_do_not_affect_best_score(self):
        in_progress = make_attempt(self.trainee, self.course, self.training, state=IN_PROGRESS, score=100)
        finished = self.finish_attempt(self.training, 5)
        in_progress.refresh_from_db()

        self.assertEqual(finished.best_score, Decimal('50.00'))
        self.assertEqual(in_progress.best_score, Decimal('0.00'))
