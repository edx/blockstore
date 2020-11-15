"""
Serializers for Collections.
"""

from rest_framework import serializers
from blockstore.apps.bundles.models import Collection
from ... import relations


class CollectionSerializer(serializers.HyperlinkedModelSerializer):
    """
    Serializer for the Collection model.
    """

    class Meta:

        model = Collection

        fields = (
            'title',
            'url',
            'uuid',
        )

    url = relations.HyperlinkedIdentityField(
        lookup_field='uuid',
        lookup_url_kwarg='uuid',
        view_name='api:v1:collection-detail',
    )
