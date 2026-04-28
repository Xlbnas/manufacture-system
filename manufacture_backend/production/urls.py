from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FactoryViewSet,
    SupplierViewSet,
    WarehouseNodeViewSet,
    MaterialViewSet,
    DyeingOrderViewSet,
    ProductViewSet,
    ProductionPlanViewSet,
    ProductionPlanDetailViewSet,
    ProductionProgressViewSet,
    WarehouseViewSet,
    TransferOrderViewSet,
)
from .views import me_view, ai_summarize_view, ai_config_view

router = DefaultRouter()
router.register(r'factories', FactoryViewSet)
router.register(r'warehouse-nodes', WarehouseNodeViewSet)
router.register(r'materials', MaterialViewSet)
router.register(r'dyeing-orders', DyeingOrderViewSet)
router.register(r'products', ProductViewSet)
router.register(r'production-plans', ProductionPlanViewSet)
router.register(r'production-plan-details', ProductionPlanDetailViewSet)
router.register(r'production-progress', ProductionProgressViewSet)
router.register(r'transfer-orders', TransferOrderViewSet)
router.register(r'warehouse', WarehouseViewSet)
router.register(r'suppliers', SupplierViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # 当前用户信息
    path('auth/me/', me_view, name='me'),
    path('ai/summarize/', ai_summarize_view, name='ai_summarize'),
    path('ai/config/', ai_config_view, name='ai_config'),
]
