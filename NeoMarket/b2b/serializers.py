from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from django.core.validators import RegexValidator
from rest_framework import serializers
from rest_framework.exceptions import NotFound
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
    Reservation,
    ModerationEvent,
)
from .services import handle_product_moderation_status, send_sku_out_of_stock_event, send_product_blocked
from .exceptions import InsufficientStockException, OutOfStockException


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
        read_only_fields = ('id',)


class FieldReportSerializer(serializers.ModelSerializer):
    sku_id = serializers.PrimaryKeyRelatedField(queryset=SKU.objects.all(), source='sku', allow_null=True, required=False)
    class Meta:
        model = FieldReport
        fields = ('id', 'field_name', 'sku_id', 'comment')
        read_only_fields = ('id',)


class ProductDetailSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True)
    characteristics = ProductCharacteristicsSerializer(many=True)
    skus = SKUNestedSerializer(many=True)
    blocking_reason_id = serializers.UUIDField(source='blocking_reason.id', allow_null=True)
    field_reports = FieldReportSerializer(many=True, default=list)
    blocked = serializers.SerializerMethodField()
    class Meta:
        model = Product
        fields = ('id', 'seller_id', 'category_id', 'title', 'description', 'blocked',
                  'status', 'moderator_comment', 'images', 'characteristics', 'deleted', 'slug',
                  'skus', 'blocking_reason_id', 'field_reports', 'created_at', 'updated_at')
        
    def get_blocked(self, obj):
        return obj.status in [ProductStatus.BLOCKED, ProductStatus.HARD_BLOCKED]


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


class B2CSKUDetailSerializer(serializers.ModelSerializer):
    images = SKUImageSerializer(many=True)
    characteristics = SKUCharacteristicSerializer(many=True)
    active_quantity = serializers.SerializerMethodField()
    class Meta:
        model = SKU
        fields = ('id', 'product_id', 'name', 'price', 'active_quantity', 'article',
                  'discount', 'images', 'characteristics', 'created_at', 'updated_at')
        
    def get_active_quantity(self, obj):
        return obj.stock_quantity - obj.reserved_quantity


class B2CListProductSerializer(serializers.ModelSerializer):
    skus = B2CSKUDetailSerializer(many=True)
    cover_image = serializers.SerializerMethodField()
    min_price = serializers.IntegerField()
    
    class Meta:
        model = Product
        fields = ('id', 'seller_id', 'category_id', 'title', 'description', 'slug', 'cover_image', 'min_price',
                  'status', 'characteristics', 'skus', 'created_at')
    
    def get_cover_image(self, obj):
        # images предзагружены через Prefetch с order_by('ordering')
        # используем предзагруженный менеджер, чтобы избежать дополнительного SQL запроса
        images = obj.images.all()
        if images:
            # Первый элемент уже отсортирован благодаря Prefetch
            return images[0].url if hasattr(images[0], 'url') else None
        return None


class B2CBatchProductSerializer(serializers.Serializer):
    product_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True
    )


class B2CDetailProductSerializer(serializers.ModelSerializer):
    skus = B2CSKUDetailSerializer(many=True)
    images = ProductImageSerializer(many=True)
    characteristics = ProductCharacteristicsSerializer(many=True)
    
    class Meta:
        model = Product
        fields = ('id', 'seller_id', 'category_id', 'title', 'slug', 'description', 'status',
                  'images', 'characteristics', 'skus', 'created_at', 'updated_at')


class ReservationItemSerializer(serializers.Serializer):
    sku_id = serializers.UUIDField()
    quantity = serializers.IntegerField()


