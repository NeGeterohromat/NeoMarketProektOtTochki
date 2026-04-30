"""
Definition of urls for NeoMarket.
"""

from datetime import datetime
from django.urls import path
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from app import forms, views


urlpatterns = [
    # default urls
    path('', views.home, name='home'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),
    path('login/',
         LoginView.as_view
         (
             template_name='app/login.html',
             authentication_form=forms.BootstrapAuthenticationForm,
             extra_context=
             {
                 'title': 'Log in',
                 'year' : datetime.now().year,
             }
         ),
         name='login'),
    path('logout/', LogoutView.as_view(next_page='/'), name='logout'),
    path('admin/', admin.site.urls),
    # default urls
    path(
        'api/invoices/',
        views.InvoiceListCreateView.as_view(),
        name='invoice-list-create'
    ),
    path(
        'api/invoices/<uuid:invoice_id>/',
        views.InvoiceDetailView.as_view(),
        name='invoice-detail'
    ),
    path(
        'api/invoices/<uuid:invoice_id>/accept/',
        views.InvoiceAcceptView.as_view(),
        name='invoice-accept'
    ),
]
