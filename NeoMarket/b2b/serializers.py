from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.validators import RegexValidator
from rest_framework import serializers
from app.models import (
    Category,
    Product,
    ProductStatus,
    ProductCharacteristic,
    ProductImage,
    SKU,
    SKUCharacteristic,
    SKUImage,
    BlockingReason,
    FieldReport,
)
from .services import handle_product_moderation_status


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


class ProductCreateUpdateSerializer(serializers.ModelSerializer):
    characteristics = ProductCharacteristicsSerializer(required=False, many=True)
    images = ProductImageSerializer(many=True, min_length=1)
    seller = serializers.HiddenField(default=serializers.CurrentUserDefault())
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category')
    class Meta:
        model = Product
        fields = ('seller', 'category_id', 'title', 'description', 'images', 'characteristics',)

    def validate(self, attrs):
        images_data = attrs.get('images', [])
        
        if images_data is not None:
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
    
    def update(self, instance, validated_data):
        characteristics_data = validated_data.pop('characteristics', None)
        images_data = validated_data.pop('images', None)

        product_status = instance.status

        with transaction.atomic():
            if instance.status in ['MODERATED', 'BLOCKED']:
                validated_data['status'] = 'ON_MODERATION'
            
            instance = super().update(instance, validated_data)

            if images_data is not None:
                instance.images.all().delete()
                image_objects = [
                    ProductImage(product=instance, **img_data)
                    for img_data in images_data
                ]
                ProductImage.objects.bulk_create(image_objects)

            if characteristics_data is not None:
                instance.characteristics.all().delete()
                characteristic_objects = [
                    ProductCharacteristic(product=instance, **char_data)
                    for char_data in characteristics_data
                ]
                ProductCharacteristic.objects.bulk_create(characteristic_objects)

        handle_product_moderation_status(product=instance, status=product_status)

        return instance
    

class SKUNestedSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKU
        fields = ('id', 'name', 'price', 'stock_quantity', 'article',)


# использовать SellerProductDetailSerializer вместо данного сериализатора
class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    characteristics = ProductCharacteristicsSerializer(many=True)
    skus = SKUNestedSerializer(many=True)
    class Meta:
        model = Product
        fields = ('id', 'seller_id', 'category_id', 'title', 'description',
                  'status', 'images', 'characteristics', 'skus', 'created_at', 'updated_at')


class SKUCharacteristicSerializer(serializers.ModelSerializer):
    class Meta:
        model = SKUCharacteristic
        fields = ('id', 'name', 'value')
        read_only_fields = ('id',)


class SKUImageSerializer(serializers.ModelSerializer):
    url = serializers.CharField(validators=[
        RegexValidator(regex=r'^(https?:\/\/|[.\/])\S+$', message='Неверно указан url')
    ])
    class Meta:
        model = SKUImage
        fields = ('id', 'url', 'ordering')
        read_only_fields = ('id',)


class SKUCreateSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField(write_only=True)
    images = SKUImageSerializer(many=True, min_length=1)
    characteristics = SKUCharacteristicSerializer(many=True, required=False)
    class Meta:
        model = SKU
        fields = ('product_id', 'name', 'price', 'discount',
                  'cost_price', 'article', 'images', 'characteristics')

    def validate(self, attrs):
        product_id = attrs.get('product_id')
        product = get_object_or_404(Product, pk=product_id)
        attrs['product'] = product

        images_data = attrs.get('images', [])
        
        if images_data is not None:
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

        product_status = None

        with transaction.atomic():
            sku = SKU.objects.create(**validated_data)
            
            product = sku.product
            product_status = product.status
            if product_status == 'CREATED':
                product.status = 'ON_MODERATION'
            product.save()

            characteristic_objects = [
                SKUCharacteristic(sku=sku, **char_data)
                for char_data in characteristics_data
            ]
            SKUCharacteristic.objects.bulk_create(characteristic_objects)

            image_objects = [
                SKUImage(sku=sku, **img_data)
                for img_data in images_data
            ]
            SKUImage.objects.bulk_create(image_objects)

        if product_status == 'CREATED':
            handle_product_moderation_status(product=sku.product, status='CREATED')
        
        return sku