class ReserveSerializer(serializers.ModelSerializer):
    idempotency_key = serializers.UUIDField(write_only=True, required=True) # только для создания
    items = ReservationItemSerializer(many=True, write_only=True)
    reserved_at = serializers.DateTimeField(read_only=True)
    status = serializers.SerializerMethodField()

    def get_status(self, obj):
        return 'RESERVED'

    class Meta:
        model = Reservation
        fields = ('idempotency_key', 'order_id', 'items', 'status', 'reserved_at')

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        idempotency_key = validated_data['idempotency_key']
        order_id = validated_data['order_id']
        
        with transaction.atomic():
            # 1. Проверяем, есть ли уже запись с таким idempotency_key
            existing_reservation = Reservation.objects.filter(
                idempotency_key=idempotency_key
            ).select_for_update().first()
            
            if existing_reservation:
                # Возвращаем существующую запись (идемпотентный ответ)
                existing_reservation._is_new = False
                return existing_reservation

            # 2. Блокируем и проверяем ВСЕ SKU
            skus_to_update = []
            for item_data in items_data:
                sku = SKU.objects.select_for_update().select_related('product').get(pk=item_data['sku_id'])

                if sku.product.status in [ProductStatus.BLOCKED, ProductStatus.HARD_BLOCKED]:
                    raise serializers.ValidationError(
                        {'items': f'Товар "{sku.product.title}" заблокирован и не доступен для резервации'}
                    )

                available = sku.stock_quantity - sku.reserved_quantity
                
                if item_data['quantity'] > available:
                    if available == 0:
                        raise OutOfStockException(
                            sku_id=str(sku.pk),
                            sku_name=sku.name
                        )
                    else:
                        raise InsufficientStockException(
                            sku_id=str(sku.pk),
                            sku_name=sku.name,
                            available=available,
                            requested=item_data['quantity']
                        )
                
                sku.reserved_quantity += item_data['quantity']
                skus_to_update.append(sku)
            
            # 3. Сохраняем все SKU
            for sku in skus_to_update:
                sku.save(update_fields=['reserved_quantity'])
            
            # 4. Только потом создаем Reservation
            # Конвертируем UUID в строки для JSON сериализации
            items_for_save = [
                {'sku_id': str(item['sku_id']), 'quantity': item['quantity']}
                for item in items_data
            ]
            try:
                reservation = Reservation.objects.create(
                    idempotency_key=idempotency_key,
                    order_id=order_id,
                    items=items_for_save
                )
            except IntegrityError:
                # Запись появилась между проверкой и созданием (race condition)
                existing = Reservation.objects.filter(idempotency_key=idempotency_key).first()
                if existing:
                    existing._is_new = False
                    return existing
                raise serializers.ValidationError(
                    {'idempotency_key': 'Резервация с таким idempotency_key уже существует'}
                )
        
            reservation._is_new = True
            
            # Отправляем событие SKU_OUT_OF_STOCK для SKU, у которых остаток стал 0
            for sku in skus_to_update:
                available_after = sku.stock_quantity - sku.reserved_quantity
                if available_after == 0:
                    # Отправляем событие после коммита транзакции
                    transaction.on_commit(lambda s=sku: send_sku_out_of_stock_event(s))
            
        return reservation


class UnreserveSerializer(serializers.Serializer):
    order_id = serializers.UUIDField(write_only=True, required=True)
    items = ReservationItemSerializer(many=True, write_only=True)
    
    def validate(self, data):
        order_id = data['order_id']
        
        try:
            self.reservation = Reservation.objects.get(order_id=order_id)
            self.reservation_exists = True
        except Reservation.DoesNotExist:
            self.reservation = None
            self.reservation_exists = False
            return data
        
        for item in data['items']:
            sku_id = str(item['sku_id'])
            quantity = item['quantity']
            
            matching_item = next(
                (i for i in self.reservation.items if str(i['sku_id']) == sku_id),
                None
            )
            
            if not matching_item:
                raise serializers.ValidationError(
                    {'items': f'SKU {sku_id} не входит в резервацию order_id={order_id}'}
                )
            
            if quantity > matching_item['quantity']:
                raise serializers.ValidationError(
                    {'items': f'Количество {quantity} превышает зарезервированное {matching_item["quantity"]} для SKU {sku_id}'}
                )
        
        return data
    
    def save(self):
        from django.db import transaction
        from app.models import SKU
        
        order_id = self.validated_data['order_id']
        items_data = self.validated_data['items']

        if not self.reservation_exists:
            return None
        
        with transaction.atomic():
            reservation = Reservation.objects.select_for_update().get(order_id=order_id)
            
            skus_to_update = []
            for item_data in items_data:
                sku = SKU.objects.select_for_update().get(pk=item_data['sku_id'])
                sku.reserved_quantity -= item_data['quantity']
                
                if sku.reserved_quantity < 0:
                    sku.reserved_quantity = 0
                
                skus_to_update.append(sku)
            
            for sku in skus_to_update:
                sku.save(update_fields=['reserved_quantity'])
            
            updated_items = []
            for item in reservation.items:
                sku_id = str(item['sku_id'])
                quantity = item['quantity']
                
                unreserved_qty = next(
                    (i['quantity'] for i in items_data if str(i['sku_id']) == sku_id),
                    0
                )
                
                new_quantity = quantity - unreserved_qty
                if new_quantity > 0:
                    updated_items.append({
                        'sku_id': str(item['sku_id']),
                        'quantity': new_quantity
                    })
            
            if not updated_items:
                reservation.delete()
                return None
            
            reservation.items = updated_items
            reservation.save(update_fields=['items'])
        
        return reservation
    

