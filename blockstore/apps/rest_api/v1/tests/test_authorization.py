"""
Tests to check that the API is only accessible by superusers or authorized
application service users. See
    blockstore.apps.rest_api.permissions.IsSuperUserOrAuthorizedApplication
for details.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()


class ApiAuthorizationTestCase(TestCase):
    """
    Check that the API authentication/authorization is working.
    """

    basic_read_urls = (
        # API endpoints that support a GET requests and require no parameters
        '/api/v1/collections',
        '/api/v1/bundles',
        '/api/v1/drafts',
    )

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def check_endpoints(self, *expected_statuses):
        """
        Check that various API endpoints return the expected status

        We don't exhaustively test all endpoints, because auth is configured
        globally for all endpoints using DEFAULT_AUTHENTICATION_CLASSES and
        DEFAULT_PERMISSION_CLASSES. So we just test a few simple endpoints to
        verify that those defaults are applied.
        """
        for url in self.basic_read_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, expected_statuses)
        create_response = self.client.post('/api/v1/collections', data={'title': "Test Collection"})
        self.assertIn(create_response.status_code, expected_statuses)

    def test_unauthenticated_user_cannot_read(self):
        """
        Verify that an unauthenticated user cannot read from API endpoints
        """
        self.check_endpoints(status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_read(self):
        """
        Verify that an authenticated non-superuser cannot read from API endpoints
        """
        user = User.objects.create(username='test')
        self.client.force_login(user)
        self.check_endpoints(status.HTTP_403_FORBIDDEN)

    def test_superuser_can_access(self):
        """
        Verify that a superuser account _can_ use the API
        """
        user = User.objects.create(username='super', is_superuser=True)
        self.client.force_login(user)
        self.check_endpoints(status.HTTP_200_OK, status.HTTP_201_CREATED)

    def test_service_user_can_access(self):
        """
        Test that an external application's service user with a valid auth token
        header can use the API.
        """
        test_user = User.objects.create(username='test-service-user')
        token = Token.objects.create(user=test_user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        self.check_endpoints(status.HTTP_200_OK, status.HTTP_201_CREATED)
