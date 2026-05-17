import uuid
from django.db import transaction
from app.models import Moderation

def handle_product_moderation_status(*, product, user, validated_data) -> dict:
    with transaction.atomic():
        if product.status in ['MODERATED', 'BLOCKED']:
            validated_data['status'] = 'ON_MODERATION'
            Moderation.objects.create(
                idempotency_key=uuid.uuid4,
                product=product,
                seller=user,
                event=Moderation.Events.EDITED
            )

    return validated_data
