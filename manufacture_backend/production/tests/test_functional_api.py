"""
功能冒烟测试：依赖 seed_demo_data 写入的【演示】数据，覆盖当前 API 能力清单中的主路径。

运行:
  cd manufacture_backend && . .venv/bin/activate && python manage.py test production.tests.test_functional_api -v 2
"""

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from production.models import DyeingOrder, Material, TransferOrder, Warehouse

User = get_user_model()


class DemoDataFunctionalAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo_data', '--force')

    def setUp(self):
        self.user = User.objects.create_user(username='apitest', password='secret-pass-9')
        self.client.force_authenticate(self.user)

    def test_unauthenticated_is_401(self):
        self.client.force_authenticate(user=None)
        r = self.client.get('/api/factories/')
        self.assertEqual(r.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_core_resources(self):
        endpoints = [
            '/api/factories/',
            '/api/suppliers/',
            '/api/warehouse-nodes/',
            '/api/materials/',
            '/api/products/',
            '/api/production-plans/',
            '/api/production-progress/',
            '/api/production-plan-details/',
            '/api/warehouse/',
            '/api/transfer-orders/',
            '/api/dyeing-orders/',
            '/api/weaving-orders/',
        ]
        for url in endpoints:
            with self.subTest(url=url):
                r = self.client.get(url)
                self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)

    def test_me_and_ai_config_get(self):
        r = self.client.get('/api/auth/me/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r.data['user']['username'], 'apitest')

        r2 = self.client.get('/api/ai/config/')
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertIn('key_configured', r2.data)

    def test_demo_factory_name_present(self):
        r = self.client.get('/api/factories/')
        self.assertTrue(any('【演示】' in str(x.get('name', '')) for x in r.data))

    def test_dyeing_partial_receipt(self):
        order = DyeingOrder.objects.filter(raw_material__name__startswith='【演示】').first()
        self.assertIsNotNone(order)
        raw_before = Material.objects.get(pk=order.raw_material_id).quantity
        r = self.client.post(
            f'/api/dyeing-orders/{order.id}/receipts/',
            {'quantity': '100.00', 'note': 'api test batch'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, msg=r.content)
        order.refresh_from_db()
        self.assertEqual(Decimal(str(order.received_quantity)), Decimal('100.00'))
        raw_after = Material.objects.get(pk=order.raw_material_id).quantity
        self.assertEqual(raw_before - raw_after, Decimal('100.00'))

    def test_transfer_complete_moves_stock(self):
        order = TransferOrder.objects.filter(status='draft', note__startswith='【演示】').first()
        self.assertIsNotNone(order)
        item = order.items.first()
        from_before = Warehouse.objects.get(
            warehouse=order.from_warehouse,
            product=item.product,
            color=item.color,
            size=item.size,
        ).quantity
        to_row, _ = Warehouse.objects.get_or_create(
            warehouse=order.to_warehouse,
            product=item.product,
            color=item.color,
            size=item.size,
            defaults={'quantity': 0},
        )
        to_before = to_row.quantity
        r = self.client.post(f'/api/transfer-orders/{order.id}/complete/')
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)
        from_after = Warehouse.objects.get(
            warehouse=order.from_warehouse,
            product=item.product,
            color=item.color,
            size=item.size,
        ).quantity
        to_after = Warehouse.objects.get(
            warehouse=order.to_warehouse,
            product=item.product,
            color=item.color,
            size=item.size,
        ).quantity
        self.assertEqual(from_before - from_after, item.quantity)
        self.assertEqual(to_after - to_before, item.quantity)
        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')

    def test_superuser_backup_export_zip(self):
        db_name = str(settings.DATABASES['default'].get('NAME', ''))
        if ':memory:' in db_name or db_name.startswith('file:memory'):
            self.skipTest('backup export expects a file-backed SQLite DB, not Django in-memory test DB')

        admin = User.objects.create_superuser(username='superzip', password='z9z9z9z9')
        self.client.force_authenticate(admin)
        r = self.client.get('/api/system/backup/export/')
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(r['Content-Type'], 'application/zip')
