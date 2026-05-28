import uuid

from django.db.models import Min, F

from rest_framework import viewsets, generics, permissions, status, filters as drf_filters
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, extend_schema_view

from django_filters import rest_framework as df_filters

from app.models import Category, Product, SKU, Reservation
from .permissions import CanCreateUpdateSKU, CanUpdateProduct, IsAuthenticatedOrService, IsSafeForModerator, IsService
from .authentication import ServiceKeyAuthentication
from .serializers import (
    CategorySerializer,
    CategoryDetailSerializer,
    ProductCreateUpdateSerializer,
    # ProductDetailSerializer,
    SellerProductDetailSerializer,
    ModeratorProductDetailSerializer,
    SKUCreateSerializer,
    # SKUResponseSerializer,
    SKUUpdateSerializer,
    SKUDetailSerializer,
    B2CListProductSerializer,
    ReserveSerializer,
)
from .pagination import B2CProductPagination
from .filters import B2CProductFilter


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.action == 'retrieve':
            queryset = Category.objects.prefetch_related('subcategories')
        
        return queryset
    
    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        
        if self.action == 'retrieve':
            serializer_class = CategoryDetailSerializer
        
        return serializer_class 
    

class ProductCreateAPIView(generics.CreateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated,]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        response_serializer = SellerProductDetailSerializer(product, context=self.get_serializer_context())
        headers = self.get_success_headers(serializer.data)
        return Response(
            response_serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    

@extend_schema_view(
    get=extend_schema(
        responses={
            200: SellerProductDetailSerializer,
        }
    ),
    put=extend_schema(
        request=ProductCreateUpdateSerializer,
        responses={200: SellerProductDetailSerializer}
    ),
    patch=extend_schema(
        request=ProductCreateUpdateSerializer,
        responses={200: SellerProductDetailSerializer}
    )
)
class ProductRetrieveUpdateAPIView(generics.RetrieveUpdateAPIView):
    queryset = Product.objects.all()
    authentication_classes = [ServiceKeyAuthentication, JWTAuthentication,]
    serializer_class = ProductCreateUpdateSerializer

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        instance = self.get_object()
        response_serializer = SellerProductDetailSerializer(instance, context=self.get_serializer_context())
        response.data = response_serializer.data
        return response
    
    def is_moderator(self):
        auth_data = self.request.auth
        return isinstance(auth_data, dict) and auth_data.get('is_moderator_service') is True
    
    def is_get_method(self):
        return self.request.method == 'GET'
    
    def is_update_method(self):
        return self.request.method in ['PUT', 'PATCH']
    
    def get_queryset(self):
        if self.is_get_method() and self.is_moderator() or self.is_update_method():
            return Product.objects.all()
        user = self.request.user
        if user.is_authenticated:
            return Product.objects.filter(seller=user)
        return Product.objects.none()
    
    def get_serializer_class(self):
        if self.is_update_method():
            return ProductCreateUpdateSerializer
        if self.is_moderator():
            return ModeratorProductDetailSerializer
        return SellerProductDetailSerializer
    
    def get_permissions(self):
        """Динамически назначаем права доступа в зависимости от метода запроса."""
        if self.is_update_method():
            return [permissions.IsAuthenticated(), IsSafeForModerator(), CanUpdateProduct()]
        return [IsAuthenticatedOrService()]
    
    def get_object(self):
        pk = self.kwargs.get('pk')
        try:
            uuid.UUID(str(pk))  # Проверяем, является ли строка валидным UUID
        except ValueError:
            raise ValidationError({'pk': 'Неверный формат UUID.'}) # Вернет HTTP 400
            
        return super().get_object()


class B2CListProductAPIView(generics.ListAPIView):
    authentication_classes = [ServiceKeyAuthentication]
    permission_classes = [IsService]
    
    queryset = Product.objects.filter(
        status="MODERATED", 
        deleted=False,
        skus__stock_quantity__gt=F('skus__reserved_quantity')
    ).prefetch_related('skus', 'images').annotate(min_price=Min('skus__price'))
    serializer_class = B2CListProductSerializer
    pagination_class = B2CProductPagination
    filter_backends = [df_filters.DjangoFilterBackend, drf_filters.OrderingFilter]
    filterset_class = B2CProductFilter
    ordering_fields = ['min_price', 'created_at']
    ordering = ['-created_at']
    ordering_param = 'sort'

    def filter_queryset(self, queryset):
        """Переопределяем фильтрацию, чтобы обработать кастомные параметры сортировки."""
        for backend in list(self.filter_backends):
            if backend == drf_filters.OrderingFilter:
                # Обрабатываем сортировку вручную
                ordering_param_value = self.request.query_params.get(self.ordering_param)
                if ordering_param_value:
                    fields = [param.strip() for param in ordering_param_value.split(',')]
                    transformed_orderings = []
                    for ordering in fields:
                        if ordering == 'price_asc':
                            transformed_orderings.append('min_price')
                        elif ordering == 'price_desc':
                            transformed_orderings.append('-min_price')
                        elif ordering == 'date_desc':
                            transformed_orderings.append('-created_at')
                        else:
                            transformed_orderings.append(ordering)
                    if transformed_orderings:
                        queryset = queryset.order_by(*transformed_orderings)
                continue
            
            queryset = backend().filter_queryset(self.request, queryset, self)
        
        return queryset


class SKUCreateAPIView(generics.CreateAPIView):
    queryset = SKU.objects.all()
    serializer_class = SKUCreateSerializer
    permission_classes = [permissions.IsAuthenticated, CanCreateUpdateSKU]

    @extend_schema(
        operation_id='create_sku_api_skus_create_post',
        summary='Создать SKU',
        tags=['SKUs'],
        request=SKUCreateSerializer,
        responses={201: SKUDetailSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        response_serializer = SKUDetailSerializer(instance, context=self.get_serializer_context())
        headers = self.get_success_headers(serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class SKUUpdateAPIView(generics.UpdateAPIView):
    queryset = SKU.objects.all()
    serializer_class = SKUUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, CanCreateUpdateSKU]

    @extend_schema(
        operation_id='update_sku_api_skus_update_post',
        summary='Обновить SKU',
        tags=['SKUs'],
        request=SKUCreateSerializer,
        responses={200: SKUDetailSerializer},
    )
    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        
        instance = self.get_object()
        
        response_serializer = SKUDetailSerializer(instance, context=self.get_serializer_context())
        
        response.data = response_serializer.data
        return response
    

class ReserveAPIView(generics.CreateAPIView):
    queryset = Reservation.objects.all()
    serializer_class = ReserveSerializer
    authentication_classes = [ServiceKeyAuthentication]
    permission_classes = [IsService]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reservation = serializer.save()
        
        # Проверяем, была ли это новая запись
        is_new = getattr(reservation, '_is_new', True)
        status_code = status.HTTP_201_CREATED if is_new else status.HTTP_200_OK
        
        return Response(
            self.get_serializer(reservation).data,
            status=status_code
        )