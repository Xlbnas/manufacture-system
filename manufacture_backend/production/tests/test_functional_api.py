"""
功能冒烟测试：依赖 seed_demo_data 写入的【演示】数据，覆盖当前 API 能力清单中的主路径。

运行:
  cd manufacture_backend && . .venv/bin/activate && python manage.py test production.tests.test_functional_api -v 2
"""

from datetime import date
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APITestCase

from production.models import (
    DyeingOrder,
    Factory,
    Material,
    Product,
    ProductionPlanDetail,
    Supplier,
    TransferOrder,
    Warehouse,
    WarehouseNode,
    WeavingOrder,
)

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

    def test_post_factory_auto_creates_factory_warehouse_node(self):
        r = self.client.post(
            '/api/factories/',
            {'name': '【API测】武昌 八车间', 'location': '武昌', 'workshop': '八'},
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, msg=r.content)
        fid = r.data['id']
        factory = Factory.objects.get(pk=fid)
        wn = WarehouseNode.objects.filter(factory=factory, warehouse_type='factory', is_active=True).first()
        self.assertIsNotNone(wn)
        self.assertIn('工厂仓', wn.name)
        self.assertIn('武昌', wn.name)
        self.assertIn('八', wn.name)

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
        self.assertEqual(raw_before, raw_after, '登记染色到货不应扣减坯布库存行')

    def test_dyeing_create_deducts_raw_delete_restores(self):
        raw = Material.objects.filter(name__startswith='【演示】', type='raw_fabric').first()
        self.assertIsNotNone(raw)
        dye_sup = Supplier.objects.filter(type='染厂', name__startswith='【演示】').first()
        self.assertIsNotNone(dye_sup)
        wh = WarehouseNode.objects.filter(name__startswith='【演示】').first()
        self.assertIsNotNone(wh)
        qty_before = Material.objects.get(pk=raw.id).quantity
        body = {
            'raw_material_id': raw.id,
            'supplier_id': dye_sup.id,
            'output_warehouse_id': wh.id,
            'output_name': '【测试】API建单染色布',
            'output_color': '测试色',
            'quantity': '15.00',
        }
        r = self.client.post('/api/dyeing-orders/', body, format='json')
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, msg=r.content)
        oid = r.data['id']
        raw.refresh_from_db()
        self.assertEqual(Decimal(str(qty_before)) - Decimal(str(raw.quantity)), Decimal('15.00'))
        r2 = self.client.delete(f'/api/dyeing-orders/{oid}/')
        self.assertEqual(r2.status_code, status.HTTP_204_NO_CONTENT)
        raw.refresh_from_db()
        self.assertEqual(Decimal(str(raw.quantity)), Decimal(str(qty_before)))

    def test_production_plan_complete_production_writes_warehouse(self):
        plan = ProductionPlanDetail.objects.filter(name__contains='排产单A').first()
        self.assertIsNotNone(plan)
        product = Product.objects.filter(production_template_key='f116').first()
        self.assertIsNotNone(product)
        self.assertEqual(plan.template, 'f116')
        wh = WarehouseNode.objects.filter(name__startswith='【演示】武昌工厂仓').first()
        self.assertIsNotNone(wh)
        stock_before, _ = Warehouse.objects.get_or_create(
            warehouse=wh,
            product=product,
            color='军绿',
            size='S',
            defaults={'quantity': 0},
        )
        q0 = stock_before.quantity
        r = self.client.post(
            f'/api/production-plan-details/{plan.id}/complete-production/',
            {
                'lines': [{'size_name': 'S', 'model_index': 0, 'qty_this_batch': 5}],
                'warehouse_id': wh.id,
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)
        stock_before.refresh_from_db()
        self.assertEqual(stock_before.quantity, q0 + 5)

    def test_dyeing_close_with_loss_blocks_more_receipts(self):
        order = DyeingOrder.objects.filter(raw_material__name__startswith='【演示】').first()
        self.assertIsNotNone(order)
        oid = order.id
        self.client.post(
            f'/api/dyeing-orders/{oid}/receipts/',
            {'quantity': '120.50', 'note': 'partial'},
            format='json',
        )
        r_close = self.client.post(
            f'/api/dyeing-orders/{oid}/close-with-loss/',
            {'note': 'test loss'},
            format='json',
        )
        self.assertEqual(r_close.status_code, status.HTTP_200_OK, msg=r_close.content)
        order.refresh_from_db()
        self.assertEqual(order.status, 'completed')
        self.assertGreater(Decimal(str(order.lost_quantity)), Decimal('0'))
        rx = self.client.post(
            f'/api/dyeing-orders/{oid}/receipts/',
            {'quantity': '1.00'},
            format='json',
        )
        self.assertEqual(rx.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weaving_delete_allowed_without_receipt_blocked_after_receive(self):
        sup = Supplier.objects.filter(type='布厂', name__startswith='【演示】').first()
        wh = WarehouseNode.objects.filter(name__startswith='【演示】武昌工厂仓').first()
        self.assertIsNotNone(sup)
        self.assertIsNotNone(wh)

        wa = WeavingOrder.objects.create(
            supplier=sup,
            fabric_name='【演示】删除测-未到货',
            quantity=Decimal('50.00'),
            inbound_warehouse=wh,
            expected_delivery=date.today(),
        )
        r_ok = self.client.delete(f'/api/weaving-orders/{wa.id}/')
        self.assertEqual(r_ok.status_code, status.HTTP_204_NO_CONTENT)

        wb = WeavingOrder.objects.create(
            supplier=sup,
            fabric_name='【演示】删除测-已到货',
            quantity=Decimal('50.00'),
            inbound_warehouse=wh,
            expected_delivery=date.today(),
        )
        self.client.post(
            f'/api/weaving-orders/{wb.id}/receipts/',
            {'quantity': '10.00', 'note': 'receive'},
            format='json',
        )
        r_bad = self.client.delete(f'/api/weaving-orders/{wb.id}/')
        self.assertEqual(r_bad.status_code, status.HTTP_400_BAD_REQUEST)

    def test_warehouse_list_filters_by_factory_warehouse_and_product(self):
        wh = WarehouseNode.objects.filter(warehouse_type='factory', name__startswith='【演示】').first()
        product = Product.objects.filter(production_template_key='f116').first()
        self.assertIsNotNone(wh)
        self.assertIsNotNone(product)
        r = self.client.get(
            '/api/warehouse/',
            {'warehouse_id': wh.id, 'product_id': product.id, 'only_positive': '1'},
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, msg=r.content)
        rows = r.data if isinstance(r.data, list) else r.data.get('results', [])
        for row in rows:
            self.assertEqual(row['warehouse']['id'], wh.id)
            self.assertEqual(row['product']['id'], product.id)
            self.assertGreaterEqual(row['quantity'], 1)

    def test_transfer_order_create_requires_factory_to_local(self):
        factory_wh = WarehouseNode.objects.filter(warehouse_type='factory', name__startswith='【演示】').first()
        local_wh = WarehouseNode.objects.filter(warehouse_type='local', name__startswith='【演示】').first()
        product = Product.objects.filter(production_template_key='f116').first()
        self.assertIsNotNone(factory_wh)
        self.assertIsNotNone(local_wh)
        self.assertIsNotNone(product)
        r = self.client.post(
            '/api/transfer-orders/',
            {
                'from_warehouse_id': local_wh.id,
                'to_warehouse_id': factory_wh.id,
                'note': 'api bad route',
                'items': [{'product_id': product.id, 'color': '军绿', 'size': 'M', 'quantity': 1}],
            },
            format='json',
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST)

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
