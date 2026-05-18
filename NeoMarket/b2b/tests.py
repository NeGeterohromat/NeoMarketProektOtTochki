from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from app.models import Product, Category, Moderation
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

        token = RefreshToken.for_user(self.user)
        access_token = str(token.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        self.category = Category.objects.create(name='category')

        self.moderated_product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category.pk,
            status='MODERATED'
        )
        self.blocked_product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category.pk,
            status='BLOCKED'
        )
        self.hard_blocked_product = Product.objects.create(
            title='iPhone 15 Pro Max',
            description='Флагманский смартфон Apple 2024 года с чипом A17 Pro',
            category=self.category.pk,
            status='HARD_BLOCKED'
        )

    # тесты из https://contract.tochka-urfu.tech/quests/contraction-implement-us-b2b-03-edit-product-sku

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
        moderation = Moderation.objects.filter(event='EDITED', product=self.moderated_product).first()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'ON_MODERATION')
        self.assertIsNotNone(moderation)
        self.assertEqual(moderation.event, 'EDITED')

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
        moderation = Moderation.objects.filter(event='EDITED', product=self.blocked_product).first()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'ON_MODERATION')
        self.assertIsNotNone(moderation)
        self.assertEqual(moderation.event, 'EDITED')

    def text_edit_hard_blocked_returns_403(self):
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