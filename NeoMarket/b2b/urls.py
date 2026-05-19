from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductCreateAPIView, ProductUpdateAPIView, SKUUpdateAPIView, SKUCreateAPIView


router = DefaultRouter()

router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
    path('products/', ProductCreateAPIView.as_view(), name='product-create'),
    path('products/<uuid:pk>/', ProductUpdateAPIView.as_view(), name='product-update'),
    path('skus/create/', SKUCreateAPIView.as_view(), name='create-sku'),
    path('skus/<uuid:pk>/', SKUUpdateAPIView.as_view(), name='sku-update'),
]