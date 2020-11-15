"""
Routers for Blockstore API.
"""

from rest_framework_nested import routers


class DefaultRouter(routers.DefaultRouter):
    """
    Customized version of DefaultRouter used for the Blockstore REST API
    """
    def get_lookup_regex(self, viewset, lookup_prefix=''):
        """
        Given a viewset, return the portion of URL regex that is used
        to match against a single instance.

        This method adds support for comma-delimited composite keys. If a resource
        requires those, set lookup_fields, lookup_url_kwargs and lookup_value_regexes
        instead of the singular versions.

        Note that lookup_prefix is not used directly inside REST rest_framework
        itself, but is required in order to nicely support nested router
        implementations, such as drf-nested-routers.

        https://github.com/alanjds/drf-nested-routers
        """

        # drf-nested-routers assumes that lookup will have length > 0 and so
        # always appends "_" to it to create the lookup_prefix. If lookup_prefix
        # is only "_" we reset it to "".
        if lookup_prefix == '_':
            lookup_prefix = ''

        lookup_fields = getattr(viewset, 'lookup_fields', None)
        if lookup_fields:
            lookup_url_kwargs = getattr(viewset, 'lookup_url_kwargs', lookup_fields)
            lookup_value_regexes = getattr(viewset, 'lookup_value_regexes', len(lookup_fields) * ['[^/.]+'])
            return ','.join([
                '(?P<{lookup_prefix}{lookup_url_kwarg}>{lookup_value_regex})'.format(
                    lookup_prefix=lookup_prefix,
                    lookup_url_kwarg=lookup_url_kwarg,
                    lookup_value_regex=lookup_value_regex,
                ) for (lookup_url_kwarg, lookup_value_regex) in zip(lookup_url_kwargs, lookup_value_regexes)
            ])

        return super().get_lookup_regex(viewset, lookup_prefix=lookup_prefix)
