from rest_framework import serializers
from app.models import Category, Product


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


# class CreateProductSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Product
#         fields = ('category_id', 'title', 'description',
#                   'images', 'characteristics')
