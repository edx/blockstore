"""
Views for Bundles and BundleVersions.
"""

from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from django_filters.widgets import CSVWidget
from django_filters.filters import AllValuesMultipleFilter, CharFilter
from rest_framework import viewsets, mixins
from rest_framework.generics import get_object_or_404

from blockstore.apps.bundles.models import Bundle, BundleVersion

from ...constants import UUID4_REGEX, VERSION_NUM_REGEX
from ..serializers.bundles import BundleSerializer, BundleVersionSerializer, BundleVersionWithFileDataSerializer


class BundleFilter(FilterSet):
    """
    Filter for BundleViewSet.
    """
    uuid = AllValuesMultipleFilter(widget=CSVWidget)  # Accepts multiple comma-separated UUIDs
    text_search = CharFilter(method='search')

    def search(self, queryset, name, value):  # pylint: disable=unused-argument
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value) | Q(slug__icontains=value))

    class Meta:
        model = Bundle
        fields = ('collection__uuid',)


class BundleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Bundle model.

    Filters available as query params:
        uuid: Accepts a comma-separated list of UUIDs and filters the bundles by them.
        text_search: Takes a string and searches its inclusion in the title, description or slug.
        collection__uuid: Filters bundles belonging to the specified collection.
    """
    lookup_field = 'uuid'
    lookup_url_kwarg = 'bundle_uuid'
    lookup_value_regex = UUID4_REGEX

    filter_backends = (DjangoFilterBackend,)
    filterset_class = BundleFilter

    queryset = Bundle.objects.all() \
                     .select_related('collection') \
                     .prefetch_related('drafts', 'versions')
    serializer_class = BundleSerializer


class BundleVersionViewSet(mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for BundleVersion model.
    """
    lookup_fields = ('bundle__uuid', 'version_num')
    lookup_url_kwargs = ('bundle_uuid', 'version_num')
    lookup_value_regexes = (UUID4_REGEX, VERSION_NUM_REGEX)

    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ('bundle__uuid', 'bundle__collection__uuid')

    queryset = BundleVersion.objects.all().select_related('bundle')

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        filter_kwargs = {
            key: self.kwargs[value] for key, value in
            zip(self.lookup_fields, self.lookup_url_kwargs)
        }
        obj = get_object_or_404(queryset, **filter_kwargs)

        # May raise a permission denied
        self.check_object_permissions(self.request, obj)

        return obj

    def get_serializer_class(self):
        """
        Return a more compact serializer for list views than detail views.

        The `retreve` method (GET of a single BundleVersion) yields full file
        metadata details, but we can't support that in list views for
        performance reasons as this metadata may grow very large when storing
        entire courses.
        """
        if self.action == 'retrieve':
            return BundleVersionWithFileDataSerializer
        # Generic model serializer is sufficient for other views.
        return BundleVersionSerializer
