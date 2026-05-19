from rest_framework import viewsets, generics, permissions, status
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema

from app.models import Category, Product, SKU
from .permissions import CanUpdateSKU, CanUpdateProduct
from .serializers import (
    CategorySerializer,
    CategoryDetailSerializer,
    ProductCreateUpdateSerializer,
    ProductDetailSerializer,
    SKUCreateSerializer,
    SKUResponseSerializer,
    SKUUpdateSerializer,
    SKUDetailSerializer,
)


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
        response_serializer = ProductDetailSerializer(product, context=self.get_serializer_context())
        headers = self.get_success_headers(serializer.data)
        return Response(
            response_serializer.data, 
            status=status.HTTP_201_CREATED, 
            headers=headers
        )
    

class ProductUpdateAPIView(generics.UpdateAPIView):
    queryset = Product.objects.all()
    serializer_class = ProductCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, CanUpdateProduct]

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        
        instance = self.get_object()
        
        response_serializer = ProductDetailSerializer(instance, context=self.get_serializer_context())
        
        response.data = response_serializer.data
        return response


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


class SKUUpdateAPIView(generics.UpdateAPIView):
    queryset = SKU.objects.all()
    serializer_class = SKUUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, CanUpdateSKU]

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        
        instance = self.get_object()
        
        response_serializer = SKUDetailSerializer(instance, context=self.get_serializer_context())
        
        response.data = response_serializer.data
        return response