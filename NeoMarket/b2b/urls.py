from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductCreateAPIView,
    ProductRetrieveUpdateAPIView,
    SKUUpdateAPIView,
    SKUCreateAPIView,
    B2CListProductAPIView,
    B2CBatchProductAPIView,
    B2CDetailProductAPIView,
    B2CDetailSKUAPIView,
    B2CSimilarProductAPIView,
    ReserveAPIView,
    UnreserveAPIView,
    ModerationEventsAPIVew,
)


router = DefaultRouter()

router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('', include(router.urls)),
    path('products/', ProductCreateAPIView.as_view(), name='product-create'),
    path('products/<str:pk>/', ProductRetrieveUpdateAPIView.as_view(), name='product-detail'),
    path('skus/', SKUCreateAPIView.as_view(), name='sku-create'),
    path('skus/<uuid:pk>/', SKUUpdateAPIView.as_view(), name='sku-update'),
    path('public/products/', B2CListProductAPIView.as_view(), name='b2c-product-list'),
    path('public/products/batch/', B2CBatchProductAPIView.as_view(), name='b2c-product-batch'),
    path('public/products/<uuid:pk>/', B2CDetailProductAPIView.as_view(), name='b2c-product-detail'),
    path('public/products/<uuid:pk>/similar/', B2CSimilarProductAPIView.as_view(), name='b2c-product-similar'),
    path('public/skus/<uuid:pk>/', B2CDetailSKUAPIView.as_view(), name='b2c-sku-detail'),
    path('inventory/reserve', ReserveAPIView.as_view(), name='reserve'),
    path('inventory/unreserve', UnreserveAPIView.as_view(), name='unreserve'),
    path('moderation/events/', ModerationEventsAPIVew.as_view(), name='moderation-events'),
]