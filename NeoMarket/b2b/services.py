import uuid
import requests
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from rest_framework import serializers 

def handle_product_moderation_status(product, status):
    if status in ['MODERATED', 'BLOCKED', 'CREATED']:
        event_type = 'PRODUCT_CREATED' if status == 'CREATED' else 'PRODUCT_EDITED'
        base_url = settings.MODERATION_URL
        url = f"{base_url}/api/v1/b2b/events/"
        headers = {
            "X-Service-Key": settings.SERVICE_TOKEN,
            "Content-Type": "application/json"
        }
        payload = {
            "event_type": event_type,
            "idempotency_key": str(uuid.uuid4()),
            "occurred_at": timezone.now().isoformat(),
            "payload": {
                "product_id": str(product.pk),
                "seller_id": str(product.seller.pk),
                "category_id": str(product.category.pk),
                "queue_priority": 3,
                "json_after": {
                    "additionalProp1": {}
                }
            }
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            response.raise_for_status() 
        except requests.exceptions.RequestException as e:
            raise serializers.ValidationError({
                "external_service": f"Ошибка внешнего сервиса: {str(e)}"
            })


def send_sku_out_of_stock_event(sku):
    """
    Отправляет событие SKU_OUT_OF_STOCK на B2C микросервис,
    когда доступный остаток товара становится равным 0.
    """
    base_url = settings.B2C_URL
    url = f"{base_url}/api/v1/b2b/events/"
    headers = {
        "X-Service-Key": settings.SERVICE_TOKEN,
        "Content-Type": "application/json"
    }
    payload = {
        "event_type": "SKU_OUT_OF_STOCK",
        "idempotency_key": str(uuid.uuid4()),
        "occurred_at": timezone.now().isoformat(),
        "payload": {
            "sku_id": str(sku.pk),
            "product_id": str(sku.product_id),
            "available_quantity": 0
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        # Логгируем ошибку, но не прерываем основной поток
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send SKU_OUT_OF_STOCK event for SKU {sku.pk}: {str(e)}")
