from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CategoryViewSet, ProductCreateAPIView, CreateSKUView


router = DefaultRouter()

router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
    path('products/', ProductCreateAPIView.as_view(), name='product-create'),
    path('skus/create/', CreateSKUView.as_view(), name='create-sku'),
]