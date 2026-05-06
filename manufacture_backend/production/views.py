import json
import os
import socket
import time
from decimal import Decimal
from pathlib import Path
from urllib import error, request as urlrequest

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import serializers, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    DyeingOrder,
    DyeingReceipt,
    Factory,
    Material,
    Product,
    ProductionPlan,
    ProductionPlanDetail,
    ProductionProgress,
    Supplier,
    TransferOrder,
    TransferOrderItem,
    Warehouse,
    WarehouseNode,
    WeavingOrder,
    WeavingReceipt,
)
from .serializers import (
    CompleteProductionSerializer,
    DyeingOrderSerializer,
    FactorySerializer,
    MaterialDetailSerializer,
    MaterialSerializer,
    OutsourceReceiptWriteSerializer,
    ProductSerializer,
    ProductionPlanDetailSerializer,
    ProductionPlanSerializer,
    ProductionProgressSerializer,
    SupplierSerializer,
    TransferOrderSerializer,
    WarehouseDetailSerializer,
    WarehouseNodeSerializer,
    WarehouseSerializer,
    WeavingOrderSerializer,
)
from .template_catalog import sync_template_product_rows
from .backup_utils import (
    BackupError,
    CONFIRM_RESTORE_TEXT,
    cleanup_temp_backup,
    create_temp_backup_archive,
    inspect_backup_archive,
    restore_backup_archive,
)


def _to_decimal(value):
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _apply_dyeing_receipt(order_id, qty, receipt_date, note=''):
    """事务内：登记染色到货；按本单「约定−已收」控制可收量，累加染色布库存行。

    坯布已在下单一并锁定在染厂侧理解下，不在此重复扣减材料溯源中的坯布行数量；
    仅更新本单已到货、生成/累加染色布库存。"""
    note = note or ''
    qty = _to_decimal(qty)
    with transaction.atomic():
        order = (
            DyeingOrder.objects.select_for_update()
            .select_related('raw_material', 'supplier', 'output_warehouse')
            .get(pk=order_id)
        )
        if order.status not in ('draft', 'receiving'):
            raise ValueError('当前状态不可登记到货')
        remaining = _to_decimal(order.quantity) - _to_decimal(order.received_quantity)
        if qty <= 0:
            raise ValueError('到货数量须大于 0')
        if qty > remaining:
            raise ValueError('超过可收货数量')

        raw = order.raw_material
        if order.dyed_material_id:
            Material.objects.filter(pk=order.dyed_material_id).update(
                quantity=F('quantity') + qty,
                stock_date=receipt_date,
            )
        else:
            dyed = Material.objects.create(
                type='dyed_fabric',
                name=order.output_name,
                color=order.output_color,
                quantity=qty,
                unit=raw.unit,
                stock_date=receipt_date,
                supplier=order.supplier,
                warehouse=order.output_warehouse,
                source_material=raw,
                remark=f'由染色单#{order.id}生成',
            )
            order.dyed_material_id = dyed.id

        DyeingReceipt.objects.create(
            order_id=order.id,
            quantity=qty,
            receipt_date=receipt_date,
            note=note,
        )
        new_received = _to_decimal(order.received_quantity) + qty
        order.received_quantity = new_received
        if new_received >= _to_decimal(order.quantity):
            order.status = 'completed'
        elif order.status == 'draft':
            order.status = 'receiving'
        order.save(update_fields=['received_quantity', 'status', 'dyed_material_id'])


def _apply_weaving_receipt(order_id, qty, receipt_date, note=''):
    """事务内：登记布厂到货；累加 raw_fabric 库存（合并同键行）。"""
    note = note or ''
    qty = _to_decimal(qty)
    with transaction.atomic():
        order = (
            WeavingOrder.objects.select_for_update()
            .select_related('supplier', 'inbound_warehouse')
            .get(pk=order_id)
        )
        if order.status not in ('draft', 'receiving'):
            raise ValueError('当前状态不可登记到货')
        remaining = _to_decimal(order.quantity) - _to_decimal(order.received_quantity)
        if qty <= 0:
            raise ValueError('到货数量须大于 0')
        if qty > remaining:
            raise ValueError('超过可收货数量')

        if order.raw_material_id:
            Material.objects.filter(pk=order.raw_material_id).update(
                quantity=F('quantity') + qty,
                stock_date=receipt_date,
            )
        else:
            match = (
                Material.objects.select_for_update()
                .filter(
                    type='raw_fabric',
                    name=order.fabric_name,
                    color=order.fabric_color or '',
                    warehouse_id=order.inbound_warehouse_id,
                    supplier_id=order.supplier_id,
                )
                .first()
            )
            if match:
                Material.objects.filter(pk=match.id).update(
                    quantity=F('quantity') + qty,
                    stock_date=receipt_date,
                )
                order.raw_material_id = match.id
            else:
                m = Material.objects.create(
                    type='raw_fabric',
                    name=order.fabric_name,
                    color=order.fabric_color or '',
                    quantity=qty,
                    unit=order.unit,
                    stock_date=receipt_date,
                    supplier=order.supplier,
                    warehouse=order.inbound_warehouse,
                    remark=f'由布厂单#{order.id}入库',
                )
                order.raw_material_id = m.id

        WeavingReceipt.objects.create(
            order_id=order.id,
            quantity=qty,
            receipt_date=receipt_date,
            note=note,
        )
        new_received = _to_decimal(order.received_quantity) + qty
        order.received_quantity = new_received
        if new_received >= _to_decimal(order.quantity):
            order.status = 'completed'
        elif order.status == 'draft':
            order.status = 'receiving'
        order.save(update_fields=['received_quantity', 'status', 'raw_material_id'])


