import uuid
from django.db import models
from django.conf import settings


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class ProductStatus(models.TextChoices):
    CREATED = "CREATED", "Создан"
    ON_MODERATION = "ON_MODERATION", "На модерации"
    MODERATED = "MODERATED", "Опубликован"
    BLOCKED = "BLOCKED", "Заблокирован"


class Category(UUIDModel):
    name = models.CharField(max_length=255, unique=True, verbose_name="Название категории")
    parent_id = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='subcategories')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Product(UUIDModel):
    title = models.CharField(max_length=255, verbose_name="Название товара")
    description = models.TextField(blank=True, default="", verbose_name="Описание")
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.CREATED,
        verbose_name="Статус модерации"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name="Категория"
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="Продавец"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"

    def __str__(self):
        return f"{self.title} ({self.status})"


class ProductImage(UUIDModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Товар"
    )
    url = models.URLField(max_length=500, verbose_name="Ссылка на изображение")
    ordering = models.PositiveIntegerField(default=0, verbose_name="Порядок отображения")

    class Meta:
        ordering = ["ordering"]
        verbose_name = "Изображение товара"
        verbose_name_plural = "Изображения товаров"

    def __str__(self):
        return f"Изображение для {self.product.title} #{self.pk}"


class ProductCharacteristic(UUIDModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="characteristics",
        verbose_name="Товар"
    )
    name = models.CharField(max_length=255, verbose_name="Название характеристики")
    value = models.CharField(max_length=500, verbose_name="Значение характеристики")

    class Meta:
        verbose_name = "Характеристика товара"
        verbose_name_plural = "Характеристики товаров"

    def __str__(self):
        return f"{self.product.title}: {self.name} = {self.value}"


class SKU(UUIDModel):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="skus",
        verbose_name="Товар"
    )
    name = models.CharField(max_length=255, verbose_name="Название варианта (артикул/модификация)")
    price = models.PositiveIntegerField(verbose_name="Цена в копейках")
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name="Остаток на складе")
    article = models.CharField(max_length=255, blank=True, verbose_name="Артикул")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "SKU"
        verbose_name_plural = "SKU"

    def __str__(self):
        return f"{self.product.title} — {self.name}"


class SKUCharacteristic(UUIDModel):
    sku = models.ForeignKey(
        SKU,
        on_delete=models.CASCADE,
        related_name="characteristics",
        verbose_name="SKU"
    )
    name = models.CharField(max_length=255, verbose_name="Название характеристики")
    value = models.CharField(max_length=500, verbose_name="Значение характеристики")

    class Meta:
        verbose_name = "Характеристика SKU"
        verbose_name_plural = "Характеристики SKU"

    def __str__(self):
        return f"{self.sku.name}: {self.name} = {self.value}"


class InvoiceStatus(models.TextChoices):
    DRAFT = "DRAFT", "Черновик"
    CREATED = "CREATED", "Создана"
    ACCEPTED = "ACCEPTED", "Принята складом"
    REJECTED = "REJECTED", "Отклонена"


class Invoice(UUIDModel):
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name="Продавец"
    )
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        verbose_name="Статус"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата принятия складом")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Накладная"
        verbose_name_plural = "Накладные"

    def __str__(self):
        return f"Накладная #{self.pk} ({self.status})"


class InvoiceItem(UUIDModel):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Накладная"
    )
    sku = models.ForeignKey(
        SKU,
        on_delete=models.PROTECT,
        related_name="invoice_items",
        verbose_name="SKU"
    )
    quantity = models.PositiveIntegerField(verbose_name="Количество единиц")
    price_per_unit = models.PositiveIntegerField(verbose_name="Цена за единицу в копейках")

    class Meta:
        verbose_name = "Позиция накладной"
        verbose_name_plural = "Позиции накладных"

    def __str__(self):
        return f"{self.sku.name} × {self.quantity}"