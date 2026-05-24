import responses
from django.urls import reverse
from django.conf import settings
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from app.models import Product, Category, SKU, BlockingReason, FieldReport
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