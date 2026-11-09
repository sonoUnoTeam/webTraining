"""
Tests de integración: un trainee recorre un curso por HTTP, como en el navegador.

Curso usado en casi todos los tests:
    T1 (1 bloque, 2 preguntas, 2 intentos) → T2 (2 bloques, 4 preguntas, 2 intentos) → Examen final (2 preguntas, 1 intento)
Umbrales: 70 % para aprobar cada training, 70 % de promedio para habilitar el examen, 70 % para aprobarlo.
"""

from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from trainingApp.models import (
    Comment,
    TraineeCourse,
    TraineeTraining,
    TrainingBlockAnswer,
    TrainingQuestionAnswer,
)

from .factories import (
    PASSWORD,
    add_block,
    answer_training,
    make_course,
    make_group,
    make_trainee,
    make_training,
    questions_of,
    simple_static_storage,
)

TT = TraineeTraining.StateTraineeTraining
TC = TraineeCourse.StateTraineeCourse


class CourseFixtureMixin:
    def setUp(self):
        self.group = make_group()
        self.trainee = make_trainee("ana", self.group)
        self.t1 = make_training("T1", blocks=1, questions_per_block=2)
        self.t2 = make_training("T2", blocks=2, questions_per_block=2)
        self.exam = make_training("Exam", attempts_allowed=1)
        self.course = make_course(
            "Sonification 101",
            [self.t1, self.t2],
            groups=[self.group],
            final_exam=self.exam,
        )
        self.client.login(username="ana", password=PASSWORD)

    def url(self, name, *args):
        return reverse(f"trainingApp:{name}", args=args)

    def attempts(self, training):
        return TraineeTraining.objects.filter(
            trainee=self.trainee, course=self.course, training=training
        ).order_by("id")

    def trainee_course(self):
        return TraineeCourse.objects.get(trainee=self.trainee, course=self.course)

    def messages(self, response):
        return [str(m) for m in get_messages(response.wsgi_request)]


