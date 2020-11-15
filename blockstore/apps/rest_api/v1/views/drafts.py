"""
Views for working with Drafts

All Bundle content is created via Drafts.

Draft Workflow Overview
=======================

Step 1: Client Creates a Bundle, by POSTing to the Bundles resource.

Drafts are tied to a Bundle, and the Bundle must exist before a Draft can be
made for it. Once a Bundle exists, any number of Drafts can be created for it.

There are two envisioned scenarios for Drafts:

* Long lived Drafts used by applications like Studio, shared by many users. In
that case, Studio would create a "studio_draft" for its own use, and that Draft
would never be deleted (commits would update the Draft).
* Short-lived Drafts that exist as temporary staging areas and are deleted
afterwards (e.g. scripts).

Step 2: Create a Draft with POST to Drafts resource.

The minimum information needed to create a Draft is to have a Bundle and a name.
When a Draft is created, it will point to the most recent BundleVersion's
Snapshot as a starting point. If no BundleVersion exists yet, then the
`base_snapshot` will be None. The `name` must be unique for a given Bundle.

Step 3: Edit Draft with PATCH to Draft Resource

Successive edits to the Draft can be done by PATCHing specific files. Multiple
files can be written to at the same time.

Step 4: Commit Draft with POST using Draft Commit endpoint

When you commit a Draft, you're asking for a new BundleVersion to be created
from the contents of your Draft. You can optionally include a list of files to
commit if you don't want the entire Draft turned into a Snapshot. The Draft is
then updated so that its `base_snapshot` points to the new Snapshot it created.

TODOs
=====

1. Have to test for large courses, to see if commits have to be asynchronous.
2. In the future, we may want to separate Snapshot creation from BundleVersion
   creation more explicitly so that we can update multiple BundleVersions in the
   same transaction (this isn't currently necessary since a Course is a single
   Bundle).
"""
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.reverse import reverse

from blockstore.apps.bundles.links import LinkCycleError
from blockstore.apps.bundles.store import DraftRepo, SnapshotRepo
from blockstore.apps.bundles.models import BundleVersion, Draft
from ..serializers.drafts import (
    DraftFileUpdateSerializer,
    DraftSerializer,
    DraftWithFileDataSerializer,
)


class DraftViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Drafts. All Bundle Content comes from committing Drafts.

    list:
    Get a list of Drafts (no file data)

    create:
    Create a new Draft.

    retrieve:
    Get a single Draft (with file data)
    """
    queryset = Draft.objects.all().select_related('bundle')
    lookup_field = 'uuid'
    page_size = 20
    http_method_names = ['get', 'head', 'options', 'patch', 'post', 'delete']

    def get_serializer_class(self):
        """
        Return a more compact serializer for list views than detail views.

        The `retreve` method (GET of a single Draft) yields full file metadata
        details, but we can't support that in list views for performance reasons
        as this metadata may grow very large when storing entire courses.
        """
        if self.action == 'retrieve':
            return DraftWithFileDataSerializer
        # Generic model serializer is sufficience for other views.
        return DraftSerializer

    def partial_update(self, request, uuid):
        """
        Create, update, and delete files in a Draft.

        The data payload in the request should be a JSON dictionary with file
        paths as keys and base64 encoded payloads as values. A null value means
        that path should be deleted.

        PATCH is a bit unusual for this resource in that the only thing you can
        patch are file data. You cannot change the draft name or the Bundle it
        belongs to, and the only way to update the `base_snapshot` is to commit
        the Draft.

        There is intentionally no PUT support for file data, for a few reasons:

        1. We can't guarantee the semantics of a PUT against a concurrent PATCH,
        particularly for large numbers of files. Our files are in an object
        store that do not support multi-file transactions. We can't really even
        guarantee it for multiple concurrent PATCHes -- there's a possibility of
        a race condition there.

        2. Bundles can become very large, and a PUT might become prohibitively
        large. Having everything as a PATCH lets us set somewhat sane per-PATCH
        request limits and let the client handle the case where we need to do
        multiple requests to make the necessary changes.

        3. It's just simpler to have only one way to update the files.
        """
        serializer = DraftFileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        files_to_write = serializer.validated_data['files']
        dependencies_to_write = serializer.validated_data['links']

        draft_repo = DraftRepo(SnapshotRepo())
        try:
            draft_repo.update(uuid, files_to_write, dependencies_to_write)
        except LinkCycleError:
            raise serializers.ValidationError("Link cycle detected: Cannot create draft.")

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def commit(self, request, uuid):
        """
        Commit the Draft and create a new BundleVersion that points to it.

        In the future, we may want to separate these two steps so that we can
        create multiple BundleVersions at once in a single transaction, however
        given our modeling conventions of a course being in a single Bundle,
        that's not something that we need to implement immediately.

        We currently return a summary of the things that were created, however
        we may need to rethink this interface if the commit process is going to
        take so long as to require async processing.

        TODO: Test with large Bundles.
        """
        draft_repo = DraftRepo(SnapshotRepo())
        staged_draft = draft_repo.get(uuid)

        # Is this the appropriate response when trying to commit a Draft with
        # no changes?
        if not staged_draft.files_to_overwrite and not staged_draft.links_to_overwrite:
            raise serializers.ValidationError("Draft has no changes to commit.")

        new_snapshot, _updated_draft = draft_repo.commit(staged_draft)
        new_bv = BundleVersion.create_new_version(
            new_snapshot.bundle_uuid, new_snapshot.hash_digest
        )

        # This is a placeholder response. May need to revisit after trying
        # some large commits.
        result = {
            'bundle_version': reverse(
                'api:v1:bundleversion-detail',
                args=[new_snapshot.bundle_uuid, new_bv.version_num],
                request=request,
            ),
            'updated_draft': reverse(
                'api:v1:draft-detail',
                args=[uuid],
                request=request,
            )
        }
        return Response(result, status=status.HTTP_201_CREATED)

    def destroy(self, request, uuid):
        """
        This removes any files that were staged along with the database entry.
        """
        draft_repo = DraftRepo(SnapshotRepo())
        draft_repo.delete(uuid)
        return super().destroy(request, uuid)  # pylint: disable=no-member
