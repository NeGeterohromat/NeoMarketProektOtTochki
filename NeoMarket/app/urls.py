from django.urls import path

from .views import CreateSKUView

urlpatterns = [
    path('create', CreateSKUView.as_view(), name='create-sku'),
]
