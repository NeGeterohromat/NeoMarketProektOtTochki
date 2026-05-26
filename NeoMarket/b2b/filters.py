import django_filters
from app.models import Product
from django.db.models import Q


class B2CProductFilter(django_filters.FilterSet):
    category = django_filters.UUIDFilter(field_name='category__id')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Product
        fields = ['category', 'search']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )