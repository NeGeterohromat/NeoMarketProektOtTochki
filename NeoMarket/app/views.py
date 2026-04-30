"""
Definition of views.
"""
# default views
from datetime import datetime
from django.shortcuts import render
from django.http import HttpRequest

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
# default views

from rest_framework import status, permissions, generics, mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404

from .models import Invoice, InvoiceItem, InvoiceStatus
from .serializers import (
    InvoiceCreateSerializer,
    InvoiceResponseSerializer,
    InvoiceListResponseSerializer
)


class IsSellerPermission(permissions.BasePermission):
    """Проверка, что пользователь является продавцом"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_seller


class InvoiceListCreateView(APIView):
    """
    GET /api/invoices - список накладных
    POST /api/invoices - создать накладную
    """
    permission_classes = [IsSellerPermission]

    def get(self, request):
        """Получить список накладных продавца с пагинацией"""
        limit = int(request.query_params.get('limit', 20))
        offset = int(request.query_params.get('offset', 0))
        
        # Валидация параметров
        if limit > 100:
            limit = 100
        if limit < 1:
            limit = 1
        if offset < 0:
            offset = 0
        
        invoices = Invoice.objects.filter(seller=request.user)
        total = invoices.count()
        
        # Применяем пагинацию
        invoices = invoices[offset:offset + limit]
        
        serializer = InvoiceResponseSerializer(invoices, many=True)
        
        response_data = {
            'total': total,
            'items': serializer.data
        }
        
        return Response(
            InvoiceListResponseSerializer(response_data).data,
            status=status.HTTP_200_OK
        )

    def post(self, request):
        """Создать новую накладную"""
        serializer = InvoiceCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        
        try:
            with transaction.atomic():
                invoice = serializer.save()
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        response_serializer = InvoiceResponseSerializer(invoice)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )


class InvoiceDetailView(APIView):
    """
    GET /api/invoices/{invoice_id} - получить накладную
    DELETE /api/invoices/{invoice_id} - удалить накладную
    """
    permission_classes = [IsSellerPermission]

    def get(self, request, invoice_id):
        """Получить детали накладной"""
        invoice = self._get_invoice(request, invoice_id)
        serializer = InvoiceResponseSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, invoice_id):
        """Удалить накладную (только если статус CREATED)"""
        invoice = self._get_invoice(request, invoice_id)
        
        if invoice.status != InvoiceStatus.CREATED:
            return Response(
                {'detail': 'Can only delete invoices with status CREATED'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        invoice.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_invoice(self, request, invoice_id):
        """Получить накладную с проверкой прав"""
        return get_object_or_404(
            Invoice,
            id=invoice_id,
            seller=request.user
        )


class InvoiceAcceptView(APIView):
    """
    POST /api/invoices/{invoice_id}/accept - принять накладную
    """
    permission_classes = [IsSellerPermission]

    def post(self, request, invoice_id):
        """Принять накладную и обновить остатки SKU"""
        invoice = get_object_or_404(
            Invoice,
            id=invoice_id,
            seller=request.user
        )
        
        if invoice.status != InvoiceStatus.CREATED:
            return Response(
                {
                    'detail': f'Invoice must be in CREATED status, current status: {invoice.status}'
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        if not invoice.items.exists():
            return Response(
                {'detail': 'Cannot accept invoice with no items'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        try:
            with transaction.atomic():
                # Обновляем остатки SKU
                for item in invoice.items.select_related('sku').all():
                    sku = item.sku
                    sku.stock_quantity += item.quantity
                    sku.save()
                
                # Меняем статус накладной
                invoice.status = InvoiceStatus.ACCEPTED
                invoice.save()
                
        except Exception as e:
            return Response(
                {'detail': f'Error accepting invoice: {str(e)}'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY
            )
        
        serializer = InvoiceResponseSerializer(invoice)
        return Response(serializer.data, status=status.HTTP_200_OK)