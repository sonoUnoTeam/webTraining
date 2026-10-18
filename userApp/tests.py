"""Tests de integración de cuentas: registro, login/logout, perfil, contraseñas y signals."""
import smtplib
from unittest import mock

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.messages import get_messages
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from trainingApp.tests.factories import PASSWORD, make_group, make_trainee, simple_static_storage
from userApp.models import Trainee

NEW_PASSWORD = 'Another-Strong-Pass-2026'


def messages_of(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


@simple_static_storage
class SignupTests(TestCase):
    def payload(self, **overrides):
        data = {
            'username': 'newbie', 'first_name': 'New', 'last_name': 'Trainee', 'email': 'newbie@example.com',
            'password1': PASSWORD, 'password2': PASSWORD,
            'age': 30, 'educationalLevel': 'University', 'occupation': 'Astronomer',
        }
        data.update(overrides)
        return data

    def test_signup_creates_a_trainee_in_the_default_group_and_logs_in(self):
        response = self.client.post(reverse('userApp:signup'), self.payload())

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        trainee = Trainee.objects.get(user__username='newbie')
        self.assertEqual((trainee.age, trainee.educationalLevel, trainee.occupation), (30, 'University', 'Astronomer'))
        self.assertEqual(trainee.group.name_group, 'Group Defect')
        self.assertEqual(int(self.client.session['_auth_user_id']), trainee.user.id)

    def test_signup_rejects_an_email_already_registered(self):
        make_trainee('existing', make_group())

        response = self.client.post(reverse('userApp:signup'), self.payload(email='EXISTING@example.com'))

        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_signup_rejects_mismatched_passwords(self):
        response = self.client.post(reverse('userApp:signup'), self.payload(password2='different-Pass-1'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newbie').exists())

    def test_signup_page_renders(self):
        self.assertEqual(self.client.get(reverse('userApp:signup')).status_code, 200)


@simple_static_storage
class SigninTests(TestCase):
    def setUp(self):
        make_trainee('ana', make_group())

    def test_valid_credentials_go_to_the_course_list(self):
        response = self.client.post(reverse('userApp:signin'), {'username': 'ana', 'password': PASSWORD})

        self.assertRedirects(response, reverse('trainingApp:course_list'), fetch_redirect_response=False)

    def test_invalid_credentials_show_an_error(self):
        response = self.client.post(reverse('userApp:signin'), {'username': 'ana', 'password': 'wrong'})

        self.assertEqual(response.status_code, 200)
        self.assertIn('Username or Password incorrect', messages_of(response))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout(self):
        self.client.login(username='ana', password=PASSWORD)

        response = self.client.get(reverse('userApp:logout'))

        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)
        self.assertNotIn('_auth_user_id', self.client.session)


@simple_static_storage
class ProfileTests(TestCase):
    def setUp(self):
        self.trainee = make_trainee('ana', make_group())
        make_trainee('bob', self.trainee.group)
        self.client.login(username='ana', password=PASSWORD)

    def test_profile_of_another_user_redirects_to_own(self):
        response = self.client.get(reverse('userApp:profile', args=['bob']))

        self.assertRedirects(response, reverse('userApp:profile', args=['ana']), fetch_redirect_response=False)

    def test_update_personal_data(self):
        self.client.post(reverse('userApp:profile', args=['ana']), {
            'update_user': '1', 'username': 'ana', 'first_name': 'Ana', 'last_name': 'García', 'email': 'ana.g@example.com',
        })

        user = User.objects.get(username='ana')
        self.assertEqual((user.first_name, user.last_name, user.email), ('Ana', 'García', 'ana.g@example.com'))

    def test_update_trainee_data(self):
        self.client.post(reverse('userApp:profile', args=['ana']), {
            'update_trainee': '1', 'age': 41, 'educationalLevel': 'Doctor', 'occupation': 'Researcher',
        })

        self.trainee.refresh_from_db()
        self.assertEqual((self.trainee.age, self.trainee.educationalLevel, self.trainee.occupation), (41, 'Doctor', 'Researcher'))

    def test_email_of_another_user_is_rejected(self):
        response = self.client.post(reverse('userApp:profile', args=['ana']), {
            'update_user': '1', 'username': 'ana', 'first_name': 'Ana', 'last_name': 'X', 'email': 'bob@example.com',
        })

        self.assertIn('email', response.context['userform'].errors)


@simple_static_storage
class PasswordTests(TestCase):
    def setUp(self):
        self.user = make_trainee('ana', make_group()).user

    def test_change_password_while_logged_in(self):
        self.client.login(username='ana', password=PASSWORD)

        response = self.client.post(reverse('userApp:changePassword'), {
            'old_password': PASSWORD, 'new_password1': NEW_PASSWORD, 'new_password2': NEW_PASSWORD,
        })

        self.assertRedirects(response, reverse('userApp:passwordResetDone'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_reset_sends_an_email_to_a_registered_address(self):
        response = self.client.post(reverse('userApp:password_reset'), {'email': 'ana@example.com'})

        self.assertRedirects(response, reverse('userApp:password_reset_done'), fetch_redirect_response=False)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['ana@example.com'])

    def test_reset_smtp_failure_shows_an_error_without_crashing(self):
        with mock.patch('django.core.mail.EmailMultiAlternatives.send', side_effect=smtplib.SMTPException('down')) as send, \
                self.assertLogs('userApp.views', level='ERROR'):
            response = self.client.post(reverse('userApp:password_reset'), {'email': 'ana@example.com'})

        self.assertRedirects(response, reverse('userApp:password_reset_done'), fetch_redirect_response=False)
        self.assertEqual(send.call_count, 1)
        self.assertIn('An error occurred while trying to send the email, contact the administrator.', messages_of(response))

    def test_reset_for_an_unknown_email_sends_nothing(self):
        response = self.client.post(reverse('userApp:password_reset'), {'email': 'nobody@example.com'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_link_sets_a_new_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        # El enlace con token redirige a una URL sin token (no se filtra por Referer)
        response = self.client.get(reverse('userApp:password_reset_confirm', args=[uid, token]))
        set_password_url = reverse('userApp:password_reset_confirm', args=[uid, 'set-password'])
        self.assertRedirects(response, set_password_url, fetch_redirect_response=False)

        response = self.client.post(set_password_url, {'new_password1': NEW_PASSWORD, 'new_password2': NEW_PASSWORD})

        self.assertRedirects(response, reverse('userApp:password_reset_complete'), fetch_redirect_response=False)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_invalid_reset_link_does_not_show_the_form(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        response = self.client.get(reverse('userApp:password_reset_confirm', args=[uid, 'bad-token']))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['validlink'])


class SuperuserSignalTests(TestCase):
    def test_superuser_gets_a_trainee_in_the_default_group(self):
        user = User.objects.create_superuser('root', 'root@example.com', PASSWORD)

        trainee = Trainee.objects.get(user=user)
        self.assertEqual(trainee.group.name_group, 'Group Defect')
        self.assertEqual(trainee.occupation, 'Administrator')

    def test_regular_users_do_not_get_a_trainee_automatically(self):
        user = User.objects.create_user('plain', password=PASSWORD)

        self.assertFalse(Trainee.objects.filter(user=user).exists())
