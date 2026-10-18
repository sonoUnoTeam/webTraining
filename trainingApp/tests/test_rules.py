"""Tests unitarios de las reglas de acceso y progreso (trainingApp/rules.py)."""
from django.test import TestCase

from trainingApp import rules
from trainingApp.models import CourseTraining, TraineeTraining

from .factories import add_block, make_attempt, make_course, make_group, make_trainee, make_training

PASSED = TraineeTraining.StateTraineeTraining.PASSED
FAILED = TraineeTraining.StateTraineeTraining.FAILED
IN_PROGRESS = TraineeTraining.StateTraineeTraining.IN_PROGRESS


class QueryHelpersTests(TestCase):
    def test_active_blocks_excludes_inactive_and_empty_blocks(self):
        training = make_training('T', blocks=0)
        active = add_block(training, 'Active')
        add_block(training, 'Inactive', state='Inactive')
        add_block(training, 'Empty', questions=0)

        self.assertEqual(list(rules.active_blocks(training)), [active])

    def test_course_trainings_are_ordered_and_only_active(self):
        first, inactive, second = make_training('A'), make_training('B', state='Inactive'), make_training('C')
        course = make_course('Course', [first, inactive, second])

        self.assertEqual([ct.training for ct in rules.course_trainings(course)], [first, second])

    def test_course_training_order_is_auto_assigned_and_compacted_on_delete(self):
        a, b, c = make_training('A'), make_training('B'), make_training('C')
        course = make_course('Course', [a, b, c])

        CourseTraining.objects.get(course=course, training=a).delete()

        self.assertEqual(list(CourseTraining.objects.filter(course=course).values_list('training__name_training', 'order')),
                         [('B', 1), ('C', 2)])

    def test_can_view_course_requires_matching_group(self):
        group, other = make_group('A'), make_group('B')
        course = make_course('Course', [], groups=[group])

        self.assertTrue(rules.can_view_course(make_trainee('member', group), course))
        self.assertFalse(rules.can_view_course(make_trainee('outsider', other), course))
        self.assertFalse(rules.can_view_course(make_trainee('nogroup', None), course))


class CheckCanAttemptTests(TestCase):
    """Course: t1 → t2 → t3 + examen final. Cada training permite 2 intentos."""

    def setUp(self):
        self.group = make_group()
        self.trainee = make_trainee('ana', self.group)
        self.t1, self.t2, self.t3 = make_training('T1'), make_training('T2'), make_training('T3')
        self.exam = make_training('Exam', attempts_allowed=1)
        self.course = make_course('C', [self.t1, self.t2, self.t3], groups=[self.group], final_exam=self.exam)

    def check(self, training):
        return rules.check_can_attempt(self.trainee, self.course, training)

    def finish(self, training, score=100, state=PASSED):
        return make_attempt(self.trainee, self.course, training, state=state, score=score)

    def test_first_training_is_available(self):
        self.assertIsNone(self.check(self.t1))

    def test_other_group_has_no_access(self):
        outsider = make_trainee('eve', make_group('Other'))

        self.assertEqual(rules.check_can_attempt(outsider, self.course, self.t1), 'You do not have access to this course.')

    def test_training_outside_the_course_is_rejected(self):
        self.assertEqual(self.check(make_training('Foreign')), 'This training is not part of the course.')

    def test_inactive_course_or_training_is_rejected(self):
        self.t1.state_training = 'Inactive'
        self.t1.save()
        self.assertEqual(self.check(self.t1), 'This training is not available.')

        self.course.state_course = 'Inactive'
        self.course.save()
        self.assertEqual(self.check(self.t2), 'This training is not available.')

    def test_next_training_requires_a_finished_attempt_of_the_previous_one(self):
        self.assertEqual(self.check(self.t2), 'You must complete the previous training first.')

        make_attempt(self.trainee, self.course, self.t1, state=IN_PROGRESS)
        self.assertEqual(self.check(self.t2), 'You must complete the previous training first.')

    def test_failed_previous_training_still_unlocks_the_next(self):
        self.finish(self.t1, score=10, state=FAILED)

        self.assertIsNone(self.check(self.t2))

    def test_starting_the_next_training_locks_retries(self):
        self.finish(self.t1, score=10, state=FAILED)
        make_attempt(self.trainee, self.course, self.t2, state=IN_PROGRESS)

        self.assertEqual(self.check(self.t1),
                         'You cannot retry this training because you have already started the next one.')

    def test_attempt_limit(self):
        self.finish(self.t1, state=FAILED)
        self.assertIsNone(self.check(self.t1))

        self.finish(self.t1, state=FAILED)
        self.assertEqual(self.check(self.t1), 'You have reached the maximum number of attempts for this training.')

    def test_an_in_progress_attempt_can_be_resumed_even_at_the_limit(self):
        self.finish(self.t1, state=FAILED)
        self.finish(self.t1, state=FAILED)
        # Datos inconsistentes posibles en producción: el intento en curso se puede terminar
        make_attempt(self.trainee, self.course, self.t1, state=IN_PROGRESS)

        self.assertIsNone(self.check(self.t1))

    def test_final_exam_requires_every_training_attempted(self):
        self.finish(self.t1)
        self.finish(self.t2)

        self.assertFalse(rules.final_exam_unlocked(self.trainee, self.course))
        self.assertEqual(self.check(self.exam), 'You have not met the requirements to take the final exam yet.')

    def test_final_exam_requires_minimum_average_of_best_scores(self):
        self.finish(self.t1, score=100)
        self.finish(self.t2, score=50, state=FAILED)
        self.finish(self.t3, score=50, state=FAILED)  # promedio 66,67 < 70
        self.assertFalse(rules.final_exam_unlocked(self.trainee, self.course))

        self.finish(self.t3, score=70)  # mejor de T3 = 70 → promedio 73,33
        self.assertTrue(rules.final_exam_unlocked(self.trainee, self.course))
        self.assertIsNone(self.check(self.exam))

    def test_starting_the_final_exam_locks_every_training(self):
        for training in (self.t1, self.t2, self.t3):
            self.finish(training)
        make_attempt(self.trainee, self.course, self.exam, state=IN_PROGRESS)

        self.assertEqual(self.check(self.t3),
                         'You cannot retry this training because you have already started the final exam.')
        self.assertEqual(self.check(self.t1),
                         'You cannot retry this training because you have already started the next one.')

    def test_final_exam_attempt_limit(self):
        for training in (self.t1, self.t2, self.t3):
            self.finish(training)
        self.finish(self.exam, score=10, state=FAILED)

        self.assertEqual(self.check(self.exam), 'You have reached the maximum number of attempts for this training.')
