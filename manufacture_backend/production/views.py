import json
import os
import socket
from decimal import Decimal
from pathlib import Path
from urllib import error, request as urlrequest

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import (
    DyeingOrder,
    Factory,
    Material,
    Product,
    ProductionPlan,
    ProductionPlanDetail,
    ProductionProgress,
    Supplier,
    TransferOrder,
    Warehouse,
    WarehouseNode,
)
from .serializers import (
    DyeingOrderSerializer,
    FactorySerializer,
    MaterialDetailSerializer,
    MaterialSerializer,
    ProductSerializer,
    ProductionPlanDetailSerializer,
    ProductionPlanSerializer,
    ProductionProgressSerializer,
    SupplierSerializer,
    TransferOrderSerializer,
    WarehouseDetailSerializer,
    WarehouseNodeSerializer,
    WarehouseSerializer,
)
from .backup_utils import (
    BackupError,
    CONFIRM_RESTORE_TEXT,
    cleanup_temp_backup,
    create_temp_backup_archive,
    inspect_backup_archive,
    restore_backup_archive,
)


def _get_stock(warehouse, product, color, size):
    stock, _ = Warehouse.objects.get_or_create(
        warehouse=warehouse,
        product=product,
        color=color or '',
        size=size or '',
        defaults={'quantity': 0}
    )
    return stock


class FactoryViewSet(viewsets.ModelViewSet):
    queryset = Factory.objects.all()
    serializer_class = FactorySerializer


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
    queryset = DyeingOrder.objects.all().order_by('-id')
    serializer_class = DyeingOrderSerializer

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        order = self.get_object()
        if order.status != 'draft':
            return Response({'error': '仅草稿状态可执行'}, status=status.HTTP_400_BAD_REQUEST)
        if order.raw_material.quantity < order.quantity:
            return Response({'error': '坯布库存不足'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            Material.objects.filter(pk=order.raw_material_id).update(quantity=F('quantity') - order.quantity)
            dyed = Material.objects.create(
                type='dyed_fabric',
                name=order.output_name,
                color=order.output_color,
                quantity=order.quantity,
                unit=order.raw_material.unit,
                stock_date=timezone.now().date(),
                supplier=order.supplier,
                warehouse=order.output_warehouse,
                source_material=order.raw_material,
                remark=f'由染色单#{order.id}生成'
            )
            order.status = 'completed'
            order.dyed_material = dyed
            order.save(update_fields=['status', 'dyed_material'])

        return Response({'message': '染色完成', 'dyed_material_id': dyed.id})


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


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
        queryset = ProductionPlanDetail.objects.all()
        date = self.request.query_params.get('date')
        plan_type = self.request.query_params.get('plan_type')
        if date:
            queryset = queryset.filter(date=date)
        if plan_type:
            queryset = queryset.filter(plan_type=plan_type)
        return queryset.order_by('-date', '-created_at')


class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all().order_by('-id')
    serializer_class = WarehouseSerializer

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

    template_prompts = {
        'general': "请基于给定系统数据与用户问题，输出简洁清晰的中文结论。",
        'daily': "请按日报格式输出：今日关键进展、异常/风险、明日计划。",
        'weekly': "请按周报格式输出：本周完成、问题与阻塞、下周计划。",
        'risk': "请聚焦风险排查：问题清单、影响评估、优先级、建议动作。",
    }
    prompt = template_prompts.get(template_key, template_prompts['general'])

    def build_system_context(scope, compact=False):
        factory_limit = 80 if compact else 200
        material_limit = 120 if compact else 300
        product_limit = 80 if compact else 200
        plan_limit = 120 if compact else 200
        warehouse_limit = 120 if compact else 300
        context = {}
        if scope in ('all', 'factory'):
            context['factories'] = list(Factory.objects.values('id', 'name', 'location', 'workshop')[:factory_limit])
        if scope in ('all', 'material'):
            context['materials'] = list(
                Material.objects.values('id', 'type', 'name', 'quantity', 'unit', 'stock_date').order_by('-id')[:material_limit]
            )
        if scope in ('all', 'product'):
            context['products'] = list(Product.objects.values('id', 'name', 'colors', 'specifications')[:product_limit])
        if scope in ('all', 'plan'):
            context['production_plan_details'] = list(
                ProductionPlanDetail.objects.values('id', 'date', 'plan_type', 'name', 'template', 'created_at').order_by('-created_at')[:plan_limit]
            )
        if scope in ('all', 'warehouse'):
            context['warehouse'] = list(
                Warehouse.objects.values('id', 'product_id', 'color', 'size', 'quantity', 'warehouse_id').order_by('-id')[:warehouse_limit]
            )
        summary = {
            'factory_count': Factory.objects.count(),
            'material_count': Material.objects.count(),
            'product_count': Product.objects.count(),
            'plan_detail_count': ProductionPlanDetail.objects.count(),
            'warehouse_record_count': Warehouse.objects.count(),
        }
        return {'summary': summary, 'scope': scope, 'compact': compact, 'data': context}

    def build_user_payload(compact=False):
        system_context = build_system_context(data_scope, compact=compact)
        return {
            '用户问题': query or '请根据数据进行总结',
            '用户补充文本': content or '',
            '系统数据上下文': system_context,
            '输出要求': '请使用简体中文，结构化输出，避免编造不存在的数据。',
        }

    user_payload = build_user_payload(compact=False)
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': f"你是工厂管理系统的数据分析助手。{prompt}"},
            {'role': 'user', 'content': json.dumps(user_payload, ensure_ascii=False)},
        ],
        'temperature': 0.3,
        'max_tokens': 1200,
    }

    def call_ai(api_payload):
        req = urlrequest.Request(
            api_url,
            data=json.dumps(api_payload).encode('utf-8'),
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            method='POST',
        )
        with urlrequest.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode('utf-8'))

    try:
        body = call_ai(payload)
    except error.HTTPError as exc:
        detail = exc.read().decode('utf-8', errors='ignore')
        return Response({'error': f'AI 服务调用失败: {detail or exc.reason}'}, status=status.HTTP_502_BAD_GATEWAY)
    except (socket.timeout, TimeoutError):
        # 超时后使用压缩上下文重试一次
        compact_payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': f"你是工厂管理系统的数据分析助手。{prompt}"},
                {'role': 'user', 'content': json.dumps(build_user_payload(compact=True), ensure_ascii=False)},
            ],
            'temperature': 0.2,
            'max_tokens': 900,
        }
        try:
            body = call_ai(compact_payload)
        except Exception:
            return Response({'error': 'AI 服务超时，请重试或缩小数据范围（如选择“出库/仓库”）'}, status=status.HTTP_504_GATEWAY_TIMEOUT)
    except Exception as exc:
        return Response({'error': f'AI 服务调用异常: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

    summary = ''
    choices = body.get('choices') or []
    if choices:
        summary = ((choices[0] or {}).get('message') or {}).get('content', '').strip()
    if not summary:
        return Response({'error': 'AI 服务返回为空'}, status=status.HTTP_502_BAD_GATEWAY)

    return Response({'summary': summary, 'used_scope': data_scope, 'template_key': template_key}, status=status.HTTP_200_OK)


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

