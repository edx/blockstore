"""
API Client methods for working with Blockstore bundles and drafts
"""

import base64
from urllib.parse import urlencode
from uuid import UUID

import dateutil.parser
from django.core.exceptions import ImproperlyConfigured
import requests
import six

from blockstore.apps.bundles import models
from blockstore.apps.bundles.links import LinkCycleError
from blockstore.apps.bundles.store import DraftRepo, SnapshotRepo
from blockstore.apps.rest_api.v1.serializers.drafts import (
    DraftFileUpdateSerializer,
    DraftSerializer,
    DraftWithFileDataSerializer,
)


from .models import (
    Bundle,
    Collection,
    Draft,
    BundleFile,
    DraftFile,
    LinkDetails,
    LinkReference,
    DraftLinkDetails,
)
from .exceptions import (
    NotFound,
    CollectionNotFound,
    BundleNotFound,
    DraftNotFound,
    BundleFileNotFound,
)


def _data_from_collection(collection):
    return Collection(uuid=collection.uuid, title=collection.title)


def get_collection(collection_uuid):
    """
    Retrieve metadata about the specified collection

    Raises CollectionNotFound if the collection does not exist
    """
    assert isinstance(collection_uuid, UUID)
    try:
        collection = models.Collection.objects.get(uuid=collection_uuid)
    except models.Collection.DoesNotExist:
        raise CollectionNotFound("Collection {} does not exist.".format(collection_uuid))

    return _data_from_collection(collection)


def create_collection(title):
    """
    Create a new collection.
    """
    collection = models.Collection(
        title=title
    )
    collection.save()

    return _data_from_collection(collection)


def update_collection(collection_uuid, title):
    """
    Update a collection's title
    """
    assert isinstance(collection_uuid, UUID)
    try:
        collection = models.Collection.objects.get(uuid=collection_uuid)
    except models.Collection.DoesNotExist:
        raise CollectionNotFound("Collection {} does not exist.".format(collection_uuid))

    collection.title = title
    collection.save()
    return _data_from_collection(collection)


def delete_collection(collection_uuid):
    """
    Delete a collection
    """
    assert isinstance(collection_uuid, UUID)
    try:
        collection = models.Collection.objects.get(uuid=collection_uuid)
    except models.Collection.DoesNotExist:
        raise CollectionNotFound("Collection {} does not exist.".format(collection_uuid))

    collection.delete()


def _data_from_bundle(bundle):
    latest_bundle_version = bundle.get_bundle_version()
    return Bundle(
        uuid=bundle.uuid,
        title=bundle.title,
        description=bundle.description,
        slug=bundle.slug,
        drafts={draft.name: draft.uuid for draft in bundle.drafts.all()},
        latest_version=latest_bundle_version.version_num if latest_bundle_version else 0,
    )


def get_bundles(uuids=None, text_search=None):
    """
    Get the details of all bundles
    """
    query_params = {}
    if uuids:
        query_params['uuid'] = ','.join(map(str, uuids))
    if text_search:
        query_params['text_search'] = text_search
    version_url = api_url('bundles') + '?' + urlencode(query_params)
    response = api_request('get', version_url)
    # build bundle from response, convert map object to list and return
    return [_bundle_from_response(item) for item in response]


def get_bundle(bundle_uuid):
    """
    Retrieve metadata about the specified bundle

    Raises BundleNotFound if the bundle does not exist
    """
    assert isinstance(bundle_uuid, UUID)
    try:
        bundle = models.Bundle.objects.get(uuid=bundle_uuid)
    except models.Bundle.DoesNotExist:
        raise BundleNotFound("Bundle {} does not exist.".format(bundle_uuid))

    return _data_from_bundle(bundle)


def create_bundle(collection_uuid, slug, title="New Bundle", description=""):
    """
    Create a new bundle.

    Note that description is currently required.
    """
    assert isinstance(collection_uuid, UUID)
    try:
        collection = models.Collection.objects.get(uuid=collection_uuid)
    except models.Collection.DoesNotExist:
        raise CollectionNotFound("Collection {} does not exist.".format(collection_uuid))

    bundle = models.Bundle(
        title=title,
        collection=collection,
        slug=slug,
        description=description,
    )
    bundle.save()
    return _data_from_bundle(bundle)


