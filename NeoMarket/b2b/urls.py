from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductCreateAPIView,
    ProductRetrieveUpdateAPIView,
    SKUUpdateAPIView,
    SKUCreateAPIView,
    B2CListProductAPIView,
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
    path('inventory/reserve/', ReserveAPIView.as_view(), name='reserve'),
    path('inventory/unreserve/', UnreserveAPIView.as_view(), name='unreserve'),
    path('moderation/events/', ModerationEventsAPIVew.as_view(), name='moderation-events'),
]