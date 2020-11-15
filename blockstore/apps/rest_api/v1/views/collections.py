"""
Views for Collections.
"""

from rest_framework import viewsets

from blockstore.apps.bundles.models import Collection

from ...constants import UUID4_REGEX
from ..serializers.collections import CollectionSerializer


class CollectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Collection model.
    """
    lookup_field = 'uuid'
    lookup_url_kwarg = 'uuid'
    lookup_value_regex = UUID4_REGEX

    queryset = Collection.objects.all()
    serializer_class = CollectionSerializer