class ModerationEventSerializer(serializers.ModelSerializer):
    blocking_reason = BlockingReasonSerializer(default=None)
    field_reports = FieldReportSerializer(many=True, default=list)
    product_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = ModerationEvent
        fields = ('idempotency_key', 'product_id', 'event_type', 'moderator_id', 'moderator_comment',
                  'blocking_reason', 'field_reports', 'hard_block', 'occurred_at')
        extra_kwargs = {
            'idempotency_key': {'validators': []}
        }
    
    def validate_product_id(self, value):
        """Проверяем существование товара и возвращаем 404 если не найден"""
        try:
            return Product.objects.get(pk=value)
        except Product.DoesNotExist:
            raise NotFound({'detail': 'Товар не найден'})
    
    def create(self, validated_data):
        blocking_reason_data = validated_data.pop('blocking_reason', None)
        field_reports_data = validated_data.pop('field_reports', [])

        event_type_data = validated_data['event_type']
        is_hard_blocked = validated_data['hard_block']

        product = validated_data['product_id']

        with transaction.atomic():
            # проверка idempotency_key
            idempotency_key = validated_data['idempotency_key']
            existing_event = ModerationEvent.objects.filter(
                idempotency_key=idempotency_key
            ).select_for_update().first()
            if existing_event:
                return existing_event
            
            product = Product.objects.select_for_update().get(pk=product.pk)

            # проверка типа события
            if event_type_data == ModerationEvent.EventType.MODERATED:
                # Удаляем blocking_reason, если он существует
                try:
                    product.blocking_reason.delete()
                except BlockingReason.DoesNotExist:
                    pass
                # удалить все field reports
                product.field_reports.all().delete()
                # обновляем толкьо статус, т.к. blocked вычисляется само от статуса
                product.status = ProductStatus.MODERATED
                product.save(update_fields=['status'])
            elif event_type_data == ModerationEvent.EventType.BLOCKED:
                if not blocking_reason_data:
                    raise serializers.ValidationError({
                        'blocking_reason': 'Необходимо указать причину блокировки'
                    })
                # Удаляем старый blocking_reason, если он существует
                try:
                    product.blocking_reason.delete()
                except BlockingReason.DoesNotExist:
                    pass
                BlockingReason.objects.create(
                    product=product,
                    title=blocking_reason_data['title'],
                    comment=blocking_reason_data['comment'],
                )
                product.field_reports.all().delete()
                field_reports_objects = [
                    FieldReport(product=product, **report_data)
                    for report_data in field_reports_data
                ]
                FieldReport.objects.bulk_create(field_reports_objects)
                
                product.status = ProductStatus.HARD_BLOCKED if is_hard_blocked else ProductStatus.BLOCKED
                product.save(update_fields=['status'])

            moderation_event = ModerationEvent.objects.create(**validated_data)
        
            if event_type_data == ModerationEvent.EventType.BLOCKED:
                transaction.on_commit(
                    lambda key=idempotency_key, product=product.pk, reason=blocking_reason_data['title'], hard=is_hard_blocked : send_product_blocked(
                        key, product, reason, hard
                    )
                )
        return moderation_event