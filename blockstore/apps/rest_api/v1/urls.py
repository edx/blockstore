""" API v1 URLs. """

from django.conf.urls import url, include

from ..routers import DefaultRouter
from .views.bundles import BundleViewSet, BundleVersionViewSet
from .views.collections import CollectionViewSet
from .views.drafts import DraftViewSet

app_name = 'blockstore'

root_router = DefaultRouter(trailing_slash=False)

root_router.register(r'bundles', BundleViewSet)
root_router.register(r'bundle_versions', BundleVersionViewSet)
root_router.register(r'collections', CollectionViewSet)
root_router.register(r'drafts', DraftViewSet)

urlpatterns = [
    url(r'^', include(root_router.urls)),
]