def update_bundle(bundle_uuid, **fields):
    """
    Update a bundle's title, description, slug, or collection.
    """
    assert isinstance(bundle_uuid, UUID)
    try:
        bundle = models.Bundle.objects.get(uuid=bundle_uuid)
    except models.Bundle.DoesNotExist:
        raise BundleNotFound("Bundle {} does not exist.".format(bundle_uuid))

    data = {}
    # Most validation will be done by Blockstore, so we don't worry too much about data validation
    for str_field in ("title", "description", "slug"):
        if str_field in fields:
            setattr(bundle, str_field, fields.pop(str_field))
    if "collection_uuid" in fields:
        collection_uuid = str(fields.pop("collection_uuid"))
        assert isinstance(collection_uuid, UUID)
        try:
            collection = models.Collection.objects.get(uuid=collection_uuid)
        except models.Collection.DoesNotExist:
            raise CollectionNotFound("Collection {} does not exist.".format(collection_uuid))
        bundle.collection = collection
    if fields:
        raise ValueError("Unexpected extra fields passed to update_bundle: {}".format(fields.keys()))

    bundle.save()
    return _data_from_bundle(bundle)


def delete_bundle(bundle_uuid):
    """
    Delete a bundle
    """
    assert isinstance(bundle_uuid, UUID)
    try:
        bundle = models.Bundle.objects.get(uuid=bundle_uuid)
    except models.Bundle.DoesNotExist:
        raise BundleNotFound("Bundle {} does not exist.".format(bundle_uuid))
    bundle.delete()


def _data_from_draft(draft):
    """
    Given data about a Draft returned by any blockstore REST API, convert it to
    a Draft instance.
    """
    return Draft(
        uuid=draft.uuid,
        bundle_uuid=draft.bundle.uuid,
        name=draft.name,
        updated_at=draft.staged_draft.updated_at,
        files={
            path: DraftFile(
                path=path,
                size=file_info.size,
                url=path,  ## Todo
                hash_digest=file_info.hash_digest,
                modified=path in draft.staged_draft.files_to_overwrite,
            )
            for path, file_info in draft.staged_draft.files.items()
        },
        links={}
        # Todo
        # links={
        #     name: DraftLinkDetails(
        #         name=name,
        #         direct=LinkReference(**link["direct"]),
        #         indirect=[LinkReference(**ind) for ind in link["indirect"]],
        #         modified=link["modified"],
        #     )
        #     for name, link in draft.staged_draft.composed_links.items()
        # }
    )


def get_draft(draft_uuid):
    """
    Retrieve metadata about the specified draft.
    If you don't know the draft's UUID, look it up using get_bundle()
    """
    assert isinstance(draft_uuid, UUID)
    try:
        draft = models.Draft.objects.get(uuid=draft_uuid)
    except models.Draft.DoesNotExist:
        raise DraftNotFound("Draft does not exist: {}".format(draft_uuid))

    return _data_from_draft(draft)


def get_or_create_bundle_draft(bundle_uuid, draft_name):
    """
    Retrieve metadata about the specified draft.
    """
    assert isinstance(bundle_uuid, UUID)
    try:
        bundle = models.Bundle.objects.get(uuid=bundle_uuid)
    except models.Bundle.DoesNotExist:
        raise BundleNotFound("Bundle {} does not exist.".format(bundle_uuid))

    try:
        draft = models.Draft.objects.get(bundle=bundle, name=draft_name)
    except models.Draft.DoesNotExist:
        # The draft doesn't exist yet, so create it:
        draft = models.Draft(
            bundle=bundle,
            name=draft_name,
        )
        draft.save()

    return _data_from_draft(draft)


def commit_draft(draft_uuid):
    """
    Commit all of the pending changes in the draft, creating a new version of
    the associated bundle.

    Does not return any value.
    """
    api_request('post', api_url('drafts', str(draft_uuid), 'commit'))


def delete_draft(draft_uuid):
    """
    Delete the specified draft, removing any staged changes/files/deletes.

    Does not return any value.
    """
    api_request('delete', api_url('drafts', str(draft_uuid)))


def get_bundle_version(bundle_uuid, version_number):
    """
    Get the details of the specified bundle version
    """
    if version_number == 0:
        return None
    version_url = api_url('bundle_versions', str(bundle_uuid) + ',' + str(version_number))
    return api_request('get', version_url)


def get_bundle_version_files(bundle_uuid, version_number):
    """
    Get a list of the files in the specified bundle version
    """
    if version_number == 0:
        return []
    version_info = get_bundle_version(bundle_uuid, version_number)
    return [BundleFile(path=path, **file_metadata) for path, file_metadata in version_info["snapshot"]["files"].items()]


