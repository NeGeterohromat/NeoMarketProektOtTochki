from rest_framework import viewsets, generics, permissions
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from app.models import Category, Product, SKU
from .serializers import CategorySerializer, CategoryDetailSerializer, ProductCreateSerializer, SKUCreateSerializer, SKUResponseSerializer


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
    queryset = Product
    serializer_class = ProductCreateSerializer
    permission_classes = [permissions.IsAuthenticated,]

    def perform_create(self, serializer):
        return super().perform_create(serializer)
    

class CreateSKUView(generics.CreateAPIView):
    queryset = SKU.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SKUCreateSerializer

    @extend_schema(
        operation_id='create_sku_api_skus_create_post',
        summary='Создать SKU',
        tags=['SKUs'],
        request=SKUCreateSerializer,
        responses={201: SKUResponseSerializer},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=422)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)
