from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class JWTAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='jwt-developer',
            email='jwt-developer@example.test',
            password='safe-test-password-123',
        )

    def obtain_tokens(self, password='safe-test-password-123'):
        return self.client.post(
            reverse('jwt_token_obtain'),
            {'username': self.user.username, 'password': password},
            format='json',
        )

    def test_protected_current_user_requires_a_valid_access_token(self):
        response = self.client.get(reverse('jwt_current_user'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_authenticates_current_user_endpoint(self):
        token_response = self.obtain_tokens()
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', token_response.data)
        self.assertIn('refresh', token_response.data)

        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token_response.data["access"]}'
        )
        response = self.client.get(reverse('jwt_current_user'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'id': self.user.pk,
            'username': self.user.username,
            'email': self.user.email,
        })

    def test_invalid_password_does_not_issue_tokens(self):
        response = self.obtain_tokens(password='incorrect-password')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)

    def test_password_change_revokes_existing_access_token(self):
        token_response = self.obtain_tokens()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {token_response.data["access"]}'
        )

        self.user.set_password('new-safe-test-password-456')
        self.user.save(update_fields=['password'])
        response = self.client.get(reverse('jwt_current_user'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rotates_token_and_blacklists_previous_refresh(self):
        token_response = self.obtain_tokens()
        old_refresh = token_response.data['refresh']

        refresh_response = self.client.post(
            reverse('jwt_token_refresh'),
            {'refresh': old_refresh},
            format='json',
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn('access', refresh_response.data)
        self.assertNotEqual(refresh_response.data['refresh'], old_refresh)

        old_refresh_response = self.client.post(
            reverse('jwt_token_refresh'),
            {'refresh': old_refresh},
            format='json',
        )
        self.assertEqual(
            old_refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        blacklist_response = self.client.post(
            reverse('jwt_token_blacklist'),
            {'refresh': refresh_response.data['refresh']},
            format='json',
        )
        self.assertEqual(blacklist_response.status_code, status.HTTP_200_OK)

        revoked_refresh_response = self.client.post(
            reverse('jwt_token_refresh'),
            {'refresh': refresh_response.data['refresh']},
            format='json',
        )
        self.assertEqual(
            revoked_refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
