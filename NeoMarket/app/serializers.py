from rest_framework import serializers

from app.models import Product, SKU, SKUCharacteristic, ProductImage, ProductCharacteristic


class SKUCharacteristicCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    value = serializers.CharField()


class SKUImageCreateSerializer(serializers.Serializer):
    url = serializers.URLField()
    ordering = serializers.IntegerField(required=False, default=0)


class SKUCreateSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    name = serializers.CharField()
    price = serializers.IntegerField(min_value=0)
    stock_quantity = serializers.IntegerField(min_value=0, default=0, required=False)
    article = serializers.CharField(allow_null=True, allow_blank=True, required=False, default=None)
    images = SKUImageCreateSerializer(many=True, required=False, default=list)
    characteristics = SKUCharacteristicCreateSerializer(many=True, required=False, default=list)

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError('Product not found.')

        request = self.context.get('request')
        if request is None or request.user.is_anonymous:
            raise serializers.ValidationError('Authentication credentials were not provided.')

        if product.seller_id != request.user.id:
            raise serializers.ValidationError('Product does not belong to the authenticated seller.')

        self._product = product
        return value

    def create(self, validated_data):
        product = getattr(self, '_product', None)
        if product is None:
            product = Product.objects.get(id=validated_data['product_id'])

        sku = SKU.objects.create(
            product=product,
            name=validated_data['name'],
            price=validated_data['price'],
            active_quantity=validated_data.get('stock_quantity', 0),
        )

        for characteristic_data in validated_data.get('characteristics', []):
            SKUCharacteristic.objects.create(sku=sku, **characteristic_data)

        return sku


class SKUCharacteristicResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKUCharacteristic
        fields = ('id', 'name', 'value')


class SKUResponseSerializer(serializers.ModelSerializer):
    seller_id = serializers.UUIDField(source='product.seller_id')
    product_id = serializers.UUIDField(source='product_id')
    stock_quantity = serializers.IntegerField(source='active_quantity')
    article = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    characteristics = SKUCharacteristicResponseSerializer(many=True)

    class Meta:
        model = SKU
        fields = (
            'id',
            'seller_id',
            'product_id',
            'name',
            'price',
            'stock_quantity',
            'article',
            'images',
            'characteristics',
            'created_at',
            'updated_at',
        )

    def get_article(self, obj):
        return None

    def get_images(self, obj):
        return []


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'url', 'ordering']


class ProductCharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCharacteristic
        fields = ['id', 'name', 'value']


class SKUInProductSerializer(serializers.ModelSerializer):
    stock_quantity = serializers.IntegerField(source='active_quantity')

    class Meta:
        model = SKU
        fields = ['id', 'name', 'price', 'stock_quantity', 'article']


class ProductDetailSerializer(serializers.ModelSerializer):
    seller_id = serializers.UUIDField(source='seller.id')
    category_id = serializers.UUIDField(source='category.id')
    images = ProductImageSerializer(many=True)
    characteristics = ProductCharacteristicSerializer(many=True)
    skus = SKUInProductSerializer(many=True)

    class Meta:
        model = Product
        fields = [
            'id', 'seller_id', 'category_id', 'title',
            'description', 'status', 'images', 'characteristics',
            'skus', 'created_at', 'updated_at'
        ]