"""
Serializer fields that add support for relationships with resources which have
composite keys.
"""

from rest_framework import relations
from rest_framework.fields import get_attribute


class HyperlinkedRelatedField(relations.HyperlinkedRelatedField):
    """
    A read-only field that represents the identity URL for a related resource.

    Includes support for related resources with composite identifier keys.
    """
    def __init__(self, *args, **kwargs):
        self.lookup_fields = kwargs.pop('lookup_fields', None)
        self.lookup_url_kwargs = kwargs.pop('lookup_url_kwargs', self.lookup_fields)
        super().__init__(*args, **kwargs)

    def get_url(self, obj, view_name, request, format):  # pylint: disable=redefined-builtin

        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, 'pk') and obj.pk in (None, ''):
            return None

        if self.lookup_fields:
            kwargs = {
                key: get_attribute(obj, value.split('__')) for key, value
                in zip(self.lookup_url_kwargs, self.lookup_fields)
            }
            return self.reverse(view_name, kwargs=kwargs, request=request, format=format)

        return super().get_url(obj, view_name, request, format)

    def use_pk_only_optimization(self):
        return False


class HyperlinkedIdentityField(HyperlinkedRelatedField):
    """
    A read-only field that represents the identity URL for an object, itself.

    Includes support for resources with composite identifier keys.
    """
    def __init__(self, view_name=None, **kwargs):
        assert view_name is not None, 'The `view_name` argument is required.'
        kwargs['read_only'] = True
        kwargs['source'] = '*'
        super().__init__(view_name=view_name, **kwargs)
