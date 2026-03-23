from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FactoryViewSet, MaterialViewSet, ProductViewSet, ProductionPlanViewSet, ProductionPlanDetailViewSet, ProductionProgressViewSet, OutboundRecordViewSet, WarehouseViewSet, SupplierViewSet
from .views import login_view, refresh_view, logout_view, me_view

router = DefaultRouter()
router.register(r'factories', FactoryViewSet)
router.register(r'materials', MaterialViewSet)
router.register(r'products', ProductViewSet)
router.register(r'production-plans', ProductionPlanViewSet)
router.register(r'production-plan-details', ProductionPlanDetailViewSet)
router.register(r'production-progress', ProductionProgressViewSet)
router.register(r'outbound-records', OutboundRecordViewSet)
router.register(r'warehouse', WarehouseViewSet)
router.register(r'suppliers', SupplierViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # 认证相关 URL
    path('auth/login/', login_view, name='login'),
    path('auth/refresh/', refresh_view, name='refresh'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/me/', me_view, name='me'),
]