def _get_stock(warehouse, product, color, size):
    stock, _ = Warehouse.objects.get_or_create(
        warehouse=warehouse,
        product=product,
        color=color or '',
        size=size or '',
        defaults={'quantity': 0}
    )
    return stock


def _plan_detail_finish_color(plan_detail):
    c = (plan_detail.cloth_color or '').strip()
    if c:
        return c[:50]
    models_json = plan_detail.models_data or []
    if isinstance(models_json, list) and models_json:
        first = models_json[0]
        if isinstance(first, dict):
            return str(first.get('color') or '').strip()[:50]
    return ''


def _planned_quantities_cell(sizes_row, model_index):
    if not isinstance(sizes_row, dict):
        return 0
    planned = sizes_row.get('quantities') or []
    if not isinstance(planned, list) or model_index >= len(planned):
        return 0
    try:
        return int(planned[model_index])
    except (TypeError, ValueError):
        return int(float(planned[model_index] or 0))


def _build_size_completion_aligned(sizes_data, size_completion):
    """与 sizes_data 按下标对齐；每项含 name、completed_quantities（长度与 quantities 一致）。"""
    sizes_data = sizes_data if isinstance(sizes_data, list) else []
    sc_in = size_completion if isinstance(size_completion, list) else []
    result = []
    for i, row in enumerate(sizes_data):
        if not isinstance(row, dict):
            result.append({'name': '', 'completed_quantities': []})
            continue
        name = str(row.get('name') or '')
        planned = row.get('quantities') or []
        if not isinstance(planned, list):
            planned = []
        n = len(planned)
        prev = sc_in[i] if i < len(sc_in) and isinstance(sc_in[i], dict) else {}
        done_raw = prev.get('completed_quantities') if isinstance(prev, dict) else None
        if not isinstance(done_raw, list):
            done_raw = []
        done_ints = []
        for j in range(n):
            if j < len(done_raw):
                try:
                    done_ints.append(max(0, int(done_raw[j])))
                except (TypeError, ValueError):
                    done_ints.append(max(0, int(float(done_raw[j] or 0))))
            else:
                done_ints.append(0)
        result.append({'name': name, 'completed_quantities': done_ints})
    return result


def _size_row_index_by_name(sizes_data):
    m = {}
    for i, row in enumerate(sizes_data or []):
        if not isinstance(row, dict):
            continue
        name = str(row.get('name') or '')
        if name and name not in m:
            m[name] = i
    return m


def _default_factory_warehouse_name_stem(factory):
    """与前端建工厂习惯一致：地区 + 车间 → 「武昌八车间」形式，再挂「工厂仓」。"""
    loc = (factory.location or '').strip()
    ws = (factory.workshop or '').strip()
    return f'{loc}{ws}车间'


def ensure_factory_warehouse_for_factory(factory):
    """
    保证每个工厂有一条启用的、且 factory 外键指向自己的工厂仓节点。
    新建工厂时在 perform_create 中调用；完工入库缺节点时由 _default_factory_warehouse 懒创建。
    """
    if factory is None:
        return None
    with transaction.atomic():
        Factory.objects.select_for_update().filter(pk=factory.pk).first()
        existing = (
            WarehouseNode.objects.filter(
                warehouse_type='factory',
                factory_id=factory.id,
                is_active=True,
            )
            .order_by('id')
            .first()
        )
        if existing:
            return existing
        stem = _default_factory_warehouse_name_stem(factory)
        name = f'{stem}工厂仓'
        resolved = name
        n = 2
        while WarehouseNode.objects.filter(name=resolved).exists():
            resolved = f'{name} ({n})'
            n += 1
        return WarehouseNode.objects.create(
            name=resolved,
            warehouse_type='factory',
            factory=factory,
        )


def _default_factory_warehouse(factory):
    if factory is None:
        return None
    return ensure_factory_warehouse_for_factory(factory)


