""" Constants for the API. """

FILE_PATH_REGEX = '[^:]+'

# Collections, Bundles, and Drafts all use UUIDs
UUID4_REGEX = '[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}'

# Bundle Version Numbers are just ints
VERSION_NUM_REGEX = '[0-9]+'

# 20-byte hash digests are used for Snapshots.
SNAPSHOT_HASH_DIGEST_REGEX = '[0-9a-f]{40}'