class SKUUpdateSerializer(serializers.ModelSerializer):
    images = SKUImageSerializer(many=True)
    characteristics = SKUCharacteristicSerializer(many=True)
    class Meta:
        model = SKU
        fields = ('name', 'price', 'cost_price', 'discount',
                  'images', 'characteristics')

    def update(self, instance, validated_data):
        characteristics_data = validated_data.pop('characteristics', None)
        images_data = validated_data.pop('images', None)

        product_status = instance.product.status

        with transaction.atomic():
            product = instance.product
            if product.status in ['MODERATED', 'BLOCKED']:
                product.status = 'ON_MODERATION'
            product.save()
            
            instance = super().update(instance, validated_data)

            if images_data is not None:
                instance.images.all().delete()
                image_objects = [
                    SKUImage(sku=instance, **img_data)
                    for img_data in images_data
                ]
                SKUImage.objects.bulk_create(image_objects)
            
            if characteristics_data is not None:
                instance.characteristics.all().delete()
                characteristic_objects = [
                    SKUCharacteristic(sku=instance, **char_data)
                    for char_data in characteristics_data
                ]
                SKUCharacteristic.objects.bulk_create(characteristic_objects)
        
        handle_product_moderation_status(product=instance.product, status=product_status)

        return instance
    

class SKUDetailSerializer(serializers.ModelSerializer):
    images = SKUImageSerializer(many=True)
    characteristics = SKUCharacteristicSerializer(many=True)
    active_quantity = serializers.SerializerMethodField()
    class Meta:
        model = SKU
        fields = ('id', 'product_id', 'name', 'price', 'stock_quantity',
                  'reserved_quantity', 'active_quantity', 'article', 'cost_price', 
                  'discount', 'images', 'characteristics', 
                  'created_at', 'updated_at')
        
    def get_active_quantity(self, obj):
        return obj.stock_quantity - obj.reserved_quantity


class BlockingReasonSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockingReason
        fields = ('id', 'title', 'comment')


class FieldReportSerializer(serializers.ModelSerializer):
    sku_id = serializers.PrimaryKeyRelatedField(queryset=SKU.objects.all(), source='sku', allow_null=True)
    class Meta:
        model = FieldReport
        fields = ('id', 'field_name', 'sku_id', 'comment')


class SellerProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    characteristics = ProductCharacteristicsSerializer(many=True)
    skus = SKUDetailSerializer(many=True)
    blocking_reason = BlockingReasonSerializer(default=None)
    # blocking_reason_id = serializers.PrimaryKeyRelatedField(source='blocking_reason', read_only=True)
    field_reports = FieldReportSerializer(many=True, default=list)
    blocked = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ('id', 'seller_id', 'category_id', 'title', 'description', 'blocked',
                  'status', 'moderator_comment', 'images', 'characteristics', 'deleted', 'slug',
                  'skus', 'blocking_reason', 'field_reports', 'created_at', 'updated_at')
        
    def get_blocked(self, obj):
        return obj.status in [ProductStatus.BLOCKED, ProductStatus.HARD_BLOCKED]
    

class ModeratorSKUDetailSerializer(serializers.ModelSerializer):
    images = SKUImageSerializer(many=True)
    characteristics = SKUCharacteristicSerializer(many=True)
    class Meta:
        model = SKU
        fields = ('id', 'product_id', 'name', 'price', 'stock_quantity', 'article',
                  'discount', 'images', 'characteristics', 'created_at', 'updated_at')


class ModeratorProductDetailSerializer(SellerProductDetailSerializer):
    skus = ModeratorSKUDetailSerializer(many=True)


class B2CListProductSerializer(serializers.ModelSerializer):
    skus = ModeratorSKUDetailSerializer(many=True)
    cover_image = serializers.SerializerMethodField()
    min_price = serializers.IntegerField()
    
    class Meta:
        model = Product
        fields = ('id', 'seller_id', 'category_id', 'title', 'description', 'slug', 'cover_image', 'min_price',
                  'status', 'characteristics', 'skus', 'created_at')
    
    def get_cover_image(self, obj):
        # images уже предзагружены через prefetch_related('images')
        image = obj.images.order_by('ordering').first()
        return image.url if image else None
