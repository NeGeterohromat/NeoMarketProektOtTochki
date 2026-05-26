import django_filters
from app.models import Product
from django.db.models import Q


class B2CProductFilter(django_filters.FilterSet):
    category_id = django_filters.UUIDFilter(field_name='category__id')
    seller_id = django_filters.UUIDFilter(field_name='seller__id')
    search = django_filters.CharFilter(method='filter_search')
    ids = django_filters.CharFilter(method='filter_ids')
    min_price = django_filters.NumberFilter(field_name='min_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='min_price', lookup_expr='lte')
    characteristics = django_filters.CharFilter(method='filter_characteristics')

    class Meta:
        model = Product
        fields = ['category_id', 'seller_id', 'search', 'ids', 'min_price', 'max_price', 'characteristics']

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )

    def filter_ids(self, queryset, name, value):
        if not value:
            return queryset
        # Разделяем строку по запятым и фильтруем по UUID
        ids_list = [id_str.strip() for id_str in value.split(',') if id_str.strip()]
        return queryset.filter(id__in=ids_list)

    def filter_characteristics(self, queryset, name, value):
        # Получаем все query-параметры с префиксом 'filters['
        # Пример: filters[brand]=apple&filters[memory]=256
        filters_data = {}
        for param in self.form.request.GET:
            if param.startswith('filters[') and param.endswith(']'):
                key = param[8:-1]  # Извлекаем имя характеристики
                filters_data[key] = self.form.request.GET.getlist(param)
        
        if not filters_data:
            return queryset
        
        # Для каждой характеристики добавляем фильтрацию
        # Товар должен иметь ВСЕ указанные характеристики (AND между разными)
        # Но может иметь ЛЮБОЕ из значений одной характеристики (OR внутри)
        for char_name, char_values in filters_data.items():
            if not char_values:
                continue
            queryset = queryset.filter(
                characteristics__name=char_name,
                characteristics__value__in=char_values
            )
        
        return queryset.distinct()