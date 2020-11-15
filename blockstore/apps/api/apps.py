""" AppConfig for API app. """

from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = 'blockstore.apps.api'
    label = 'blockstore_apps_api'
    verbose_name = "Blockstore API"
