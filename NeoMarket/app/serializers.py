from rest_framework import serializers
from .models import Invoice, InvoiceItem, InvoiceStatus


class InvoiceItemCreateSerializer(serializers.Serializer):
    sku_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_sku_id(self, value):
        from skus.models import SKU  # импорт здесь, чтобы избежать циклического импорта
        try:
            sku = SKU.objects.get(id=value)
        except SKU.DoesNotExist:
            raise serializers.ValidationError(f"SKU with id {value} does not exist")
        
        # Проверяем, что SKU принадлежит текущему продавцу
        request = self.context.get('request')
        if request and request.user != sku.product.seller:
            raise serializers.ValidationError("You don't have access to this SKU")
        
        return value


class InvoiceCreateSerializer(serializers.Serializer):
    items = InvoiceItemCreateSerializer(many=True, min_length=1)

    def validate(self, data):
        if not data.get('items'):
            raise serializers.ValidationError({"items": "At least one item is required"})
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        items_data = validated_data.pop('items')
        
        invoice = Invoice.objects.create(seller=request.user)
        
        for item_data in items_data:
            InvoiceItem.objects.create(
                invoice=invoice,
                sku_id=item_data['sku_id'],
                quantity=item_data['quantity']
            )
        
        return invoice


class InvoiceItemResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ['id', 'sku_id', 'quantity']


class InvoiceResponseSerializer(serializers.ModelSerializer):
    items = InvoiceItemResponseSerializer(many=True, read_only=True)
    seller_id = serializers.UUIDField(source='seller.id', read_only=True)
    
    class Meta:
        model = Invoice
        fields = [
            'id', 
            'seller_id', 
            'status', 
            'items', 
            'created_at', 
            'updated_at'
        ]


class InvoiceListResponseSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    items = InvoiceResponseSerializer(many=True)
