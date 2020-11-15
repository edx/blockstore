"""
Django Rest Framework Permissions/Authorization classes for Blockstore's API
"""
from rest_framework import permissions


class IsSuperUserOrAuthorizedApplication(permissions.BasePermission):
    """
    DRF Permissions class that prevents any usage of the API unless
    * The user is authenticated as a django superuser (is_superuser=True)
    or
    * The user is authenticated as a service user account with a valid
      rest_framework.authtoken.models.Token associated. This is meant to be used
      by other applications like the Open edX LMS which use this API via a
      service user account. Tokens can be created at /admin/authtoken/token/

    Blockstore does not handle detailed (object-level/bundle-level)
    authorization because it relies on many details (enrollment, due dates,
    cohorts, etc.) that Blockstore is not aware of. Instead, applications like
    the Open edX LMS have full access to Blockstore and are responsible for
    providing a limited subset of Blockstore functionality to authorized users
    via their own API or by partially proxying the Blockstore API.
    """
    message = 'Only administrators or authorized app service user accounts may use this API.'

    def has_permission(self, request, view):
        """
        Check if the given request may proceed.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            # Superusers are always allowed to do anything
            return True
        if request.auth and request.user.auth_token:
            # This is a service user account for an app like the LMS.
            # It's allowed to do anything using the REST API.
            return True
        # Nobody else is allowed to use the API:
        return False
