from django.db import transaction
from django.core.validators import RegexValidator
from rest_framework import serializers
from app.models import Category, Product, ProductCharacteristic, ProductImage, SKU, SKUCharacteristic


# list (нужно добавить фильтр), post, вложенный в detail, patch
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'parent_id', 'created_at')
        read_only_fields = ('id', 'created_at')


class CategoryDetailSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    class Meta:
        model = Category
        fields = ('id', 'name', 'parent_id', 'created_at', 'children')

    def get_children(self, obj):
        children = obj.subcategories.all()
        return CategorySerializer(children, many=True).data


class ProductCharacteristicsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCharacteristic
        fields = ('id', 'name', 'value')
        read_only_fields = ('id',)


class ProductImageSerializer(serializers.ModelSerializer):
    url = serializers.CharField(validators=[
        RegexValidator(regex=r'^(https?:\/\/|[.\/])\S+$', message='Неверно указан url')
    ])
    class Meta:
        model = ProductImage
        fields = ('id', 'url', 'ordering')
        read_only_fields = ('id',)


class ProductCreateSerializer(serializers.ModelSerializer):
    characteristics = ProductCharacteristicsSerializer(required=False, many=True)
    images = ProductImageSerializer(many=True, min_length=1)
    seller = serializers.HiddenField(default=serializers.CurrentUserDefault())
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category')
    class Meta:
        model = Product
        fields = ('seller', 'category_id', 'title', 'description', 'images', 'characteristics',)

    def validate(self, attrs):
        images_data = attrs.get('images', [])
        
        # дубликаты ordering внутри запроса
        orderings = [img.get('ordering') for img in images_data if img.get('ordering') is not None]
        if len(orderings) != len(set(orderings)):
            raise serializers.ValidationError({
                "images": "В списке изображений присутствуют дубликаты порядковых номеров (ordering)."
            })

        return attrs

    def create(self, validated_data):
        characteristics_data = validated_data.pop('characteristics', [])
        images_data = validated_data.pop('images', [])

        with transaction.atomic():
            product = Product.objects.create(**validated_data)
            
            characteristic_objects = [
                ProductCharacteristic(product=product, **char_data)
                for char_data in characteristics_data
            ]
            ProductCharacteristic.objects.bulk_create(characteristic_objects)

            image_objects = [
                ProductImage(product=product, **img_data)
                for img_data in images_data
            ]
            ProductImage.objects.bulk_create(image_objects)

        return product
    

class SKUNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'stock_quantity', 'article',)


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    characteristics = ProductCharacteristicsSerializer(many=True)
    skus = SKUNestedSerializer(many=True)
    class Meta:
        model = Product
        fields = ('id', 'seller_id', 'category_id', 'title', 'description',
                  'status', 'images', 'characteristics',
                  'skus', 'created_at', 'updated_at')


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
    product_id = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), source='product')
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
