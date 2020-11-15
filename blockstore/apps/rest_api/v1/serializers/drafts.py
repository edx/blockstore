"""
Serializers for Draft (the Django Model) and StagedDraft (the repo primitive)

This is a bit unusual in that we have slightly different serializers for list
vs. detail, and an entirely different one for writes.
"""
import base64
import binascii
import uuid

from django.core.files.base import ContentFile
from rest_framework import relations, serializers
from rest_framework.serializers import ValidationError

from blockstore.apps.bundles.links import Dependency
from blockstore.apps.bundles.models import Bundle, BundleVersion, Draft
from blockstore.apps.bundles.store import DraftRepo, SnapshotRepo, is_safe_file_path


class DraftSerializer(serializers.ModelSerializer):
    """Serializer for Drafts, appropriate for list views. No files metadata."""
    class Meta:
        model = Draft
        queryset = Draft.objects.all().select_related('bundle')
        fields = ('uuid', 'url', 'bundle', 'bundle_uuid', 'name')

    url = relations.HyperlinkedIdentityField(
        lookup_field='uuid',
        view_name='api:v1:draft-detail',
    )

    bundle = relations.HyperlinkedRelatedField(
        lookup_field='uuid',
        lookup_url_kwarg='bundle_uuid',
        view_name='api:v1:bundle-detail',
        read_only=True,
    )

    bundle_uuid = relations.SlugRelatedField(
        source='bundle',
        slug_field='uuid',
        queryset=Bundle.objects.all(),
    )


class DraftWithFileDataSerializer(DraftSerializer):
    """
    DraftSerializer subclass that adds files metadata.

    This payload could become very large, so this serializer should not be used
    for list views.
    """
    class Meta:
        model = Draft
        queryset = Draft.objects.all()
        fields = DraftSerializer.Meta.fields + ('staged_draft',)

    class StagedDraftField(serializers.Field):
        """Read-only field for a StagedDraft."""

        def _expand_url(self, url):
            """Ensure that the given URL is an absolute URL"""
            if not url.startswith('http'):
                url = self.context['request'].build_absolute_uri(url)
            return url

        def to_representation(self, value):
            """StagedDraft JSON serialization."""
            staged_draft = value
            draft_repo = DraftRepo(SnapshotRepo())
            if staged_draft.base_snapshot is None:
                base_snapshot_repr = None
            else:
                base_snapshot_repr = staged_draft.base_snapshot.hash_digest.hex()

            basic_info = {
                'base_snapshot': base_snapshot_repr,
                'created_at': staged_draft.created_at,
                'updated_at': staged_draft.updated_at,
            }
            basic_info['files'] = {
                path: {
                    "url": self._expand_url(draft_repo.url(staged_draft, path)),
                    "size": file_info.size,
                    "hash_digest": file_info.hash_digest.hex(),
                    "modified": path in staged_draft.files_to_overwrite
                }
                for path, file_info in staged_draft.composed_files().items()
            }
            basic_info['links'] = {
                link.name: {
                    "direct": self._serialized_dep(link.direct_dependency),
                    "indirect": [
                        self._serialized_dep(dep)
                        for dep in link.indirect_dependencies
                    ],
                    "modified": link.name in staged_draft.links_to_overwrite.modified_set
                }
                for link in staged_draft.composed_links()
                if link.direct_dependency
            }

            return basic_info

        def _serialized_dep(self, dependency):
            return {
                "bundle_uuid": dependency.bundle_uuid,
                "version": dependency.version,
                "snapshot_digest": dependency.snapshot_digest.hex(),
            }

        def to_internal_value(self, _data):
            raise NotImplementedError()

    staged_draft = StagedDraftField()


class DraftFileUpdateSerializer(serializers.BaseSerializer):
    """Write-only serializer for Draft file updates."""
    # pylint: disable=abstract-method

    def to_internal_value(self, data):
        """
        Convert file names -> b64 strings into file names -> ContentFiles.

        `data` has two dicts:
          1. 'files' - file names to base64 encoded data representations.
          2. 'links' - snapshots that we have as dependencies.
        """
        files = self._parse_files(data.get('files', {}))
        links = self._parse_links(data.get('links', {}))

        return {
            'files': files,
            'links': links,
        }

    def _parse_files(self, files):
        """Parse file dict from client PATCH JSON."""
        for file_name in files:
            if not is_safe_file_path(file_name):
                raise serializers.ValidationError(f'"{file_name}" is not a valid file name')

        def _parse_file_data(file_path, b64_encoded_str):
            """Parse base64 encoded file data into ContentFile if valid."""
            # If the value is None, it means "delete this file".
            if b64_encoded_str is None:
                return None

            # Otherwise, return the base64 representation
            try:
                binary_file_data = base64.b64decode(b64_encoded_str)
            except binascii.Error as err:
                raise ValidationError(
                    f"Error decoding file {file_path}: {err} (check if it's base64 encoded?)"
                )
            return ContentFile(binary_file_data)

        # TODO: make sure they can't write outside the draft space
        return {
            file_path: _parse_file_data(file_path, file_data)
            for file_path, file_data in files.items()
        }

    def _parse_links(self, links):
        """
        Parse link information supplied by the user.

        We expect links to come to us in a format that looks like:

        "links": {
            "algebra_problem_bank": {
                "bundle_uuid": "408d549c-2ebf-4bae-9350-d72109a54163",
                "version": 1
            },
            "link_to_delete": None
        }

        Once we have this information, we need to verify that the linked Bundles
        actually exist, and then return a dict of link names to direct
        Dependencies.
        """
        names_to_dependencies = {}
        for name, bv_info in links.items():
            # If bv_info is None, we want to delete this Link (set to None)
            if name and bv_info is None:
                names_to_dependencies[name] = None
                continue

            # Check that our fields exist.
            if 'bundle_uuid' not in bv_info:
                raise ValidationError(
                    f"Link {name} has no 'bundle_uuid' specified."
                )
            if 'version' not in bv_info:
                raise ValidationError(
                    f"Link {name} has no 'version' specified."
                )

            # Check that our field values make sense (proper types).
            if not isinstance(name, str):
                raise ValidationError(
                    f"{name} is not a valid Link name."
                )
            version = bv_info['version']
            # Python's bool is a subclass of int
            if (not isinstance(version, int)) or isinstance(version, bool):
                raise ValidationError(
                    f"Link {name}: {version} must be an integer."
                )
            try:
                bundle_uuid_str = bv_info['bundle_uuid']
                bundle_uuid = uuid.UUID(bundle_uuid_str)
            except ValueError:
                raise ValidationError(
                    f"Link {name}: {bundle_uuid_str} is not a valid UUID."
                )

            # At this point it's syntactically correct, but it might be pointing
            # to a BundleVersion that doesn't really exist.
            bundle_version = BundleVersion.get_bundle_version(
                bundle_uuid=bundle_uuid,
                version_num=version,
            )
            if not bundle_version:
                raise ValidationError(
                        "BundleVersion ({}, {}) referenced in Link {} does not exist."
                        .format(bundle_uuid, version, name)
                )

            # If everything checks out, create a Dependency. We can't make a
            # Link yet because we don't know the indirect Dependencies (i.e.
            # this Dependency's dependencies).
            names_to_dependencies[name] = Dependency(
                bundle_uuid=bundle_uuid,
                version=version,
                snapshot_digest=bundle_version.snapshot_digest_bytes,
            )

        return names_to_dependencies
