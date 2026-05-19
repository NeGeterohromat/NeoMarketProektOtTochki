from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductCreateAPIView, ProductRetrieveUpdateAPIView, SKUUpdateAPIView, SKUCreateAPIView


router = DefaultRouter()

router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
    path('products/', ProductCreateAPIView.as_view(), name='product-create'),
    path('products/<uuid:pk>/', ProductRetrieveUpdateAPIView.as_view(), name='product-detail'),
    path('skus/', SKUCreateAPIView.as_view(), name='sku-create'),
    path('skus/<uuid:pk>/', SKUUpdateAPIView.as_view(), name='sku-update'),
]