@simple_static_storage
class CourseJourneyTests(CourseFixtureMixin, TestCase):
    def test_trainee_completes_the_course_going_through_every_state(self):
        # 1. Ve el curso en su lista; al abrir el detalle se crea el progreso "Not Started"
        response = self.client.get(self.url("course_list"))
        self.assertContains(response, "Sonification 101")
        self.assertEqual(
            self.client.get(self.url("course_detail", self.course.id)).status_code, 200
        )
        self.assertEqual(self.trainee_course().state, TC.Not_Started)

        # 2. T2 y el examen están bloqueados
        response = self.client.get(
            self.url("block_deploy_list", self.course.id, self.t2.id)
        )
        self.assertRedirects(
            response,
            self.url("course_detail", self.course.id),
            fetch_redirect_response=False,
        )
        self.assertIn(
            "You must complete the previous training first.", self.messages(response)
        )

        # 3. Empieza T1: el intento queda en progreso y el curso pasa a "In Progress"
        self.assertEqual(
            self.client.get(
                self.url("block_deploy_list", self.course.id, self.t1.id)
            ).status_code,
            200,
        )
        self.assertEqual(self.attempts(self.t1).get().state, TT.IN_PROGRESS)
        self.assertEqual(self.trainee_course().state, TC.In_Progress)

        # 4. Termina T1 con 1/2 → desaprobado (50 %), vuelve al detalle con aviso
        response = answer_training(self.client, self.course, self.t1, [True, False])
        self.assertRedirects(
            response,
            self.url("course_detail", self.course.id),
            fetch_redirect_response=False,
        )
        first = self.attempts(self.t1).get()
        self.assertEqual((first.state, first.score_percentage), (TT.FAILED, 50))
        self.assertIsNotNone(first.time_spent)

        # 5. Reintenta T1 y aprueba (100 %); best_score se comparte entre intentos
        answer_training(self.client, self.course, self.t1, True)
        first, second = self.attempts(self.t1)
        self.assertEqual((second.state, second.score_percentage), (TT.PASSED, 100))
        self.assertEqual((first.best_score, second.best_score), (100, 100))
        self.assertEqual(first.correct_answers, 1)

        # 6. El examen todavía no se puede rendir (falta T2)
        response = self.client.get(
            self.url("block_deploy_list", self.course.id, self.exam.id)
        )
        self.assertIn(
            "You have not met the requirements to take the final exam yet.",
            self.messages(response),
        )

        # 7. T2 aprobado con 3/4 (75 %); los dos bloques quedan completos
        answer_training(self.client, self.course, self.t2, [True, True, True, False])
        t2_attempt = self.attempts(self.t2).get()
        self.assertEqual(
            (t2_attempt.state, t2_attempt.score_percentage), (TT.PASSED, 75)
        )
        self.assertEqual(
            TrainingBlockAnswer.objects.filter(
                trainee_Training=t2_attempt, state_block="Completed"
            ).count(),
            2,
        )

        # 8. Examen final aprobado → curso completado y redirección a la encuesta
        response = answer_training(self.client, self.course, self.exam, True)
        self.assertRedirects(
            response,
            self.url("comment", self.course.id, self.exam.id),
            fetch_redirect_response=False,
        )
        exam_attempt = self.attempts(self.exam).get()
        self.assertTrue(exam_attempt.is_final_exam_attempt)
        self.assertEqual(exam_attempt.state, TT.PASSED)
        trainee_course = self.trainee_course()
        self.assertEqual(trainee_course.state, TC.Completed)
        self.assertTrue(trainee_course.exam_passed)
        self.assertIsNotNone(trainee_course.completion_date)

        # 9. Deja su comentario
        self.assertEqual(
            self.client.get(
                self.url("comment", self.course.id, self.exam.id)
            ).status_code,
            200,
        )
        self.client.post(
            self.url("comment", self.course.id, self.exam.id),
            {
                "course_rating": "very_interesting",
                "training_method": "novel",
                "explanations": "very_useful",
                "stars": "5",
            },
        )
        self.assertEqual(Comment.objects.get(trainee=self.trainee).stars, 5)

        # 10. Ya no puede reintentar nada
        for training in (self.t1, self.t2, self.exam):
            response = self.client.get(
                self.url("block_deploy_list", self.course.id, training.id)
            )
            self.assertEqual(response.status_code, 302, training.name_training)

        # 11. Revisa sus resultados: lista de intentos, bloques y pregunta por pregunta
        response = self.client.get(
            self.url("review_list_tt", self.course.id, self.t1.id)
        )
        self.assertEqual(
            {a.id for a in response.context["trainee_training_list"]},
            {first.id, second.id},
        )
        self.assertEqual(
            self.client.get(self.url("review_block", first.id)).status_code, 200
        )
        block_answer = TrainingBlockAnswer.objects.filter(
            trainee_Training=first
        ).first()
        self.assertEqual(
            self.client.get(self.url("review_deploy", block_answer.id)).status_code, 200
        )
        response = self.client.post(self.url("review_deploy", block_answer.id))
        self.assertRedirects(
            response,
            self.url("review_deploy", block_answer.id),
            fetch_redirect_response=False,
        )

        # 12. El detalle del curso renderiza con todo terminado
        self.assertEqual(
            self.client.get(self.url("course_detail", self.course.id)).status_code, 200
        )

    def test_failing_the_last_final_exam_attempt_fails_the_course(self):
        answer_training(self.client, self.course, self.t1, True)
        answer_training(self.client, self.course, self.t2, True)

        response = answer_training(self.client, self.course, self.exam, False)

        self.assertRedirects(
            response,
            self.url("course_detail", self.course.id),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.attempts(self.exam).get().state, TT.FAILED)
        self.assertEqual(self.trainee_course().state, TC.Failed)
        self.assertFalse(self.trainee_course().exam_passed)

    def test_failing_a_final_exam_with_attempts_left_keeps_the_course_in_progress(self):
        self.exam.attempts_allowed = 2
        self.exam.save()
        answer_training(self.client, self.course, self.t1, True)
        answer_training(self.client, self.course, self.t2, True)

        answer_training(self.client, self.course, self.exam, False)

        self.assertEqual(self.trainee_course().state, TC.In_Progress)
        answer_training(self.client, self.course, self.exam, True)
        self.assertEqual(self.trainee_course().state, TC.Completed)

    def test_low_average_keeps_the_final_exam_locked(self):
        answer_training(self.client, self.course, self.t1, [True, False])  # 50
        answer_training(
            self.client, self.course, self.t2, [True, True, False, False]
        )  # 50

        response = self.client.get(
            self.url("block_deploy_list", self.course.id, self.exam.id)
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.attempts(self.exam).exists())

    def test_starting_the_next_training_locks_the_previous_one(self):
        answer_training(self.client, self.course, self.t1, False)
        self.client.get(self.url("block_deploy_list", self.course.id, self.t2.id))

        response = self.client.get(
            self.url("block_deploy_list", self.course.id, self.t1.id)
        )

        self.assertIn(
            "You cannot retry this training because you have already started the next one.",
            self.messages(response),
        )
        self.assertEqual(self.attempts(self.t1).count(), 1)

    def test_attempt_limit_is_enforced(self):
        answer_training(self.client, self.course, self.t1, False)
        answer_training(self.client, self.course, self.t1, False)

        response = self.client.get(
            self.url("block_deploy_list", self.course.id, self.t1.id)
        )

        self.assertIn(
            "You have reached the maximum number of attempts for this training.",
            self.messages(response),
        )
        self.assertEqual(self.attempts(self.t1).count(), 2)


