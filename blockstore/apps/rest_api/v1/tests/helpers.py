"""
Helper utilities for tests.
"""
import base64
import json


def create_bundle_with_history(client, col_uuid_str, bundle_title, commit_data):
    """
    Create a Bundle and add each file dict in `commit_data` as a Snapshot.
    """
    bundle_data = response_data(
        client.post(
            '/api/v1/bundles',
            data={
                'collection_uuid': col_uuid_str,
                'description': "Link Test 😀😀😀😀 Bundle",
                'slug': 'link_test_course',
                'title': bundle_title,
            }
        )
    )
    draft_data = response_data(
        client.post(
            '/api/v1/drafts',
            {
                'bundle_uuid': bundle_data['uuid'],
                'name': 'test_draft',
                'title': f"Draft for {bundle_title} 😀"
            }
        )
    )

    for file_data in commit_data:
        client.patch(draft_data['url'], data={'files': file_data}, format='json')
        client.post(draft_data['url'] + "/commit")

    updated_bundle_data = response_data(client.get(bundle_data['url']))
    return updated_bundle_data


def encode_str_for_draft(input_str):
    """Given a string, return UTF-8 representation that is then base64 encoded."""
    return base64.b64encode(input_str.encode('utf8'))


def response_str_file(response):
    """Return a String by parsing a response's streaming content as UTF-8."""
    return b''.join(response.streaming_content).decode('utf8')


def response_data(response):
    """
    Parse data from the response into Python primitives.

    We need this because response.data is too smart about deserializing
    (e.g. it will automatically parse UUID strings into a UUID object.), and
    we want the basic primitives exactly as the REST API returns them so
    that we can be more confident about compatibility. For instance, UUIDs
    can be represented in multiple ways and parse the same, but if we
    suddenly change the output format, we've broken backwards compatibility.
    """
    try:
        data = json.loads(response.content.decode('utf-8'))
    except Exception:
        raise ValueError(
            f"The following could not be parsed as JSON: {response.content}"
        )
    return data
