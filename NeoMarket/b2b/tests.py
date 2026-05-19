from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from app.models import Product, Category, SKU
from users.models import User


class ProductCreateAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            password='12345678User',
            email='user@mail.com',
            company_name='urfu',
        )

        token = RefreshToken.for_user(self.user)
        access_token = str(token.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        self.category = Category.objects.create(name='category')
        self.url = reverse('product-create')

    # тесты из https://contract.tochka-urfu.tech/quests/contraction-implement-us-b2b-01-create-product

    def test_create_product_returns_201_with_created_status(self):
        data = {
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
            "category_id": self.category.pk,
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
                {
                "url": "/s3/iphone15-back.jpg",
                "ordering": 1
                }
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
                {
                "name": "Страна-производитель",
                "value": "Китай"
                }
            ]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data.get('status'), 'CREATED')

    def test_seller_id_taken_from_jwt(self):
        data = {
            "title": "Название",
            "description": "Тестовое описание",
            "category_id": self.category.pk,
            "images": [{"url": "/s3/image.jpg", "ordering": 0}]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data.get('seller_id')), str(self.user.pk))
        product = Product.objects.get(id=response.data['id'])
        self.assertEqual(product.seller.pk, self.user.pk)

    def test_missing_images_returns_400(self):
        data = {
            "title": "Название",
            "description": "Тестовое описание",
            "category_id": self.category.pk,
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_category_returns_400(self):
        data = {
            "title": "Название",
            "description": "Тестовое описание",
            "images": [{"url": "/s3/image.jpg", "ordering": 0}],
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_category_id_returns_400(self):
        data = {
            "title": "Название",
            "description": "Тестовое описание",
            "category_id": "Сам ты инвалид",
            "images": [{"url": "/s3/image.jpg", "ordering": 0}]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # тесты из https://github.com/URFU2026-NeoMarket/neomarket-canon/blob/main/flows/b2b-flows.md#%D0%B2%D0%B0%D0%BB%D0%B8%D0%B4%D0%B0%D1%86%D0%B8%D1%8F-%D0%B8-%D0%BE%D1%88%D0%B8%D0%B1%D0%BA%D0%B8

    def test_blank_title_returns_400(self):
        data = {
            "title": "",
            "description": "Тестовое описание",
            "category_id": self.category.pk,
            "images": [{"url": "/s3/image.jpg", "ordering": 0}]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_title_is_longer_than_255_returns_400(self):
        title = "".join(['a' for _ in range(256)])
        data = {
            "title": title,
            "description": "Тестовое описание",
            "category_id": self.category.pk,
            "images": [{"url": "/s3/image.jpg", "ordering": 0}]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_category_id_do_not_exist_returns_400(self):
        data = {
            "title": "Название",
            "description": "Тестовое описание",
            "category_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "images": [{"url": "/s3/image.jpg", "ordering": 0}]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_images_returns_400(self):
        data = {
            "title": "Название",
            "description": "Тестовое описание",
            "category_id": self.category.pk,
            "images": []
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductUpdateAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            password='12345678User',
            email='user@mail.com',
            company_name='urfu',
        )
        self.other_user = User.objects.create_user(
            username='user2',
            password='12345678User',
            email='user2@mail.com',
            company_name='urfu',
        )

        token = RefreshToken.for_user(self.user)
        access_token = str(token.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        self.category = Category.objects.create(name='category')

        self.moderated_product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category,
            seller=self.user,
            status='MODERATED'
        )
        self.blocked_product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category,
            seller=self.user,
            status='BLOCKED'
        )
        self.hard_blocked_product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category,
            seller=self.user,
            status='HARD_BLOCKED'
        )
        self.foreign_product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category,
            seller=self.other_user,
            status='HARD_BLOCKED'
        )

    def test_edit_moderated_product_returns_to_on_moderation(self):
        url = reverse('product-update', kwargs={'pk': self.moderated_product.pk})
        data = {
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
            "category_id": self.category.pk,
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
                {
                "url": "/s3/iphone15-back.jpg",
                "ordering": 1
                }
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
                {
                "name": "Страна-производитель",
                "value": "Китай"
                }
            ]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'ON_MODERATION')

    def test_edit_blocked_product_returns_to_on_moderation(self):
        url = reverse('product-update', kwargs={'pk': self.blocked_product.pk})
        data = {
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
            "category_id": self.category.pk,
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
                {
                "url": "/s3/iphone15-back.jpg",
                "ordering": 1
                }
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
                {
                "name": "Страна-производитель",
                "value": "Китай"
                }
            ]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'ON_MODERATION')

    def test_edit_hard_blocked_returns_403(self):
        url = reverse('product-update', kwargs={'pk': self.hard_blocked_product.pk})
        data = {
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
            "category_id": self.category.pk,
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
            ]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_others_product_returns_403(self):
        url = reverse('product-update', kwargs={'pk': self.foreign_product.pk})
        data = {
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
            "category_id": self.category.pk,
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
            ]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_product_not_found_returns_404(self):
        url = reverse('product-update', kwargs={'pk': 'aa712d8e-2e30-452c-b3bf-12806f5a0a3e'})
        data = {
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
            "category_id": self.category.pk,
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
            ]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_invalid_data_returns_400(self):
        url = reverse('product-update', kwargs={'pk': self.moderated_product.pk})
        data = {
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
            "category_id": "hello world",
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SKUUpdateAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user',
            password='12345678User',
            email='user@mail.com',
            company_name='urfu',
        )
        self.other_user = User.objects.create_user(
            username='user2',
            password='12345678User',
            email='user2@mail.com',
            company_name='urfu',
        )

        token = RefreshToken.for_user(self.user)
        access_token = str(token.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        self.category = Category.objects.create(name='category')

        self.product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category,
            seller=self.user,
        )
        self.other_product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category,
            seller=self.other_user,
        )

        self.sku = SKU.objects.create(
            product=self.product,
            name='sku1',
            price=10,
            cost_price=10,
            article="hello",
            reserved_quantity=999
        )
        self.other_sku = SKU.objects.create(
            product=self.other_product,
            name='sku1',
            price=10,
            cost_price=10,
            article="hello",
            reserved_quantity=999
        )
        
    def test_reserves_preserved_after_sku_edit(self):
        url = reverse('sku-update', kwargs={'pk': self.sku.pk})
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
            ]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.data.get('reserved_quantity'), 999)

    def test_sku_not_found_returns_404(self):
        url = reverse('sku-update', kwargs={'pk': 'aa712d8e-2e30-452c-b3bf-12806f5a0a3e'})
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
            ]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_foreign_sku_returns_403(self):
        url = reverse('sku-update', kwargs={'pk': self.other_sku.pk})
        data = {
            "product_id": self.other_product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [
                {
                "url": "/s3/iphone15-front.jpg",
                "ordering": 0
                },
            ],
            "characteristics": [
                {
                "name": "Бренд",
                "value": "Apple"
                },
            ]
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invalid_data_returns_400(self):
        url = reverse('sku-update', kwargs={'pk': self.sku.pk})
        data = {
            "product_id": self.product.pk,
            "name": 1,
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": 100
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)