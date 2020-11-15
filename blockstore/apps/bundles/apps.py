""" AppConfig for bundles app. """

from django.apps import AppConfig


class BundlesConfig(AppConfig):
    name = 'blockstore.apps.bundles'
    label = 'blockstore_apps_bundles'
    verbose_name = "Blockstore Bundles"
