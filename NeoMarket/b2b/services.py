import uuid
import requests
from django.conf import settings
from django.utils import timezone
from rest_framework import serializers 

def handle_product_moderation_status(product):
    if product.status in ['MODERATED', 'BLOCKED']:
        base_url = settings.MODERATION_URL
        url = f"{base_url}/api/v1/b2b/events/"
        headers = {
            "X-Service-Key": settings.MODERATION_TOKEN,
            "Content-Type": "application/json"
        }
        payload = {
            "event_type": "PRODUCT_EDITED",
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