@simple_static_storage
class AnsweringTests(CourseFixtureMixin, TestCase):
    def question_url(self, training, block_id):
        return self.url("forms", self.course.id, training.id, block_id)

    def test_going_back_and_changing_an_answer_keeps_the_last_one(self):
        q1, q2 = questions_of(self.t1)
        url = self.question_url(self.t1, q1.block_id)
        self.client.get(self.url("block_deploy_list", self.course.id, self.t1.id))
        self.client.post(
            url, {"selectedChoice": q1.choice_set.get(correctChoice=False).id}
        )

        # Vuelve a la pregunta 1: la respuesta previa aparece seleccionada
        self.client.get(
            self.url("back_deploy", self.course.id, self.t1.id, q1.block_id)
        )
        response = self.client.get(url)
        self.assertEqual(response.context["deploy"], q1)
        self.assertEqual(
            response.context["form"].initial["selectedChoice"],
            q1.choice_set.get(correctChoice=False).id,
        )

        self.client.post(
            url, {"selectedChoice": q1.choice_set.get(correctChoice=True).id}
        )
        self.client.post(
            url, {"selectedChoice": q2.choice_set.get(correctChoice=True).id}
        )

        self.assertEqual(self.attempts(self.t1).get().score_percentage, 100)

    def test_back_from_the_first_question_returns_to_the_block_list(self):
        block_id = questions_of(self.t1)[0].block_id
        self.client.get(self.url("block_deploy_list", self.course.id, self.t1.id))

        response = self.client.get(
            self.url("back_deploy", self.course.id, self.t1.id, block_id)
        )

        self.assertRedirects(
            response,
            self.url("block_deploy_list", self.course.id, self.t1.id),
            fetch_redirect_response=False,
        )

    def test_submitting_without_choosing_shows_the_question_again(self):
        block_id = questions_of(self.t1)[0].block_id
        self.client.get(self.url("block_deploy_list", self.course.id, self.t1.id))

        response = self.client.post(self.question_url(self.t1, block_id), {})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_a_choice_from_another_question_is_rejected(self):
        q1, q2 = questions_of(self.t1)
        self.client.get(self.url("block_deploy_list", self.course.id, self.t1.id))

        response = self.client.post(
            self.question_url(self.t1, q1.block_id),
            {"selectedChoice": q2.choice_set.first().id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_an_interrupted_attempt_is_resumed_in_a_new_session(self):
        q1, _ = questions_of(self.t1)
        self.client.get(self.url("block_deploy_list", self.course.id, self.t1.id))
        self.client.post(
            self.question_url(self.t1, q1.block_id),
            {"selectedChoice": q1.choice_set.get(correctChoice=True).id},
        )

        self.client.logout()
        self.client.login(username="ana", password=PASSWORD)
        answer_training(self.client, self.course, self.t1, True)

        attempt = self.attempts(self.t1).get()
        self.assertEqual((attempt.state, attempt.score_percentage), (TT.PASSED, 100))

    def test_a_completed_block_cannot_be_answered_again_in_the_same_attempt(self):
        first_block = questions_of(self.t2)[0].block_id
        answer_training(self.client, self.course, self.t1, True)
        self.client.get(self.url("block_deploy_list", self.course.id, self.t2.id))
        for question in questions_of(self.t2)[:2]:
            self.client.post(
                self.question_url(self.t2, first_block),
                {"selectedChoice": question.choice_set.first().id},
            )

        response = self.client.get(self.question_url(self.t2, first_block))

        self.assertRedirects(
            response,
            self.url("block_deploy_list", self.course.id, self.t2.id),
            fetch_redirect_response=False,
        )

    def test_inactive_and_empty_blocks_are_skipped(self):
        inactive = add_block(self.t1, "Inactive", state="Inactive")
        add_block(self.t1, "Empty", questions=0)

        self.assertEqual(
            self.client.get(self.question_url(self.t1, inactive.id)).status_code, 404
        )
        answer_training(self.client, self.course, self.t1, True)
        self.assertEqual(self.attempts(self.t1).get().state, TT.PASSED)

    def test_direct_url_to_a_locked_training_question_is_blocked(self):
        response = self.client.get(
            self.question_url(self.exam, questions_of(self.exam)[0].block_id)
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.attempts(self.exam).exists())


@simple_static_storage
class QuestionStepsTests(TestCase):
    """Indicador de pasos de un bloque y navegación con ?q=<n> (bloque de 3 preguntas)."""

    def setUp(self):
        group = make_group()
        self.trainee = make_trainee("ana", group)
        self.training = make_training("Steps", questions_per_block=3)
        self.course = make_course("Sonification 101", [self.training], groups=[group])
        self.client.login(username="ana", password=PASSWORD)
        self.q1, self.q2, self.q3 = questions_of(self.training)
        self.url = reverse(
            "trainingApp:forms",
            args=[self.course.id, self.training.id, self.q1.block_id],
        )
        self.client.get(
            reverse(
                "trainingApp:block_deploy_list", args=[self.course.id, self.training.id]
            )
        )

    def answer(self, question, correct=True):
        return self.client.post(
            self.url,
            {"selectedChoice": question.choice_set.get(correctChoice=correct).id},
        )

    def go_to(self, number):
        return self.client.get(f"{self.url}?q={number}")

    def accessible_steps(self, response):
        return [step["accessible"] for step in response.context["steps_info"]]

    def test_cannot_jump_past_the_first_unanswered_question(self):
        self.answer(self.q1)

        response = self.go_to(3)

        self.assertEqual(response.context["deploy"], self.q2)
        self.assertEqual(self.accessible_steps(response), [True, True, False])

    def test_invalid_step_values_are_ignored(self):
        self.answer(self.q1)
        for value in ("0", "-1", "999", "abc", ""):
            with self.subTest(q=value):
                response = self.go_to(value)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["deploy"], self.q2)

    def test_going_back_keeps_the_furthest_question_reachable(self):
        self.answer(self.q1)
        self.answer(self.q2)

        response = self.go_to(1)
        self.assertEqual(response.context["deploy"], self.q1)
        self.assertEqual(self.accessible_steps(response), [True, True, True])
        self.assertEqual(self.go_to(3).context["deploy"], self.q3)

    def test_changing_an_answer_after_jumping_back_does_not_duplicate_it(self):
        self.answer(self.q1, correct=False)
        self.answer(self.q2)
        self.go_to(1)

        self.answer(self.q1, correct=True)

        answers = TrainingQuestionAnswer.objects.filter(deploy=self.q1)
        self.assertEqual(answers.count(), 1)
        self.assertTrue(answers.get().selectedChoice.correctChoice)
        self.assertEqual(self.client.get(self.url).context["deploy"], self.q2)

    def test_answered_steps_are_announced_and_progress_markup_is_closed(self):
        self.answer(self.q1)
        html = self.client.get(self.url).content.decode()

        self.assertIn(
            '<span class="visually-hidden">(answered)</span><span aria-hidden="true">✓</span>',
            html,
        )
        self.assertIn('aria-current="step"', html)
        # El contenedor del texto de progreso se cierra antes del título de la pregunta
        self.assertRegex(
            html,
            r'<div class="progress-indicator[^>]*>\s*<span id="progreso-texto">[^<]*</span>\s*</div>',
        )


@simple_static_storage
class BlockListProgressTests(CourseFixtureMixin, TestCase):
    """Lista de bloques: progreso y estado por bloque, y resumen del intento."""

    def blocks(self, response):
        return {block.id: block for block in response.context["block_list"]}

    def test_progress_and_completion_follow_the_answers(self):
        answer_training(self.client, self.course, self.t1, True)
        list_url = self.url("block_deploy_list", self.course.id, self.t2.id)
        questions = questions_of(self.t2)
        first_block, second_block = questions[0].block_id, questions[2].block_id

        response = self.client.get(list_url)
        self.assertEqual(response.context["current_attempt"], 1)
        self.assertEqual(response.context["total_training_answered"], 0)

        form_url = self.url("forms", self.course.id, self.t2.id, first_block)
        self.client.post(
            form_url, {"selectedChoice": questions[0].choice_set.first().id}
        )
        response = self.client.get(list_url)
        blocks = self.blocks(response)
        self.assertEqual(
            (blocks[first_block].answered_count, blocks[first_block].is_completed),
            (1, False),
        )
        self.assertContains(response, 'aria-label="Continue ')

        self.client.post(
            form_url, {"selectedChoice": questions[1].choice_set.first().id}
        )
        response = self.client.get(list_url)
        blocks = self.blocks(response)
        self.assertEqual(
            (blocks[first_block].answered_count, blocks[first_block].is_completed),
            (2, True),
        )
        self.assertEqual(
            (blocks[second_block].answered_count, blocks[second_block].is_completed),
            (0, False),
        )
        self.assertEqual(response.context["total_training_answered"], 2)

    def test_summary_is_translated(self):
        # La petición a /es/ activa el español en el hilo: override lo restaura para los tests siguientes
        with translation.override("es"):
            list_url = reverse(
                "trainingApp:block_deploy_list", args=[self.course.id, self.t1.id]
            )
            response = self.client.get(list_url)

        self.assertContains(
            response, "Intento 1 de 2. 1 bloques. 0 preguntas respondidas."
        )


@simple_static_storage
class AccessControlTests(CourseFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        answer_training(self.client, self.course, self.t1, True)
        self.attempt = self.attempts(self.t1).get()
        self.block_answer = TrainingBlockAnswer.objects.get(
            trainee_Training=self.attempt
        )
        make_trainee("eve", make_group("Other group"))
        self.intruder = self.client_class()
        self.intruder.login(username="eve", password=PASSWORD)

    def test_anonymous_users_are_sent_to_login(self):
        self.client.logout()
        for url in (
            self.url("course_list"),
            self.url("course_detail", self.course.id),
            self.url("review_block", self.attempt.id),
        ):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse("userApp:signup"), response.url)

    def test_course_of_another_group_is_hidden(self):
        self.assertNotContains(
            self.intruder.get(self.url("course_list")), "Sonification 101"
        )
        response = self.intruder.get(self.url("course_detail", self.course.id))
        self.assertRedirects(
            response, self.url("course_list"), fetch_redirect_response=False
        )

    def test_course_of_another_group_cannot_be_attempted(self):
        self.intruder.get(self.url("block_deploy_list", self.course.id, self.t1.id))
        self.intruder.get(
            self.url(
                "forms", self.course.id, self.t1.id, questions_of(self.t1)[0].block_id
            )
        )

        self.assertFalse(
            TraineeTraining.objects.filter(trainee__user__username="eve").exists()
        )

    def test_results_of_other_trainees_are_not_visible(self):
        self.assertEqual(
            self.intruder.get(self.url("review_block", self.attempt.id)).status_code,
            404,
        )
        self.assertEqual(
            self.intruder.get(
                self.url("review_deploy", self.block_answer.id)
            ).status_code,
            404,
        )
        self.assertEqual(
            self.intruder.post(
                self.url("review_deploy", self.block_answer.id)
            ).status_code,
            404,
        )
        self.assertEqual(
            self.intruder.get(
                self.url("review_list_tt", self.course.id, self.t1.id)
            ).status_code,
            404,
        )

    def test_an_in_progress_attempt_cannot_be_reviewed(self):
        self.client.get(self.url("block_deploy_list", self.course.id, self.t2.id))
        in_progress = self.attempts(self.t2).get()

        self.assertEqual(
            self.client.get(self.url("review_block", in_progress.id)).status_code, 404
        )

    def test_comments_require_access_and_a_finished_attempt(self):
        payload = {
            "course_rating": "interesting",
            "training_method": "novel",
            "explanations": "very_useful",
            "stars": "3",
        }

        self.assertEqual(
            self.intruder.post(
                self.url("comment", self.course.id, self.t1.id), payload
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(
                self.url("comment", self.course.id, self.t2.id), payload
            ).status_code,
            404,
        )
        self.client.post(self.url("comment", self.course.id, self.t1.id), payload)

        self.assertEqual(
            list(Comment.objects.values_list("trainee__user__username", flat=True)),
            ["ana"],
        )

    def test_user_without_trainee_profile_is_redirected_home(self):
        from django.contrib.auth.models import User

        User.objects.create_user("staffonly", password=PASSWORD)
        client = self.client_class()
        client.login(username="staffonly", password=PASSWORD)

        response = client.get(self.url("block_deploy_list", self.course.id, self.t1.id))

        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)