def get_bundle_version_links(bundle_uuid, version_number):
    """
    Get a dictionary of the links in the specified bundle version
    """
    if version_number == 0:
        return {}
    version_info = get_bundle_version(bundle_uuid, version_number)
    return {
        name: LinkDetails(
            name=name,
            direct=LinkReference(**link["direct"]),
            indirect=[LinkReference(**ind) for ind in link["indirect"]],
        )
        for name, link in version_info['snapshot']['links'].items()
    }


def get_bundle_files_dict(bundle_uuid, use_draft=None):
    """
    Get a dict of all the files in the specified bundle.

    Returns a dict where the keys are the paths (strings) and the values are
    BundleFile or DraftFile tuples.
    """
    bundle = get_bundle(bundle_uuid)
    if use_draft and use_draft in bundle.drafts:  # pylint: disable=unsupported-membership-test
        draft_uuid = bundle.drafts[use_draft]  # pylint: disable=unsubscriptable-object
        return get_draft(draft_uuid).files
    elif not bundle.latest_version:
        # This bundle has no versions so definitely does not contain any files
        return {}
    else:
        return {file_meta.path: file_meta for file_meta in get_bundle_version_files(bundle_uuid, bundle.latest_version)}


def get_bundle_files(bundle_uuid, use_draft=None):
    """
    Get an iterator over all the files in the specified bundle or draft.
    """
    return get_bundle_files_dict(bundle_uuid, use_draft).values()


def get_bundle_links(bundle_uuid, use_draft=None):
    """
    Get a dict of all the links in the specified bundle.

    Returns a dict where the keys are the link names (strings) and the values
    are LinkDetails or DraftLinkDetails tuples.
    """
    bundle = get_bundle(bundle_uuid)
    if use_draft and use_draft in bundle.drafts:  # pylint: disable=unsupported-membership-test
        draft_uuid = bundle.drafts[use_draft]  # pylint: disable=unsubscriptable-object
        return get_draft(draft_uuid).links
    elif not bundle.latest_version:
        # This bundle has no versions so definitely does not contain any links
        return {}
    else:
        return get_bundle_version_links(bundle_uuid, bundle.latest_version)


def get_bundle_file_metadata(bundle_uuid, path, use_draft=None):
    """
    Get the metadata of the specified file.
    """
    assert isinstance(bundle_uuid, UUID)
    files_dict = get_bundle_files_dict(bundle_uuid, use_draft=use_draft)
    try:
        return files_dict[path]
    except KeyError:
        raise BundleFileNotFound(
            "Bundle {} (draft: {}) does not contain a file {}".format(bundle_uuid, use_draft, path)
        )


def get_bundle_file_data(bundle_uuid, path, use_draft=None):
    """
    Read all the data in the given bundle file and return it as a
    binary string.

    Do not use this for large files!
    """
    metadata = get_bundle_file_metadata(bundle_uuid, path, use_draft)
    with requests.get(metadata.url, stream=True) as r:
        return r.content


def write_draft_file(draft_uuid, path, contents):
    """
    Create or overwrite the file at 'path' in the specified draft with the given
    contents. To delete a file, pass contents=None.

    If you don't know the draft's UUID, look it up using
    get_or_create_bundle_draft()

    Does not return anything.
    """
    data = {
        'files': {
            path: encode_str_for_draft(contents) if contents is not None else None,
        },
    }
    serializer = DraftFileUpdateSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    files_to_write = serializer.validated_data['files']
    dependencies_to_write = serializer.validated_data['links']

    draft_repo = DraftRepo(SnapshotRepo())
    try:
        draft_repo.update(draft_uuid, files_to_write, dependencies_to_write)
    except LinkCycleError:
        raise serializers.ValidationError("Link cycle detected: Cannot create draft.")


def set_draft_link(draft_uuid, link_name, bundle_uuid, version):
    """
    Create or replace the link with the given name in the specified draft so
    that it points to the specified bundle version. To delete a link, pass
    bundle_uuid=None, version=None.

    If you don't know the draft's UUID, look it up using
    get_or_create_bundle_draft()

    Does not return anything.
    """
    api_request('patch', api_url('drafts', str(draft_uuid)), json={
        'links': {
            link_name: {"bundle_uuid": str(bundle_uuid), "version": version} if bundle_uuid is not None else None,
        },
    })


def encode_str_for_draft(input_str):
    """
    Given a string, return UTF-8 representation that is then base64 encoded.
    """
    if isinstance(input_str, six.text_type):
        binary = input_str.encode('utf8')
    else:
        binary = input_str
    return base64.b64encode(binary)
