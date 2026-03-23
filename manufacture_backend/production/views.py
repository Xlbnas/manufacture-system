from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Factory, Material, Product, ProductionPlan, ProductionPlanDetail, ProductionProgress, OutboundRecord, Warehouse, Supplier
from .serializers import FactorySerializer, MaterialSerializer, ProductSerializer, ProductionPlanSerializer, ProductionPlanDetailSerializer, ProductionProgressSerializer, OutboundRecordSerializer, WarehouseSerializer, WarehouseDetailSerializer, SupplierSerializer, MaterialDetailSerializer

class FactoryViewSet(viewsets.ModelViewSet):
    queryset = Factory.objects.all()
    serializer_class = FactorySerializer

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer

class MaterialViewSet(viewsets.ModelViewSet):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MaterialDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MaterialDetailSerializer(queryset, many=True)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class ProductionPlanViewSet(viewsets.ModelViewSet):
    queryset = ProductionPlan.objects.all()
    serializer_class = ProductionPlanSerializer

class ProductionProgressViewSet(viewsets.ModelViewSet):
    queryset = ProductionProgress.objects.all()
    serializer_class = ProductionProgressSerializer

class OutboundRecordViewSet(viewsets.ModelViewSet):
    queryset = OutboundRecord.objects.all()
    serializer_class = OutboundRecordSerializer
    
    @action(detail=True, methods=['post'])
    def revoke(self, request, pk=None):
        """撤回出库记录并返还库存"""
        try:
            record = self.get_object()
            
            # 查找对应的仓库库存记录
            warehouse_item = Warehouse.objects.filter(
                factory__name=record.warehouse,
                product=record.product,
                color=record.color,
                size=record.size
            ).first()
            
            if warehouse_item:
                # 返还库存
                warehouse_item.quantity += record.quantity
                warehouse_item.save()
            
            # 删除出库记录
            record.delete()
            
            return Response({'message': '撤回成功，库存已返还'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class WarehouseViewSet(viewsets.ModelViewSet):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = WarehouseDetailSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = WarehouseDetailSerializer(queryset, many=True)
        return Response(serializer.data)

class ProductionPlanDetailViewSet(viewsets.ModelViewSet):
    queryset = ProductionPlanDetail.objects.all()
    serializer_class = ProductionPlanDetailSerializer
    
    def get_queryset(self):
        queryset = ProductionPlanDetail.objects.all()
        date = self.request.query_params.get('date', None)
        plan_type = self.request.query_params.get('plan_type', None)
        
        if date:
            queryset = queryset.filter(date=date)
        if plan_type:
            queryset = queryset.filter(plan_type=plan_type)
            
        return queryset.order_by('-date', '-created_at')


# 认证相关视图
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework import serializers

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """用户登录视图"""
    username = request.data.get('username')
    password = request.data.get('password')
    remember_me = request.data.get('remember_me', False)
    
    if not username or not password:
        return Response({
            'error': '请输入用户名和密码'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = authenticate(username=username, password=password)
    
    if user is None:
        return Response({
            'error': '用户名或密码错误'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    # 生成 JWT 令牌
    refresh = RefreshToken.for_user(user)
    
    # 根据 remember_me 设置刷新令牌有效期
    if remember_me:
        # 30 天有效期
        refresh.set_exp(lifetime=timedelta(days=30))
    else:
        # 7 天有效期
        refresh.set_exp(lifetime=timedelta(days=7))
    
    response = Response({
        'user': UserSerializer(user).data,
        'access': str(refresh.access_token),
        'message': '登录成功'
    })
    
    # 设置刷新令牌到 HttpOnly Cookie
    response.set_cookie(
        'refresh_token',
        str(refresh),
        httponly=True,
        samesite='Lax',
        max_age=30 * 24 * 60 * 60 if remember_me else 7 * 24 * 60 * 60
    )
    
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    """刷新访问令牌视图"""
    refresh_token = request.COOKIES.get('refresh_token')
    
    if not refresh_token:
        return Response({
            'error': '未提供刷新令牌'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        return Response({
            'access': access_token,
            'message': '令牌刷新成功'
        })
    except Exception as e:
        return Response({
            'error': '刷新令牌无效或已过期'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """用户登出视图"""
    refresh_token = request.COOKIES.get('refresh_token')
    
    if refresh_token:
        try:
            refresh = RefreshToken(refresh_token)
            refresh.blacklist()  # 将令牌加入黑名单
        except Exception:
            pass  # 即使黑名单失败也继续清除 Cookie
    
    response = Response({
        'message': '登出成功'
    })
    
    # 清除刷新令牌 Cookie
    response.delete_cookie('refresh_token')
    
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """获取当前用户信息"""
    return Response({
        'user': UserSerializer(request.user).data
    })

