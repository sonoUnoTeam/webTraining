"""Tests de configuración del proyecto: helpers de entorno y rutas globales."""
import os
import tempfile
from unittest import mock

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase
from django.urls import resolve
from django.utils import translation
from django.views.static import serve

from webTraining import settings as project_settings


class EnvHelpersTests(SimpleTestCase):
    def test_env_bool(self):
        for value in ('True', 'true', '1', 'yes', 'ON'):
            with mock.patch.dict('os.environ', {'FLAG': value}):
                self.assertTrue(project_settings.env_bool('FLAG'), value)
        for value in ('False', '0', 'no', ''):
            with mock.patch.dict('os.environ', {'FLAG': value}):
                self.assertFalse(project_settings.env_bool('FLAG', True), value)

    def test_env_bool_default_when_missing(self):
        with mock.patch.dict('os.environ', {}, clear=True):
            self.assertFalse(project_settings.env_bool('MISSING'))
            self.assertTrue(project_settings.env_bool('MISSING', True))

    def test_env_list_strips_and_skips_empty_items(self):
        with mock.patch.dict('os.environ', {'HOSTS': ' a.com , ,b.org,'}):
            self.assertEqual(project_settings.env_list('HOSTS'), ['a.com', 'b.org'])


class PathSettingsTests(SimpleTestCase):
    def test_filesystem_paths_are_absolute(self):
        # Bajo Apache/mod_wsgi el directorio de trabajo no es el del proyecto: una ruta relativa rompe en producción
        paths = [*settings.TEMPLATES[0]['DIRS'], *settings.STATICFILES_DIRS, *settings.LOCALE_PATHS,
                 settings.STATIC_ROOT, settings.MEDIA_ROOT]
        for path in paths:
            self.assertTrue(os.path.isabs(path), path)

    def test_global_templates_resolve_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as other_dir:
            previous = os.getcwd()
            os.chdir(other_dir)
            try:
                for name in ('base.html', 'home.html', 'navbar.html', 'footer.html'):
                    get_template(name)
            finally:
                os.chdir(previous)


class UrlTests(SimpleTestCase):
    def test_media_is_served_without_language_prefix(self):
        self.assertEqual(resolve('/media/trainingApp/sound/example.mp3').func, serve)

    def test_app_urls_use_language_prefix(self):
        for language in ('en', 'es'):
            with translation.override(language):
                self.assertEqual(resolve(f'/{language}/trainingApp/').url_name, 'course_list')
