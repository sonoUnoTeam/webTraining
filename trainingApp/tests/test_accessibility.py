"""
Accesibilidad de las páginas: idioma del documento, título propio por página y un único <main>.
"""

import re

from django.test import TestCase
from django.urls import reverse
from django.utils import translation

from trainingApp.models import Choice

from .factories import (
    PASSWORD,
    make_course,
    make_group,
    make_trainee,
    make_training,
    questions_of,
    simple_static_storage,
)


def page_title(response):
    return (
        re.search(r"<title>(.*?)</title>", response.content.decode(), re.DOTALL)
        .group(1)
        .strip()
    )


@simple_static_storage
class DocumentLanguageTests(TestCase):
    def test_html_lang_follows_the_active_language(self):
        for language in ("en", "es"):
            with self.subTest(language=language):
                response = self.client.get(f"/{language}/")
                self.assertContains(response, f'<html lang="{language}">')

    def test_skip_link_points_to_the_only_main(self):
        response = self.client.get("/es/")
        html = response.content.decode()
        self.assertContains(response, 'href="#contenido"')
        self.assertContains(response, "Saltar al contenido principal")
        self.assertEqual(html.count("<main"), 1)
        self.assertIn('<main id="contenido"', html)

    def test_pages_without_session_have_their_own_title(self):
        self.assertEqual(page_title(self.client.get("/en/")), "Home · sonoTrainings")
        self.assertEqual(
            page_title(self.client.get("/es/userApp/signin/")),
            "Acceder · sonoTrainings",
        )


@simple_static_storage
class TrainingPageTitleTests(TestCase):
    def setUp(self):
        group = make_group()
        make_trainee("ana", group)
        self.training = make_training("Ruido", questions_per_block=8)
        self.course = make_course("Sonification 101", [self.training], groups=[group])
        self.client.login(username="ana", password=PASSWORD)

    def url(self, language, name, *args):
        with translation.override(language):
            return reverse(f"trainingApp:{name}", args=args)

    def test_logged_in_pages_render_and_title_the_block_list(self):
        response = self.client.get(
            self.url("en", "block_deploy_list", self.course.id, self.training.id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(page_title(response), "Blocks · Ruido · sonoTrainings")
        self.assertEqual(response.content.decode().count("<main"), 1)

    def test_question_title_says_which_question_of_how_many(self):
        questions = questions_of(self.training)
        block_id = questions[0].block_id
        self.client.get(
            self.url("en", "block_deploy_list", self.course.id, self.training.id)
        )
        for question in questions[:2]:
            right = Choice.objects.get(deploy=question, correctChoice=True)
            self.client.post(
                self.url("en", "forms", self.course.id, self.training.id, block_id),
                {"selectedChoice": right.id},
            )

        title_en = page_title(
            self.client.get(
                self.url("en", "forms", self.course.id, self.training.id, block_id)
            )
        )
        title_es = page_title(
            self.client.get(
                self.url("es", "forms", self.course.id, self.training.id, block_id)
            )
        )
        self.assertEqual(title_en, "Question 3 of 8 · Ruido B1 · sonoTrainings")
        self.assertEqual(title_es, "Pregunta 3 de 8 · Ruido B1 · sonoTrainings")

    def test_title_is_not_repeated_inside_the_page(self):
        response = self.client.get(self.url("en", "tutorial"))
        # El bloque title no debe imprimirse también dentro del contenido
        before_h1 = response.content.decode().split("<main", 1)[1].split("<h1", 1)[0]
        self.assertNotIn("Tutorial", re.sub(r"<[^>]+>", " ", before_h1))
        self.assertEqual(page_title(response), "Tutorial · sonoTrainings")
