"""
Definition of views.
"""

from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from .serializers import SKUCreateSerializer, SKUResponseSerializer
from app.models import SKU
from .serializers import ProductDetailSerializer
from app.models import Product


def home(request):
    """Renders the home page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/index.html',
        {
            'title':'Home Page',
            'year':datetime.now().year,
        }
    )

def contact(request):
    """Renders the contact page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/contact.html',
        {
            'title':'Contact',
            'message':'Your contact page.',
            'year':datetime.now().year,
        }
    )

def about(request):
    """Renders the about page."""
    assert isinstance(request, HttpRequest)
    return render(
        request,
        'app/about.html',
        {
            'title':'About',
            'message':'Your application description page.',
            'year':datetime.now().year,
        }
    )


@extend_schema(
    operation_id='create_sku_api_skus_create_post',
    summary='Создать SKU',
    tags=['SKUs'],
    request=SKUCreateSerializer,
    responses={201: SKUResponseSerializer},
)
class CreateSKUView(generics.CreateAPIView):
    queryset = SKU.objects.all()
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SKUCreateSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=422)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)


@extend_schema(
    operation_id='get_product_api_products_product_id_get',
    summary='Получить товар по ID',
    tags=['Products'],
    responses={200: ProductDetailSerializer},
)
class ProductDetailView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id, seller=request.user)
        except Product.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = ProductDetailSerializer(product)
        return Response(serializer.data)