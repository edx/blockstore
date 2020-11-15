"""
Serializers for Bundles and BundleVersions.
"""
from django.core.validators import validate_unicode_slug
from rest_framework import serializers
from rest_framework.relations import SlugRelatedField
from rest_framework.reverse import reverse

from blockstore.apps.bundles.models import Bundle, BundleVersion, Collection
from blockstore.apps.bundles.store import SnapshotRepo
from ... import relations


class BundleSerializer(serializers.ModelSerializer):
    """
    Serializer for the Bundle model.
    """
    class Meta:
        model = Bundle
        fields = (
            'collection',
            'collection_uuid',
            'description',
            'drafts',
            'slug',
            'title',
            'url',
            'uuid',
            'versions',
        )

    class DraftLinksField(serializers.Field):
        """Read-only field that serializes to a {draft.name : URL} mapping."""

        def to_representation(self, value):
            """A dict of draft names to URLs."""
            drafts = value
            request = self.context['request']
            return {
                draft.name: reverse(
                    'api:v1:draft-detail', args=[draft.uuid], request=request
                )
                for draft in drafts.all()
            }

        def to_internal_value(self, _data):
            raise NotImplementedError()

    collection = relations.HyperlinkedRelatedField(
        lookup_field='uuid',
        lookup_url_kwarg='uuid',
        view_name='api:v1:collection-detail',
        read_only=True,
    )

    collection_uuid = SlugRelatedField(
        source='collection',
        slug_field='uuid',
        queryset=Collection.objects.all(),
    )

    # DRF slug fields don't support unicode by default, so override it:
    slug = serializers.CharField(validators=(validate_unicode_slug, ))

    url = relations.HyperlinkedIdentityField(
        lookup_field='uuid',
        lookup_url_kwarg='bundle_uuid',
        view_name='api:v1:bundle-detail',
    )

    drafts = DraftLinksField(read_only=True)

    versions = relations.HyperlinkedRelatedField(
        lookup_fields=['bundle__uuid', 'version_num'],
        lookup_url_kwargs=['bundle_uuid', 'version_num'],
        many=True,
        read_only=True,
        view_name='api:v1:bundleversion-detail',
    )


class BundleVersionSerializer(serializers.ModelSerializer):
    """Serializer for the BundleVersion model."""

    class Meta:
        model = BundleVersion
        fields = (
            'bundle',
            'bundle_uuid',
            'change_description',
            'url',
            'version_num',
        )

    bundle = relations.HyperlinkedRelatedField(
        lookup_field='uuid',
        lookup_url_kwarg='bundle_uuid',
        view_name='api:v1:bundle-detail',
        read_only=True,
    )

    bundle_uuid = SlugRelatedField(
        source='bundle',
        slug_field='uuid',
        read_only=True,
    )

    url = relations.HyperlinkedIdentityField(
        lookup_fields=['bundle__uuid', 'version_num'],
        lookup_url_kwargs=['bundle_uuid', 'version_num'],
        view_name='api:v1:bundleversion-detail',
    )


class BundleVersionWithFileDataSerializer(BundleVersionSerializer):
    """
    Like BundleVersionSerializer, but with Snapshot file details.

    For performance reasons, this serializer should only be used in detail
    views. The snapshot metadata could grow very large for some Bundles.
    """
    class Meta:
        model = BundleVersion
        fields = BundleVersionSerializer.Meta.fields + ('snapshot',)

    class SnapshotField(serializers.Field):
        """Helper read-only field for a Snapshot."""
        def _serialized_dep(self, dependency):
            return {
                "bundle_uuid": dependency.bundle_uuid,
                "version": dependency.version,
                "snapshot_digest": dependency.snapshot_digest.hex(),
            }

        def _expand_url(self, url):
            """Ensure that the given URL is an absolute URL"""
            if not url.startswith('http'):
                url = self.context['request'].build_absolute_uri(url)
            return url

        def to_representation(self, value):
            """Snapshot JSON serialization."""
            snapshot = value
            snapshot_repo = SnapshotRepo()
            info = {
                'hash_digest': snapshot.hash_digest.hex(),
                'created_at': snapshot.created_at,
            }

            info['files'] = {
                path: {
                    "url": self._expand_url(snapshot_repo.url(snapshot, path)),
                    "size": file_info.size,
                    "hash_digest": file_info.hash_digest.hex(),
                }
                for path, file_info in snapshot.files.items()
            }

            info['links'] = {
                link.name: {
                    "direct": self._serialized_dep(link.direct_dependency),
                    "indirect": [
                        self._serialized_dep(dep)
                        for dep in link.indirect_dependencies
                    ]
                }
                for link in snapshot.links
            }

            return info

        def to_internal_value(self, _data):
            raise NotImplementedError()

    snapshot = SnapshotField()
