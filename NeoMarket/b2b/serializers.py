from django.db import transaction
from rest_framework import serializers
from app.models import Category, Product, ProductCharacteristic, ProductImage


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
    class Meta:
        model = ProductImage
        fields = ('id', 'url', 'ordering')
        read_only_fields = ('id',)


class ProductCreateSerializer(serializers.ModelSerializer):
    characteristics = ProductCharacteristicsSerializer(many=True)
    images = ProductImageSerializer(many=True)
    seller = serializers.HiddenField(default=serializers.CurrentUserDefault())
    category_id = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all(), source='category')
    class Meta:
        model = Product
        fields = ('seller', 'category_id', 'title', 'description', 'images', 'characteristics',)

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
    

# доделать
# class ProductSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Product
#         fields = ('id', 'seller_id', 'category_id', 'title', 'description',
#                   'status', 'images', 'characteristics',
#                   'skus', 'created_at', 'updated_at')