class FactoryViewSet(viewsets.ModelViewSet):
    queryset = Factory.objects.all()
    serializer_class = FactorySerializer

    def perform_create(self, serializer):
        factory = serializer.save()
        ensure_factory_warehouse_for_factory(factory)


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer


class WarehouseNodeViewSet(viewsets.ModelViewSet):
    queryset = WarehouseNode.objects.all().order_by('-id')
    serializer_class = WarehouseNodeSerializer


class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all().order_by('-id')
    serializer_class = MaterialSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MaterialDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MaterialDetailSerializer(queryset, many=True)
        return Response(serializer.data)


class DyeingOrderViewSet(viewsets.ModelViewSet):
    queryset = DyeingOrder.objects.all().select_related(
        'raw_material', 'supplier', 'output_warehouse', 'dyed_material'
    ).prefetch_related('receipts').order_by('-id')
    serializer_class = DyeingOrderSerializer

    def perform_destroy(self, instance):
        """无到货记录时可删单，并退回建单时扣减的坯布数量。"""
        if instance.receipts.exists() or _to_decimal(instance.received_quantity) > 0:
            raise ValidationError('已有染色到货记录，不能删除该单；如需冲账请在材料溯源中手工调整。')
        with transaction.atomic():
            raw_id = instance.raw_material_id
            if raw_id:
                Material.objects.filter(pk=raw_id).update(quantity=F('quantity') + instance.quantity)
            instance.delete()

    @action(detail=True, methods=['post'], url_path='receipts')
    def receipts(self, request, pk=None):
        order = self.get_object()
        ser = OutsourceReceiptWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rd = ser.validated_data.get('receipt_date') or timezone.now().date()
        try:
            _apply_dyeing_receipt(
                order.id,
                ser.validated_data['quantity'],
                rd,
                ser.validated_data.get('note') or '',
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        return Response(DyeingOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """兼容旧流程：一次性收齐剩余数量（等价于一笔到货）。"""
        order = self.get_object()
        remaining = _to_decimal(order.quantity) - _to_decimal(order.received_quantity)
        if remaining <= 0:
            return Response({'error': '已无剩余可收货量'}, status=status.HTTP_400_BAD_REQUEST)
        if order.status not in ('draft', 'receiving'):
            return Response({'error': '当前状态不可执行'}, status=status.HTTP_400_BAD_REQUEST)
        raw_date = request.data.get('receipt_date')
        receipt_date = parse_date(str(raw_date)) if raw_date else timezone.now().date()
        if receipt_date is None:
            receipt_date = timezone.now().date()
        note = (request.data.get('note') or '').strip() or '整单收货'
        try:
            _apply_dyeing_receipt(order.id, remaining, receipt_date, note=note)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        return Response(DyeingOrderSerializer(order).data)

    @action(detail=True, methods=['post'], url_path='close-with-loss')
    def close_with_loss(self, request, pk=None):
        """剩余约定未到货部分记为产出损耗并关单，不再允许登记到货。"""

        note = str(request.data.get('note') or request.data.get('loss_note') or '').strip()
        with transaction.atomic():
            order = DyeingOrder.objects.select_for_update().get(pk=pk)
            if order.status not in ('draft', 'receiving'):
                return Response({'error': '当前状态不可执行收尾记损耗'}, status=status.HTTP_400_BAD_REQUEST)
            rem = _to_decimal(order.quantity) - _to_decimal(order.received_quantity)
            if rem <= 0:
                return Response({'error': '无剩余约定量可记为损耗'}, status=status.HTTP_400_BAD_REQUEST)
            order.lost_quantity = rem
            order.loss_note = note[:500]
            order.status = 'completed'
            order.save(update_fields=['lost_quantity', 'loss_note', 'status'])
        order.refresh_from_db()
        return Response(DyeingOrderSerializer(order).data, status=status.HTTP_200_OK)


class WeavingOrderViewSet(viewsets.ModelViewSet):
    queryset = WeavingOrder.objects.all().select_related(
        'supplier', 'inbound_warehouse', 'raw_material'
    ).prefetch_related('receipts').order_by('-id')
    serializer_class = WeavingOrderSerializer

    def perform_destroy(self, instance):
        if instance.receipts.exists() or _to_decimal(instance.received_quantity) > 0:
            raise ValidationError(
                '已有布厂到货记录，不能删除该单；如需冲账请在材料溯源中手工调整。'
            )
        instance.delete()

    @action(detail=True, methods=['post'], url_path='receipts')
    def receipts(self, request, pk=None):
        order = self.get_object()
        ser = OutsourceReceiptWriteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        rd = ser.validated_data.get('receipt_date') or timezone.now().date()
        try:
            _apply_weaving_receipt(
                order.id,
                ser.validated_data['quantity'],
                rd,
                ser.validated_data.get('note') or '',
            )
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        return Response(WeavingOrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        remaining = _to_decimal(order.quantity) - _to_decimal(order.received_quantity)
        if remaining <= 0:
            return Response({'error': '已无剩余可收货量'}, status=status.HTTP_400_BAD_REQUEST)
        if order.status not in ('draft', 'receiving'):
            return Response({'error': '当前状态不可执行'}, status=status.HTTP_400_BAD_REQUEST)
        raw_date = request.data.get('receipt_date')
        receipt_date = parse_date(str(raw_date)) if raw_date else timezone.now().date()
        if receipt_date is None:
            receipt_date = timezone.now().date()
        note = (request.data.get('note') or '').strip() or '整单收货'
        try:
            _apply_weaving_receipt(order.id, remaining, receipt_date, note=note)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        order.refresh_from_db()
        return Response(WeavingOrderSerializer(order).data)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

    def perform_destroy(self, instance):
        if Warehouse.objects.filter(product=instance).exists():
            raise ValidationError('该产品仍有成品库存行，无法删除。')
        if TransferOrderItem.objects.filter(product=instance).exists():
            raise ValidationError('该产品仍被调拨单引用，无法删除。')
        super().perform_destroy(instance)

    @action(detail=False, methods=['post'], url_path='sync-from-catalog')
    def sync_from_catalog(self, request):
        """按 template_catalog 补全缺失的模板线 Product（不覆盖已有名称）。"""
        created_keys = sync_template_product_rows()
        return Response({'created_keys': created_keys})


class ProductionPlanViewSet(viewsets.ModelViewSet):
    queryset = ProductionPlan.objects.all()
    serializer_class = ProductionPlanSerializer


class ProductionProgressViewSet(viewsets.ModelViewSet):
    queryset = ProductionProgress.objects.all()
    serializer_class = ProductionProgressSerializer


class ProductionPlanDetailViewSet(viewsets.ModelViewSet):
    queryset = ProductionPlanDetail.objects.all()
    serializer_class = ProductionPlanDetailSerializer

    def get_queryset(self):
        queryset = ProductionPlanDetail.objects.select_related('factory').all()
        date = self.request.query_params.get('date')
        plan_type = self.request.query_params.get('plan_type')
        if date:
            queryset = queryset.filter(date=date)
        if plan_type:
            queryset = queryset.filter(plan_type=plan_type)
        return queryset.order_by('-date', '-created_at')

    @action(detail=True, methods=['post'], url_path='complete-production')
    def complete_production(self, request, pk=None):
        ser = CompleteProductionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        wh_candidate = ser.validated_data.get('warehouse_id')
        lines_in = ser.validated_data['lines']
        if not lines_in:
            return Response({'error': '至少需要一行完工数量'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            plan = (
                ProductionPlanDetail.objects.select_for_update()
                .select_related('factory')
                .get(pk=pk)
            )
            product = None
            if plan.template:
                product = Product.objects.filter(production_template_key=plan.template).first()
            if product is None:
                return Response(
                    {
                        'error': (
                            '未找到与该排产模板对应的产品：请在「模板成品」页同步模板行，'
                            '或执行 python manage.py sync_template_products，确保存在该模板键的 Product。'
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            warehouse = wh_candidate or _default_factory_warehouse(plan.factory)
            if warehouse is None:
                return Response(
                    {'error': '未找到目标仓库：请为该排产选择目标工厂或在请求中传入 warehouse_id'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            color = _plan_detail_finish_color(plan)
            if not color:
                return Response(
                    {'error': '未能解析成品颜色（请填写用布颜色或在型号数据中填写颜色）'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sizes_data = plan.sizes_data if isinstance(plan.sizes_data, list) else []
            matrix = _build_size_completion_aligned(sizes_data, plan.size_completion)
            name_to_i = _size_row_index_by_name(sizes_data)

            for line in lines_in:
                sz = str(line['size_name'] or '').strip()
                mi = line['model_index']
                qty = line['qty_this_batch']
                if sz not in name_to_i:
                    return Response({'error': f'未知尺码: {sz}'}, status=status.HTTP_400_BAD_REQUEST)
                ri = name_to_i[sz]
                comp_row = matrix[ri]['completed_quantities']
                if mi < 0 or mi >= len(comp_row):
                    return Response(
                        {'error': f'尺码 {sz} 不存在型号列 {mi + 1}（与排产尺码表列数不一致）'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                row_plan = sizes_data[ri]
                planned = _planned_quantities_cell(row_plan, mi)
                cur_done = comp_row[mi]
                if cur_done + qty > planned:
                    return Response(
                        {
                            'error': (
                                f'尺码 {sz} 型号列 {mi + 1} 完工累计将超过计划'
                                f'（已 {cur_done} + 本批 {qty} > 计划 {planned}）'
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            increments = []
            for line in lines_in:
                sz = str(line['size_name'] or '').strip()
                mi = line['model_index']
                qty = line['qty_this_batch']
                ri = name_to_i[sz]
                increments.append((sz, qty, ri, mi))

            # 分批累加矩阵与库存（合并同 SKU 入库行）
            wh_key = {}

            def add_wh(size_key, add_q):
                wh_key.setdefault(size_key, 0)
                wh_key[size_key] += add_q

            for sz, qty, ri, mi in increments:
                matrix[ri]['completed_quantities'][mi] += qty
                add_wh(sz, qty)

            for size_key, add_q in wh_key.items():
                stock = _get_stock(warehouse, product, color, size_key)
                locked = Warehouse.objects.select_for_update().get(pk=stock.pk)
                locked.quantity += add_q
                locked.save(update_fields=['quantity'])

            plan.size_completion = matrix
            plan.save(update_fields=['size_completion', 'updated_at'])

        plan.refresh_from_db()
        return Response(ProductionPlanDetailSerializer(plan).data, status=status.HTTP_200_OK)


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by('-id')
    serializer_class = WarehouseSerializer

    def get_queryset(self):
        qs = Warehouse.objects.select_related('warehouse', 'product').order_by('-id')
        wid_raw = self.request.query_params.get('warehouse') or self.request.query_params.get('warehouse_id')
        pid_raw = self.request.query_params.get('product') or self.request.query_params.get('product_id')
        if wid_raw not in (None, ''):
            try:
                qs = qs.filter(warehouse_id=int(wid_raw))
            except (TypeError, ValueError):
                pass
        if pid_raw not in (None, ''):
            try:
                qs = qs.filter(product_id=int(pid_raw))
            except (TypeError, ValueError):
                pass
        only_pos = (self.request.query_params.get('only_positive') or '').lower()
        if only_pos in ('1', 'true', 'yes'):
            qs = qs.filter(quantity__gt=0)
        return qs

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = WarehouseDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = WarehouseDetailSerializer(queryset, many=True)
        return Response(serializer.data)


class TransferOrderViewSet(viewsets.ModelViewSet):
    queryset = TransferOrder.objects.all().order_by('-id')
    serializer_class = TransferOrderSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        items_data = serializer.validated_data.pop('items', [])
        with transaction.atomic():
            order = TransferOrder.objects.create(**serializer.validated_data)
            for item in items_data:
                order.items.create(**item)
        return Response(self.get_serializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        if order.status != 'draft':
            return Response({'error': '仅草稿状态可执行'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            for item in order.items.select_related('product'):
                from_stock = _get_stock(order.from_warehouse, item.product, item.color, item.size)
                if from_stock.quantity < item.quantity:
                    return Response({'error': f'库存不足: {item.product.name} {item.color}/{item.size}'}, status=status.HTTP_400_BAD_REQUEST)

            for item in order.items.select_related('product'):
                from_stock = _get_stock(order.from_warehouse, item.product, item.color, item.size)
                to_stock = _get_stock(order.to_warehouse, item.product, item.color, item.size)
                from_stock.quantity -= item.quantity
                to_stock.quantity += item.quantity
                from_stock.save(update_fields=['quantity'])
                to_stock.save(update_fields=['quantity'])

            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save(update_fields=['status', 'completed_at'])

        return Response({'message': '调拨完成'})


def _read_env_map(env_file: Path):
    data = {}
    if env_file.exists():
        for line in env_file.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _write_env_map(env_file: Path, updates: dict):
    current = _read_env_map(env_file)
    current.update(updates)
    lines = [f"{k}={v}" for k, v in current.items()]
    env_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _mask_key(key: str):
    if not key:
        return ''
    if len(key) <= 10:
        return '*' * len(key)
    return f"{key[:6]}...{key[-4:]}"


def _resolve_ai_config():
    env_file = Path(settings.BASE_DIR) / '.env'
    env_map = _read_env_map(env_file)
    api_key = (
        (settings.SILICONFLOW_API_KEY or '').strip()
        or (os.environ.get('SILICONFLOW_API_KEY', '')).strip()
        or (env_map.get('SILICONFLOW_API_KEY', '')).strip()
    )
    model = (
        (settings.SILICONFLOW_MODEL or '').strip()
        or (os.environ.get('SILICONFLOW_MODEL', '')).strip()
        or (env_map.get('SILICONFLOW_MODEL', '')).strip()
        or 'deepseek-ai/DeepSeek-V4-Flash'
    )
    api_url = (
        (settings.SILICONFLOW_API_URL or '').strip()
        or (os.environ.get('SILICONFLOW_API_URL', '')).strip()
        or (env_map.get('SILICONFLOW_API_URL', '')).strip()
        or 'https://api.siliconflow.cn/v1/chat/completions'
    )
    return api_key, model, api_url, env_file


_AI_TEMPLATE_PROMPTS = {
    'general': '请基于给定系统数据与用户问题，输出简洁清晰的中文结论。',
    'daily': '请按日报格式输出：今日关键进展、异常/风险、明日计划。',
    'weekly': '请按周报格式输出：本周完成、问题与阻塞、下周计划。',
    'risk': '请聚焦风险排查：问题清单、影响评估、优先级、建议动作。',
}


def _ai_template_instruction(template_key):
    return _AI_TEMPLATE_PROMPTS.get(template_key, _AI_TEMPLATE_PROMPTS['general'])


def _ai_build_system_context(data_scope, compact=False):
    factory_limit = 80 if compact else 200
    material_limit = 120 if compact else 300
    product_limit = 80 if compact else 200
    plan_limit = 120 if compact else 200
    warehouse_limit = 120 if compact else 300
    transfer_limit = 80 if compact else 200
    context = {}
    if data_scope in ('all', 'factory'):
        context['factories'] = list(Factory.objects.values('id', 'name', 'location', 'workshop')[:factory_limit])
    if data_scope in ('all', 'material'):
        context['materials'] = list(
            Material.objects.values('id', 'type', 'name', 'quantity', 'unit', 'stock_date').order_by('-id')[:material_limit]
        )
    if data_scope in ('all', 'product'):
        context['products'] = list(Product.objects.values('id', 'name', 'colors', 'specifications')[:product_limit])
    if data_scope in ('all', 'plan'):
        context['production_plan_details'] = list(
            ProductionPlanDetail.objects.values('id', 'date', 'plan_type', 'name', 'template', 'created_at').order_by('-created_at')[:plan_limit]
        )
    if data_scope in ('all', 'warehouse'):
        context['warehouse'] = list(
            Warehouse.objects.values('id', 'product_id', 'color', 'size', 'quantity', 'warehouse_id').order_by('-id')[:warehouse_limit]
        )
    if data_scope in ('all', 'outbound'):
        context['transfer_orders'] = list(
            TransferOrder.objects.values(
                'id',
                'from_warehouse__name',
                'to_warehouse__name',
                'status',
                'note',
                'created_at',
                'completed_at',
            ).order_by('-id')[:transfer_limit]
        )
    summary = {
        'factory_count': Factory.objects.count(),
        'material_count': Material.objects.count(),
        'product_count': Product.objects.count(),
        'plan_detail_count': ProductionPlanDetail.objects.count(),
        'warehouse_record_count': Warehouse.objects.count(),
        'transfer_order_count': TransferOrder.objects.count(),
    }
    return {'summary': summary, 'scope': data_scope, 'compact': compact, 'data': context}


def _ai_build_user_payload(query, content, data_scope, compact):
    system_context = _ai_build_system_context(data_scope, compact=compact)
    return {
        '用户问题': query or '请根据数据进行总结',
        '用户补充文本': content or '',
        '系统数据上下文': system_context,
        '输出要求': '请使用简体中文，结构化输出，避免编造不存在的数据。',
    }


def _ai_build_api_payload(model, query, content, data_scope, template_key, compact=False, stream=False):
    prompt = _ai_template_instruction(template_key)
    user_payload = _ai_build_user_payload(query, content, data_scope, compact)
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': f'你是工厂管理系统的数据分析助手。{prompt}'},
            {'role': 'user', 'content': json.dumps(user_payload, ensure_ascii=False, default=str)},
        ],
        'temperature': 0.2 if compact else 0.3,
        'max_tokens': 900 if compact else 1200,
    }
    if stream:
        payload['stream'] = True
    return payload


def _ai_extract_summary_from_body(body):
    if not isinstance(body, dict):
        return '', None
    choices = body.get('choices') or []
    if not choices:
        return '', None
    c0 = choices[0] or {}
    msg = c0.get('message') or {}
    raw = msg.get('content')
    if raw is None:
        text = ''
    elif isinstance(raw, str):
        text = raw.strip()
    elif isinstance(raw, list):
        parts = []
        for p in raw:
            if isinstance(p, dict) and p.get('type') == 'text':
                parts.append((p.get('text') or '').strip())
            elif isinstance(p, str):
                parts.append(p.strip())
        text = '\n'.join(x for x in parts if x).strip()
    else:
        text = str(raw).strip()
    return text, c0.get('finish_reason')


def _ai_call_sync_json(api_url, api_key, api_payload):
    req = urlrequest.Request(
        api_url,
        data=json.dumps(api_payload, default=str).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urlrequest.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _ai_sse_pack(obj):
    return f'data: {json.dumps(obj, ensure_ascii=False, default=str)}\n\n'


def _ai_upstream_stream_events(api_url, api_key, api_payload, read_timeout=300):
    """Yields slim SSE lines: {\"t\": text}, {\"e\": msg}, then {\"d\": true} in finally.

    SiliconFlow / 部分推理模型可能在较长时间内只通过 delta.reasoning_content 推流，
    content 为空；若只转发 content 则前端长时间无数据直至超时。
    """
    try:
        req = urlrequest.Request(
            api_url,
            data=json.dumps(api_payload, default=str).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Accept': 'text/event-stream',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urlrequest.urlopen(req, timeout=read_timeout) as resp:
            while True:
                raw_line = resp.readline()
                if not raw_line:
                    break
                line = raw_line.decode('utf-8', errors='replace').strip()
                if not line or line.startswith(':'):
                    continue
                if not line.startswith('data:'):
                    continue
                data_str = line[5:].lstrip()
                if data_str == '[DONE]':
                    break
                try:
                    obj = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict) and obj.get('error'):
                    err = obj['error']
                    if isinstance(err, dict):
                        err = err.get('message') or json.dumps(err, ensure_ascii=False)
                    yield _ai_sse_pack({'e': str(err)})
                    return
                choices = obj.get('choices') or []
                if not choices:
                    continue
                delta = (choices[0] or {}).get('delta') or {}
                if not isinstance(delta, dict):
                    continue
                piece = delta.get('content')
                if piece is None:
                    piece = ''
                elif not isinstance(piece, str):
                    piece = str(piece)
                reasoning = delta.get('reasoning_content')
                if reasoning is None:
                    reasoning = ''
                elif not isinstance(reasoning, str):
                    reasoning = str(reasoning)
                if piece:
                    yield _ai_sse_pack({'t': piece})
                elif reasoning:
                    yield _ai_sse_pack({'t': reasoning})
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        yield _ai_sse_pack({'e': detail or str(exc.reason)})
    except (socket.timeout, TimeoutError):
        yield _ai_sse_pack({'e': 'AI 服务超时，请缩小数据范围后重试'})
    except Exception as exc:
        yield _ai_sse_pack({'e': str(exc)})
    finally:
        yield _ai_sse_pack({'d': True})


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """获取当前用户信息"""
    return Response({
        'user': UserSerializer(request.user).data
    })


def _require_superuser(request):
    if not request.user.is_superuser:
        return Response({'error': '仅超级管理员可执行系统备份操作'}, status=status.HTTP_403_FORBIDDEN)
    return None


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def backup_export_view(request):
    denied = _require_superuser(request)
    if denied:
        return denied

    archive_path = create_temp_backup_archive()
    try:
        data = archive_path.read_bytes()
    finally:
        cleanup_temp_backup(archive_path)

    response = HttpResponse(data, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{archive_path.name}"'
    response['Cache-Control'] = 'no-store'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backup_inspect_view(request):
    denied = _require_superuser(request)
    if denied:
        return denied

    upload = request.FILES.get('file')
    if not upload:
        return Response({'error': '请上传备份文件'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        info = inspect_backup_archive(upload)
    except BackupError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    return Response(info)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def backup_restore_view(request):
    denied = _require_superuser(request)
    if denied:
        return denied

    confirm_text = (request.data.get('confirm_text') or '').strip()
    if confirm_text != CONFIRM_RESTORE_TEXT:
        return Response({'error': f'请输入确认文本：{CONFIRM_RESTORE_TEXT}'}, status=status.HTTP_400_BAD_REQUEST)

    upload = request.FILES.get('file')
    if not upload:
        return Response({'error': '请上传备份文件'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = restore_backup_archive(upload)
    except BackupError as exc:
        return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return Response({'error': f'恢复失败，已尝试回滚: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_summarize_view(request):
    query = (request.data.get('query') or '').strip()
    content = (request.data.get('content') or '').strip()
    template_key = (request.data.get('template_key') or 'general').strip()
    data_scope = (request.data.get('data_scope') or 'all').strip()

    if not query and not content:
        return Response({'error': '请至少提供查询问题或待总结文本'}, status=status.HTTP_400_BAD_REQUEST)

    api_key, model, api_url, _ = _resolve_ai_config()

    if not api_key:
        return Response({'error': '服务端未配置 AI API Key'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    payload_full = _ai_build_api_payload(model, query, content, data_scope, template_key, compact=False, stream=False)
    payload_compact = _ai_build_api_payload(model, query, content, data_scope, template_key, compact=True, stream=False)
    body = None
    summary = ''
    finish_reason = None
    attempted_compact = False

    def try_compact_after_failure(reason_http=None):
        nonlocal body, summary, finish_reason, attempted_compact
        attempted_compact = True
        if reason_http == 429:
            time.sleep(0.6)
        try:
            body = _ai_call_sync_json(api_url, api_key, payload_compact)
            summary, finish_reason = _ai_extract_summary_from_body(body)
        except error.HTTPError as exc2:
            detail2 = exc2.read().decode('utf-8', errors='ignore')
            raise RuntimeError(detail2 or exc2.reason) from exc2
        except (socket.timeout, TimeoutError) as exc2:
            raise TimeoutError from exc2

    try:
        body = _ai_call_sync_json(api_url, api_key, payload_full)
        summary, finish_reason = _ai_extract_summary_from_body(body)
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        if exc.code in (429, 502, 503, 504):
            try:
                try_compact_after_failure(reason_http=exc.code)
            except TimeoutError:
                return Response(
                    {'error': 'AI 服务超时，请重试或缩小数据范围（如选择“出库/仓库”）'},
                    status=status.HTTP_504_GATEWAY_TIMEOUT,
                )
            except Exception as exc2:
                return Response(
                    {'error': f'AI 服务调用失败（已用压缩数据重试）: {detail or exc.reason}；重试错误: {exc2}'},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
        else:
            return Response({'error': f'AI 服务调用失败: {detail or exc.reason}'}, status=status.HTTP_502_BAD_GATEWAY)
    except (socket.timeout, TimeoutError):
        try:
            try_compact_after_failure()
        except TimeoutError:
            return Response(
                {'error': 'AI 服务超时，请重试或缩小数据范围（如选择“出库/仓库”）'},
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        except Exception as exc:
            return Response({'error': f'AI 服务调用异常: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)
    except Exception as exc:
        return Response({'error': f'AI 服务调用异常: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

    if not summary and body is not None and not attempted_compact:
        try:
            try_compact_after_failure()
        except Exception:
            pass

    if not summary:
        hint = '请重试或缩小数据范围（如选择“出库/仓库”）。'
        if finish_reason:
            return Response(
                {'error': f'AI 服务返回为空（finish_reason={finish_reason}），{hint}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response({'error': f'AI 服务返回为空，{hint}'}, status=status.HTTP_502_BAD_GATEWAY)

    return Response({'summary': summary, 'used_scope': data_scope, 'template_key': template_key}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ai_summarize_stream_view(request):
    query = (request.data.get('query') or '').strip()
    content = (request.data.get('content') or '').strip()
    template_key = (request.data.get('template_key') or 'general').strip()
    data_scope = (request.data.get('data_scope') or 'all').strip()

    if not query and not content:
        return Response({'error': '请至少提供查询问题或待总结文本'}, status=status.HTTP_400_BAD_REQUEST)

    api_key, model, api_url, _ = _resolve_ai_config()

    if not api_key:
        return Response({'error': '服务端未配置 AI API Key'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    stream_payload = _ai_build_api_payload(
        model, query, content, data_scope, template_key, compact=False, stream=True
    )
    stream = StreamingHttpResponse(
        _ai_upstream_stream_events(api_url, api_key, stream_payload),
        content_type='text/event-stream; charset=utf-8',
    )
    stream['Cache-Control'] = 'no-cache'
    stream['X-Accel-Buffering'] = 'no'
    return stream


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def ai_config_view(request):
    if request.method == 'GET':
        api_key, model, api_url, _ = _resolve_ai_config()
        return Response({
            'key_configured': bool(api_key),
            'masked_key': _mask_key(api_key),
            'model': model,
            'api_url': api_url,
        })

    # 只有 staff 用户允许改写配置
    if not request.user.is_staff:
        return Response({'error': '仅管理员可修改 AI 配置'}, status=status.HTTP_403_FORBIDDEN)

    api_key = (request.data.get('api_key') or '').strip()
    model = (request.data.get('model') or '').strip() or 'deepseek-ai/DeepSeek-V4-Flash'
    api_url = (request.data.get('api_url') or '').strip() or 'https://api.siliconflow.cn/v1/chat/completions'

    if not api_key:
        return Response({'error': 'API Key 不能为空'}, status=status.HTTP_400_BAD_REQUEST)

    _, _, _, env_file = _resolve_ai_config()
    _write_env_map(env_file, {
        'SILICONFLOW_API_KEY': api_key,
        'SILICONFLOW_MODEL': model,
        'SILICONFLOW_API_URL': api_url,
    })

    # 同步进当前进程环境，避免必须重启
    os.environ['SILICONFLOW_API_KEY'] = api_key
    os.environ['SILICONFLOW_MODEL'] = model
    os.environ['SILICONFLOW_API_URL'] = api_url

    return Response({
        'message': 'AI 配置已更新',
        'key_configured': True,
        'masked_key': _mask_key(api_key),
        'model': model,
        'api_url': api_url,
    })

