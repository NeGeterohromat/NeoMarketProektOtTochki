import responses
from django.urls import reverse
from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from app.models import Product, Category, SKU, BlockingReason, FieldReport, ProductImage, ProductCharacteristic
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
        url = reverse('product-detail', kwargs={'pk': self.moderated_product.pk})
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
        url = reverse('product-detail', kwargs={'pk': self.blocked_product.pk})
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
        url = reverse('product-detail', kwargs={'pk': self.hard_blocked_product.pk})
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
        url = reverse('product-detail', kwargs={'pk': self.foreign_product.pk})
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
        url = reverse('product-detail', kwargs={'pk': 'aa712d8e-2e30-452c-b3bf-12806f5a0a3e'})
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
        url = reverse('product-detail', kwargs={'pk': self.moderated_product.pk})
        data = {
            "title": "iPhone 15 Pro Max",
            "description": "Флагманский смартфон Apple 2024 года с чипом A17 Pro",
            "category_id": "hello world",
        }
        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ProductRetrieveAPITestCase(APITestCase):
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

        self.product = Product.objects.create(title='string', description='string',
                                              category=self.category, seller=self.user)
        
        self.other_product = Product.objects.create(title='string', description='string',
                                              category=self.category, seller=self.other_user)
        
        self.sku = SKU.objects.create(product=self.product, name='sku1', price=10,
                                      cost_price=10, article="hello", reserved_quantity=999)
        self.blocked_product = Product.objects.create(title='string', description='string',
                                              category=self.category, seller=self.user, status="BLOCKED")
        self.blocking_reason = BlockingReason.objects.create(product=self.blocked_product, title='string', comment='string')
        self.field_report = FieldReport.objects.create(product=self.blocked_product, field_name='string', comment='string')
        
    def test_get_moderated_product_returns_full_payload(self):
        url = reverse('product-detail', kwargs={'pk': self.product.pk})
        self.product.status = "MODERATED"
        self.product.save()
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('skus')[0].get('cost_price'), 10)
        self.assertEqual(response.data.get('blocking_reason'), None)

    def test_get_blocked_product_returns_blocking_reason_and_field_reports(self):
        url = reverse('product-detail', kwargs={'pk': self.blocked_product.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.data.get('blocking_reason_id'), self.blocking_reason.pk)
        self.assertEqual(response.data.get('field_reports')[0].get('field_name'), self.field_report.field_name)

    def test_get_others_product_returns_404(self):
        url = reverse('product-detail', kwargs={'pk': self.other_product.pk})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_nonexistent_returns_404(self):
        url = reverse('product-detail', kwargs={'pk': 'b691aea1-93d5-44ca-8feb-0a72d5e33f44'})
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
    def test_invalid_uuid_returns_400(self):
        url = url = '/api/v1/products/helloworld/'
        response = self.client.get(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SKUCreateAPITestCase(APITestCase):
    def setUp(self):
        self.url = reverse('sku-create')
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
    
    def test_first_sku_transitions_product_to_on_moderation(self):
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [{"url": "/s3/iphone15-front.jpg", "ordering": 0},],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.product.refresh_from_db()    
        self.assertEqual(self.product.status, 'ON_MODERATION')

    @responses.activate
    def test_first_sku_emits_created_event_to_moderation(self):
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [{"url": "/s3/iphone15-front.jpg", "ordering": 0},],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        base_url = settings.MODERATION_URL
        mod_url = f"{base_url}/api/v1/b2b/events/"
        responses.add(
            method=responses.POST,
            url=mod_url,
            json={"status": "Request accepted for processing."},
            status=status.HTTP_201_CREATED
        )
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(responses.calls), 1)
        executed_request = responses.calls[0].request
        self.assertEqual(executed_request.url, mod_url)
        self.assertEqual(executed_request.method, "POST")
        import json
        sent_body = json.loads(executed_request.body)
        self.assertEqual(sent_body["event_type"], "PRODUCT_CREATED")

    @responses.activate
    def test_second_sku_no_state_change(self):
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [{"url": "/s3/iphone15-front.jpg", "ordering": 0},],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        base_url = settings.MODERATION_URL
        mod_url = f"{base_url}/api/v1/b2b/events/"
        responses.add(
            method=responses.POST,
            url=mod_url,
            json={"status": "Request accepted for processing."},
            status=status.HTTP_201_CREATED
        )
        # первый запрос
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # меняем статус, чтобы проверить, что втоой запрос его не изменит
        self.product.status = 'MODERATED'
        self.product.save()
        # второй запрос
        response = self.client.post(self.url, data, format='json')
        # при втором запросе событие не уходит в Moderation:
        self.assertEqual(len(responses.calls), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'MODERATED')

    def test_add_sku_to_hard_blocked_returns_403(self):
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [{"url": "/s3/iphone15-front.jpg", "ordering": 0},],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        self.product.status = 'HARD_BLOCKED'
        self.product.save()
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_product_id_does_not_exist_returns_404(self):
        data = {
            "product_id": "aa712d8e-2e30-452c-b3bf-12806f5a0a3e",
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [{"url": "/s3/iphone15-front.jpg", "ordering": 0},],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_price_below_zero_returns_400(self):
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": -10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [{"url": "/s3/iphone15-front.jpg", "ordering": 0},],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cost_price_below_zero_returns_400(self):
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": -10,
            "article": "string",
            "images": [{"url": "/s3/iphone15-front.jpg", "ordering": 0},],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_empty_name_returns_400(self):
        data = {
            "product_id": self.product.pk,
            "name": "",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [{"url": "/s3/iphone15-front.jpg", "ordering": 0},],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_image_returns_400(self):
        data = {
            "product_id": self.product.pk,
            "name": "string",
            "price": 10,
            "discount": 10,
            "cost_price": 10,
            "article": "string",
            "images": [],
            "characteristics": [{"name": "Бренд", "value": "Apple"},]
        }
        response = self.client.post(self.url, data, format='json')
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


class B2CListProductAPITestCase(APITestCase):
    def setUp(self):
        self.url = reverse('b2c-product-list')
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

        self.category1 = Category.objects.create(name='Electronics')
        self.category2 = Category.objects.create(name='Books')

        # MODERATED product with active SKU
        self.moderated_product = Product.objects.create(
            title='iPhone 15',
            description='Apple smartphone',
            category=self.category1,
            seller=self.user,
            status='MODERATED'
        )
        self.active_sku = SKU.objects.create(
            product=self.moderated_product,
            name='128GB',
            price=100000,
            stock_quantity=10,
            reserved_quantity=0
        )
        ProductImage.objects.create(product=self.moderated_product, url='/images/iphone.jpg', ordering=0)

        # MODERATED product with only reserved SKU (no active quantity)
        self.no_active_product = Product.objects.create(
            title='iPhone 14',
            description='Older model',
            category=self.category1,
            seller=self.user,
            status='MODERATED'
        )
        self.reserved_sku = SKU.objects.create(
            product=self.no_active_product,
            name='256GB',
            price=90000,
            stock_quantity=5,
            reserved_quantity=5  # Все зарезервировано
        )

        # BLOCKED product (should not appear)
        self.blocked_product = Product.objects.create(
            title='Blocked Phone',
            description='Blocked item',
            category=self.category1,
            seller=self.user,
            status='BLOCKED'
        )
        self.blocked_sku = SKU.objects.create(
            product=self.blocked_product,
            name='64GB',
            price=50000,
            stock_quantity=10
        )

        self.hard_blocked_product = Product.objects.create(
            title='Hard blocked Phone',
            description='Hard blocked item',
            category=self.category1,
            seller=self.user,
            status='HARD_BLOCKED'
        )
        self.hard_blocked_sku = SKU.objects.create(
            product=self.hard_blocked_product,
            name='64GB',
            price=50000,
            stock_quantity=10
        )

        # Product with same seller
        self.same_seller_product = Product.objects.create(
            title='Samsung Galaxy',
            description='Samsung smartphone',
            category=self.category1,
            seller=self.user,
            status='MODERATED'
        )
        self.same_seller_sku = SKU.objects.create(
            product=self.same_seller_product,
            name='128GB',
            price=80000,
            stock_quantity=15
        )

        # Product from other seller
        self.other_seller_product = Product.objects.create(
            title='Sony Xperia',
            description='Sony smartphone',
            category=self.category2,
            seller=self.other_user,
            status='MODERATED'
        )
        self.other_seller_sku = SKU.objects.create(
            product=self.other_seller_product,
            name='256GB',
            price=70000,
            stock_quantity=20
        )

        # Set service key authentication
        self.client.credentials(HTTP_X_SERVICE_KEY=settings.MODERATION_TOKEN)

    def test_catalog_missing_service_key_returns_401(self):
        """Без X-Service-Key должен вернуться 401"""
        self.client.credentials()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_catalog_returns_moderated_in_stock_products(self):
        """Возвращаются только MODERATED товары с active_quantity > 0"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('iPhone 15', titles)
        self.assertIn('Samsung Galaxy', titles)
        self.assertIn('Sony Xperia', titles)
        self.assertNotIn('Blocked Phone', titles)
        self.assertNotIn('iPhone 14', titles)

    def test_catalog_excludes_hard_blocked(self):
        """Заблокированные товары не возвращаются"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertNotIn('Blocked Phone', titles)
        self.assertNotIn('Hard blocked Phone', titles)

    def test_catalog_response_has_no_cost_price(self):
        """cost_price не возвращается"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        iphone = next(p for p in response.data['results'] if p['title'] == 'iPhone 15')
        self.assertEqual(iphone.get('cost_price'), None)

    def test_cover_image_returns_first_image_by_order(self):
        """cover_image берёт изображение с наименьшим order"""
        ProductImage.objects.create(product=self.moderated_product, url='/images/iphone-back.jpg', ordering=1)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        iphone = next(p for p in response.data['results'] if p['title'] == 'iPhone 15')
        self.assertEqual(iphone['cover_image'], '/images/iphone.jpg')

    def test_min_price_is_calculated_correctly(self):
        """min_price = минимальная цена среди SKU"""
        SKU.objects.create(product=self.moderated_product, name='512GB', price=150000, stock_quantity=5)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        iphone = next(p for p in response.data['results'] if p['title'] == 'iPhone 15')
        self.assertEqual(iphone['min_price'], 100000)

    def test_filter_by_category_id(self):
        """Фильтрация по category_id"""
        response = self.client.get(self.url + f'?category_id={self.category1.pk}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('iPhone 15', titles)
        self.assertNotIn('Sony Xperia', titles)  # другая категория

    def test_filter_by_seller_id(self):
        """Фильтрация по seller_id"""
        response = self.client.get(self.url + f'?seller_id={self.user.pk}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('iPhone 15', titles)
        self.assertNotIn('Sony Xperia', titles)  # другой продавец

    def test_filter_by_search_in_title(self):
        """Текстовый поиск по title"""
        response = self.client.get(self.url + '?search=iPhone')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('iPhone 15', titles)
        self.assertNotIn('Samsung Galaxy', titles)

    def test_filter_by_search_in_description(self):
        """Текстовый поиск по description"""
        response = self.client.get(self.url + '?search=smartphone')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('iPhone 15', titles)
        self.assertIn('Samsung Galaxy', titles)

    def test_filter_by_ids(self):
        """Фильтрация по списку UUID"""
        response = self.client.get(self.url + f'?ids={self.moderated_product.pk}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.moderated_product.pk))

    def test_batch_ids_returns_visible_subset(self):
        """Фильтрация по нескольким UUID"""
        response = self.client.get(self.url + f'?ids={self.moderated_product.pk},{self.same_seller_product.pk}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_min_price(self):
        """Фильтрация по минимальной цене"""
        response = self.client.get(self.url + '?min_price=90000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('iPhone 15', titles)  # 100000
        self.assertNotIn('Samsung Galaxy', titles)  # 80000
        self.assertNotIn('Sony Xperia', titles)  # 70000

    def test_filter_by_max_price(self):
        """Фильтрация по максимальной цене"""
        response = self.client.get(self.url + '?max_price=75000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertNotIn('iPhone 15', titles)  # 100000
        self.assertNotIn('Samsung Galaxy', titles)  # 80000
        self.assertIn('Sony Xperia', titles)  # 70000

    def test_sort_by_price_asc(self):
        """Сортировка по цене (возрастание)"""
        response = self.client.get(self.url + '?sort=price_asc')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [p['min_price'] for p in response.data['results']]
        self.assertEqual(prices, sorted(prices))

    def test_sort_by_price_desc(self):
        """Сортировка по цене (убывание)"""
        response = self.client.get(self.url + '?sort=price_desc')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        prices = [p['min_price'] for p in response.data['results']]
        self.assertEqual(prices, sorted(prices, reverse=True))

    def test_sort_by_date_desc(self):
        """Сортировка по дате (новые сначала)"""
        response = self.client.get(self.url + '?sort=date_desc')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Новые товары должны быть в начале
        created_dates = [p['created_at'] for p in response.data['results']]
        self.assertEqual(created_dates, sorted(created_dates, reverse=True))

    def test_filter_by_characteristics(self):
        """Фильтрация по характеристикам"""
        ProductCharacteristic.objects.create(product=self.moderated_product, name='brand', value='Apple')
        ProductCharacteristic.objects.create(product=self.same_seller_product, name='brand', value='Samsung')
        response = self.client.get(self.url + '?filters[brand]=Apple')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        titles = [p['title'] for p in response.data['results']]
        self.assertIn('iPhone 15', titles)
        self.assertNotIn('Samsung Galaxy', titles)