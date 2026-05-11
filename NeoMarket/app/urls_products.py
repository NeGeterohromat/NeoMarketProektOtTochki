from django.urls import path

from .views import ProductDetailView

urlpatterns = [
    path('<uuid:product_id>/', ProductDetailView.as_view(), name='product-detail'),
]